"""
Página de empleados: gestión de base de datos + buscador + carrito de generación.
Se integra en app.py como función llamable.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date

from utils.empleados_db import (
    empleados_listar, empleados_buscar, empleado_obtener,
    empleado_guardar, empleado_desactivar, empleado_eliminar,
    importar_desde_excel, empleados_stats,
)

TIPOS_CONTRATO = ["Indefinido", "Fijo", "Obra o labor", "Prestación de servicios"]
PLANTILLA_EXCEL = Path("plantillas/Base_Empleados.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def pantalla_empleados(email: str):
    """Renderiza la pantalla completa de empleados."""

    tab_base, tab_buscar, tab_nuevo = st.tabs([
        "📋 Base de empleados",
        "🔍 Buscar y generar documentos",
        "➕ Agregar / Editar empleado",
    ])

    with tab_base:
        _tab_base(email)

    with tab_buscar:
        _tab_buscar(email)

    with tab_nuevo:
        _tab_nuevo_empleado(email)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: BASE DE EMPLEADOS
# ══════════════════════════════════════════════════════════════════════════════

def _tab_base(email: str):
    st.markdown("### Base de empleados")

    # Stats rápidos
    stats = empleados_stats(email)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total",         stats["total"])
    c2.metric("Activos",       stats["activos"])
    c3.metric("Retirados",     stats["retirados"])
    c4.metric("Con variable",  stats["con_variable"])

    st.divider()

    # Importar Excel
    with st.expander("📥 Importar / actualizar desde Excel"):
        if PLANTILLA_EXCEL.exists():
            with open(PLANTILLA_EXCEL, "rb") as f:
                st.download_button("⬇️ Descargar plantilla",f,
                    file_name="Base_Empleados_GestorRHCol.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        archivo = st.file_uploader("Sube tu Excel", type=["xlsx"], key="imp_excel")
        if archivo:
            if st.button("📥 Importar ahora", type="primary"):
                with st.spinner("Importando..."):
                    creados, actualizados, errores = importar_desde_excel(email, archivo)
                st.success(f"✅ {creados} creados · {actualizados} actualizados")
                if errores:
                    st.warning(f"⚠️ {len(errores)} errores:")
                    for e in errores: st.caption(f"- {e}")
                st.rerun()

    st.divider()

    # Filtros
    c1, c2 = st.columns([3, 1])
    with c1:
        filtro = st.text_input("🔍 Filtrar por nombre, documento o cargo",
            placeholder="Escribe para filtrar...")
    with c2:
        mostrar = st.selectbox("Mostrar", ["Activos", "Retirados", "Todos"])

    solo_activos = {"Activos": True, "Retirados": False, "Todos": None}[mostrar]

    if filtro:
        empleados = empleados_buscar(email, filtro)
        if solo_activos is not None:
            empleados = [e for e in empleados if e.get("activo", True) == solo_activos]
    else:
        if solo_activos is None:
            empleados = empleados_listar(email, solo_activos=False)
        else:
            empleados = empleados_listar(email, solo_activos=solo_activos)

    if not empleados:
        st.info("No hay empleados. Importa un Excel o agrega uno manualmente.")
        return

    st.caption(f"Mostrando {len(empleados)} empleado(s)")

    # Tabla de empleados
    # Aviso visual para que el usuario sepa que hay botones dentro
    if empleados:
        st.info(
            "💡 **Haz clic en cualquier empleado** para ver las acciones disponibles: "
            "Editar · 📄 Docs · 📝 Contrato · ✍️ Otrosí · 🔴 Retirar"
        )

    for i, emp in enumerate(empleados):
        activo = emp.get("activo", True)
        ing_var = float(emp.get("ingreso_promedio_variable", 0) or 0)
        badge_var = " 📊" if ing_var > 0 else ""
        badge_ret = " 🔴" if not activo else ""
        salario_fmt = f"${float(emp.get('salario',0)):,.0f}".replace(",",".")

        with st.expander(
            f"{'✅' if activo else '⭕'} **{emp.get('nombre','')}**"
            f"{badge_ret}{badge_var} · {emp.get('documento','')} · "
            f"{emp.get('cargo','')} · {salario_fmt}",
            expanded=(i == 0),   # ← Primer empleado abierto por defecto
        ):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"""
                **Documento:** {emp.get('documento','')}
                **Cargo:** {emp.get('cargo','')}
                **Contrato:** {emp.get('tipo_contrato','')}
                **Ingreso:** {date_fmt(emp.get('fecha_ingreso',''))}
                """)
            with c2:
                ing_var_fmt = f"${ing_var:,.0f}".replace(",",".") if ing_var > 0 else "—"
                correo_emp  = emp.get('correo','') or '—'
                retiro_fmt  = date_fmt(emp.get('fecha_retiro','')) or 'Activo'
                st.markdown(f"""
                **Salario:** {salario_fmt}
                **Var. mensual:** {ing_var_fmt}
                **Correo:** {correo_emp}
                **Retiro:** {retiro_fmt}
                """)
            with c3:
                doc = emp.get("documento","")
                # Editar
                if st.button("✏️ Editar", key=f"edit_{doc}",
                             use_container_width=True):
                    st.session_state["emp_editar"] = emp
                    st.session_state["emp_tab"] = "editar"
                    st.rerun()
                # Agregar al carrito de generación
                if activo:
                    if st.button("📄 Docs", key=f"gen_{doc}",
                                 use_container_width=True, type="primary"):
                        _agregar_al_carrito(emp)
                        st.rerun()
                    # Generar contrato directo
                    if st.button("📝 Contrato", key=f"contrato_{doc}",
                                 use_container_width=True):
                        st.session_state["emp_contrato"] = emp
                        st.rerun()
                    # Generar otrosí
                    if st.button("✍️ Otrosí", key=f"otrosi_{doc}",
                                 use_container_width=True):
                        st.session_state["emp_otrosi"] = emp
                        st.rerun()
                    # Carta de terminación
                    if st.button("📮 Terminación", key=f"term_{doc}",
                                 use_container_width=True):
                        st.session_state["emp_terminacion"] = emp
                        st.rerun()
                # Retirar / Eliminar
                if activo:
                    if st.button("🔴 Retirar", key=f"ret_{doc}",
                                 use_container_width=True):
                        empleado_desactivar(email, doc)
                        st.rerun()
                else:
                    if st.button("🗑️ Eliminar", key=f"del_{doc}",
                                 use_container_width=True):
                        empleado_eliminar(email, doc)
                        st.rerun()

    # ── Modales de Contrato, Otrosí y Terminación ────────────────────────
    if st.session_state.get("emp_contrato"):
        _modal_contrato(email, st.session_state["emp_contrato"])

    if st.session_state.get("emp_otrosi"):
        _modal_otrosi(email, st.session_state["emp_otrosi"])

    if st.session_state.get("emp_terminacion"):
        _modal_terminacion(email, st.session_state["emp_terminacion"])

    # Carrito flotante
    _mostrar_carrito_resumen()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: BUSCADOR + CARRITO DE GENERACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _tab_buscar(email: str):
    st.markdown("### 🔍 Busca empleados y genera sus documentos")
    st.caption("Agrega uno o varios empleados, configura cada uno y genera todos de una vez.")

    # Inicializar carrito
    if "carrito_gen" not in st.session_state:
        st.session_state.carrito_gen = {}

    # Buscador
    termino = st.text_input("Buscar por nombre, documento o cargo",
        placeholder="Ej: García · 1020304050 · Auxiliar...",
        key="busq_term")

    resultados = empleados_buscar(email, termino) if termino else []

    if termino and not resultados:
        st.warning("No se encontraron empleados con ese criterio.")

    # Resultados de búsqueda
    if resultados:
        st.markdown(f"**{len(resultados)} resultado(s):**")
        for emp in resultados[:20]:
            doc = emp.get("documento","")
            en_carrito = doc in st.session_state.carrito_gen
            ing_var = float(emp.get("ingreso_promedio_variable",0) or 0)
            sal_fmt = f"${float(emp.get('salario',0)):,.0f}".replace(",",".")

            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                st.markdown(
                    f"**{emp.get('nombre','')}** · {doc} · "
                    f"{emp.get('cargo','')} · {sal_fmt}"
                    + (" · 📊 Var." if ing_var > 0 else "")
                )
            with c2:
                st.caption(f"Ingreso: {date_fmt(emp.get('fecha_ingreso',''))}")
            with c3:
                if en_carrito:
                    if st.button("✓ Quitar", key=f"q_{doc}",
                                 use_container_width=True):
                        del st.session_state.carrito_gen[doc]
                        st.rerun()
                else:
                    if st.button("➕ Agregar", key=f"a_{doc}",
                                 type="primary", use_container_width=True):
                        _agregar_al_carrito(emp)
                        st.rerun()

    st.divider()

    # ── CARRITO ──────────────────────────────────────────────────────────────
    carrito = st.session_state.get("carrito_gen", {})

    if not carrito:
        st.info("💡 Busca y agrega empleados arriba para configurar sus documentos.")
        return

    st.markdown(f"### 📋 Carrito de generación — {len(carrito)} empleado(s)")

    for doc, item in list(carrito.items()):
        emp  = item["empleado"]
        conf = item["config"]
        nombre = emp.get("nombre","")
        sal_base = float(emp.get("salario", 0))
        ing_var_orig = float(emp.get("ingreso_promedio_variable", 0) or 0)

        with st.expander(f"⚙️ {nombre} · {doc}", expanded=True):
            c_left, c_right = st.columns([3, 1])

            with c_left:
                # ── Qué documentos generar ───────────────────────────────
                st.markdown("**Documentos a generar:**")
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    gen_cert = st.checkbox("📋 Certificado laboral",
                        value=conf.get("gen_cert", True), key=f"cert_{doc}")
                with cc2:
                    gen_vac  = st.checkbox("🏖️ Carta vacaciones",
                        value=conf.get("gen_vac", False), key=f"vac_{doc}")
                with cc3:
                    gen_liq  = st.checkbox("💰 Liquidación",
                        value=conf.get("gen_liq", False), key=f"liq_{doc}")

                # Fechas vacaciones
                if gen_vac:
                    cv1, cv2 = st.columns(2)
                    with cv1:
                        fi_vac = st.date_input("Inicio vacaciones",
                            value=conf.get("fecha_ini_vac") or date.today(),
                            key=f"fiv_{doc}")
                    with cv2:
                        ff_vac = st.date_input("Fin vacaciones",
                            value=conf.get("fecha_fin_vac") or date.today(),
                            key=f"ffv_{doc}")
                    conf["fecha_ini_vac"] = fi_vac
                    conf["fecha_fin_vac"] = ff_vac

                # Motivo retiro para liquidación
                if gen_liq:
                    MOTIVOS = {
                        "renuncia":              "Renuncia voluntaria",
                        "despido_sin_justa_causa": "Despido sin justa causa (Art.64 CST)",
                        "mutuo_acuerdo":           "Mutuo acuerdo",
                        "vencimiento_contrato":    "Vencimiento de contrato",
                    }
                    motivo = st.selectbox("Motivo de retiro",
                        list(MOTIVOS.keys()), format_func=lambda x: MOTIVOS[x],
                        index=list(MOTIVOS.keys()).index(
                            conf.get("motivo_retiro","renuncia")),
                        key=f"mot_{doc}")
                    conf["motivo_retiro"] = motivo

                    fecha_corte = st.date_input("Fecha de corte",
                        value=conf.get("fecha_corte") or date.today(),
                        key=f"fc_{doc}")
                    conf["fecha_corte"] = fecha_corte

                st.divider()

                # ── Configuración de salario ─────────────────────────────
                st.markdown("**Configuración de salario:**")
                cs1, cs2 = st.columns(2)

                with cs1:
                    tipo_sal = st.radio("Tipo de salario",
                        ["Fijo", "Con variable"],
                        index=0 if conf.get("tipo_salario","fijo") == "fijo" else 1,
                        horizontal=True, key=f"ts_{doc}")
                    conf["tipo_salario"] = "fijo" if tipo_sal == "Fijo" else "variable"

                with cs2:
                    # Salario base — editable por si cambió
                    sal_edit = st.number_input("Salario base ($)",
                        value=float(conf.get("salario_base", sal_base)),
                        min_value=0.0, step=50000.0,
                        key=f"sb_{doc}")
                    conf["salario_base"] = sal_edit

                # Salario variable
                if conf["tipo_salario"] == "variable":
                    ing_var = st.number_input(
                        "Promedio mensual ingresos variables ($)",
                        value=float(conf.get("salario_variable", ing_var_orig)),
                        min_value=0.0, step=50000.0,
                        help="Se incluye en el certificado y en la base de liquidación",
                        key=f"sv_{doc}")
                    conf["salario_variable"] = ing_var
                    if gen_cert:
                        st.caption(
                            f"✅ El certificado dirá: salario fijo "
                            f"${sal_edit:,.0f} + variable promedio "
                            f"${ing_var:,.0f}/mes".replace(",","."))
                else:
                    conf["salario_variable"] = 0.0

                # Guardar config actualizada
                conf["gen_cert"] = gen_cert
                conf["gen_vac"]  = gen_vac
                conf["gen_liq"]  = gen_liq
                st.session_state.carrito_gen[doc]["config"] = conf

            with c_right:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Quitar del\ncarrito",
                             key=f"rm_{doc}", use_container_width=True):
                    del st.session_state.carrito_gen[doc]
                    st.rerun()

    # ── BOTÓN GENERAR TODOS ───────────────────────────────────────────────────
    st.divider()
    docs_a_generar = sum(
        sum([item["config"].get("gen_cert",False),
             item["config"].get("gen_vac",False),
             item["config"].get("gen_liq",False)])
        for item in carrito.values()
    )
    st.info(f"📄 Se generarán **{docs_a_generar} documentos** para "
            f"**{len(carrito)} empleado(s)**")

    col_gen, col_vac = st.columns(2)

    # Opción de envío por correo
    from utils.correo import smtp_configurado
    with col_gen:
        enviar_correo = st.checkbox(
            "📧 Enviar documentos por correo a cada empleado",
            value=False,
            disabled=not smtp_configurado(),
            help="Requiere SMTP configurado y correo del empleado en la base de datos"
        )

    with col_vac:
        if st.button("🚀 Generar todos los documentos",
                     type="primary", use_container_width=True):
            _ejecutar_generacion(email, enviar_correo)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: NUEVO / EDITAR EMPLEADO
# ══════════════════════════════════════════════════════════════════════════════

def _tab_nuevo_empleado(email: str):
    emp_editar = st.session_state.get("emp_editar")
    modo = "Editar" if emp_editar else "Nuevo"
    st.markdown(f"### {'✏️ Editar' if emp_editar else '➕ Agregar nuevo'} empleado")

    if emp_editar:
        st.info(f"Editando: **{emp_editar.get('nombre','')}** · {emp_editar.get('documento','')}")
        if st.button("← Cancelar edición"):
            st.session_state.pop("emp_editar", None)
            st.rerun()

    with st.form(f"form_emp_{modo}"):
        c1, c2 = st.columns(2)
        with c1:
            doc    = st.text_input("Número de documento *",
                value=emp_editar.get("documento","") if emp_editar else "",
                placeholder="Cédula, NIT, pasaporte...")
            nombre = st.text_input("Nombre completo *",
                value=emp_editar.get("nombre","") if emp_editar else "")
            cargo  = st.text_input("Cargo *",
                value=emp_editar.get("cargo","") if emp_editar else "")
            contrato = st.selectbox("Tipo de contrato",
                TIPOS_CONTRATO,
                index=TIPOS_CONTRATO.index(emp_editar.get("tipo_contrato","Indefinido"))
                      if emp_editar and emp_editar.get("tipo_contrato") in TIPOS_CONTRATO
                      else 0)
        with c2:
            salario  = st.number_input("Salario base ($) *",
                value=float(emp_editar.get("salario",0)) if emp_editar else 0.0,
                min_value=0.0, step=50000.0)
            fi = st.text_input("Fecha de ingreso (dd/mm/aaaa) *",
                value=emp_editar.get("fecha_ingreso","") if emp_editar else "",
                placeholder="01/02/2024")
            fr = st.text_input("Fecha de retiro (dd/mm/aaaa)",
                value=emp_editar.get("fecha_retiro","") if emp_editar else "",
                placeholder="Dejar vacío si sigue activo")
            correo_emp = st.text_input("Correo del empleado",
                value=emp_editar.get("correo","") if emp_editar else "",
                placeholder="empleado@empresa.com")

        st.markdown("**Salario variable:**")
        cv1, cv2 = st.columns(2)
        with cv1:
            ing_var_orig = float(emp_editar.get("ingreso_promedio_variable",0) or 0) if emp_editar else 0.0
            tiene_variable = st.checkbox("Este empleado tiene ingresos variables",
                value=ing_var_orig > 0)
        with cv2:
            if tiene_variable:
                ing_var = st.number_input("Promedio mensual variable ($)",
                    value=ing_var_orig, min_value=0.0, step=50000.0)
            else:
                ing_var = 0.0

        cuenta = st.text_input("Cuenta bancaria (para liquidaciones)",
            value=emp_editar.get("cuenta_bancaria","") if emp_editar else "",
            placeholder="Bancolombia Ahorros #123456")

        guardar = st.form_submit_button(
            f"{'💾 Guardar cambios' if emp_editar else '➕ Agregar empleado'}",
            type="primary")

        if guardar:
            errores_v = []
            if not doc:    errores_v.append("Documento requerido")
            if not nombre: errores_v.append("Nombre requerido")
            if not cargo:  errores_v.append("Cargo requerido")
            if salario <= 0: errores_v.append("Salario debe ser mayor a 0")
            if not fi:     errores_v.append("Fecha de ingreso requerida")

            if errores_v:
                for e in errores_v: st.error(e)
            else:
                ok, msg = empleado_guardar(email, {
                    "documento": doc, "nombre": nombre, "cargo": cargo,
                    "salario": salario, "fecha_ingreso": fi,
                    "fecha_retiro": fr, "tipo_contrato": contrato,
                    "correo": correo_emp, "cuenta_bancaria": cuenta,
                    "ingreso_promedio_variable": ing_var,
                    "tipo_salario": "variable" if tiene_variable else "fijo",
                    "activo": True,
                })
                if ok:
                    st.success(f"✅ {msg}")
                    st.session_state.pop("emp_editar", None)
                    st.rerun()
                else:
                    st.error(msg)


# ══════════════════════════════════════════════════════════════════════════════
# CARRITO — funciones auxiliares
# ══════════════════════════════════════════════════════════════════════════════

def _agregar_al_carrito(emp: dict):
    if "carrito_gen" not in st.session_state:
        st.session_state.carrito_gen = {}
    doc = emp.get("documento","")
    if doc not in st.session_state.carrito_gen:
        st.session_state.carrito_gen[doc] = {
            "empleado": emp,
            "config": {
                "gen_cert": True, "gen_vac": False, "gen_liq": False,
                "tipo_salario": emp.get("tipo_salario","fijo"),
                "salario_base": float(emp.get("salario",0)),
                "salario_variable": float(emp.get("ingreso_promedio_variable",0) or 0),
                "motivo_retiro": "renuncia",
                "fecha_corte": date.today(),
                "fecha_ini_vac": date.today(),
                "fecha_fin_vac": date.today(),
            }
        }
        st.toast(f"✅ {emp.get('nombre','')} agregado al carrito")


def _mostrar_carrito_resumen():
    carrito = st.session_state.get("carrito_gen", {})
    if not carrito: return
    st.divider()
    st.markdown(
        f"🛒 **Carrito de generación:** {len(carrito)} empleado(s) · "
        f"Ve a la pestaña **🔍 Buscar y generar** para configurar y generar."
    )


def _ejecutar_generacion(email: str, enviar_correo: bool):
    """Ejecuta la generación de todos los documentos del carrito."""
    import zipfile, io
    from datetime import datetime as dt
    from utils.calcular_liquidacion import calcular_liquidacion_fila
    from utils.plantillas_disenio import (
        generar_certificado, generar_vacaciones, generar_liquidacion,
    )
    from utils.correo import enviar_documentos

    carrito       = st.session_state.get("carrito_gen", {})
    datos_empresa = st.session_state.get("datos_empresa", {})
    disenio       = st.session_state.get("disenio_seleccionado", 1)
    usar_mda      = st.session_state.get("usar_marca_agua", False)
    usar_logo     = st.session_state.get("usar_logo_enc", True)
    membrete      = st.session_state.get("membrete_path")
    SALIDAS       = Path("salidas"); SALIDAS.mkdir(exist_ok=True)

    archivos = []; errores = []
    barra = st.progress(0, text="Generando documentos...")
    total = len(carrito); paso = 0

    for doc, item in carrito.items():
        emp    = item["empleado"]
        conf   = item["config"]
        nombre = emp.get("nombre","Sin nombre")
        nb     = nombre.strip().replace(" ","_")

        # Preparar datos del empleado con la config del carrito
        emp_doc = {**emp,
            "Nombre":    nombre,
            "Documento": doc,
            "Cargo":     emp.get("cargo",""),
            "Salario":   conf.get("salario_base", emp.get("salario",0)),
            "Fecha ingreso": emp.get("fecha_ingreso",""),
            "Tipo contrato": emp.get("tipo_contrato","Indefinido"),
            "Ingreso promedio variable": conf.get("salario_variable",0)
                if conf.get("tipo_salario") == "variable" else 0,
        }

        # Firmantes por tipo
        rep = datos_empresa.get("representante","")
        datos_cert = {**datos_empresa,
            "representante":    datos_empresa.get("firmante_cert_nombre") or rep,
            "_cargo_firmante":  datos_empresa.get("firmante_cert_cargo","Representante Legal"),
        }
        datos_vac = {**datos_empresa,
            "representante":    datos_empresa.get("firmante_vac_nombre") or rep,
            "_cargo_firmante":  datos_empresa.get("firmante_vac_cargo","Representante Legal"),
        }
        datos_liq_emp = {**datos_empresa,
            "representante":    datos_empresa.get("firmante_liq_nombre") or rep,
            "_cargo_firmante":  datos_empresa.get("firmante_liq_cargo","Representante Legal"),
        }

        pdfs_empleado = []

        # Certificado
        if conf.get("gen_cert"):
            try:
                ruta = str(SALIDAS / f"Certificado_{nb}.pdf")
                generar_certificado(emp_doc, datos_cert, ruta, disenio,
                    usar_mda, membrete, usar_logo)
                archivos.append(Path(ruta)); pdfs_empleado.append(ruta)
            except Exception as e:
                errores.append(f"Cert {nombre}: {e}")

        # Vacaciones
        if conf.get("gen_vac"):
            try:
                ruta = str(SALIDAS / f"Vacaciones_{nb}.pdf")
                fi   = conf.get("fecha_ini_vac", date.today()).strftime("%d/%m/%Y")
                ff   = conf.get("fecha_fin_vac", date.today()).strftime("%d/%m/%Y")
                generar_vacaciones(emp_doc, datos_vac, ruta, fi, ff,
                    disenio, usar_mda, membrete, usar_logo)
                archivos.append(Path(ruta)); pdfs_empleado.append(ruta)
            except Exception as e:
                errores.append(f"Vac {nombre}: {e}")

        # Liquidación
        if conf.get("gen_liq"):
            try:
                import pandas as pd_inner
                fila_liq = pd.Series({
                    "Nombre": nombre, "Documento": doc,
                    "Cargo": emp.get("cargo",""),
                    "Salario": conf.get("salario_base", emp.get("salario",0)),
                    "Fecha ingreso": emp.get("fecha_ingreso",""),
                    "Fecha retiro": emp.get("fecha_retiro",""),
                    "Tipo contrato": emp.get("tipo_contrato","Indefinido"),
                    "Cuenta bancaria": emp.get("cuenta_bancaria",""),
                })
                from datetime import datetime as dtt
                fc = conf.get("fecha_corte", date.today())
                fc_dt = dtt(fc.year, fc.month, fc.day)
                resultado = calcular_liquidacion_fila(fila_liq, fc_dt,
                    conf.get("motivo_retiro","renuncia"))
                ruta = str(SALIDAS / f"Liquidacion_{nb}.pdf")
                generar_liquidacion(resultado, datos_liq_emp, ruta, disenio,
                    usar_mda, membrete, True, usar_logo)
                archivos.append(Path(ruta)); pdfs_empleado.append(ruta)
            except Exception as e:
                errores.append(f"Liq {nombre}: {e}")

        # Envío por correo
        if enviar_correo and pdfs_empleado:
            correo_dest = emp.get("correo","").strip()
            if correo_dest and "@" in correo_dest:
                try:
                    enviar_documentos(correo_dest, nombre,
                        datos_empresa.get("nombre",""),
                        "Documentos laborales", pdfs_empleado,
                        datos_empresa.get("correo_empresa",""))
                except Exception as e:
                    errores.append(f"Correo {nombre}: {e}")

        paso += 1
        barra.progress(paso / total, text=f"Procesando {nombre}...")

    barra.empty()

    if errores:
        st.warning(f"⚠️ {len(errores)} error(es):")
        for e in errores: st.caption(f"- {e}")

    if archivos:
        st.success(f"✅ {len(archivos)} documento(s) generados para {len(carrito)} empleado(s).")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for p in archivos:
                if p.exists(): zf.write(p, p.name)
        buf.seek(0)
        empresa_nombre = datos_empresa.get("nombre","empresa").replace(" ","_")
        st.download_button(
            "⬇️ Descargar todos los documentos (ZIP)",
            buf, mime="application/zip", type="primary",
            file_name=f"GestorRHCol_{empresa_nombre}_{dt.today().strftime('%Y%m%d')}.zip",
        )
        # Limpiar carrito
        if st.button("🗑️ Vaciar carrito y generar nuevos"):
            st.session_state.carrito_gen = {}
            st.rerun()


def date_fmt(val: str) -> str:
    """Formatea una fecha para mostrar."""
    if not val or val == "None" or val == "nan": return ""
    return str(val)[:10]


# ══════════════════════════════════════════════════════════════════════════════
# MODAL: GENERAR CONTRATO DIRECTO DESDE EMPLEADOS
# ══════════════════════════════════════════════════════════════════════════════

def _modal_contrato(email: str, emp: dict):
    """Formulario compacto para generar un contrato directo desde empleados."""
    st.divider()
    st.markdown(f"### 📝 Generar contrato para {emp.get('nombre','')}")
    if st.button("← Cancelar", key="cancel_contrato"):
        del st.session_state["emp_contrato"]
        st.rerun()

    TIPOS = {
        "contrato_indefinido": "Contrato a Término Indefinido (Art. 47 CST)",
        "contrato_fijo":       "Contrato a Término Fijo (Art. 46 CST · Ley 2466/2025)",
        "contrato_obra":       "Contrato por Obra o Labor (Art. 46 CST)",
        "contrato_prestacion": "Contrato de Prestación de Servicios (civil, no laboral)",
    }

    with st.form("form_contrato_directo"):
        tipo = st.selectbox("Tipo de contrato *", list(TIPOS.keys()),
            format_func=lambda x: TIPOS[x])

        c1, c2 = st.columns(2)
        with c1:
            fi = st.date_input("Fecha de inicio *", value=date.today())
            lugar = st.text_input("Lugar de trabajo",
                value=st.session_state.get("datos_empresa",{}).get("ciudad","Colombia"))
        with c2:
            ff = None
            if tipo in ("contrato_fijo","contrato_prestacion"):
                ff = st.date_input("Fecha de terminación *", value=date.today(),
                    help="Máximo 4 años según Ley 2466/2025" if tipo == "contrato_fijo" else None)
            jornada = st.selectbox("Jornada", ["Diurna","Nocturna","Mixta"])

        desc_obra = objeto = honorarios = forma_pago = None
        if tipo == "contrato_obra":
            desc_obra = st.text_area("Descripción específica de la obra *",
                placeholder="Ej: Construcción del muro perimetral del proyecto ABC...")
        elif tipo == "contrato_prestacion":
            objeto = st.text_area("Objeto del contrato *",
                placeholder="Ej: Servicios profesionales de asesoría contable mensual...")
            cc1, cc2 = st.columns(2)
            with cc1:
                honorarios = st.number_input("Honorarios mensuales ($)",
                    min_value=0.0, step=100000.0)
            with cc2:
                forma_pago = st.selectbox("Forma de pago", [
                    "Mensual, contra entrega de factura o cuenta de cobro",
                    "Quincenal, contra entrega de factura",
                    "Único pago al finalizar el servicio",
                ])

        periodo_prueba = True
        if tipo in ("contrato_indefinido","contrato_fijo"):
            periodo_prueba = st.checkbox("Incluir período de prueba de 2 meses", value=True)

        funciones = st.text_area("Funciones específicas (opcional)")

        generar = st.form_submit_button("🚀 Generar contrato", type="primary")

        if generar:
            # Validaciones
            errores = []
            if tipo == "contrato_obra" and not desc_obra:
                errores.append("La descripción de la obra es obligatoria (Art. 46 CST)")
            if tipo == "contrato_prestacion" and not objeto:
                errores.append("El objeto del contrato es obligatorio")

            if errores:
                for e in errores: st.error(e)
            else:
                _ejecutar_contrato_directo(email, emp, tipo, {
                    "fecha_inicio_contrato": fi,
                    "fecha_fin_contrato":    ff,
                    "lugar_trabajo":         lugar,
                    "jornada":               jornada,
                    "periodo_prueba":        periodo_prueba,
                    "descripcion_obra":      desc_obra,
                    "objeto_contrato":       objeto,
                    "honorarios":            honorarios or 0,
                    "forma_pago":            forma_pago or "",
                    "funciones":             funciones,
                })

    # ── Botón de descarga FUERA del form (Streamlit no lo permite dentro) ──
    if st.session_state.get("pdf_contrato_listo"):
        pdf_info = st.session_state["pdf_contrato_listo"]
        st.success(f"✅ Contrato generado para {pdf_info['empleado']}.")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Descargar contrato PDF",
                pdf_info["bytes"],
                file_name=pdf_info["filename"],
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        with c2:
            if st.button("✓ Cerrar y volver", use_container_width=True,
                         key="cerrar_contrato"):
                del st.session_state["pdf_contrato_listo"]
                if "emp_contrato" in st.session_state:
                    del st.session_state["emp_contrato"]
                st.rerun()


def _ejecutar_contrato_directo(email: str, emp: dict, tipo: str, cfg: dict):
    """Ejecuta la generación del contrato y ofrece descarga."""
    from utils.contratos import (
        generar_contrato_indefinido, generar_contrato_fijo,
        generar_contrato_obra, generar_contrato_prestacion,
    )
    from utils.historial import registrar as registrar_hist

    datos_empresa = st.session_state.get("datos_empresa", {})
    rep = datos_empresa.get("representante","")
    datos_c = {**datos_empresa,
        "representante":   rep,
        "_cargo_firmante": "Representante Legal",
    }

    emp_doc = {
        "Nombre":        emp.get("nombre",""),
        "Documento":     emp.get("documento",""),
        "Cargo":         emp.get("cargo",""),
        "Salario":       float(emp.get("salario", 0) or 0),
        "Fecha ingreso": emp.get("fecha_ingreso",""),
        "Tipo contrato": emp.get("tipo_contrato","Indefinido"),
    }

    SALIDAS = Path("salidas"); SALIDAS.mkdir(exist_ok=True)
    nb = emp.get("nombre","empleado").strip().replace(" ","_")
    disenio  = st.session_state.get("disenio_seleccionado", 1)
    usar_mda = st.session_state.get("usar_marca_agua", False)
    usar_logo= st.session_state.get("usar_logo_enc", True)
    membrete = st.session_state.get("membrete_path")

    try:
        if tipo == "contrato_indefinido":
            ruta = str(SALIDAS / f"ContratoIndefinido_{nb}.pdf")
            generar_contrato_indefinido(emp_doc, datos_c, ruta, cfg,
                disenio, usar_mda, membrete, usar_logo)
        elif tipo == "contrato_fijo":
            ruta = str(SALIDAS / f"ContratoFijo_{nb}.pdf")
            generar_contrato_fijo(emp_doc, datos_c, ruta, cfg,
                disenio, usar_mda, membrete, usar_logo)
        elif tipo == "contrato_obra":
            ruta = str(SALIDAS / f"ContratoObra_{nb}.pdf")
            generar_contrato_obra(emp_doc, datos_c, ruta, cfg,
                disenio, usar_mda, membrete, usar_logo)
        else:  # contrato_prestacion
            ruta = str(SALIDAS / f"ContratoPrestacion_{nb}.pdf")
            generar_contrato_prestacion(emp_doc, datos_c, ruta, cfg,
                disenio, usar_mda, membrete, usar_logo)

        # Registrar historial
        registrar_hist(email, email, datos_empresa.get("nombre",""),
            tipo, emp.get("documento",""), emp.get("nombre",""),
            Path(ruta).name)

        # Guardar el PDF en session_state — se mostrará fuera del formulario
        with open(ruta, "rb") as f:
            st.session_state["pdf_contrato_listo"] = {
                "bytes":    f.read(),
                "filename": Path(ruta).name,
                "empleado": emp.get("nombre",""),
                "tipo":     "contrato",
            }
    except Exception as e:
        st.error(f"Error generando el contrato: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MODAL: GENERAR OTROSÍ (Cambio cargo, salario, lugar)
# ══════════════════════════════════════════════════════════════════════════════

def _modal_otrosi(email: str, emp: dict):
    """Formulario para generar un otrosí — modifica el contrato existente."""
    st.divider()
    st.markdown(f"### ✍️ Otrosí para {emp.get('nombre','')}")
    st.caption("Modifica el contrato original por cambio de cargo, salario y/o lugar de trabajo.")

    if st.button("← Cancelar", key="cancel_otrosi"):
        del st.session_state["emp_otrosi"]
        st.rerun()

    with st.form("form_otrosi"):
        st.markdown("**¿Qué se modifica?** Puedes seleccionar uno o varios cambios:")
        c1, c2, c3 = st.columns(3)
        with c1:
            cambio_cargo = st.checkbox("Cambio de cargo")
        with c2:
            cambio_salario = st.checkbox("Cambio de salario")
        with c3:
            cambio_lugar = st.checkbox("Cambio de lugar de trabajo")

        fecha_vig = st.date_input("Fecha de vigencia del cambio *", value=date.today(),
            help="Fecha desde la cual aplica el cambio")

        st.divider()

        nuevo_cargo = nuevas_funciones = ""
        if cambio_cargo:
            st.markdown("**📋 Cambio de cargo:**")
            st.info(f"Cargo actual: **{emp.get('cargo','')}**")
            nuevo_cargo = st.text_input("Nuevo cargo *",
                placeholder="Ej: Coordinador de Operaciones")
            nuevas_funciones = st.text_area("Funciones específicas del nuevo cargo (opcional)")

        nuevo_salario = 0.0
        if cambio_salario:
            st.markdown("**💰 Cambio de salario:**")
            sal_actual = float(emp.get("salario", 0) or 0)
            st.info(f"Salario actual: **${sal_actual:,.0f}**".replace(",","."))
            nuevo_salario = st.number_input("Nuevo salario mensual ($) *",
                min_value=0.0, step=50000.0, value=sal_actual)

        nuevo_lugar = ""
        if cambio_lugar:
            st.markdown("**📍 Cambio de lugar de trabajo:**")
            lugar_actual = st.session_state.get("datos_empresa",{}).get("ciudad","Colombia")
            st.info(f"Lugar actual: **{lugar_actual}**")
            nuevo_lugar = st.text_input("Nuevo lugar de trabajo *",
                placeholder="Ej: Bogotá D.C. — Cra 45 #50-30")

        motivo = st.text_area("Motivo del cambio (opcional)",
            placeholder="Ej: Promoción por desempeño destacado / reestructuración organizacional...")

        generar = st.form_submit_button("🚀 Generar otrosí", type="primary")

        if generar:
            # Validaciones
            tipos_cambio = []
            errores = []
            if cambio_cargo:
                if not nuevo_cargo: errores.append("Debes indicar el nuevo cargo")
                else: tipos_cambio.append("cargo")
            if cambio_salario:
                if nuevo_salario <= 0: errores.append("El nuevo salario debe ser mayor a 0")
                else: tipos_cambio.append("salario")
            if cambio_lugar:
                if not nuevo_lugar: errores.append("Debes indicar el nuevo lugar")
                else: tipos_cambio.append("lugar")
            if not tipos_cambio:
                errores.append("Selecciona al menos un tipo de cambio")

            if errores:
                for e in errores: st.error(e)
            else:
                _ejecutar_otrosi(email, emp, {
                    "tipo_cambio":       tipos_cambio,
                    "fecha_vigencia":    fecha_vig,
                    "nuevo_cargo":       nuevo_cargo,
                    "nuevas_funciones":  nuevas_funciones,
                    "nuevo_salario":     nuevo_salario,
                    "nuevo_lugar":       nuevo_lugar,
                    "lugar_actual":      st.session_state.get("datos_empresa",{}).get("ciudad","Colombia"),
                    "motivo":            motivo,
                })

    # ── Botón de descarga FUERA del form ──
    if st.session_state.get("pdf_otrosi_listo"):
        pdf_info = st.session_state["pdf_otrosi_listo"]
        st.success(f"✅ Otrosí generado para {pdf_info['empleado']}. Los datos del empleado fueron actualizados.")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Descargar otrosí PDF",
                pdf_info["bytes"],
                file_name=pdf_info["filename"],
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        with c2:
            if st.button("✓ Cerrar y volver", use_container_width=True,
                         key="cerrar_otrosi"):
                del st.session_state["pdf_otrosi_listo"]
                if "emp_otrosi" in st.session_state:
                    del st.session_state["emp_otrosi"]
                st.rerun()


def _ejecutar_otrosi(email: str, emp: dict, cfg: dict):
    """Ejecuta la generación del otrosí y actualiza la BD si aplica."""
    from utils.contratos import generar_otrosi
    from utils.historial import registrar as registrar_hist
    from utils.empleados_db import empleado_guardar

    datos_empresa = st.session_state.get("datos_empresa", {})
    rep = datos_empresa.get("representante","")
    datos_c = {**datos_empresa,
        "representante":   rep,
        "_cargo_firmante": "Representante Legal",
    }
    emp_doc = {
        "Nombre":        emp.get("nombre",""),
        "Documento":     emp.get("documento",""),
        "Cargo":         emp.get("cargo",""),
        "Salario":       float(emp.get("salario",0) or 0),
        "Fecha ingreso": emp.get("fecha_ingreso",""),
    }

    SALIDAS = Path("salidas"); SALIDAS.mkdir(exist_ok=True)
    nb = emp.get("nombre","empleado").strip().replace(" ","_")
    disenio  = st.session_state.get("disenio_seleccionado", 1)
    usar_mda = st.session_state.get("usar_marca_agua", False)
    usar_logo= st.session_state.get("usar_logo_enc", True)
    membrete = st.session_state.get("membrete_path")

    ruta = str(SALIDAS / f"Otrosi_{nb}_{date.today().strftime('%Y%m%d')}.pdf")

    try:
        generar_otrosi(emp_doc, datos_c, ruta, cfg,
            disenio, usar_mda, membrete, usar_logo)

        # Actualizar datos del empleado en la BD según los cambios
        datos_actualizados = {**emp}
        if "cargo" in cfg["tipo_cambio"]:
            datos_actualizados["cargo"] = cfg["nuevo_cargo"]
        if "salario" in cfg["tipo_cambio"]:
            datos_actualizados["salario"] = cfg["nuevo_salario"]
        empleado_guardar(email, datos_actualizados)

        registrar_hist(email, email, datos_empresa.get("nombre",""),
            "otrosi", emp.get("documento",""), emp.get("nombre",""),
            Path(ruta).name,
            observaciones=f"Cambios: {', '.join(cfg['tipo_cambio'])}")

        st.success("✅ Otrosí generado y datos del empleado actualizados.")
        with open(ruta, "rb") as f:
            st.session_state["pdf_otrosi_listo"] = {
                "bytes":    f.read(),
                "filename": Path(ruta).name,
                "empleado": emp.get("nombre",""),
                "tipo":     "otrosi",
            }
    except Exception as e:
        st.error(f"Error generando el otrosí: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MODAL: CARTA DE TERMINACIÓN DIRECTA
# ══════════════════════════════════════════════════════════════════════════════

def _modal_terminacion(email: str, emp: dict):
    """Formulario para generar carta de terminación desde empleados."""
    st.divider()
    st.markdown(f"### 📮 Carta de terminación para {emp.get('nombre','')}")
    st.caption("Genera la carta según el motivo de terminación conforme al CST colombiano.")

    if st.button("← Cancelar", key="cancel_terminacion"):
        del st.session_state["emp_terminacion"]
        st.rerun()

    MODALIDADES = {
        "renuncia_voluntaria":     "Renuncia voluntaria (Art. 47 CST)",
        "con_justa_causa":         "Con justa causa (Art. 62 CST) — sin indemnización",
        "sin_justa_causa":         "Sin justa causa (Art. 64 CST) — con indemnización",
    }

    with st.form("form_terminacion_directa"):
        modalidad = st.selectbox("Modalidad de terminación *",
            list(MODALIDADES.keys()),
            format_func=lambda x: MODALIDADES[x],
            key="tm_modalidad")

        c1, c2 = st.columns(2)
        with c1:
            fecha_ret = st.date_input("Fecha efectiva de retiro *",
                value=date.today(), key="tm_fecha_ret")

        causal = "6"
        hechos = ""
        if modalidad == "con_justa_causa":
            from utils.contratos import CAUSAL_JUSTA_CAUSA
            with c2:
                opciones = {k: f"Num. {k} — {v[:60]}..." if len(v)>60 else f"Num. {k} — {v}"
                            for k, v in CAUSAL_JUSTA_CAUSA.items()}
                causal = st.selectbox("Causal del Art. 62 CST *",
                    list(CAUSAL_JUSTA_CAUSA.keys()),
                    format_func=lambda x: opciones[x],
                    key="tm_causal")
                st.caption(f"📖 **Causal seleccionado:** {CAUSAL_JUSTA_CAUSA[causal]}")

            hechos = st.text_area("Descripción de los hechos *",
                key="tm_hechos",
                placeholder="Describa los hechos específicos que fundamentan la "
                            "justa causa. Incluya fechas, testigos y evidencia si aplica.",
                help="Debe ser preciso y verificable. La justa causa debe probarse en juicio.")

            st.warning(
                "⚠️ **Debido proceso obligatorio:** Antes de terminar con justa causa "
                "debe haber llamados de atención previos, citación a descargos y "
                "evaluación de pruebas. Consulte un abogado laboral."
            )

        obs = st.text_area("Observaciones adicionales (opcional)", key="tm_obs")

        generar = st.form_submit_button("🚀 Generar carta", type="primary")

        if generar:
            errores = []
            if modalidad == "con_justa_causa" and not hechos:
                errores.append("Los hechos son obligatorios para justa causa")

            if errores:
                for e in errores: st.error(e)
            else:
                _ejecutar_terminacion_directa(email, emp, {
                    "modalidad":          modalidad,
                    "fecha_retiro":       fecha_ret,
                    "causal_justa_causa": causal,
                    "hechos":             hechos,
                    "observaciones":      obs,
                })

    # ── Botón de descarga FUERA del form ──
    if st.session_state.get("pdf_terminacion_listo"):
        pdf_info = st.session_state["pdf_terminacion_listo"]
        st.success(f"✅ Carta de terminación generada para {pdf_info['empleado']}.")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Descargar carta PDF",
                pdf_info["bytes"],
                file_name=pdf_info["filename"],
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        with c2:
            if st.button("✓ Cerrar y volver", use_container_width=True,
                         key="cerrar_terminacion"):
                del st.session_state["pdf_terminacion_listo"]
                if "emp_terminacion" in st.session_state:
                    del st.session_state["emp_terminacion"]
                st.rerun()


def _ejecutar_terminacion_directa(email: str, emp: dict, cfg: dict):
    """Ejecuta la generación de la carta de terminación."""
    from utils.contratos import generar_carta_terminacion
    from utils.historial import registrar as registrar_hist

    datos_empresa = st.session_state.get("datos_empresa", {})
    rep = datos_empresa.get("representante","")
    datos_t = {**datos_empresa,
        "representante":   rep,
        "_cargo_firmante": "Representante Legal",
    }

    emp_doc = {
        "Nombre":        emp.get("nombre",""),
        "Documento":     emp.get("documento",""),
        "Cargo":         emp.get("cargo",""),
        "Salario":       float(emp.get("salario", 0) or 0),
        "Fecha ingreso": emp.get("fecha_ingreso",""),
        "Tipo contrato": emp.get("tipo_contrato","Indefinido"),
    }

    SALIDAS = Path("salidas"); SALIDAS.mkdir(exist_ok=True)
    nb = emp.get("nombre","empleado").strip().replace(" ","_")
    disenio  = st.session_state.get("disenio_seleccionado", 1)
    usar_mda = st.session_state.get("usar_marca_agua", False)
    usar_logo= st.session_state.get("usar_logo_enc", True)
    membrete = st.session_state.get("membrete_path")

    ruta = str(SALIDAS / f"Terminacion_{nb}_{date.today().strftime('%Y%m%d')}.pdf")

    try:
        generar_carta_terminacion(emp_doc, datos_t, ruta, cfg,
            disenio, usar_mda, membrete, usar_logo)

        registrar_hist(email, email, datos_empresa.get("nombre",""),
            "carta_terminacion", emp.get("documento",""), emp.get("nombre",""),
            Path(ruta).name,
            observaciones=f"Modalidad: {cfg['modalidad']}")

        # Guardar en session_state para mostrar botón fuera del form
        with open(ruta, "rb") as f:
            st.session_state["pdf_terminacion_listo"] = {
                "bytes":    f.read(),
                "filename": Path(ruta).name,
                "empleado": emp.get("nombre",""),
                "tipo":     "terminacion",
            }
    except Exception as e:
        st.error(f"Error generando la carta de terminación: {e}")
