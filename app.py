"""RH Fácil v5 — Login + 5 diseños + correo SMTP + ingresos variables + bug fix"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime
import zipfile, io

from utils.validar_datos import cargar_y_validar
from utils.calcular_liquidacion import calcular_liquidacion_df, SALARIO_MINIMO_2026, AUXILIO_TRANSPORTE_2026
from utils.plantillas_disenio import (
    generar_certificado, generar_vacaciones, generar_liquidacion,
    nombre_disenio, PALETAS,
)
from utils.plan_control import PLANES, link_whatsapp
from utils.auth import login, registrar, registrar_uso_usuario, obtener_limite_plan
from utils.correo import enviar_documentos, smtp_configurado, instrucciones_gmail
from utils.estilos import CSS

st.set_page_config(page_title="RH Fácil", page_icon="📄", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

CARPETA_SALIDAS = Path("salidas"); CARPETA_SALIDAS.mkdir(exist_ok=True)
CARPETA_ASSETS  = Path("assets");  CARPETA_ASSETS.mkdir(exist_ok=True)
PLANTILLA_EXCEL = Path("plantillas/Base_Empleados.xlsx")

# ── Sesión ──────────────────────────────────────────────────────────────────
for k,v in [("usuario",None),("datos_empresa",{
        "nombre":"","nit":"","representante":"","correo_empresa":"",
        "ciudad":"","logo_path":None,
        "firmante_cert_nombre":"","firmante_cert_cargo":"",
        "firmante_vac_nombre": "","firmante_vac_cargo": "",
        "firmante_liq_nombre": "","firmante_liq_cargo": "",
    }),
    ("df_empleados",None),("archivos_generados",[]),("disenio_seleccionado",1)]:
    if k not in st.session_state: st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA DE LOGIN / REGISTRO
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.usuario:
    col_izq, col_centro, col_der = st.columns([1,2,1])
    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;margin-bottom:1.5rem'>
            <div style='font-size:2.5rem'>📄</div>
            <h1 style='color:#1B3F6E;margin:0'>RH Fácil</h1>
            <p style='color:#6B7280;margin-top:4px'>Documentos laborales para PYMES colombianas</p>
        </div>""", unsafe_allow_html=True)

        tab_login, tab_registro = st.tabs(["🔐 Iniciar sesión", "✨ Crear cuenta"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            email_l    = st.text_input("Correo electrónico", key="l_email",
                placeholder="tucorreo@empresa.com")
            password_l = st.text_input("Contraseña", type="password", key="l_pass")

            if st.button("Ingresar", type="primary", use_container_width=True):
                ok, msg, datos = login(email_l, password_l)
                if ok:
                    st.session_state.usuario = datos
                    # Cargar empresa guardada del usuario
                    from utils.auth import cargar_empresa_usuario
                    empresa_guardada = cargar_empresa_usuario(email_l)
                    if empresa_guardada:
                        st.session_state.datos_empresa = {
                            **st.session_state.datos_empresa,
                            **empresa_guardada,
                        }
                        # Restaurar diseño guardado
                        if empresa_guardada.get("disenio_seleccionado"):
                            st.session_state.disenio_seleccionado = empresa_guardada["disenio_seleccionado"]
                        st.session_state.usar_marca_agua  = empresa_guardada.get("usar_marca_agua", False)
                        st.session_state.usar_logo_enc    = empresa_guardada.get("usar_logo_encabezado", True)
                    st.rerun()
                else:
                    st.error(msg)

            st.divider()
            st.markdown("""
            <div style='background:#EFF6FF;border-radius:10px;padding:1rem;margin-top:0.5rem'>
                <p style='margin:0;font-size:0.85rem;color:#1B3F6E;font-weight:600'>
                    🎯 Cuenta Demo — acceso completo</p>
                <p style='margin:4px 0 0;font-size:0.82rem;color:#374151'>
                    <b>Usuario:</b> demo@rhfacil.co<br>
                    <b>Contraseña:</b> RHFacil2026</p>
            </div>""", unsafe_allow_html=True)

        with tab_registro:
            st.markdown("<br>", unsafe_allow_html=True)
            nombre_r   = st.text_input("Nombre completo", key="r_nombre")
            email_r    = st.text_input("Correo electrónico", key="r_email")
            password_r = st.text_input("Contraseña (mín. 6 caracteres)", type="password", key="r_pass")
            password_r2= st.text_input("Confirmar contraseña", type="password", key="r_pass2")

            if st.button("Crear cuenta gratis", type="primary", use_container_width=True):
                if password_r != password_r2:
                    st.error("Las contraseñas no coinciden.")
                else:
                    ok, msg = registrar(email_r, nombre_r, password_r)
                    if ok:
                        st.success(f"✅ {msg} Ya puedes iniciar sesión.")
                    else:
                        st.error(msg)
    st.stop()

# ── Usuario autenticado ──────────────────────────────────────────────────────
usuario    = st.session_state.usuario
plan_info  = obtener_limite_plan(usuario["plan"])
empresa_ok = bool(st.session_state.datos_empresa["nombre"] and
                  st.session_state.datos_empresa["nit"])

# ── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## 📄 RH Fácil")
    st.caption(f"Hola, **{usuario['nombre'].split()[0]}** 👋")
    st.divider()

    pagina = st.radio("nav", [
        "🏠  Inicio", "🏢  Mi empresa", "👥  Empleados",
        "🎨  Diseño de plantillas", "⚡  Generar docs", "💎  Planes",
    ], label_visibility="collapsed")

    st.divider()
    docs_usados = usuario.get("documentos_usados", 0)
    max_docs    = plan_info["max_docs"]
    sin_limite  = not plan_info["tiene_limite"]

    st.markdown(f"""
    <div class="sidebar-plan-badge">
        <div class="sidebar-plan-nombre">Plan {usuario['plan'].capitalize()}</div>
        <div class="sidebar-plan-docs">
            {'✅ Documentos ilimitados' if sin_limite
             else f'📄 {docs_usados} usados · {max(0, max_docs-docs_usados)} restantes'}
        </div>
    </div>""", unsafe_allow_html=True)

    if not sin_limite and max_docs > 0:
        prog = min(docs_usados / max_docs, 1.0)
        st.progress(prog)

    st.divider()
    st.markdown(
        f'<p style="color:rgba(255,255,255,0.5);font-size:0.72rem">'
        f'{"✅" if empresa_ok else "⬜"} Empresa configurada<br>'
        f'{"✅" if st.session_state.df_empleados is not None else "⬜"} Empleados cargados<br>'
        f'🎨 Diseño #{st.session_state.disenio_seleccionado}: '
        f'{nombre_disenio(st.session_state.disenio_seleccionado)}</p>',
        unsafe_allow_html=True)

    st.divider()
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state.usuario = None
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# INICIO
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "🏠  Inicio":
    st.markdown("# Genera documentos laborales en minutos")
    st.markdown("<p style='color:#6B7280'>Certificados, vacaciones y liquidaciones según el CST colombiano 2026.</p>", unsafe_allow_html=True)
    st.divider()
    c1,c2,c3 = st.columns(3)
    c1.metric("⏱ Por certificado","< 3 seg","vs 15 min manual")
    c2.metric("📋 Conceptos liquidación","6 conceptos","CST 2026")
    c3.metric("🎨 Diseños disponibles","5 plantillas","Elige la tuya")
    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("### 1️⃣ Empresa y diseño"); st.write("Configura tus datos y elige entre 5 plantillas profesionales.")
    with c2:
        st.markdown("### 2️⃣ Empleados"); st.write("Sube el Excel con tu personal. Descarga la plantilla actualizada.")
    with c3:
        st.markdown("### 3️⃣ Genera y envía"); st.write("PDF por empleado + ZIP + envío directo al correo de cada uno.")
    st.divider()
    st.warning(f"⚖️ Las liquidaciones son una **estimación de referencia**. No reemplazan el concepto de un contador o abogado laboral. SMMLV 2026: **${SALARIO_MINIMO_2026:,.0f}** · Auxilio transporte: **${AUXILIO_TRANSPORTE_2026:,.0f}**".replace(",","."))

# ══════════════════════════════════════════════════════════════════════════════
# MI EMPRESA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏢  Mi empresa":
    st.markdown("# Datos de tu empresa")
    with st.form("form_empresa"):
        # ── Datos generales ───────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            nombre     = st.text_input("Razón social *",
                value=st.session_state.datos_empresa["nombre"],
                placeholder="Distribuciones ABC SAS")
            nit        = st.text_input("NIT *",
                value=st.session_state.datos_empresa["nit"],
                placeholder="900123456-7")
            correo_emp = st.text_input("Correo corporativo *",
                value=st.session_state.datos_empresa.get("correo_empresa",""),
                placeholder="rrhh@miempresa.com",
                help="Se usa para enviar documentos y como remitente en correos.")
            ciudad = st.text_input("Ciudad *",
                value=st.session_state.datos_empresa.get("ciudad",""),
                placeholder="Barranquilla, Medellín, Bogotá...",
                help="Aparece en la fecha de expedición del documento")
        with c2:
            representante = st.text_input("Representante legal *",
                value=st.session_state.datos_empresa["representante"],
                placeholder="Nombre completo — aparece en documentos legales")
            logo = st.file_uploader("Logo / Membrete (PNG o JPG)",
                type=["png","jpg","jpeg"],
                help="Aparece en esquina derecha del encabezado")

        # ── Responsables de firma ─────────────────────────────────────────
        st.divider()
        st.markdown("### ✍️ Responsables de firma")
        st.caption(
            "Define quién firma cada tipo de documento. Si no completas estos campos, "
            "se usará el representante legal. Útil cuando quien firma es el **Líder de RH**, "
            "**Gerente Administrativo** u otro cargo."
        )
        de = st.session_state.datos_empresa
        rep_default = de.get("representante","") or representante

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**📋 Certificados laborales**")
            fcn = st.text_input("Nombre del firmante",
                value=de.get("firmante_cert_nombre",""),
                placeholder=rep_default or "Nombre completo",
                key="fcn")
            fcc = st.text_input("Cargo",
                value=de.get("firmante_cert_cargo",""),
                placeholder="Líder de Recursos Humanos",
                key="fcc")
        with c2:
            st.markdown("**🏖️ Cartas de vacaciones**")
            fvn = st.text_input("Nombre del firmante",
                value=de.get("firmante_vac_nombre",""),
                placeholder=rep_default or "Nombre completo",
                key="fvn")
            fvc = st.text_input("Cargo",
                value=de.get("firmante_vac_cargo",""),
                placeholder="Gerente Administrativo",
                key="fvc")
        with c3:
            st.markdown("**💰 Liquidaciones**")
            fln = st.text_input("Nombre del firmante",
                value=de.get("firmante_liq_nombre",""),
                placeholder=rep_default or "Nombre completo",
                key="fln")
            flc = st.text_input("Cargo",
                value=de.get("firmante_liq_cargo",""),
                placeholder="Representante Legal",
                key="flc")

        guardar = st.form_submit_button("💾 Guardar datos", type="primary")
        if guardar:
            if not nombre or not nit or not representante or not correo_emp:
                st.error("Completa los campos obligatorios (*): razón social, NIT, representante y correo.")
            else:
                logo_path = st.session_state.datos_empresa.get("logo_path")
                if logo:
                    ext = logo.name.split(".")[-1]
                    logo_path = str(CARPETA_ASSETS / f"logo_empresa.{ext}")
                    with open(logo_path,"wb") as f: f.write(logo.getbuffer())

                st.session_state.datos_empresa = {
                    "nombre":         nombre,
                    "nit":            nit,
                    "representante":  representante,
                    "correo_empresa": correo_emp,
                    "ciudad":         ciudad,
                    "logo_path":      logo_path,
                    # Firmantes: si vacío usa el representante legal
                    "firmante_cert_nombre": fcn.strip() or representante,
                    "firmante_cert_cargo":  fcc.strip() or "Representante Legal",
                    "firmante_vac_nombre":  fvn.strip() or representante,
                    "firmante_vac_cargo":   fvc.strip() or "Representante Legal",
                    "firmante_liq_nombre":  fln.strip() or representante,
                    "firmante_liq_cargo":   flc.strip() or "Representante Legal",
                    # Opciones de logo (se sincronizan desde session_state)
                    "usar_logo_encabezado": st.session_state.get("usar_logo_enc", True),
                    "usar_marca_agua":      st.session_state.get("usar_marca_agua", False),
                    "disenio_seleccionado": st.session_state.get("disenio_seleccionado", 1),
                }
                # Persistir en JSON para que cargue en el próximo login
                from utils.auth import guardar_empresa_usuario
                guardar_empresa_usuario(usuario["email"], st.session_state.datos_empresa)
                st.success("✅ Datos guardados correctamente. Se cargarán automáticamente en tu próximo inicio de sesión.")

    # Vista previa de firmantes y logo
    de = st.session_state.datos_empresa
    if de.get("representante"):
        st.divider()
        st.markdown("**Firmantes configurados actualmente:**")
        c1, c2, c3 = st.columns(3)
        with c1:
            n = de.get("firmante_cert_nombre") or de.get("representante","")
            c = de.get("firmante_cert_cargo")  or "Representante Legal"
            st.markdown(f"📋 **{n}**  \n*{c}*")
        with c2:
            n = de.get("firmante_vac_nombre") or de.get("representante","")
            c = de.get("firmante_vac_cargo")  or "Representante Legal"
            st.markdown(f"🏖️ **{n}**  \n*{c}*")
        with c3:
            n = de.get("firmante_liq_nombre") or de.get("representante","")
            c = de.get("firmante_liq_cargo")  or "Representante Legal"
            st.markdown(f"💰 **{n}**  \n*{c}*")

    if de.get("logo_path") and Path(de["logo_path"]).exists():
        st.image(de["logo_path"], width=120, caption="Logo actual")

    # ── Opciones de logo con sugerencia visual ────────────────────────────
    st.divider()
    st.markdown("### 🖼️ Opciones de visualización del logo")
    st.caption("Configura cómo aparece el logo de tu empresa en los documentos.")

    c1, c2 = st.columns(2)
    with c1:
        usar_logo_enc = st.checkbox(
            "✅ Mostrar logo en el **encabezado** (esquina superior derecha, semitransparente)",
            value=st.session_state.get("usar_logo_enc", True),
            help="El logo aparece al 45% de opacidad junto al nombre de la empresa",
        )
        st.session_state.usar_logo_enc = usar_logo_enc

        usar_mda = st.checkbox(
            "💧 Agregar logo como **marca de agua** (fondo de página, muy sutil)",
            value=st.session_state.get("usar_marca_agua", False),
            help="El logo aparece al 7% de opacidad en el centro de cada página — da formalismo sin distraer",
        )
        st.session_state.usar_marca_agua = usar_mda

        # Guardar en datos_empresa
        st.session_state.datos_empresa["usar_logo_encabezado"] = usar_logo_enc
        st.session_state.datos_empresa["usar_marca_agua"]      = usar_mda

    with c2:
        # Sugerencia visual de cómo queda cada opción
        st.markdown("**💡 Sugerencia — así queda tu documento:**")
        if usar_logo_enc and usar_mda:
            st.markdown("""
            <div style='border:1.5px solid #DBEAFE;border-radius:10px;padding:10px;background:#F8FAFC;font-size:.82rem'>
                <div style='display:flex;justify-content:space-between;background:#1B3F6E;
                    color:white;padding:6px 10px;border-radius:6px;margin-bottom:8px'>
                    <b>Tu Empresa SAS &nbsp; Nit #900.123</b>
                    <span style='opacity:.45;font-size:1.2rem'>🏢</span>
                </div>
                <div style='text-align:center;color:#9CA3AF;font-size:.7rem;
                    margin-bottom:6px;position:relative'>
                    <span style='opacity:.12;font-size:2rem;position:absolute;
                        left:50%;transform:translateX(-50%)'>🏢</span>
                    <b>CERTIFICACIÓN LABORAL</b>
                </div>
                <div style='color:#374151;font-size:.75rem;line-height:1.5'>
                    La empresa <b>Tu Empresa SAS</b> certifica que...
                </div>
                <div style='color:#10B981;font-size:.72rem;margin-top:6px'>
                    ✅ Logo en encabezado + marca de agua — máximo formalismo
                </div>
            </div>""", unsafe_allow_html=True)
        elif usar_logo_enc:
            st.markdown("""
            <div style='border:1.5px solid #DBEAFE;border-radius:10px;padding:10px;background:#F8FAFC;font-size:.82rem'>
                <div style='display:flex;justify-content:space-between;background:#1B3F6E;
                    color:white;padding:6px 10px;border-radius:6px;margin-bottom:8px'>
                    <b>Tu Empresa SAS &nbsp; Nit #900.123</b>
                    <span style='opacity:.45;font-size:1.2rem'>🏢</span>
                </div>
                <div style='text-align:center;color:#374151;font-size:.75rem;
                    font-weight:700;margin-bottom:6px'>CERTIFICACIÓN LABORAL</div>
                <div style='color:#374151;font-size:.75rem;line-height:1.5'>
                    La empresa <b>Tu Empresa SAS</b> certifica que...
                </div>
                <div style='color:#3B82F6;font-size:.72rem;margin-top:6px'>
                    ✅ Logo suave en encabezado — profesional y limpio
                </div>
            </div>""", unsafe_allow_html=True)
        elif usar_mda:
            st.markdown("""
            <div style='border:1.5px solid #DBEAFE;border-radius:10px;padding:10px;background:#F8FAFC;font-size:.82rem'>
                <div style='background:#1B3F6E;color:white;padding:6px 10px;
                    border-radius:6px;margin-bottom:8px'>
                    <b>Tu Empresa SAS &nbsp;&nbsp; Nit #900.123</b>
                </div>
                <div style='text-align:center;position:relative;margin-bottom:6px'>
                    <span style='opacity:.1;font-size:2.5rem;position:absolute;
                        left:50%;transform:translateX(-50%)'>🏢</span>
                    <b style='font-size:.75rem'>CERTIFICACIÓN LABORAL</b>
                </div>
                <div style='color:#374151;font-size:.75rem;line-height:1.5;margin-top:8px'>
                    La empresa <b>Tu Empresa SAS</b> certifica que...
                </div>
                <div style='color:#7C3AED;font-size:.72rem;margin-top:6px'>
                    ✅ Solo marca de agua — elegante y discreto
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='border:1.5px solid #E5E7EB;border-radius:10px;padding:10px;background:#F9FAFB;font-size:.82rem'>
                <div style='background:#1B3F6E;color:white;padding:6px 10px;
                    border-radius:6px;margin-bottom:8px'>
                    <b>Tu Empresa SAS &nbsp;&nbsp; Nit #900.123</b>
                </div>
                <div style='text-align:center;font-weight:700;font-size:.75rem;
                    margin-bottom:6px'>CERTIFICACIÓN LABORAL</div>
                <div style='color:#374151;font-size:.75rem;line-height:1.5'>
                    La empresa <b>Tu Empresa SAS</b> certifica que...
                </div>
                <div style='color:#6B7280;font-size:.72rem;margin-top:6px'>
                    ℹ️ Sin logo — solo texto (recomendado si usas papel membretado físico)
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#FEF3C7;border-left:3px solid #D97706;border-radius:0 8px 8px 0;
        padding:8px 12px;font-size:.82rem;color:#92400E;margin-top:8px'>
        💡 <b>Consejo ICONTEC:</b> Si vas a imprimir en papel membretado físico,
        desactiva ambas opciones para dejar espacio al membrete preimpreso.
        El sistema ajusta automáticamente el margen superior a 4.0cm cuando hay logo.
    </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### Configuración de correo (SMTP)")
    if smtp_configurado():
        st.success("✅ SMTP configurado. Los envíos de correo están activos.")
    else:
        st.warning("⚠️ SMTP no configurado. Activa el envío de correos en Render → Environment.")
        with st.expander("📧 Cómo configurar Gmail para envíos automáticos"):
            st.markdown(instrucciones_gmail())

# ══════════════════════════════════════════════════════════════════════════════
# DISEÑO DE PLANTILLAS — Galería con previsualizaciones reales
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🎨  Diseño de plantillas":
    from utils.preview_disenios import generar_previews, limpiar_previews, EMPRESA_DEMO
    from utils.plantillas_disenio import PALETAS

    st.markdown("# Elige el diseño de tus documentos")
    st.markdown(
        "<p style='color:#6B7280'>Mira exactamente cómo va a quedar cada documento "
        "antes de decidir. Elige el diseño predeterminado para tu empresa.</p>",
        unsafe_allow_html=True,
    )

    # ── Controles superiores ─────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        tipo_preview = st.radio(
            "Ver previsualización de:",
            ["📋 Certificado laboral", "💰 Liquidación"],
            horizontal=True,
        )
    with c3:
        if st.button("🔄 Regenerar previsualizaciones"):
            limpiar_previews()
            st.session_state.pop("previews_cert", None)
            st.session_state.pop("previews_liq", None)
            st.rerun()

    st.divider()

    # ── Generar o recuperar previews (se cachean en session_state) ───────────
    if "previews_cert" not in st.session_state or "previews_liq" not in st.session_state:
        with st.spinner("Generando previsualizaciones de los 5 diseños… (solo la primera vez)"):
            certs, liqs = generar_previews(forzar=False)
            st.session_state.previews_cert = certs
            st.session_state.previews_liq  = liqs

    previews = (st.session_state.previews_cert
                if "Certificado" in tipo_preview
                else st.session_state.previews_liq)

    # ── Galería: 5 diseños en 2 filas ────────────────────────────────────────
    # Fila 1: diseños 1, 2, 3
    nombres_disenios = {d: PALETAS[d]["nombre"] for d in range(1, 6)}
    disenio_actual = st.session_state.disenio_seleccionado

    st.markdown(
        f"<p style='color:#374151;font-size:.9rem'>✅ Diseño predeterminado actual: "
        f"<b>#{disenio_actual} — {nombres_disenios[disenio_actual]}</b></p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    for fila_disenios in [[1, 2, 3], [4, 5]]:
        cols = st.columns(len(fila_disenios))
        for col, d in zip(cols, fila_disenios):
            seleccionado = disenio_actual == d
            png = previews.get(d)

            with col:
                # Marco de selección
                borde_color = "#2D6BE4" if seleccionado else "#E5E7EB"
                sombra = "0 0 0 3px #DBEAFE, 0 4px 16px rgba(45,107,228,.15)" if seleccionado else "0 2px 8px rgba(0,0,0,.06)"

                st.markdown(
                    f'<div style="border:3px solid {borde_color};border-radius:14px;'
                    f'overflow:hidden;box-shadow:{sombra};margin-bottom:8px">',
                    unsafe_allow_html=True,
                )

                if png and Path(png).exists():
                    st.image(png, use_container_width=True)
                else:
                    st.markdown(
                        '<div style="height:300px;background:#F9FAFB;display:flex;'
                        'align-items:center;justify-content:center;color:#9CA3AF">'
                        'Sin preview disponible</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)

                # Nombre y badge
                badge = "✅ Predeterminado" if seleccionado else f"Diseño {d}"
                color_badge = "#1B3F6E" if seleccionado else "#6B7280"
                peso = "700" if seleccionado else "400"
                st.markdown(
                    f'<div style="text-align:center;margin:4px 0 8px;'
                    f'font-size:.82rem;font-weight:{peso};color:{color_badge}">'
                    f'{badge}<br><span style="font-weight:400;font-size:.78rem;color:#9CA3AF">'
                    f'{nombres_disenios[d]}</span></div>',
                    unsafe_allow_html=True,
                )

                # Botón seleccionar / descargar muestra
                if seleccionado:
                    # Descargar PDF real con datos de la empresa del usuario
                    from utils.plantillas_disenio import generar_certificado as _gc
                    from utils.preview_disenios import EMPLEADO_DEMO
                    emp_datos = st.session_state.datos_empresa if empresa_ok else EMPRESA_DEMO
                    ruta_m = str(CARPETA_SALIDAS / f"muestra_d{d}.pdf")
                    try:
                        _gc(EMPLEADO_DEMO, emp_datos, ruta_m, d)
                        with open(ruta_m, "rb") as f_pdf:
                            st.download_button(
                                "⬇️ Descargar muestra PDF",
                                f_pdf, use_container_width=True,
                                file_name=f"muestra_{nombres_disenios[d].replace(' ','_')}.pdf",
                                mime="application/pdf",
                            )
                    except Exception:
                        st.caption("Error generando muestra")
                else:
                    if st.button(
                        f"Usar este diseño", key=f"sel_{d}",
                        use_container_width=True, type="secondary",
                    ):
                        st.session_state.disenio_seleccionado = d
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    st.info(
        f"🎨 Diseño **#{disenio_actual} — {nombres_disenios[disenio_actual]}** "
        f"será aplicado a todos tus certificados, cartas de vacaciones y liquidaciones. "
        f"Puedes cambiarlo en cualquier momento."
    )
    if not empresa_ok:
        st.caption("💡 Completa los datos de tu empresa para que las muestras incluyan tu nombre y NIT.")

    st.divider()

    # ── Opciones avanzadas de personalización ────────────────────────────
    st.markdown("### ⚙️ Opciones de personalización")

    with st.expander("🖼️ Logo: posición y marca de agua", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            usar_mda = st.checkbox(
                "Usar logo como **marca de agua** (fondo semitransparente)",
                value=st.session_state.get("usar_marca_agua", False),
                help="El logo aparecerá tenuemente en el fondo de cada página",
            )
            st.session_state.usar_marca_agua = usar_mda
            if usar_mda and st.session_state.datos_empresa.get("logo_path"):
                st.caption("✅ Marca de agua activada — el logo aparecerá al 7% de opacidad en el fondo")
            elif usar_mda:
                st.caption("⚠️ Sube el logo en 'Mi empresa' para activar la marca de agua")
        with c2:
            if st.session_state.datos_empresa.get("logo_path"):
                st.image(st.session_state.datos_empresa["logo_path"],
                         width=100, caption="Logo actual (aparece en esquina derecha)")

    with st.expander("📄 Membrete personalizado desde Word (certificados y cartas)", expanded=False):
        st.markdown(
            "Si tu empresa ya tiene un documento Word con su **membrete oficial**, "
            "súbelo aquí. El sistema extraerá el encabezado y lo usará en lugar del "
            "encabezado estándar para certificados y cartas de vacaciones."
        )
        word_file = st.file_uploader(
            "Sube tu Word con membrete (.docx)", type=["docx"],
            key="word_membrete",
        )
        if word_file:
            from utils.membrete import extraer_membrete_word
            ruta_word_tmp = str(CARPETA_ASSETS / "membrete_uploaded.docx")
            with open(ruta_word_tmp, "wb") as f:
                f.write(word_file.getbuffer())
            with st.spinner("Extrayendo membrete del Word..."):
                ruta_membrete, msg_membrete = extraer_membrete_word(ruta_word_tmp)
            if ruta_membrete:
                st.success(f"✅ {msg_membrete}")
                st.image(ruta_membrete, caption="Membrete extraído — así aparecerá en tus documentos")
                st.session_state.membrete_path = ruta_membrete
            else:
                st.warning(f"⚠️ {msg_membrete}")
                st.session_state.membrete_path = None

        if st.session_state.get("membrete_path"):
            if st.button("❌ Quitar membrete personalizado"):
                st.session_state.membrete_path = None
                st.rerun()
            st.caption(f"✅ Membrete activo: {Path(st.session_state.membrete_path).name}")

    with st.expander("✍️ Firmas en liquidación", expanded=False):
        st.markdown("En la liquidación de prestaciones sociales, ¿quién debe firmar?")
        opcion_firmas = st.radio(
            "Firmas en la liquidación:",
            ["Solo representante legal",
             "Representante legal Y empleado (recomendado — deja constancia del recibido)"],
            index=1,
            key="opcion_firmas_liq",
        )
        st.session_state.firma_empleado_liq = "empleado" in opcion_firmas.lower()
        st.caption(
            "✅ La línea de firma aparece **encima** del nombre, tal como lo indicaste."
            if st.session_state.get("firma_empleado_liq") else
            "Solo la firma del representante legal."
        )

# ══════════════════════════════════════════════════════════════════════════════
# EMPLEADOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "👥  Empleados":
    st.markdown("# Cargar empleados")
    if PLANTILLA_EXCEL.exists():
        with open(PLANTILLA_EXCEL,"rb") as f:
            st.download_button("⬇️ Descargar plantilla Excel",f,
                file_name="Base_Empleados_RHFacil.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Obligatorios: **Nombre, Documento, Cargo, Salario, Fecha ingreso** · Nuevos: **Cuenta bancaria, Ingreso promedio variable, Correo**")
    st.divider()
    archivo = st.file_uploader("Sube tu Excel de empleados", type=["xlsx"])
    if archivo:
        df, err_col, err_fila = cargar_y_validar(archivo)
        if err_col:
            for e in err_col: st.error(e)
        else:
            if err_fila:
                st.warning(f"⚠️ {len(err_fila)} problema(s):")
                for e in err_fila: st.write(f"- {e}")
            else:
                st.success(f"✅ {len(df)} empleado(s) cargados sin errores.")
            st.dataframe(df, use_container_width=True)
            if not err_fila:
                st.session_state.df_empleados = df
            elif st.button("Continuar con filas válidas"):
                st.session_state.df_empleados = df

# ══════════════════════════════════════════════════════════════════════════════
# GENERAR DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "⚡  Generar docs":
    st.markdown("# Generar documentos")
    if not empresa_ok:
        st.error("⚠️ Completa los **datos de tu empresa** primero."); st.stop()
    if st.session_state.df_empleados is None:
        st.error("⚠️ Carga una **base de empleados** primero."); st.stop()

    df             = st.session_state.df_empleados
    datos_empresa  = st.session_state.datos_empresa
    disenio        = st.session_state.disenio_seleccionado
    max_docs       = plan_info["max_docs"]
    sin_limite     = not plan_info["tiene_limite"]
    docs_usados    = usuario.get("documentos_usados",0)
    docs_restantes = None if sin_limite else max(0, max_docs - docs_usados)

    c1,c2,c3 = st.columns(3)
    c1.metric("Empresa", datos_empresa["nombre"])
    c2.metric("Empleados", len(df))
    c3.metric("Diseño activo", f"#{disenio} {nombre_disenio(disenio)}")
    st.divider()

    # ── BUG FIX: checkboxes sin valor por defecto True ──
    st.markdown("### Selecciona qué documentos generar")
    c1,c2,c3 = st.columns(3)
    with c1: gen_cert = st.checkbox("📋 Certificados laborales")
    with c2: gen_vac  = st.checkbox("🏖️ Cartas de vacaciones")
    with c3: gen_liq  = st.checkbox("💰 Liquidaciones de prestaciones")

    # Ingresos variables (solo para certificados)
    ing_variable_global = 0
    if gen_cert:
        st.markdown("**Certificados laborales:**")
        tiene_variable = st.radio(
            "¿Algún empleado tiene ingresos variables?",
            ["No", "Sí — usar el valor del Excel por empleado",
             "Sí — aplicar un valor global a todos"],
            horizontal=True,
        )
        if tiene_variable == "Sí — aplicar un valor global a todos":
            ing_variable_global = st.number_input(
                "Promedio mensual de ingresos variables ($)",
                min_value=0, value=0, step=50000,
                help="Se incluirá en todos los certificados de esta generación.")

    # Vacaciones
    fecha_ini_vac = fecha_fin_vac = None
    if gen_vac:
        st.markdown("**Período de vacaciones:**")
        c1,c2 = st.columns(2)
        with c1: fecha_ini_vac = st.date_input("Fecha inicio", date.today(), key="vi")
        with c2: fecha_fin_vac = st.date_input("Fecha fin", date.today(), key="vf")

    # Liquidaciones
    fecha_corte_liq = None; motivo_retiro = "renuncia"
    if gen_liq:
        st.markdown("**Liquidaciones:**")
        c1,c2 = st.columns(2)
        with c1:
            fecha_corte_liq = st.date_input("Fecha de corte (activos)", date.today())
        with c2:
            MOTIVOS = {"renuncia":"Renuncia voluntaria","despido_sin_justa_causa":"Despido sin justa causa (Art.64 CST)",
                "mutuo_acuerdo":"Mutuo acuerdo","vencimiento_contrato":"Vencimiento de contrato"}
            motivo_retiro = st.selectbox("Motivo de retiro",
                list(MOTIVOS.keys()), format_func=lambda x: MOTIVOS[x])
        if motivo_retiro == "despido_sin_justa_causa":
            st.warning("⚠️ La indemnización es una estimación. Valídala con un abogado laboral.")

    # Correo
    st.divider()
    enviar_correos = False
    if smtp_configurado():
        enviar_correos = st.checkbox(
            "📧 Enviar documentos por correo a cada empleado",
            help="Requiere que cada empleado tenga correo en el Excel.")
    else:
        st.caption("💡 Configura SMTP en 'Mi empresa' para habilitar el envío por correo.")

    st.divider()
    tipos = sum([gen_cert, gen_vac, gen_liq])
    docs_a_generar = len(df) * tipos
    if not sin_limite and docs_restantes is not None and docs_a_generar > docs_restantes:
        st.warning(f"⚠️ Se generarán {min(docs_a_generar, docs_restantes)} de {docs_a_generar} docs (límite de plan).")

    if st.button("🚀 Generar documentos", type="primary"):
        if tipos == 0:
            st.error("Selecciona al menos un tipo de documento."); st.stop()

        archivos_generados = []; errores = []; contador = 0
        limite = docs_restantes if not sin_limite else 99999
        barra  = st.progress(0, text="Generando…")
        total  = len(df) * tipos

        # ── Preparar datos de firmantes por tipo ─────────────────────────
        de = datos_empresa
        rep = de.get("representante","")
        datos_cert = {**de,
            "representante": de.get("firmante_cert_nombre") or rep,
            "_cargo_firmante": de.get("firmante_cert_cargo") or "Representante Legal",
        }
        datos_vac = {**de,
            "representante": de.get("firmante_vac_nombre") or rep,
            "_cargo_firmante": de.get("firmante_vac_cargo") or "Representante Legal",
        }
        datos_liq = {**de,
            "representante": de.get("firmante_liq_nombre") or rep,
            "_cargo_firmante": de.get("firmante_liq_cargo") or "Representante Legal",
        }
        membrete  = st.session_state.get("membrete_path")
        usar_mda  = st.session_state.get("usar_marca_agua", False)
        firma_emp = st.session_state.get("firma_empleado_liq", True)

        for paso, (_, fila) in enumerate(df.iterrows()):
            if contador >= limite: break
            empleado = fila.to_dict()
            nb = str(fila.get("Nombre","x")).strip().replace(" ","_")
            pdfs_empleado = []

            if gen_cert and contador < limite:
                if tiene_variable == "Sí — usar el valor del Excel por empleado":
                    empleado["Ingreso promedio variable"] = fila.get("Ingreso promedio variable", 0) or 0
                elif tiene_variable == "Sí — aplicar un valor global a todos":
                    empleado["Ingreso promedio variable"] = ing_variable_global
                try:
                    ruta = str(CARPETA_SALIDAS / f"Certificado_{nb}.pdf")
                    generar_certificado(empleado, datos_cert, ruta, disenio,
                                        usar_mda, membrete)
                    archivos_generados.append(Path(ruta)); pdfs_empleado.append(ruta)
                    contador += 1
                except Exception as e:
                    errores.append(f"Cert {fila.get('Nombre')}: {e}")

            if gen_vac and contador < limite:
                try:
                    ruta = str(CARPETA_SALIDAS / f"Vacaciones_{nb}.pdf")
                    generar_vacaciones(empleado, datos_vac, ruta,
                        fecha_ini_vac.strftime("%d/%m/%Y"),
                        fecha_fin_vac.strftime("%d/%m/%Y"),
                        disenio, usar_mda, membrete)
                    archivos_generados.append(Path(ruta)); pdfs_empleado.append(ruta)
                    contador += 1
                except Exception as e:
                    errores.append(f"Vac {fila.get('Nombre')}: {e}")

            # Envío por correo individual
            if enviar_correos and pdfs_empleado:
                correo_emp_dest = str(fila.get("Correo","")).strip()
                if correo_emp_dest and "@" in correo_emp_dest:
                    ok_mail, msg_mail = enviar_documentos(
                        correo_emp_dest, str(fila.get("Nombre","")),
                        datos_empresa["nombre"], "Documentos laborales",
                        pdfs_empleado, datos_empresa.get("correo_empresa",""))
                    if not ok_mail: errores.append(f"Correo {fila.get('Nombre')}: {msg_mail}")

            barra.progress(min((paso+1)/len(df), 1.0))

        # Liquidaciones en bloque
        if gen_liq and contador < limite:
            df_res, err_liq = calcular_liquidacion_df(
                df.copy(),
                fecha_corte_default=datetime(fecha_corte_liq.year,
                    fecha_corte_liq.month, fecha_corte_liq.day),
                motivo_retiro=motivo_retiro)
            errores.extend(err_liq)
            for _, res in df_res.iterrows():
                if contador >= limite: break
                nb = str(res["Nombre"]).strip().replace(" ","_")
                try:
                    ruta = str(CARPETA_SALIDAS / f"Liquidacion_{nb}.pdf")
                    generar_liquidacion(res.to_dict(), datos_liq, ruta, disenio,
                                        usar_mda, membrete, firma_empleado=firma_emp)
                    archivos_generados.append(Path(ruta))
                    contador += 1
                    if enviar_correos:
                        correo_emp_dest = str(df.loc[df["Nombre"]==res["Nombre"],"Correo"].values[0] if "Correo" in df.columns else "").strip()
                        if correo_emp_dest and "@" in correo_emp_dest:
                            enviar_documentos(correo_emp_dest, res["Nombre"],
                                datos_empresa["nombre"], "Liquidación de Prestaciones Sociales",
                                [ruta], datos_empresa.get("correo_empresa",""))
                except Exception as e:
                    errores.append(f"Liq {res['Nombre']}: {e}")

            if not df_res.empty:
                ruta_xls = str(CARPETA_SALIDAS / "Resumen_Liquidaciones.xlsx")
                df_res.to_excel(ruta_xls, index=False)
                archivos_generados.append(Path(ruta_xls))

        barra.progress(1.0, text="¡Listo!")
        registrar_uso_usuario(usuario["email"], contador)
        usuario["documentos_usados"] = usuario.get("documentos_usados",0) + contador
        st.session_state.archivos_generados = archivos_generados

        if errores:
            st.warning(f"{len(errores)} error(es):")
            for e in errores: st.write(f"- {e}")
        if archivos_generados:
            st.success(f"✅ {contador} documento(s) generados con el diseño **{nombre_disenio(disenio)}**.")

    # Descargar ZIP
    if st.session_state.archivos_generados:
        st.divider()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf,"w") as zf:
            for p in st.session_state.archivos_generados:
                if Path(p).exists(): zf.write(p, Path(p).name)
        buf.seek(0)
        st.download_button("⬇️ Descargar todos los documentos (ZIP)", buf,
            file_name=f"RHFacil_{datos_empresa['nombre'].replace(' ','_')}_{date.today()}.zip",
            mime="application/zip", type="primary")
        with st.expander("Ver archivos generados"):
            for p in st.session_state.archivos_generados:
                st.write(f"- {Path(p).name}")

# ══════════════════════════════════════════════════════════════════════════════
# PLANES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "💎  Planes":
    st.markdown("# Planes y precios")
    st.markdown("<p style='color:#6B7280'>Escríbenos por WhatsApp y activamos tu plan en minutos.</p>", unsafe_allow_html=True)
    st.divider()
    cols = st.columns(4)
    plan_keys = ["gratuito","basico","pro","empresarial"]
    for col, key in zip(cols, plan_keys):
        plan = PLANES[key]
        precio = "Gratis" if plan["precio"]==0 else f"${plan['precio']:,}".replace(",",".")
        periodo = "" if plan["precio"]==0 else "/mes"
        activo  = usuario["plan"] == key
        features = "".join([f'<div class="plan-feature">✓ {f}</div>' for f in plan["features"]])
        with col:
            st.markdown(f"""
            <div class="plan-card {'destacado' if key in ('basico','pro') else ''}">
                <div style="font-weight:700;font-size:1rem;margin-bottom:.5rem">{plan['nombre']}</div>
                <div class="plan-precio">{precio}</div>
                <div class="plan-periodo">{periodo}</div>
                <hr style="border-color:#E5E7EB;margin:.6rem 0">
                {features}
            </div>""", unsafe_allow_html=True)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if activo:
                st.markdown("<p style='text-align:center;font-size:0.8rem;color:#059669'>✅ Plan actual</p>", unsafe_allow_html=True)
            else:
                msg = f"Quiero activar el plan {plan['nombre']} de RH Fácil (${plan['precio']:,}/mes). Mi correo es {usuario['email']}".replace(",",".")
                st.link_button("💬 Activar por WhatsApp", link_whatsapp(msg), use_container_width=True)
    st.divider()
    st.markdown("<p style='text-align:center;color:#6B7280;font-size:0.85rem'>💳 Aceptamos transferencia, Nequi y PSE · Activación en menos de 2 horas · Cancela cuando quieras</p>", unsafe_allow_html=True)
