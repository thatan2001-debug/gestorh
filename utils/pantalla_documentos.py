"""
Dashboard y pantalla unificada de generación de documentos para Gestor RH IA.
Integra: métricas reales, catálogo de documentos, historial y generación.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime
import zipfile, io

from utils.documentos_catalogo import (
    CATALOGO, CATEGORIAS_ORDEN, obtener_por_categoria,
    plan_permite, TOTAL_DOCUMENTOS, IMPLEMENTADOS,
)
from utils.historial import registrar, obtener, stats_mes, NOMBRES_DOCUMENTO
from utils.empleados_db import empleados_listar, empleados_stats, empleados_buscar
from utils.plan_control import (
    PLANES, plan_permite_documento, docs_restantes_totales,
    link_whatsapp_plan, DISCLAIMER_DOCUMENTOS, DISCLAIMER_LIQUIDACIONES,
)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def pantalla_dashboard(usuario: dict):
    """Dashboard principal con métricas reales del usuario."""
    email = usuario["email"]
    plan  = usuario.get("plan", "gratuito")
    nombre = usuario.get("nombre","").split()[0]

    # Métricas
    emp_stats  = empleados_stats(email)
    hist_stats = stats_mes(email)
    docs_usados = usuario.get("documentos_usados", 0)
    docs_mes    = hist_stats.get("total_mes", 0)
    restantes   = docs_restantes_totales(plan, docs_usados)

    st.markdown(f"# Bienvenido, {nombre} 👋")
    st.caption(f"Plan **{PLANES[plan]['nombre']}** · {PLANES[plan]['precio_fmt']}/mes")
    st.divider()

    # ── Métricas principales ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Empleados activos",    emp_stats["activos"],
              delta=f"{emp_stats['total']} en total")
    c2.metric("📄 Documentos este mes",  docs_mes)
    c3.metric("📊 Total generados",      docs_usados)
    if restantes is not None:
        c4.metric("📋 Restantes en plan", restantes,
                  delta="⚠️ Casi al límite" if restantes < 5 else None,
                  delta_color="inverse" if restantes < 5 else "normal")
    else:
        c4.metric("📋 Documentos", "Ilimitados", delta="Plan activo")

    st.divider()

    # ── Accesos rápidos ───────────────────────────────────────────────────────
    st.markdown("### ⚡ Accesos rápidos")
    cc1, cc2, cc3, cc4 = st.columns(4)

    with cc1:
        st.markdown("""
        <div style='background:#EFF6FF;border-radius:10px;padding:16px;
            text-align:center;cursor:pointer'>
            <div style='font-size:1.8rem'>📋</div>
            <div style='font-size:.85rem;font-weight:600;color:#1B3F6E;margin-top:6px'>
                Certificado Laboral</div>
            <div style='font-size:.75rem;color:#6B7280'>El más solicitado</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Generar", key="dash_cert", use_container_width=True):
            st.session_state["doc_preseleccionado"] = "certificado_con_salario"
            st.session_state["ir_a"] = "⚡  Generar docs"
            st.rerun()

    with cc2:
        st.markdown("""
        <div style='background:#ECFDF5;border-radius:10px;padding:16px;
            text-align:center;cursor:pointer'>
            <div style='font-size:1.8rem'>🏖️</div>
            <div style='font-size:.85rem;font-weight:600;color:#064E3B;margin-top:6px'>
                Carta Vacaciones</div>
            <div style='font-size:.75rem;color:#6B7280'>Art. 186 CST</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Generar", key="dash_vac", use_container_width=True):
            st.session_state["doc_preseleccionado"] = "carta_vacaciones"
            st.session_state["ir_a"] = "⚡  Generar docs"
            st.rerun()

    with cc3:
        st.markdown("""
        <div style='background:#FEF3C7;border-radius:10px;padding:16px;
            text-align:center;cursor:pointer'>
            <div style='font-size:1.8rem'>💰</div>
            <div style='font-size:.85rem;font-weight:600;color:#92400E;margin-top:6px'>
                Liquidación</div>
            <div style='font-size:.75rem;color:#6B7280'>Con paz y salvo</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Generar", key="dash_liq",
                     use_container_width=True,
                     disabled=not plan_permite(plan, "pro")):
            st.session_state["doc_preseleccionado"] = "liquidacion_prestaciones"
            st.session_state["ir_a"] = "⚡  Generar docs"
            st.rerun()

    with cc4:
        st.markdown("""
        <div style='background:#F5F3FF;border-radius:10px;padding:16px;
            text-align:center;cursor:pointer'>
            <div style='font-size:1.8rem'>👥</div>
            <div style='font-size:.85rem;font-weight:600;color:#4C1D95;margin-top:6px'>
                Mis Empleados</div>
            <div style='font-size:.75rem;color:#6B7280'>{} activos</div>
        </div>""".format(emp_stats["activos"]), unsafe_allow_html=True)
        if st.button("Ver", key="dash_emp", use_container_width=True):
            st.session_state["ir_a"] = "👥  Empleados"
            st.rerun()

    st.divider()

    # ── Historial reciente ────────────────────────────────────────────────────
    st.markdown("### 📋 Documentos recientes")
    historial = obtener(email, limite=8)
    if not historial:
        st.info("Aún no has generado documentos. ¡Comienza ahora desde 'Generar docs'!")
    else:
        for h in historial:
            tipo_fmt  = NOMBRES_DOCUMENTO.get(h.get("tipo_documento",""), h.get("tipo_documento",""))
            empleado  = h.get("empleado_nombre","—")
            fecha     = str(h.get("generado_en",""))[:10]
            enviado   = "📧 " if h.get("enviado_correo") else ""
            estado    = h.get("estado","generado")
            badge_col = {"generado":"#DBEAFE","enviado":"#D1FAE5",
                         "firmado":"#FEF3C7","anulado":"#FEE2E2"}.get(estado,"#F3F4F6")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;padding:8px 12px;border-radius:8px;'
                f'background:#F8FAFC;margin-bottom:4px;font-size:.85rem">'
                f'<span><b>{tipo_fmt}</b> · {empleado}</span>'
                f'<span style="display:flex;gap:8px;align-items:center">'
                f'{enviado}'
                f'<span style="background:{badge_col};padding:2px 8px;'
                f'border-radius:12px;font-size:.75rem">{estado}</span>'
                f'<span style="color:#9CA3AF">{fecha}</span>'
                f'</span></div>',
                unsafe_allow_html=True)

    st.divider()
    # Aviso si plan gratuito cerca del límite
    if restantes is not None and restantes <= 3:
        st.warning(
            f"⚠️ Te quedan **{restantes} documento(s)** en el plan gratuito. "
            f"Actualiza para seguir generando sin límites."
        )
        st.link_button(
            "💬 Actualizar plan por WhatsApp",
            link_whatsapp_plan("basico"),
        )


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA UNIFICADA DE GENERACIÓN DE DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════

def pantalla_generar(usuario: dict, datos_empresa: dict):
    """
    Pantalla unificada de generación de documentos.
    1. Selección del tipo de documento (catálogo)
    2. Búsqueda y selección de empleados
    3. Configuración por empleado
    4. Generación y descarga/envío
    """
    email = usuario["email"]
    plan  = usuario.get("plan","gratuito")

    st.markdown("# ⚡ Generar documentos")

    if not datos_empresa.get("nombre") or not datos_empresa.get("nit"):
        st.error("⚠️ Completa los **datos de tu empresa** primero (sección 🏢 Mi empresa).")
        st.stop()

    # ── PASO 1: Selección del tipo de documento ─────────────────────────────
    st.markdown("### Paso 1 — ¿Qué documento necesitas?")

    # Preselección desde dashboard
    presel = st.session_state.pop("doc_preseleccionado", None)

    # Auto-cargar empleado si viene de acción rápida
    emp_rapido = st.session_state.pop("accion_rapida_empleado", None)
    if emp_rapido and presel:
        # Inicializar carrito si no existe
        if "carrito_docs" not in st.session_state:
            st.session_state.carrito_docs = {}
        # Agregar el empleado con el tipo de documento pre-seleccionado
        doc_e = emp_rapido.get("documento","")
        st.session_state.carrito_docs[doc_e] = {
            "empleado": emp_rapido,
            "tipo_doc": presel,
            "config":   _config_default(emp_rapido, presel),
        }
        st.success(
            f"✅ Empleado **{emp_rapido.get('nombre','')}** cargado. "
            f"Configura los detalles y genera."
        )

    categorias = obtener_por_categoria()
    tipo_seleccionado = st.session_state.get("tipo_doc_sel", presel or "certificado_con_salario")

    # Mostrar catálogo por categoría
    for cat in CATEGORIAS_ORDEN:
        docs_cat = categorias.get(cat, [])
        if not docs_cat:
            continue

        # Filtrar solo los del plan actual o implementados
        docs_visibles = [
            d for d in docs_cat
            if d["implementado"] or plan_permite(plan, d["plan_minimo"])
        ]
        if not docs_visibles:
            continue

        with st.expander(f"**{cat}** ({len(docs_cat)} documentos)", expanded=(cat == "Certificados")):
            cols = st.columns(3)
            for i, doc in enumerate(docs_cat):
                col = cols[i % 3]
                doc_id   = doc["id"]
                habilitado = doc["implementado"] and plan_permite(plan, doc["plan_minimo"])
                es_prox  = not doc["implementado"]
                seleccionado = tipo_seleccionado == doc_id

                borde  = "#2D6BE4" if seleccionado else ("#E5E7EB" if habilitado else "#F3F4F6")
                fondo  = "#EFF6FF" if seleccionado else ("#FFFFFF" if habilitado else "#F9FAFB")
                color_txt = "#111827" if habilitado else "#9CA3AF"
                badge_txt = "🔜 Próx." if es_prox else (
                    f"Plan {doc['plan_minimo'].capitalize()}" if not plan_permite(plan, doc["plan_minimo"]) else ""
                )

                with col:
                    st.markdown(f"""
                    <div style="border:2px solid {borde};border-radius:10px;
                        background:{fondo};padding:12px;margin-bottom:8px;
                        {'opacity:.6' if not habilitado else ''}">
                        <div style="font-size:1.4rem">{doc['icono']}</div>
                        <div style="font-size:.82rem;font-weight:600;
                            color:{color_txt};margin:4px 0">{doc['nombre']}</div>
                        {f'<div style="font-size:.7rem;color:#6B7280">{badge_txt}</div>' if badge_txt else ''}
                    </div>""", unsafe_allow_html=True)

                    lbl = "✓ Seleccionado" if seleccionado else ("Seleccionar" if habilitado else "🔒 Requiere plan")
                    btn_type = "primary" if seleccionado else "secondary"

                    if habilitado:
                        if st.button(lbl, key=f"sel_{doc_id}",
                                     use_container_width=True, type=btn_type):
                            st.session_state["tipo_doc_sel"] = doc_id
                            st.rerun()
                    else:
                        st.button(lbl, key=f"sel_{doc_id}",
                                  use_container_width=True, disabled=True)

    doc_info = CATALOGO.get(tipo_seleccionado, {})
    if not doc_info:
        st.stop()

    st.success(f"✅ Documento seleccionado: **{doc_info['nombre']}**")
    if doc_info.get("disclaimer"):
        st.warning(f"⚖️ {doc_info['disclaimer']}")

    st.divider()

    # ── PASO 2: Búsqueda de empleados ──────────────────────────────────────
    st.markdown("### Paso 2 — Selecciona los empleados")

    termino = st.text_input("🔍 Buscar por nombre, documento o cargo",
        placeholder="Escribe para buscar...", key="gen_busq")
    resultados = empleados_buscar(email, termino) if termino else empleados_listar(email)

    if not resultados:
        st.info("No hay empleados. Ve a **👥 Empleados** para agregar o importar.")
        st.stop()

    # Carrito de generación
    if "carrito_docs" not in st.session_state:
        st.session_state.carrito_docs = {}

    carrito = st.session_state.carrito_docs

    # Botones de selección rápida
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("✅ Agregar todos los resultados"):
            for emp in resultados:
                doc_e = emp.get("documento","")
                if doc_e and doc_e not in carrito:
                    carrito[doc_e] = {"empleado": emp, "config": _config_default(emp, tipo_seleccionado)}
            st.rerun()
    with cc2:
        if carrito and st.button("🗑️ Vaciar selección"):
            st.session_state.carrito_docs = {}
            st.rerun()

    # Lista de resultados
    for emp in resultados[:30]:
        doc_e  = emp.get("documento","")
        nombre = emp.get("nombre","")
        cargo  = emp.get("cargo","")
        sal    = float(emp.get("salario",0))
        en_carrito = doc_e in carrito

        c1, c2, c3, c4 = st.columns([3,2,1,1])
        with c1: st.markdown(f"**{nombre}** · {doc_e}")
        with c2: st.caption(f"{cargo} · ${sal:,.0f}".replace(",","."))
        with c3:
            if en_carrito:
                if st.button("✓", key=f"r_{doc_e}", use_container_width=True):
                    del carrito[doc_e]; st.rerun()
            else:
                if st.button("➕", key=f"a_{doc_e}",
                             type="primary", use_container_width=True):
                    carrito[doc_e] = {"empleado": emp,
                                      "config": _config_default(emp, tipo_seleccionado)}
                    st.rerun()

    if not carrito:
        st.info("Agrega al menos un empleado para continuar.")
        st.stop()

    st.divider()

    # ── PASO 3: Configuración ──────────────────────────────────────────────
    st.markdown(f"### Paso 3 — Configuración ({len(carrito)} empleado(s) seleccionado(s))")

    # Configuración global (aplica a todos)
    _mostrar_config_global(tipo_seleccionado, carrito)

    st.divider()

    # ── PASO 4: Generar ───────────────────────────────────────────────────
    st.markdown("### Paso 4 — Generar y descargar")
    st.info(f"📄 Se generarán **{len(carrito)}** documentos de tipo **{doc_info['nombre']}**")
    st.caption(DISCLAIMER_DOCUMENTOS)

    c_envio, c_desc = st.columns(2)
    from utils.correo import smtp_configurado
    with c_envio:
        enviar = st.checkbox("📧 Enviar por correo a cada empleado",
            disabled=not smtp_configurado(),
            help="Requiere SMTP configurado en 'Mi empresa'")
    with c_desc:
        descargar = st.checkbox("⬇️ Descargar ZIP", value=True)

    if st.button("🚀 Generar documentos", type="primary", use_container_width=True):
        archivos = _ejecutar_generacion_unificada(
            email, datos_empresa, carrito, tipo_seleccionado,
            usuario.get("plan","gratuito"), enviar, descargar
        )
        if archivos and descargar:
            empresa_nb = datos_empresa.get("nombre","empresa").replace(" ","_")
            # Adaptativo: PDF único si es uno solo, ZIP si son varios
            st.caption(f"📦 {len(archivos)} archivo(s) generado(s)")
            if len(archivos) == 1:
                ruta_unica = archivos[0]
                if Path(ruta_unica).exists():
                    with open(ruta_unica, "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        f"⬇️ Descargar {Path(ruta_unica).name}",
                        pdf_bytes,
                        file_name=Path(ruta_unica).name,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                        key=f"dl_pdf_unico_{Path(ruta_unica).stem}"
                    )
                else:
                    st.error(f"❌ El archivo no existe en disco: {ruta_unica}")
            else:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    for p in archivos:
                        if Path(p).exists(): zf.write(p, Path(p).name)
                buf.seek(0)
                st.download_button(
                    f"⬇️ Descargar {len(archivos)} documentos (ZIP)",
                    buf, mime="application/zip", type="primary",
                    file_name=f"GestorRHIA_{empresa_nb}_{date.today()}.zip",
                    use_container_width=True,
                    key="dl_zip_multi"
                )
            if st.button("🗑️ Nueva generación", key="btn_nueva_gen"):
                st.session_state.carrito_docs = {}
                st.rerun()


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def _config_default(emp: dict, tipo_doc: str) -> dict:
    """Configuración por defecto para un empleado en un tipo de documento."""
    return {
        "tipo_doc":         tipo_doc,
        "fecha_ini_vac":    date.today(),
        "fecha_fin_vac":    date.today(),
        "motivo_retiro":    "renuncia",
        "fecha_corte":      date.today(),
        "salario_base":     float(emp.get("salario",0)),
        "tipo_salario":     emp.get("tipo_salario","fijo"),
        "salario_variable": float(emp.get("ingreso_promedio_variable",0) or 0),
        "conceptos_pend":   "",
        "observaciones":    "",
    }


def _mostrar_config_global(tipo_doc: str, carrito: dict):
    """Muestra los campos de configuración según el tipo de documento."""
    doc_info = CATALOGO.get(tipo_doc, {})
    campos   = doc_info.get("campos_req", [])

    if tipo_doc in ("certificado_con_salario", "certificado_sin_salario"):
        ing_var = st.radio("Ingresos variables",
            ["No aplica", "Usar valor del Excel", "Aplicar valor global"],
            horizontal=True, key="cfg_ingresos")
        if ing_var == "Aplicar valor global":
            val_global = st.number_input("Promedio mensual variable ($)",
                min_value=0.0, step=50000.0, key="cfg_var_global")
            for doc_e in carrito:
                carrito[doc_e]["config"]["salario_variable"] = val_global

    elif tipo_doc == "carta_vacaciones" or "fecha_inicio_vac" in campos:
        c1, c2 = st.columns(2)
        with c1:
            fi = st.date_input("Inicio vacaciones", date.today(), key="cfg_fi_vac")
        with c2:
            ff = st.date_input("Fin vacaciones", date.today(), key="cfg_ff_vac")
        for doc_e in carrito:
            carrito[doc_e]["config"]["fecha_ini_vac"] = fi
            carrito[doc_e]["config"]["fecha_fin_vac"] = ff

    elif tipo_doc == "liquidacion_prestaciones":
        c1, c2 = st.columns(2)
        with c1:
            fc = st.date_input("Fecha de corte", date.today(), key="cfg_fc_liq")
        with c2:
            MOTIVOS = {
                "renuncia":                "Renuncia voluntaria (sin indemnización)",
                "con_justa_causa":         "Despido con justa causa (Art. 62 CST)",
                "despido_sin_justa_causa": "Despido SIN justa causa (Art. 64 CST) — con indemnización",
                "mutuo_acuerdo":           "Terminación por mutuo acuerdo",
                "vencimiento_contrato":    "Vencimiento contrato a término fijo",
                "obra_terminada":          "Finalización de obra o labor",
                "periodo_prueba":          "Terminación en período de prueba",
                "jubilacion":              "Jubilación",
            }
            motivo = st.selectbox("Motivo de retiro *", list(MOTIVOS.keys()),
                format_func=lambda x: MOTIVOS[x], key="cfg_motivo")

        # Días pendientes para contratos fijos/obra (necesario para calcular indemnización)
        emp_actual = list(carrito.values())[0].get("empleado", {}) if carrito else {}
        tipo_c = str(emp_actual.get("tipo_contrato","indefinido")).lower()
        dias_pendientes = 0
        if motivo == "despido_sin_justa_causa" and ("fijo" in tipo_c or "obra" in tipo_c):
            st.info(
                f"📌 Contrato **{tipo_c}**: para calcular la indemnización correctamente "
                f"necesitamos saber cuántos días faltaban para terminar el contrato/obra."
            )
            dias_pendientes = st.number_input(
                "Días pendientes para terminar contrato u obra *",
                min_value=0, step=1, value=0,
                help="Ej: si el contrato fijo terminaba en 4 meses, ingresa 120 días",
                key="cfg_dias_pend"
            )

        # Aviso legal según el motivo seleccionado
        if motivo == "despido_sin_justa_causa":
            st.warning("⚠️ Este motivo genera **INDEMNIZACIÓN** según Art. 64 CST.")
        elif motivo == "con_justa_causa":
            st.info("ℹ️ No genera indemnización, pero requiere debido proceso previo.")
        elif motivo == "vencimiento_contrato":
            st.info("ℹ️ Requiere preaviso de 30 días. Sin preaviso, se prorroga automáticamente.")

        for doc_e in carrito:
            carrito[doc_e]["config"]["fecha_corte"]    = fc
            carrito[doc_e]["config"]["motivo_retiro"]  = motivo
            carrito[doc_e]["config"]["dias_pendientes"] = dias_pendientes

    elif tipo_doc == "paz_salvo":
        obs = st.text_area("Observaciones (opcional)", key="cfg_obs_ps",
            placeholder="Ej: El empleado devuelve el computador el viernes 10 de julio")
        for doc_e in carrito:
            carrito[doc_e]["config"]["observaciones"] = obs

    # ── Cambio de horario ────────────────────────────────────────────────
    elif tipo_doc == "cambio_horario":
        c1, c2 = st.columns(2)
        with c1:
            h_actual = st.text_input("Horario actual",
                placeholder="L-V 8:00 a.m. - 5:00 p.m.",
                key="cfg_h_actual")
            fecha_vig = st.date_input("Fecha de vigencia *",
                value=date.today(), key="cfg_fecha_vig_horario")
        with c2:
            h_nuevo = st.text_input("Nuevo horario *",
                placeholder="L-V 7:00 a.m. - 4:00 p.m.",
                key="cfg_h_nuevo")
        justif = st.text_area("Justificación (opcional)",
            placeholder="Ej: Ajuste por cambio en horario de atención al cliente.",
            key="cfg_justif_horario")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "horario_actual": h_actual,
                "horario_nuevo":  h_nuevo,
                "fecha_vigencia": fecha_vig,
                "justificacion":  justif,
            })

    # ── Cambio de cargo ──────────────────────────────────────────────────
    elif tipo_doc == "cambio_cargo":
        c1, c2 = st.columns(2)
        with c1:
            cargo_actual = st.text_input("Cargo actual",
                key="cfg_cargo_actual")
            fecha_vig_c = st.date_input("Fecha de vigencia *",
                value=date.today(), key="cfg_fecha_vig_cargo")
        with c2:
            cargo_nuevo = st.text_input("Nuevo cargo *",
                key="cfg_cargo_nuevo")
            salario_nuevo = st.number_input(
                "Nuevo salario (opcional, si cambia)",
                min_value=0.0, step=50000.0, key="cfg_salario_cargo")
        funciones = st.text_area("Funciones principales del nuevo cargo",
            placeholder="Ej: Liderar proyectos, coordinar equipo de 5 personas...",
            key="cfg_funciones_cargo")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "cargo_actual":     cargo_actual,
                "cargo_nuevo":      cargo_nuevo,
                "fecha_vigencia":   fecha_vig_c,
                "salario_nuevo":    salario_nuevo,
                "funciones_nuevas": funciones,
            })

    # ── Cambio salarial ──────────────────────────────────────────────────
    elif tipo_doc == "cambio_salario":
        c1, c2 = st.columns(2)
        with c1:
            sal_actual = st.number_input("Salario actual",
                min_value=0.0, step=50000.0, key="cfg_sal_actual")
            fecha_vig_s = st.date_input("Fecha de vigencia *",
                value=date.today(), key="cfg_fecha_vig_salario")
        with c2:
            sal_nuevo = st.number_input("Nuevo salario *",
                min_value=0.0, step=50000.0, key="cfg_sal_nuevo")
        motivo_sal = st.text_input("Motivo del ajuste (opcional)",
            placeholder="Ej: Reconocimiento por desempeño, ajuste anual...",
            key="cfg_motivo_salario")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "salario_actual": sal_actual,
                "salario_nuevo":  sal_nuevo,
                "fecha_vigencia": fecha_vig_s,
                "motivo":         motivo_sal,
            })

    # ── Cambio de sede ───────────────────────────────────────────────────
    elif tipo_doc == "cambio_sede":
        c1, c2 = st.columns(2)
        with c1:
            sede_actual = st.text_input("Sede actual", key="cfg_sede_actual")
            fecha_vig_sede = st.date_input("Fecha de vigencia *",
                value=date.today(), key="cfg_fecha_vig_sede")
        with c2:
            sede_nueva = st.text_input("Nueva sede *", key="cfg_sede_nueva")
            direccion_nueva = st.text_input("Dirección de la nueva sede",
                key="cfg_dir_nueva")
        motivo_sede = st.text_area("Motivo del traslado (opcional)",
            key="cfg_motivo_sede")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "sede_actual":     sede_actual,
                "sede_nueva":      sede_nueva,
                "direccion_nueva": direccion_nueva,
                "fecha_vigencia":  fecha_vig_sede,
                "motivo":          motivo_sede,
            })

    # ── Ascenso ──────────────────────────────────────────────────────────
    elif tipo_doc == "ascenso":
        c1, c2 = st.columns(2)
        with c1:
            cargo_a_actual = st.text_input("Cargo actual", key="cfg_cargo_a_act")
            sal_a_actual = st.number_input("Salario actual",
                min_value=0.0, step=50000.0, key="cfg_sal_a_act")
        with c2:
            cargo_a_nuevo = st.text_input("Nuevo cargo *", key="cfg_cargo_a_nuevo")
            sal_a_nuevo = st.number_input("Nuevo salario",
                min_value=0.0, step=50000.0, key="cfg_sal_a_nuevo")
        fecha_vig_a = st.date_input("Fecha de vigencia *",
            value=date.today(), key="cfg_fecha_vig_ascenso")
        mensaje_a = st.text_area("Mensaje personalizado (opcional)",
            placeholder="Ej: Reconocemos su liderazgo natural y compromiso.",
            key="cfg_mensaje_ascenso")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "cargo_actual":     cargo_a_actual,
                "cargo_nuevo":      cargo_a_nuevo,
                "salario_actual":   sal_a_actual,
                "salario_nuevo":    sal_a_nuevo,
                "fecha_vigencia":   fecha_vig_a,
                "mensaje_personal": mensaje_a,
            })

    # ── Reconocimiento ───────────────────────────────────────────────────
    elif tipo_doc == "reconocimiento":
        motivo_rec = st.text_input("Motivo del reconocimiento *",
            placeholder="Ej: cumplimiento de metas, 5 años de servicio...",
            key="cfg_motivo_rec")
        detalle_rec = st.text_area("Detalle o descripción",
            placeholder="Describa el logro específico o la razón del reconocimiento.",
            key="cfg_detalle_rec")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "motivo":  motivo_rec,
                "detalle": detalle_rec,
            })

    # ── Permiso (remunerado o no) ────────────────────────────────────────
    elif tipo_doc in ("permiso_remunerado", "permiso_no_remunerado"):
        c1, c2 = st.columns(2)
        with c1:
            fecha_ini_p = st.date_input("Fecha de inicio *",
                value=date.today(), key="cfg_fecha_ini_permiso")
        with c2:
            fecha_fin_p = st.date_input("Fecha de fin *",
                value=date.today(), key="cfg_fecha_fin_permiso")
        dias_p = st.number_input("Días autorizados", min_value=1, step=1, value=1,
            key="cfg_dias_permiso")
        motivo_p = st.text_area("Motivo *",
            placeholder="Ej: Cita médica, diligencia personal...",
            key="cfg_motivo_permiso")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "fecha_inicio": fecha_ini_p,
                "fecha_fin":    fecha_fin_p,
                "dias":         dias_p,
                "motivo":       motivo_p,
            })

    # ── Constancia de retiro ─────────────────────────────────────────────
    elif tipo_doc == "constancia_retiro":
        motivo_ret = st.text_input("Motivo del retiro (opcional)",
            placeholder="Ej: Renuncia voluntaria, terminación de contrato...",
            key="cfg_motivo_ret")
        st.info("💡 Este documento usa la fecha de retiro registrada en la ficha del empleado.")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "motivo_retiro": motivo_ret,
            })

    # ── Entrega de dotación ──────────────────────────────────────────────
    elif tipo_doc == "entrega_dotacion":
        fecha_ent = st.date_input("Fecha de entrega *",
            value=date.today(), key="cfg_fecha_entrega_dot")

        st.markdown("**Items entregados:**")
        st.caption("Agrega uno o más items separados por línea nueva.")
        items_texto = st.text_area(
            "Lista de items (uno por línea, formato: `descripción | cantidad | estado`)",
            placeholder="Camisa polo con logo | 3 | Nuevo\nPantalón dril azul | 2 | Nuevo\nZapato de seguridad | 1 | Nuevo",
            key="cfg_items_dot", height=120)
        obs_dot = st.text_input("Observaciones (opcional)", key="cfg_obs_dot")

        # Parsear items
        items = []
        for linea in items_texto.strip().split("\n"):
            if "|" in linea:
                partes = [p.strip() for p in linea.split("|")]
                if len(partes) >= 2:
                    items.append({
                        "descripcion": partes[0],
                        "cantidad":    int(partes[1]) if partes[1].isdigit() else 1,
                        "estado":      partes[2] if len(partes) >= 3 else "Nuevo",
                    })

        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "fecha_entrega": fecha_ent,
                "items":         items,
                "observaciones": obs_dot,
            })

    # ── Autorización de descuento ────────────────────────────────────────
    elif tipo_doc == "autorizacion_descuento":
        concepto_d = st.text_input("Concepto del descuento *",
            placeholder="Ej: Préstamo personal, libranza, elemento perdido...",
            key="cfg_concepto_desc")
        c1, c2, c3 = st.columns(3)
        with c1:
            valor_total_d = st.number_input("Valor total *",
                min_value=0.0, step=50000.0, key="cfg_valor_total_desc")
        with c2:
            num_cuotas_d = st.number_input("Número de cuotas *",
                min_value=1, step=1, value=1, key="cfg_num_cuotas_desc")
        with c3:
            valor_cuota_d = st.number_input("Valor por cuota",
                min_value=0.0, step=10000.0,
                value=float(valor_total_d/num_cuotas_d) if num_cuotas_d > 0 else 0.0,
                key="cfg_valor_cuota_desc")
        fecha_ini_d = st.date_input("Fecha de inicio del descuento *",
            value=date.today(), key="cfg_fecha_ini_desc")
        for doc_e in carrito:
            carrito[doc_e]["config"].update({
                "concepto":     concepto_d,
                "valor_total":  valor_total_d,
                "num_cuotas":   num_cuotas_d,
                "valor_cuota":  valor_cuota_d,
                "fecha_inicio": fecha_ini_d,
            })

    # ── Contratos laborales ──────────────────────────────────────────────
    elif tipo_doc in ("contrato_indefinido","contrato_fijo","contrato_obra","contrato_prestacion"):
        st.markdown("**Configuración del contrato:**")
        c1, c2 = st.columns(2)
        with c1:
            fi_contrato = st.date_input("Fecha de inicio del contrato *",
                value=date.today(), key="cfg_fi_contrato")
            lugar = st.text_input("Lugar de trabajo",
                value=st.session_state.get("datos_empresa",{}).get("ciudad","Colombia"),
                key="cfg_lugar")
        with c2:
            if tipo_doc == "contrato_fijo":
                ff_contrato = st.date_input("Fecha de terminación *",
                    value=date.today(), key="cfg_ff_contrato",
                    help="Máximo 4 años según Ley 2466/2025")
            elif tipo_doc == "contrato_prestacion":
                ff_contrato = st.date_input("Fecha de terminación *",
                    value=date.today(), key="cfg_ff_contrato")
            jornada = st.selectbox("Jornada",
                ["Diurna","Nocturna","Mixta"], key="cfg_jornada")

        # Campos específicos por tipo de contrato
        if tipo_doc == "contrato_obra":
            desc_obra = st.text_area("Descripción específica de la obra o labor *",
                key="cfg_desc_obra",
                placeholder="Ej: Construcción del muro perimetral del proyecto ABC, "
                            "ubicado en la Cra 45 con Cll 30, con área de 120m²...",
                help="Debe ser específica y determinada según Art. 46 CST")
        elif tipo_doc == "contrato_prestacion":
            objeto = st.text_area("Objeto del contrato *",
                key="cfg_objeto",
                placeholder="Ej: Servicios profesionales de asesoría contable "
                            "mensual para la empresa...")
            c3, c4 = st.columns(2)
            with c3:
                honorarios = st.number_input("Honorarios mensuales ($) *",
                    min_value=0.0, step=100000.0, key="cfg_honorarios")
            with c4:
                forma_pago = st.selectbox("Forma de pago", [
                    "Mensual, contra entrega de factura o cuenta de cobro",
                    "Quincenal, contra entrega de factura",
                    "Único pago al finalizar el servicio",
                ], key="cfg_forma_pago")

        if tipo_doc in ("contrato_indefinido","contrato_fijo"):
            per_prueba = st.checkbox("Incluir período de prueba de 2 meses (Art. 78 CST)",
                value=True, key="cfg_periodo_prueba")

        # Guardar en el carrito
        for doc_e in carrito:
            cfg = carrito[doc_e]["config"]
            cfg["fecha_inicio_contrato"] = fi_contrato
            cfg["lugar_trabajo"] = lugar
            cfg["jornada"] = jornada
            if tipo_doc == "contrato_fijo":
                cfg["fecha_fin_contrato"] = ff_contrato
                cfg["periodo_prueba"] = per_prueba
            elif tipo_doc == "contrato_indefinido":
                cfg["periodo_prueba"] = per_prueba
            elif tipo_doc == "contrato_obra":
                cfg["descripcion_obra"] = desc_obra
            elif tipo_doc == "contrato_prestacion":
                cfg["fecha_fin_contrato"] = ff_contrato
                cfg["objeto_contrato"]    = objeto
                cfg["honorarios"]         = honorarios
                cfg["forma_pago"]         = forma_pago

    # ── Carta de terminación ─────────────────────────────────────────────
    elif tipo_doc == "carta_terminacion":
        st.markdown("**Configuración de la terminación:**")

        MODALIDADES = {
            "renuncia_voluntaria":     "Renuncia voluntaria (Art. 47 CST)",
            "con_justa_causa":         "Con justa causa (Art. 62 CST) — sin indemnización",
            "sin_justa_causa":         "Sin justa causa (Art. 64 CST) — con indemnización",
        }
        modalidad = st.selectbox("Modalidad de terminación *",
            list(MODALIDADES.keys()),
            format_func=lambda x: MODALIDADES[x],
            key="cfg_modalidad_term")

        c1, c2 = st.columns(2)
        with c1:
            fecha_ret = st.date_input("Fecha efectiva de retiro *",
                value=date.today(), key="cfg_fecha_ret_term")

        # Si es con justa causa, mostrar causales del Art. 62 CST
        causal = "6"
        hechos = ""
        if modalidad == "con_justa_causa":
            from utils.contratos import CAUSAL_JUSTA_CAUSA
            with c2:
                # Mostrar solo primeros 60 chars de cada causal para el dropdown
                opciones = {k: f"Num. {k} — {v[:60]}..." if len(v)>60 else f"Num. {k} — {v}"
                            for k, v in CAUSAL_JUSTA_CAUSA.items()}
                causal = st.selectbox("Causal del Art. 62 CST *",
                    list(CAUSAL_JUSTA_CAUSA.keys()),
                    format_func=lambda x: opciones[x],
                    key="cfg_causal")
                # Mostrar el texto completo del causal seleccionado
                st.caption(f"📖 **Causal seleccionado:** {CAUSAL_JUSTA_CAUSA[causal]}")

            hechos = st.text_area("Descripción de los hechos *",
                key="cfg_hechos",
                placeholder="Describa los hechos específicos que fundamentan la "
                            "justa causa. Incluya fechas, testigos y evidencia si aplica.",
                help="Debe ser preciso y verificable. La justa causa debe probarse en juicio.")

            st.warning(
                "⚠️ **Debido proceso obligatorio:** Antes de terminar con justa causa "
                "debe haber llamados de atención previos, citación a descargos y "
                "evaluación de pruebas. Consulte un abogado laboral."
            )

        obs = st.text_area("Observaciones adicionales (opcional)", key="cfg_obs_term")

        for doc_e in carrito:
            cfg = carrito[doc_e]["config"]
            cfg["modalidad"]          = modalidad
            cfg["fecha_retiro"]       = fecha_ret
            cfg["causal_justa_causa"] = causal
            cfg["hechos"]             = hechos
            cfg["observaciones"]      = obs


def _ejecutar_generacion_unificada(
    email: str, datos_empresa: dict, carrito: dict,
    tipo_doc: str, plan: str, enviar: bool, descargar: bool
) -> list:
    """Genera todos los documentos del carrito y registra en historial."""
    from utils.plantillas_disenio import (
        generar_certificado, generar_certificado_sin_salario,
        generar_vacaciones, generar_liquidacion, generar_paz_salvo,
    )
    from utils.calcular_liquidacion import calcular_liquidacion_fila
    from utils.correo import enviar_documentos

    SALIDAS = Path("salidas"); SALIDAS.mkdir(exist_ok=True)
    disenio  = st.session_state.get("disenio_seleccionado", 1)
    usar_mda = st.session_state.get("usar_marca_agua", False)
    usar_logo= st.session_state.get("usar_logo_enc", True)
    membrete = st.session_state.get("membrete_path")
    rep      = datos_empresa.get("representante","")

    archivos = []; errores = []
    barra = st.progress(0, text="Generando…")

    for idx, (doc_e, item) in enumerate(carrito.items()):
        emp  = item["empleado"]
        conf = item["config"]
        nom  = emp.get("nombre","")
        nb   = nom.strip().replace(" ","_")

        # Datos de empresa con firmante correcto
        datos_cert = {**datos_empresa,
            "representante":   datos_empresa.get("firmante_cert_nombre") or rep,
            "_cargo_firmante": datos_empresa.get("firmante_cert_cargo","Representante Legal"),
        }
        datos_vac = {**datos_empresa,
            "representante":   datos_empresa.get("firmante_vac_nombre") or rep,
            "_cargo_firmante": datos_empresa.get("firmante_vac_cargo","Representante Legal"),
        }
        datos_liq = {**datos_empresa,
            "representante":   datos_empresa.get("firmante_liq_nombre") or rep,
            "_cargo_firmante": datos_empresa.get("firmante_liq_cargo","Representante Legal"),
        }

        emp_doc = {**emp,
            "Nombre": nom, "Documento": doc_e,
            "Cargo":  emp.get("cargo",""),
            "Salario": conf.get("salario_base", float(emp.get("salario",0))),
            "Fecha ingreso": emp.get("fecha_ingreso",""),
            "Fecha retiro":  emp.get("fecha_retiro",""),  # pasar fecha retiro si existe
            "Tipo contrato": emp.get("tipo_contrato","Indefinido"),
            "Ingreso promedio variable": conf.get("salario_variable",0),
        }

        # Si el empleado ya se retiró y pidieron cert con salario, usar sin salario
        fecha_ret_raw = emp.get("fecha_retiro") or ""  # None → ""
        empleado_retirado = bool(str(fecha_ret_raw).strip())
        tipo_efectivo = tipo_doc
        if tipo_doc == "certificado_con_salario" and empleado_retirado:
            tipo_efectivo = "certificado_sin_salario"

        ruta = None
        try:
            if tipo_efectivo == "certificado_con_salario":
                ruta = str(SALIDAS / f"Certificado_{nb}.pdf")
                generar_certificado(emp_doc, datos_cert, ruta, disenio,
                    usar_mda, membrete, usar_logo)

            elif tipo_efectivo == "certificado_sin_salario":
                ruta = str(SALIDAS / f"CertSinSalario_{nb}.pdf")
                generar_certificado_sin_salario(emp_doc, datos_cert, ruta, disenio,
                    usar_mda, membrete, usar_logo)

            elif tipo_doc == "carta_vacaciones":
                ruta = str(SALIDAS / f"Vacaciones_{nb}.pdf")
                generar_vacaciones(emp_doc, datos_vac, ruta,
                    conf["fecha_ini_vac"].strftime("%d/%m/%Y"),
                    conf["fecha_fin_vac"].strftime("%d/%m/%Y"),
                    disenio, usar_mda, membrete, usar_logo)

            elif tipo_doc == "liquidacion_prestaciones":
                import pandas as pd
                from utils.logs import log_info, log_error, log_debug, log_warn
                fc = conf.get("fecha_corte", date.today())
                motivo_usado = conf.get("motivo_retiro", "renuncia")
                dias_pend = int(conf.get("dias_pendientes", 0) or 0)

                # Log completo del input recibido — cero especulación
                log_info("liquidacion.input",
                    empleado=nom, documento=doc_e,
                    motivo=motivo_usado,
                    fecha_corte=str(fc),
                    dias_pendientes=dias_pend,
                    tipo_contrato=emp.get("tipo_contrato","Indefinido"),
                    salario=conf.get("salario_base", float(emp.get("salario",0))),
                    fecha_ingreso=emp.get("fecha_ingreso",""),
                    keys_conf=list(conf.keys()),
                )

                # ✅ Mensaje diagnóstico visible: muestra qué motivo se está usando
                st.info(
                    f"🔍 **Liquidando a {nom}** con motivo: **{motivo_usado}** "
                    + (f"· Días pendientes: {dias_pend}" if dias_pend > 0 else "")
                )

                fila = pd.Series({
                    "Nombre": nom, "Documento": doc_e,
                    "Cargo": emp.get("cargo",""),
                    "Salario": conf.get("salario_base", float(emp.get("salario",0))),
                    "Fecha ingreso": emp.get("fecha_ingreso",""),
                    "Fecha retiro":  emp.get("fecha_retiro",""),
                    "Tipo contrato": emp.get("tipo_contrato","Indefinido"),
                    "Cuenta bancaria": emp.get("cuenta_bancaria",""),
                })
                fc_dt = datetime(fc.year, fc.month, fc.day)

                try:
                    res = calcular_liquidacion_fila(fila, fc_dt,
                        motivo_retiro=motivo_usado,
                        dias_pendientes_fijo=dias_pend)
                except Exception as e:
                    log_error("liquidacion.calculo.fallo",
                        empleado=nom, error=str(e), motivo=motivo_usado)
                    st.error(f"❌ Error al calcular liquidación: {e}")
                    barra.progress((idx+1)/len(carrito), text=f"Error en {nom}")
                    continue

                # ✅ Verificar el cálculo antes de generar PDF
                indem_calc = res.get("Indemnizacion (Art. 64 CST)", 0)
                log_info("liquidacion.calculado",
                    empleado=nom,
                    motivo_recibido=motivo_usado,
                    motivo_registrado=res.get("Motivo retiro",""),
                    indem_calc=indem_calc,
                    genera_indem=res.get("Genera indemnizacion", False),
                    detalle=res.get("Indemnizacion detalle",""),
                    total=res.get("TOTAL LIQUIDACION ESTIMADA", 0),
                )

                if indem_calc > 0:
                    st.success(f"✅ Indemnización calculada: **${indem_calc:,.0f}** COP".replace(",","."))
                elif motivo_usado == "despido_sin_justa_causa":
                    st.error(
                        f"⚠️ Motivo '{motivo_usado}' pero indemnización = $0. "
                        f"Detalle: {res.get('Indemnizacion detalle','')}"
                    )
                    log_warn("liquidacion.indemnizacion.cero_inesperada",
                        empleado=nom, motivo=motivo_usado,
                        detalle=res.get("Indemnizacion detalle",""),
                        dias_pend=dias_pend)

                ruta = str(SALIDAS / f"Liquidacion_{nb}.pdf")
                try:
                    generar_liquidacion(res, datos_liq, ruta, disenio,
                        usar_mda, membrete, True, usar_logo)
                    log_info("liquidacion.pdf.ok", empleado=nom, ruta=ruta)
                except Exception as e:
                    log_error("liquidacion.pdf.fallo",
                        empleado=nom, error=str(e))
                    st.error(f"❌ Error generando PDF: {e}")
                    barra.progress((idx+1)/len(carrito), text=f"Error PDF en {nom}")
                    continue

                # ── AUTO-UPDATE: guardar fecha de retiro y marcar como retirado ──
                from utils.empleados_db import empleado_guardar
                fecha_retiro_str = fc.strftime("%d/%m/%Y")
                emp_actualizado = {**emp,
                    "fecha_retiro": fecha_retiro_str,
                    "activo":       False,   # marcarlo como retirado
                }
                empleado_guardar(email, emp_actualizado)

            elif tipo_doc == "paz_salvo":
                ruta = str(SALIDAS / f"PazSalvo_{nb}.pdf")
                generar_paz_salvo(emp_doc, datos_liq, ruta, disenio,
                    usar_mda, membrete, usar_logo,
                    conceptos_pendientes=conf.get("conceptos_pend",""),
                    observaciones=conf.get("observaciones",""))

            # ── CONTRATOS ────────────────────────────────────────────────
            elif tipo_doc in ("contrato_indefinido","contrato_fijo",
                              "contrato_obra","contrato_prestacion"):
                from utils.contratos import (
                    generar_contrato_indefinido, generar_contrato_fijo,
                    generar_contrato_obra, generar_contrato_prestacion,
                )
                # Firmante: usar el del rep. legal para contratos
                datos_c = {**datos_empresa,
                    "representante":   rep,
                    "_cargo_firmante": "Representante Legal",
                }
                config_contrato = {
                    "fecha_inicio_contrato": conf.get("fecha_inicio_contrato", date.today()),
                    "fecha_fin_contrato":    conf.get("fecha_fin_contrato", date.today()),
                    "lugar_trabajo":         conf.get("lugar_trabajo",
                        datos_empresa.get("ciudad","Colombia")),
                    "jornada":               conf.get("jornada", "Diurna"),
                    "periodo_prueba":        conf.get("periodo_prueba", True),
                    "descripcion_obra":      conf.get("descripcion_obra",""),
                    "objeto_contrato":       conf.get("objeto_contrato",""),
                    "honorarios":            conf.get("honorarios", 0),
                    "forma_pago":            conf.get("forma_pago",
                        "Mensual, contra entrega de factura o cuenta de cobro"),
                    "funciones":             conf.get("funciones",""),
                }

                if tipo_doc == "contrato_indefinido":
                    ruta = str(SALIDAS / f"ContratoIndefinido_{nb}.pdf")
                    generar_contrato_indefinido(emp_doc, datos_c, ruta,
                        config_contrato, disenio, usar_mda, membrete, usar_logo)
                elif tipo_doc == "contrato_fijo":
                    ruta = str(SALIDAS / f"ContratoFijo_{nb}.pdf")
                    generar_contrato_fijo(emp_doc, datos_c, ruta,
                        config_contrato, disenio, usar_mda, membrete, usar_logo)
                elif tipo_doc == "contrato_obra":
                    ruta = str(SALIDAS / f"ContratoObra_{nb}.pdf")
                    generar_contrato_obra(emp_doc, datos_c, ruta,
                        config_contrato, disenio, usar_mda, membrete, usar_logo)
                elif tipo_doc == "contrato_prestacion":
                    ruta = str(SALIDAS / f"ContratoPrestacion_{nb}.pdf")
                    generar_contrato_prestacion(emp_doc, datos_c, ruta,
                        config_contrato, disenio, usar_mda, membrete, usar_logo)

            # ── CARTA DE TERMINACIÓN ─────────────────────────────────────
            elif tipo_doc == "carta_terminacion":
                from utils.contratos import generar_carta_terminacion
                datos_t = {**datos_empresa,
                    "representante":   rep,
                    "_cargo_firmante": "Representante Legal",
                }
                config_term = {
                    "modalidad":          conf.get("modalidad", "renuncia_voluntaria"),
                    "fecha_retiro":       conf.get("fecha_retiro", date.today()),
                    "causal_justa_causa": conf.get("causal_justa_causa", "6"),
                    "hechos":             conf.get("hechos",""),
                    "observaciones":      conf.get("observaciones",""),
                }
                ruta = str(SALIDAS / f"Terminacion_{nb}.pdf")
                generar_carta_terminacion(emp_doc, datos_t, ruta,
                    config_term, disenio, usar_mda, membrete, usar_logo)

            # ── CARTAS ADMINISTRATIVAS (Etapa 7 - documentos nuevos) ──
            elif tipo_doc in ("cambio_horario", "cambio_cargo", "cambio_salario",
                                "cambio_sede", "ascenso", "reconocimiento",
                                "permiso_remunerado", "permiso_no_remunerado",
                                "constancia_retiro", "entrega_dotacion",
                                "autorizacion_descuento"):
                from utils.cartas_administrativas import (
                    generar_cambio_horario, generar_cambio_cargo,
                    generar_cambio_salarial, generar_cambio_sede,
                    generar_ascenso, generar_reconocimiento,
                    generar_permiso, generar_constancia_retiro,
                    generar_entrega_dotacion, generar_autorizacion_descuento,
                )
                _MAPEO_CARTAS = {
                    "cambio_horario":         (generar_cambio_horario, "CambioHorario"),
                    "cambio_cargo":           (generar_cambio_cargo, "CambioCargo"),
                    "cambio_salario":         (generar_cambio_salarial, "CambioSalarial"),
                    "cambio_sede":            (generar_cambio_sede, "CambioSede"),
                    "ascenso":                (generar_ascenso, "Ascenso"),
                    "reconocimiento":         (generar_reconocimiento, "Reconocimiento"),
                    "permiso_remunerado":     (generar_permiso, "PermisoRemunerado"),
                    "permiso_no_remunerado":  (generar_permiso, "PermisoNoRemunerado"),
                    "constancia_retiro":      (generar_constancia_retiro, "ConstanciaRetiro"),
                    "entrega_dotacion":       (generar_entrega_dotacion, "ActaDotacion"),
                    "autorizacion_descuento": (generar_autorizacion_descuento, "AutorizDescuento"),
                }
                gen_fn, prefix = _MAPEO_CARTAS[tipo_doc]
                ruta = str(SALIDAS / f"{prefix}_{nb}.pdf")

                # Config específica según tipo
                config_carta = dict(conf)
                if tipo_doc == "permiso_no_remunerado":
                    config_carta["remunerado"] = False
                elif tipo_doc == "permiso_remunerado":
                    config_carta["remunerado"] = True

                gen_fn(emp_doc, datos_empresa, ruta, config_carta,
                        disenio, usar_mda, membrete, usar_logo)

            else:
                # ─── Catch-all: usar el generador universal ───
                # Cubre los 16 documentos nuevos (Etapa 7)
                try:
                    from utils.plantillas_universales import (
                        generar_documento, PLANTILLAS,
                    )
                    # Mapeo de códigos del catálogo → códigos del generador universal
                    _MAPEO_UNIV = {
                        "paz_salvo":              "paz_y_salvo",
                        "entrega_cargo":          "acta_entrega_cargo",
                        "entrega_equipos":        "acta_entrega_equipos",
                        "entrega_dotacion":       "acta_entrega_dotacion",
                        "cambio_salario":         "carta_cambio_salario",
                        "cambio_cargo":           "carta_cambio_cargo",
                    }
                    tipo_universal = _MAPEO_UNIV.get(tipo_doc, tipo_doc)

                    if tipo_universal in PLANTILLAS:
                        nombre_archivo = tipo_universal.replace("_", "").title()
                        ruta = str(SALIDAS / f"{nombre_archivo}_{nb}.pdf")

                        # Preparar empleado con todos los datos disponibles
                        emp_doc_univ = {**emp, "documento": doc_e}

                        # Datos extra específicos por tipo (los pasa el usuario)
                        datos_extra = conf.get("datos_extra", {})

                        generar_documento(
                            tipo=tipo_universal,
                            empleado=emp_doc_univ,
                            datos_empresa=datos_empresa,
                            ruta_salida=ruta,
                            datos_extra=datos_extra,
                            disenio=disenio,
                            usar_marca_agua=usar_mda,
                            membrete=membrete,
                            usar_logo=usar_logo,
                        )
                    else:
                        st.warning(f"⚠️ Tipo '{tipo_doc}' aún no está implementado.")
                        continue
                except Exception as e_univ:
                    st.error(f"❌ Error generando {tipo_doc}: {e_univ}")
                    try:
                        from utils.logs import log_error
                        log_error("universal.fallo", tipo=tipo_doc, error=str(e_univ))
                    except Exception:
                        pass
                    continue

            if ruta:
                archivos.append(ruta)
                # Registrar en historial
                registrar(
                    email_usuario=email,
                    email_empresa=email,
                    nombre_empresa=datos_empresa.get("nombre",""),
                    tipo_documento=tipo_doc,
                    empleado_documento=doc_e,
                    empleado_nombre=nom,
                    nombre_archivo=Path(ruta).name,
                )

                # Envío por correo
                if enviar:
                    correo_dest = (emp.get("correo") or "").strip()
                    if correo_dest and "@" in correo_dest:
                        tipo_nb = NOMBRES_DOCUMENTO.get(tipo_doc, tipo_doc)
                        ok_m, _ = enviar_documentos(
                            correo_dest, nom,
                            datos_empresa.get("nombre",""),
                            tipo_nb, [ruta],
                            datos_empresa.get("correo_empresa",""))
                        if ok_m:
                            registrar(email, email,
                                datos_empresa.get("nombre",""), tipo_doc,
                                doc_e, nom, Path(ruta).name, estado="enviado",
                                enviado_correo=True, correo_destino=correo_dest)

        except Exception as e:
            errores.append(f"{nom}: {e}")

        barra.progress((idx+1)/len(carrito), text=f"Procesando {nom}…")

    barra.empty()
    if errores:
        st.warning(f"⚠️ {len(errores)} error(es):")
        for e in errores: st.caption(f"- {e}")
    if archivos:
        st.success(f"✅ {len(archivos)} documento(s) generado(s).")
    return archivos
