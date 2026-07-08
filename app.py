"""
RH Fácil v16 — App principal con Supabase, onboarding y dashboard
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime
import zipfile, io

# ── DB (Supabase con fallback JSON) ──────────────────────────────────────────
from utils.db_bridge import (
    usuario_login, usuario_registrar, usuario_registrar_uso,
    empresa_guardar, empresa_cargar,
    admin_listar, admin_activar, admin_cambiar_plan, admin_eliminar, admin_stats,
    usar_supabase,
)
from utils.plan_control import PLANES, link_whatsapp
from utils.calcular_liquidacion import calcular_liquidacion_df, SALARIO_MINIMO_2026, AUXILIO_TRANSPORTE_2026
from utils.validar_datos import cargar_y_validar
from utils.plantillas_disenio import (
    generar_certificado, generar_vacaciones, generar_liquidacion, nombre_disenio, PALETAS,
)
from utils.preview_disenios import generar_previews, limpiar_previews
from utils.correo import enviar_documentos, smtp_configurado, instrucciones_gmail
from utils.estilos import CSS

st.set_page_config(page_title="RH Fácil", page_icon="📄", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

CARPETA_SALIDAS = Path("salidas"); CARPETA_SALIDAS.mkdir(exist_ok=True)
CARPETA_ASSETS  = Path("assets");  CARPETA_ASSETS.mkdir(exist_ok=True)
PLANTILLA_EXCEL = Path("plantillas/Base_Empleados.xlsx")
ADMIN_EMAIL     = "admin@rhfacil.co"

# ── Estado de sesión ──────────────────────────────────────────────────────────
DEFAULTS = {
    "usuario": None,
    "datos_empresa": {
        "nombre":"","nit":"","representante":"","correo_empresa":"","logo_path":None,
        "firmante_cert_nombre":"","firmante_cert_cargo":"",
        "firmante_vac_nombre": "","firmante_vac_cargo": "",
        "firmante_liq_nombre": "","firmante_liq_cargo": "",
        "usar_logo_encabezado": True, "usar_marca_agua": False,
        "disenio_seleccionado": 1,
    },
    "df_empleados":         None,
    "archivos_generados":   [],
    "disenio_seleccionado": 1,
    "usar_marca_agua":      False,
    "usar_logo_enc":        True,
    "firma_empleado_liq":   True,
    "membrete_path":        None,
    "previews_cert":        None,
    "previews_liq":         None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: LOGIN / REGISTRO / ONBOARDING
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_auth():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div style='text-align:center;padding:2rem 0 1rem'>
            <div style='font-size:2.5rem'>📄</div>
            <h1 style='color:#1B3F6E;margin:0'>RH Fácil</h1>
            <p style='color:#6B7280;margin-top:4px'>
                Documentos laborales para PYMES colombianas
            </p>
        </div>""", unsafe_allow_html=True)

        tab_login, tab_reg = st.tabs(["🔐 Ingresar", "✨ Crear cuenta"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            email_l = st.text_input("Correo", key="l_email", placeholder="tucorreo@empresa.com")
            pass_l  = st.text_input("Contraseña", type="password", key="l_pass")
            if st.button("Ingresar", type="primary", use_container_width=True):
                ok, msg, datos = usuario_login(email_l, pass_l)
                if ok:
                    st.session_state.usuario = datos
                    # Cargar empresa guardada
                    empresa = empresa_cargar(email_l)
                    if empresa:
                        st.session_state.datos_empresa = {
                            **st.session_state.datos_empresa, **empresa
                        }
                        st.session_state.disenio_seleccionado = empresa.get("disenio_seleccionado", 1)
                        st.session_state.usar_logo_enc   = empresa.get("usar_logo_encabezado", True)
                        st.session_state.usar_marca_agua = empresa.get("usar_marca_agua", False)
                    st.rerun()
                else:
                    st.error(msg)

            st.divider()
            st.markdown("""
            <div style='background:#EFF6FF;border-radius:10px;padding:1rem'>
                <p style='margin:0;font-size:.85rem;color:#1B3F6E;font-weight:600'>
                    🎯 Cuenta Demo — acceso completo</p>
                <p style='margin:4px 0 0;font-size:.82rem;color:#374151'>
                    <b>Usuario:</b> demo@rhfacil.co &nbsp;·&nbsp;
                    <b>Contraseña:</b> RHFacil2026</p>
            </div>""", unsafe_allow_html=True)

        with tab_reg:
            st.markdown("<br>", unsafe_allow_html=True)
            nombre_r  = st.text_input("Nombre completo *", key="r_nombre")
            email_r   = st.text_input("Correo electrónico *", key="r_email")
            empresa_r = st.text_input("Nombre de tu empresa *", key="r_empresa",
                                       placeholder="Distribuciones ABC SAS")
            tel_r     = st.text_input("Teléfono / WhatsApp", key="r_tel",
                                       placeholder="300 123 4567")
            pass_r    = st.text_input("Contraseña (mín. 6 caracteres) *", type="password", key="r_pass")
            pass_r2   = st.text_input("Confirmar contraseña *", type="password", key="r_pass2")

            if st.button("Crear cuenta gratis", type="primary", use_container_width=True):
                if pass_r != pass_r2:
                    st.error("Las contraseñas no coinciden.")
                elif not empresa_r.strip():
                    st.error("Ingresa el nombre de tu empresa.")
                else:
                    ok, msg = usuario_registrar(email_r, nombre_r, pass_r,
                                                 empresa_r, tel_r)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.info("Cuando el administrador active tu cuenta, ya tendrás tu empresa pre-configurada para empezar de inmediato.")
                    else:
                        st.error(msg)


def pantalla_onboarding():
    """Flujo único de configuración de empresa al primer ingreso."""
    u = st.session_state.usuario
    st.markdown(f"""
    <div style='text-align:center;padding:2rem 0 1rem'>
        <div style='font-size:2rem'>🎉</div>
        <h2 style='color:#1B3F6E'>¡Bienvenido, {u['nombre'].split()[0]}!</h2>
        <p style='color:#6B7280'>Configura tu empresa una sola vez.
        Estos datos aparecerán en todos tus documentos.</p>
    </div>""", unsafe_allow_html=True)

    with st.form("onboarding_empresa"):
        st.markdown("### 1. Datos de la empresa")
        c1, c2 = st.columns(2)
        with c1:
            nombre     = st.text_input("Razón social *", placeholder="Distribuciones ABC SAS")
            nit        = st.text_input("NIT *", placeholder="900123456-7")
            ciudad     = st.text_input("Ciudad", placeholder="Medellín")
        with c2:
            representante = st.text_input("Representante legal *",
                placeholder="Nombre completo")
            correo_emp = st.text_input("Correo corporativo *",
                placeholder="rrhh@miempresa.com")
            tel_emp    = st.text_input("Teléfono empresa", placeholder="604 123 4567")

        st.markdown("### 2. Responsables de firma")
        st.caption("¿Quién firma cada documento? Si es siempre el representante legal, déjalo vacío.")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**📋 Certificados**")
            fcn = st.text_input("Nombre firmante cert.", key="o_fcn")
            fcc = st.text_input("Cargo", key="o_fcc", placeholder="Líder de RH")
        with c2:
            st.markdown("**🏖️ Vacaciones**")
            fvn = st.text_input("Nombre firmante vac.", key="o_fvn")
            fvc = st.text_input("Cargo", key="o_fvc", placeholder="Gerente Admin.")
        with c3:
            st.markdown("**💰 Liquidaciones**")
            fln = st.text_input("Nombre firmante liq.", key="o_fln")
            flc = st.text_input("Cargo", key="o_flc", placeholder="Representante Legal")

        st.markdown("### 3. Identidad visual")
        logo = st.file_uploader("Logo de tu empresa (PNG o JPG)", type=["png","jpg","jpeg"])
        c1, c2 = st.columns(2)
        with c1:
            uso_logo = st.checkbox("Logo en encabezado (esquina superior derecha)", value=True)
        with c2:
            uso_mda  = st.checkbox("Logo como marca de agua (fondo de página)")

        guardar = st.form_submit_button("💾 Guardar y empezar a generar documentos",
                                         type="primary", use_container_width=True)
        if guardar:
            if not nombre or not nit or not representante or not correo_emp:
                st.error("Completa los campos obligatorios (*)")
            else:
                logo_path = None
                if logo:
                    ext = logo.name.split(".")[-1]
                    logo_path = str(CARPETA_ASSETS / f"logo_{u['email'].split('@')[0]}.{ext}")
                    with open(logo_path, "wb") as f:
                        f.write(logo.getbuffer())

                datos_emp = {
                    "nombre": nombre, "nit": nit,
                    "representante": representante,
                    "correo_empresa": correo_emp,
                    "ciudad": ciudad, "telefono_empresa": tel_emp,
                    "firmante_cert_nombre": fcn.strip() or representante,
                    "firmante_cert_cargo":  fcc.strip() or "Representante Legal",
                    "firmante_vac_nombre":  fvn.strip() or representante,
                    "firmante_vac_cargo":   fvc.strip() or "Representante Legal",
                    "firmante_liq_nombre":  fln.strip() or representante,
                    "firmante_liq_cargo":   flc.strip() or "Representante Legal",
                    "usar_logo_encabezado": uso_logo,
                    "usar_marca_agua":      uso_mda,
                    "disenio_seleccionado": 1,
                    "logo_path": logo_path,
                }
                empresa_guardar(u["email"], datos_emp)
                st.session_state.datos_empresa = datos_emp
                st.session_state.usar_logo_enc   = uso_logo
                st.session_state.usar_marca_agua = uso_mda
                st.session_state.usuario["onboarding_completo"] = True
                st.success("✅ ¡Empresa configurada! Ya puedes generar documentos.")
                st.rerun()

    if st.button("⏭️ Completar después", help="Puedes configurar la empresa más tarde"):
        st.session_state.usuario["onboarding_completo"] = True
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# FLUJO DE AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.usuario:
    pantalla_auth()
    st.stop()

u = st.session_state.usuario

# Mostrar onboarding si es primer ingreso y empresa no configurada
if not u.get("onboarding_completo") and not u.get("es_admin"):
    pantalla_onboarding()
    st.stop()

empresa_ok = bool(st.session_state.datos_empresa.get("nombre") and
                  st.session_state.datos_empresa.get("nit"))

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📄 RH Fácil")
    st.caption(f"Hola, **{u['nombre'].split()[0]}** 👋")
    if usar_supabase():
        st.caption("🟢 Base de datos activa")
    st.divider()

    nav_opciones = [
        "🏠  Inicio", "🏢  Mi empresa", "👥  Empleados",
        "🎨  Diseño", "⚡  Generar", "💎  Planes",
    ]
    if u.get("es_admin"):
        nav_opciones.append("🛡️  Admin")

    pagina = st.radio("nav", nav_opciones, label_visibility="collapsed")
    st.divider()

    plan_info_sidebar = PLANES.get(u["plan"], PLANES["gratuito"])
    docs_usados       = u.get("documentos_usados", 0)
    max_docs          = plan_info_sidebar["max_documentos"]
    sin_limite        = not plan_info_sidebar["limite"]

    st.markdown(f"""
    <div class="sidebar-plan-badge">
        <div class="sidebar-plan-nombre">Plan {u['plan'].capitalize()}</div>
        <div class="sidebar-plan-docs">
            {'✅ Sin límite de documentos' if sin_limite
             else f'📄 {docs_usados} usados · {max(0, max_docs - docs_usados)} restantes'}
        </div>
    </div>""", unsafe_allow_html=True)

    if not sin_limite and max_docs > 0:
        st.progress(min(docs_usados / max_docs, 1.0))

    st.divider()
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        for k in DEFAULTS:
            st.session_state[k] = DEFAULTS[k]
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# INICIO — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "🏠  Inicio":
    nombre_emp = st.session_state.datos_empresa.get("nombre","tu empresa")

    # Hero personalizado
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1B3F6E,#2D6BE4);
        border-radius:16px;padding:2.5rem;margin-bottom:1.5rem;color:white'>
        <h1 style='margin:0 0 .5rem;font-size:1.8rem'>
            Buenos días, {u['nombre'].split()[0]} 👋</h1>
        <p style='margin:0;opacity:.85;font-size:1.05rem'>
            {nombre_emp} · Plan <b>{u['plan'].capitalize()}</b></p>
        <p style='margin:.8rem 0 0;opacity:.7;font-size:.9rem'>
            RH Fácil te ayuda a generar certificados laborales, cartas de vacaciones
            y liquidaciones en segundos, cumpliendo el CST colombiano 2026.
        </p>
    </div>""", unsafe_allow_html=True)

    # Métricas rápidas
    docs_rest = max(0, max_docs - docs_usados) if not sin_limite else None
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Docs generados", docs_usados)
    c2.metric("📋 Disponibles", "∞" if sin_limite else docs_rest)
    c3.metric("🎨 Diseño activo",
              f"#{st.session_state.disenio_seleccionado} "
              f"{nombre_disenio(st.session_state.disenio_seleccionado)}")
    c4.metric("💾 Base de datos", "Supabase ☁️" if usar_supabase() else "Local 💻")

    st.divider()

    # ── ¿Qué puedes hacer? ───────────────────────────────────────────────────
    st.markdown("### ¿Qué puedes generar hoy?")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style='border:1.5px solid #DBEAFE;border-radius:12px;padding:1.2rem'>
            <div style='font-size:1.8rem'>📋</div>
            <h4 style='color:#1B3F6E;margin:.5rem 0 .3rem'>Certificado Laboral</h4>
            <p style='color:#6B7280;font-size:.85rem;margin:0'>
                Certifica antigüedad, cargo y salario de cualquier empleado.
                Con fecha de expedición y firma del responsable.
            </p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style='border:1.5px solid #D1FAE5;border-radius:12px;padding:1.2rem'>
            <div style='font-size:1.8rem'>🏖️</div>
            <h4 style='color:#064E3B;margin:.5rem 0 .3rem'>Carta de Vacaciones</h4>
            <p style='color:#6B7280;font-size:.85rem;margin:0'>
                Informa el período de vacaciones aprobado. Art. 186 CST.
                Generación masiva para toda la nómina.
            </p>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div style='border:1.5px solid #FEF3C7;border-radius:12px;padding:1.2rem'>
            <div style='font-size:1.8rem'>💰</div>
            <h4 style='color:#92400E;margin:.5rem 0 .3rem'>Liquidación de Prestaciones</h4>
            <p style='color:#6B7280;font-size:.85rem;margin:0'>
                Cesantías, intereses, prima, vacaciones, salario pendiente e
                indemnización. Con paz y salvo y firmas dobles.
            </p>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Flujo de 3 pasos ─────────────────────────────────────────────────────
    st.markdown("### Cómo funciona")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style='text-align:center;padding:1rem'>
            <div style='width:48px;height:48px;background:#EFF6FF;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-weight:700;color:#1B3F6E;font-size:1.3rem;margin:0 auto .8rem'>1</div>
            <h4 style='color:#1B3F6E;margin:0 0 .3rem'>Sube el Excel</h4>
            <p style='color:#6B7280;font-size:.85rem;margin:0'>
                Carga la base de empleados con nuestra plantilla o la tuya.
            </p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style='text-align:center;padding:1rem'>
            <div style='width:48px;height:48px;background:#EFF6FF;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-weight:700;color:#1B3F6E;font-size:1.3rem;margin:0 auto .8rem'>2</div>
            <h4 style='color:#1B3F6E;margin:0 0 .3rem'>Selecciona documentos</h4>
            <p style='color:#6B7280;font-size:.85rem;margin:0'>
                Certificados, vacaciones o liquidaciones. Uno o todos a la vez.
            </p>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div style='text-align:center;padding:1rem'>
            <div style='width:48px;height:48px;background:#EFF6FF;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-weight:700;color:#1B3F6E;font-size:1.3rem;margin:0 auto .8rem'>3</div>
            <h4 style='color:#1B3F6E;margin:0 0 .3rem'>Descarga o envía</h4>
            <p style='color:#6B7280;font-size:.85rem;margin:0'>
                PDFs listos en ZIP. O envía directo al correo de cada empleado.
            </p>
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.warning(
        f"⚖️ Las liquidaciones son una **estimación de referencia** (CST 2026). "
        f"SMMLV: **${SALARIO_MINIMO_2026:,.0f}** · "
        f"Auxilio transporte: **${AUXILIO_TRANSPORTE_2026:,.0f}**. "
        "Valide siempre con su contador.".replace(",",".")
    )

# ══════════════════════════════════════════════════════════════════════════════
# MI EMPRESA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏢  Mi empresa":
    st.markdown("# Datos de tu empresa")
    st.caption("Se guardan automáticamente en la nube. Al cerrar sesión y volver, estarán aquí.")

    with st.form("form_empresa"):
        c1, c2 = st.columns(2)
        de = st.session_state.datos_empresa
        with c1:
            nombre        = st.text_input("Razón social *", value=de.get("nombre",""),
                               placeholder="Distribuciones ABC SAS")
            nit           = st.text_input("NIT *", value=de.get("nit",""),
                               placeholder="900123456-7")
            correo_emp    = st.text_input("Correo corporativo *",
                               value=de.get("correo_empresa",""),
                               placeholder="rrhh@miempresa.com")
            ciudad        = st.text_input("Ciudad", value=de.get("ciudad",""),
                               placeholder="Medellín")
        with c2:
            representante = st.text_input("Representante legal *",
                               value=de.get("representante",""))
            tel_emp       = st.text_input("Teléfono empresa",
                               value=de.get("telefono_empresa",""))
            logo          = st.file_uploader("Logo (PNG o JPG)",
                               type=["png","jpg","jpeg"])

        st.divider()
        st.markdown("### ✍️ Responsables de firma")
        st.caption("Vacío = usa el representante legal")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**📋 Certificados**")
            fcn = st.text_input("Nombre", value=de.get("firmante_cert_nombre",""), key="fcn")
            fcc = st.text_input("Cargo",  value=de.get("firmante_cert_cargo",""),  key="fcc")
        with c2:
            st.markdown("**🏖️ Vacaciones**")
            fvn = st.text_input("Nombre", value=de.get("firmante_vac_nombre",""),  key="fvn")
            fvc = st.text_input("Cargo",  value=de.get("firmante_vac_cargo",""),   key="fvc")
        with c3:
            st.markdown("**💰 Liquidaciones**")
            fln = st.text_input("Nombre", value=de.get("firmante_liq_nombre",""),  key="fln")
            flc = st.text_input("Cargo",  value=de.get("firmante_liq_cargo",""),   key="flc")

        guardar = st.form_submit_button("💾 Guardar en la nube", type="primary")
        if guardar:
            if not nombre or not nit or not representante or not correo_emp:
                st.error("Completa los campos obligatorios (*)")
            else:
                logo_path = de.get("logo_path")
                if logo:
                    ext = logo.name.split(".")[-1]
                    logo_path = str(CARPETA_ASSETS / f"logo_{u['email'].split('@')[0]}.{ext}")
                    with open(logo_path,"wb") as f: f.write(logo.getbuffer())

                datos_nuevo = {
                    "nombre":nombre,"nit":nit,"representante":representante,
                    "correo_empresa":correo_emp,"ciudad":ciudad,
                    "telefono_empresa":tel_emp,"logo_path":logo_path,
                    "firmante_cert_nombre": fcn.strip() or representante,
                    "firmante_cert_cargo":  fcc.strip() or "Representante Legal",
                    "firmante_vac_nombre":  fvn.strip() or representante,
                    "firmante_vac_cargo":   fvc.strip() or "Representante Legal",
                    "firmante_liq_nombre":  fln.strip() or representante,
                    "firmante_liq_cargo":   flc.strip() or "Representante Legal",
                    "usar_logo_encabezado": st.session_state.get("usar_logo_enc", True),
                    "usar_marca_agua":      st.session_state.get("usar_marca_agua", False),
                    "disenio_seleccionado": st.session_state.disenio_seleccionado,
                }
                empresa_guardar(u["email"], datos_nuevo)
                st.session_state.datos_empresa = datos_nuevo
                st.success("✅ Datos guardados en la nube. Disponibles en tu próximo inicio de sesión.")

    # Opciones de logo
    de = st.session_state.datos_empresa
    if de.get("logo_path") and Path(de["logo_path"]).exists():
        st.image(de["logo_path"], width=120, caption="Logo actual")

    st.divider()
    st.markdown("### 🖼️ Visualización del logo")
    c1, c2 = st.columns(2)
    with c1:
        uso_logo = st.checkbox("Logo en encabezado (esquina superior derecha)",
            value=st.session_state.get("usar_logo_enc", True))
        uso_mda  = st.checkbox("Logo como marca de agua (fondo de página)",
            value=st.session_state.get("usar_marca_agua", False))
        st.session_state.usar_logo_enc   = uso_logo
        st.session_state.usar_marca_agua = uso_mda
    with c2:
        if uso_logo and uso_mda:
            st.info("✅ Logo en encabezado + marca de agua — máximo formalismo")
        elif uso_logo:
            st.info("✅ Logo suave en encabezado — profesional y limpio")
        elif uso_mda:
            st.info("✅ Solo marca de agua — elegante y discreto")
        else:
            st.info("ℹ️ Sin logo — ideal para papel membretado físico")

# ══════════════════════════════════════════════════════════════════════════════
# EMPLEADOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "👥  Empleados":
    from utils.empleados_db import (
        empleados_listar, empleados_buscar, empleado_guardar,
        empleado_retirar, empleado_eliminar, empleados_importar_excel,
        empleados_stats,
    )

    email_usr = usuario["email"]
    st.markdown("# Base de empleados")

    # ── Tabs principales ──────────────────────────────────────────────────────
    tab_buscar, tab_agregar, tab_importar, tab_todos = st.tabs([
        "🔍 Buscar y seleccionar",
        "➕ Agregar empleado",
        "📥 Importar Excel",
        "📋 Ver todos",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: BUSCADOR + CARRITO DE GENERACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    with tab_buscar:
        st.markdown("### Busca el empleado y agrégalo a la lista de generación")

        # Inicializar carrito
        if "carrito_empleados" not in st.session_state:
            st.session_state.carrito_empleados = {}  # {documento: config}

        col_busq, col_stats = st.columns([3, 1])
        with col_busq:
            query = st.text_input("🔍 Buscar por nombre o número de documento",
                placeholder="Ej: María López o 1020304050",
                key="busq_empleado")
        with col_stats:
            stats = empleados_stats(email_usr)
            st.metric("Total empleados", stats["total"])
            st.metric("Activos", stats["activos"])

        # Resultados de búsqueda
        if query and len(query) >= 2:
            resultados = empleados_buscar(email_usr, query)
            if not resultados:
                st.info(f"No se encontraron empleados con '{query}'")
            else:
                st.caption(f"{len(resultados)} resultado(s) encontrado(s)")
                for emp in resultados:
                    doc  = str(emp.get("documento",""))
                    nom  = emp.get("nombre","")
                    carg = emp.get("cargo","")
                    sal  = float(emp.get("salario", 0) or 0)
                    activo = emp.get("activo", True)
                    en_carrito = doc in st.session_state.carrito_empleados

                    with st.container():
                        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                        with c1:
                            estado = "🟢" if activo else "🔴"
                            st.markdown(f"**{estado} {nom}**  \n"
                                       f"<span style='color:#6B7280;font-size:.85rem'>"
                                       f"CC {doc} · {carg}</span>",
                                       unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"<span style='color:#1B3F6E;font-weight:600'>"
                                       f"${sal:,.0f}</span>".replace(",","."),
                                       unsafe_allow_html=True)
                        with c3:
                            if en_carrito:
                                if st.button("✅ Agregado", key=f"rm_{doc}",
                                             use_container_width=True):
                                    del st.session_state.carrito_empleados[doc]
                                    st.rerun()
                            else:
                                if st.button("➕ Agregar", key=f"add_{doc}",
                                             type="primary", use_container_width=True):
                                    st.session_state.carrito_empleados[doc] = {
                                        "empleado": emp,
                                        "mostrar_salario": True,
                                        "tiene_variable": False,
                                        "salario_variable": 0,
                                        "docs": {"cert": True, "vac": False, "liq": False},
                                        "fecha_ini_vac": str(date.today()),
                                        "fecha_fin_vac": str(date.today()),
                                        "motivo_retiro": "renuncia",
                                    }
                                    st.rerun()
                        with c4:
                            if not activo:
                                st.caption("Retirado")
                        st.divider()

        elif not query:
            st.caption("Escribe al menos 2 caracteres para buscar")

        # ── CARRITO DE GENERACIÓN ─────────────────────────────────────────────
        if st.session_state.carrito_empleados:
            st.markdown("---")
            st.markdown(f"### ⚡ Generar documentos "
                       f"({len(st.session_state.carrito_empleados)} empleado(s))")

            for doc, config in list(st.session_state.carrito_empleados.items()):
                emp = config["empleado"]
                nom = emp.get("nombre","")
                sal = float(emp.get("salario", 0) or 0)

                with st.expander(f"**{nom}** — CC {doc}", expanded=True):
                    c1, c2 = st.columns([2, 1])

                    with c1:
                        # Documentos a generar
                        st.markdown("**¿Qué documentos generar?**")
                        cc1, cc2, cc3 = st.columns(3)
                        with cc1:
                            config["docs"]["cert"] = st.checkbox(
                                "📋 Certificado", value=config["docs"]["cert"],
                                key=f"cert_{doc}")
                        with cc2:
                            config["docs"]["vac"] = st.checkbox(
                                "🏖️ Vacaciones", value=config["docs"]["vac"],
                                key=f"vac_{doc}")
                        with cc3:
                            config["docs"]["liq"] = st.checkbox(
                                "💰 Liquidación", value=config["docs"]["liq"],
                                key=f"liq_{doc}")

                        # Configuración de certificado
                        if config["docs"]["cert"]:
                            st.markdown("**Certificado laboral:**")
                            config["mostrar_salario"] = st.radio(
                                "¿Incluir salario en el certificado?",
                                ["Con salario", "Sin salario"],
                                index=0 if config["mostrar_salario"] else 1,
                                horizontal=True,
                                key=f"sal_opt_{doc}",
                            ) == "Con salario"

                            if config["mostrar_salario"]:
                                config["tiene_variable"] = st.checkbox(
                                    "¿Tiene ingresos variables?",
                                    value=config["tiene_variable"],
                                    key=f"var_{doc}")
                                if config["tiene_variable"]:
                                    config["salario_variable"] = st.number_input(
                                        "Promedio mensual ingresos variables ($)",
                                        min_value=0, value=int(config["salario_variable"]),
                                        step=50000, key=f"varval_{doc}",
                                        help="Se mencionará en el certificado junto al salario fijo")

                        # Fechas vacaciones
                        if config["docs"]["vac"]:
                            st.markdown("**Período de vacaciones:**")
                            vc1, vc2 = st.columns(2)
                            with vc1:
                                fi = st.date_input("Inicio", key=f"vi_{doc}",
                                    value=date.today())
                                config["fecha_ini_vac"] = str(fi)
                            with vc2:
                                ff = st.date_input("Fin", key=f"vf_{doc}",
                                    value=date.today())
                                config["fecha_fin_vac"] = str(ff)

                        # Motivo retiro liquidación
                        if config["docs"]["liq"]:
                            st.markdown("**Liquidación:**")
                            MOTIVOS = {
                                "renuncia": "Renuncia voluntaria",
                                "despido_sin_justa_causa": "Despido sin justa causa (Art. 64 CST)",
                                "mutuo_acuerdo": "Mutuo acuerdo",
                                "vencimiento_contrato": "Vencimiento de contrato",
                            }
                            config["motivo_retiro"] = st.selectbox(
                                "Motivo de retiro",
                                list(MOTIVOS.keys()),
                                format_func=lambda x: MOTIVOS[x],
                                key=f"mot_{doc}")
                            if config["motivo_retiro"] == "despido_sin_justa_causa":
                                st.warning("⚠️ La indemnización es una estimación. Valide con abogado.")

                    with c2:
                        st.markdown("**Resumen**")
                        st.markdown(f"**Nombre:** {nom}")
                        st.markdown(f"**Documento:** {doc}")
                        st.markdown(f"**Cargo:** {emp.get('cargo','—')}")
                        if config["mostrar_salario"]:
                            st.markdown(f"**Salario:** ${sal:,.0f}".replace(",","."))
                            if config["tiene_variable"] and config["salario_variable"]:
                                st.markdown(f"**Variable:** "
                                           f"${config['salario_variable']:,.0f}".replace(",","."))
                        else:
                            st.markdown("**Salario:** No se incluye")
                        if st.button("🗑️ Quitar", key=f"del_c_{doc}",
                                    use_container_width=True):
                            del st.session_state.carrito_empleados[doc]
                            st.rerun()

            # ── BOTÓN GENERAR ─────────────────────────────────────────────────
            st.divider()
            if not empresa_ok:
                st.error("⚠️ Configura los datos de tu empresa antes de generar.")
            else:
                if st.button("🚀 Generar todos los documentos",
                            type="primary", use_container_width=True):
                    datos_empresa  = st.session_state.datos_empresa
                    disenio        = st.session_state.get("disenio_seleccionado", 1)
                    usar_mda       = st.session_state.get("usar_marca_agua", False)
                    usar_logo_enc  = st.session_state.get("usar_logo_enc", True)
                    membrete       = st.session_state.get("membrete_path")
                    firma_emp_liq  = st.session_state.get("firma_empleado_liq", True)

                    archivos_gen = []
                    errores_gen  = []
                    barra = st.progress(0, text="Generando...")
                    total_items = sum(
                        sum(c["docs"].values())
                        for c in st.session_state.carrito_empleados.values()
                    )
                    paso = 0

                    for doc, config in st.session_state.carrito_empleados.items():
                        emp     = config["empleado"]
                        nom_b   = str(emp.get("nombre","x")).replace(" ","_")
                        emp_doc = dict(emp)

                        # Aplicar configuración de salario/variable al empleado
                        if not config["mostrar_salario"]:
                            emp_doc["_ocultar_salario"] = True
                        emp_doc["Ingreso promedio variable"] = (
                            config["salario_variable"]
                            if config["tiene_variable"] else 0
                        )
                        # Normalizar claves para los generadores
                        emp_doc["Nombre"]       = emp.get("nombre","")
                        emp_doc["Documento"]    = emp.get("documento","")
                        emp_doc["Cargo"]        = emp.get("cargo","")
                        emp_doc["Salario"]      = emp.get("salario", 0)
                        emp_doc["Fecha ingreso"]= emp.get("fecha_ingreso","")
                        emp_doc["Tipo contrato"]= emp.get("tipo_contrato","Indefinido")

                        # ── Certificado ───────────────────────────────────────
                        if config["docs"]["cert"]:
                            try:
                                ruta = str(CARPETA_SALIDAS / f"Certificado_{nom_b}.pdf")
                                datos_cert = {
                                    **datos_empresa,
                                    "representante": datos_empresa.get("firmante_cert_nombre")
                                                     or datos_empresa.get("representante",""),
                                    "_cargo_firmante": datos_empresa.get("firmante_cert_cargo","Representante Legal"),
                                }
                                generar_certificado(emp_doc, datos_cert, ruta,
                                    disenio, usar_mda, membrete, usar_logo_enc)
                                archivos_gen.append(Path(ruta))
                            except Exception as e:
                                errores_gen.append(f"Cert {emp.get('nombre')}: {e}")
                            paso += 1
                            barra.progress(min(paso/max(total_items,1), 1.0))

                        # ── Vacaciones ────────────────────────────────────────
                        if config["docs"]["vac"]:
                            try:
                                ruta = str(CARPETA_SALIDAS / f"Vacaciones_{nom_b}.pdf")
                                datos_vac = {
                                    **datos_empresa,
                                    "representante": datos_empresa.get("firmante_vac_nombre")
                                                     or datos_empresa.get("representante",""),
                                    "_cargo_firmante": datos_empresa.get("firmante_vac_cargo","Representante Legal"),
                                }
                                generar_vacaciones(emp_doc, datos_vac, ruta,
                                    config["fecha_ini_vac"],
                                    config["fecha_fin_vac"],
                                    disenio, usar_mda, membrete, usar_logo_enc)
                                archivos_gen.append(Path(ruta))
                            except Exception as e:
                                errores_gen.append(f"Vac {emp.get('nombre')}: {e}")
                            paso += 1
                            barra.progress(min(paso/max(total_items,1), 1.0))

                        # ── Liquidación ───────────────────────────────────────
                        if config["docs"]["liq"]:
                            try:
                                import pandas as pd
                                from utils.calcular_liquidacion import calcular_liquidacion_fila
                                fila_liq = pd.Series({
                                    "Nombre":          emp.get("nombre",""),
                                    "Documento":       emp.get("documento",""),
                                    "Cargo":           emp.get("cargo",""),
                                    "Salario":         emp.get("salario", 0),
                                    "Fecha ingreso":   emp.get("fecha_ingreso",""),
                                    "Fecha retiro":    emp.get("fecha_retiro","") or "",
                                    "Cuenta bancaria": emp.get("cuenta_bancaria",""),
                                    "Tipo contrato":   emp.get("tipo_contrato","Indefinido"),
                                })
                                resultado = calcular_liquidacion_fila(
                                    fila_liq,
                                    motivo_retiro=config["motivo_retiro"])
                                ruta = str(CARPETA_SALIDAS / f"Liquidacion_{nom_b}.pdf")
                                datos_liq = {
                                    **datos_empresa,
                                    "representante": datos_empresa.get("firmante_liq_nombre")
                                                     or datos_empresa.get("representante",""),
                                    "_cargo_firmante": datos_empresa.get("firmante_liq_cargo","Representante Legal"),
                                }
                                generar_liquidacion(resultado, datos_liq, ruta,
                                    disenio, usar_mda, membrete,
                                    firma_empleado=firma_emp_liq,
                                    usar_logo_enc=usar_logo_enc)
                                archivos_gen.append(Path(ruta))
                            except Exception as e:
                                errores_gen.append(f"Liq {emp.get('nombre')}: {e}")
                            paso += 1
                            barra.progress(min(paso/max(total_items,1), 1.0))

                    barra.progress(1.0, text="¡Listo!")
                    usuario_registrar_uso(email_usr, len(archivos_gen))
                    st.session_state.archivos_generados = archivos_gen

                    if errores_gen:
                        st.warning(f"{len(errores_gen)} error(es):")
                        for e in errores_gen: st.write(f"- {e}")
                    if archivos_gen:
                        st.success(f"✅ {len(archivos_gen)} documento(s) generados.")

                # Descarga ZIP
                if st.session_state.get("archivos_generados"):
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf,"w") as zf:
                        for p in st.session_state.archivos_generados:
                            if Path(p).exists(): zf.write(p, Path(p).name)
                    buf.seek(0)
                    st.download_button(
                        "⬇️ Descargar todos los documentos (ZIP)", buf,
                        file_name=f"RHFacil_{date.today()}.zip",
                        mime="application/zip", type="primary")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: AGREGAR / EDITAR EMPLEADO
    # ══════════════════════════════════════════════════════════════════════════
    with tab_agregar:
        st.markdown("### Agregar o editar un empleado")
        st.caption("Los cambios se guardan inmediatamente en la base de datos.")

        # Buscar si quiere editar uno existente
        doc_editar = st.text_input("¿Editar uno existente? Ingresa su documento",
            placeholder="Dejar vacío para agregar nuevo", key="doc_editar")

        emp_previo = {}
        if doc_editar:
            resultados = empleados_buscar(email_usr, doc_editar)
            exacto = [e for e in resultados
                     if str(e.get("documento","")) == doc_editar.strip()]
            if exacto:
                emp_previo = exacto[0]
                st.success(f"✅ Editando: {emp_previo.get('nombre','')}")

        with st.form("form_empleado"):
            c1, c2 = st.columns(2)
            with c1:
                documento  = st.text_input("Documento *",
                    value=emp_previo.get("documento",""),
                    placeholder="Número de cédula o NIT")
                nombre     = st.text_input("Nombre completo *",
                    value=emp_previo.get("nombre",""),
                    placeholder="Apellidos y Nombre")
                cargo      = st.text_input("Cargo *",
                    value=emp_previo.get("cargo",""),
                    placeholder="Auxiliar Administrativo")
                salario    = st.number_input("Salario mensual *",
                    min_value=0, step=50000,
                    value=int(float(emp_previo.get("salario",0) or 0)))
            with c2:
                fecha_ing  = st.text_input("Fecha ingreso (dd/mm/aaaa) *",
                    value=emp_previo.get("fecha_ingreso",""),
                    placeholder="01/01/2024")
                fecha_ret  = st.text_input("Fecha retiro (dejar vacío si activo)",
                    value=emp_previo.get("fecha_retiro","") or "",
                    placeholder="")
                tipo_c     = st.selectbox("Tipo contrato",
                    ["Indefinido","Fijo","Obra o labor","Prestación de servicios"],
                    index=["Indefinido","Fijo","Obra o labor","Prestación de servicios"]
                    .index(emp_previo.get("tipo_contrato","Indefinido"))
                    if emp_previo.get("tipo_contrato","Indefinido") in
                    ["Indefinido","Fijo","Obra o labor","Prestación de servicios"] else 0)
                correo_e   = st.text_input("Correo empleado",
                    value=emp_previo.get("correo",""),
                    placeholder="empleado@email.com")
                cuenta_b   = st.text_input("Cuenta bancaria",
                    value=emp_previo.get("cuenta_bancaria",""),
                    placeholder="Bancolombia Ahorros #123456")

            activo = st.checkbox("Empleado activo",
                value=bool(emp_previo.get("activo", True)))

            guardar = st.form_submit_button("💾 Guardar empleado", type="primary")
            if guardar:
                ok, msg = empleado_guardar(email_usr, {
                    "documento": documento, "nombre": nombre, "cargo": cargo,
                    "salario": salario, "fecha_ingreso": fecha_ing,
                    "fecha_retiro": fecha_ret, "tipo_contrato": tipo_c,
                    "correo": correo_e, "cuenta_bancaria": cuenta_b,
                    "activo": activo,
                })
                if ok: st.success(f"✅ {msg}")
                else:  st.error(msg)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: IMPORTAR EXCEL
    # ══════════════════════════════════════════════════════════════════════════
    with tab_importar:
        st.markdown("### Importar desde Excel")
        st.caption("Importa o actualiza empleados masivamente. "
                  "Si un documento ya existe, actualiza sus datos.")

        if PLANTILLA_EXCEL.exists():
            with open(PLANTILLA_EXCEL,"rb") as f:
                st.download_button("⬇️ Descargar plantilla Excel", f,
                    file_name="Base_Empleados_RHFacil.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        archivo = st.file_uploader("Sube tu Excel de empleados", type=["xlsx"])
        if archivo:
            df, err_col, err_fila = cargar_y_validar(archivo)
            if err_col:
                for e in err_col: st.error(e)
            else:
                st.dataframe(df.head(5), use_container_width=True)
                st.caption(f"{len(df)} empleado(s) en el archivo")
                if err_fila:
                    st.warning(f"⚠️ {len(err_fila)} problema(s) encontrado(s):")
                    for e in err_fila: st.write(f"- {e}")

                if st.button("📥 Importar a la base de datos", type="primary"):
                    with st.spinner("Importando..."):
                        nuevos, actualizados, errores = empleados_importar_excel(
                            email_usr, df)
                    st.success(f"✅ {nuevos} nuevos · {actualizados} actualizados")
                    if errores:
                        st.warning(f"{len(errores)} error(es):")
                        for e in errores: st.write(f"- {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: VER TODOS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_todos:
        st.markdown("### Base completa de empleados")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_estado = st.radio("Estado",
                ["Todos","Solo activos","Solo retirados"],
                horizontal=True, key="filtro_estado_tab")
        with col_f2:
            if st.button("🔄 Actualizar lista"):
                st.rerun()

        todos = empleados_listar(email_usr)
        if filtro_estado == "Solo activos":
            todos = [e for e in todos if e.get("activo", True)]
        elif filtro_estado == "Solo retirados":
            todos = [e for e in todos if not e.get("activo", True)]

        if not todos:
            st.info("No hay empleados en la base de datos. "
                   "Impórtalos desde Excel o agrégalos uno a uno.")
        else:
            st.caption(f"Mostrando {len(todos)} empleado(s)")
            # Convertir a DataFrame para mostrar en tabla
            df_show = pd.DataFrame([{
                "Estado":        "✅ Activo" if e.get("activo",True) else "🔴 Retirado",
                "Nombre":        e.get("nombre",""),
                "Documento":     e.get("documento",""),
                "Cargo":         e.get("cargo",""),
                "Salario":       f"${float(e.get('salario',0) or 0):,.0f}".replace(",","."),
                "Ingreso":       e.get("fecha_ingreso",""),
                "Retiro":        e.get("fecha_retiro","") or "—",
                "Contrato":      e.get("tipo_contrato",""),
            } for e in todos])
            st.dataframe(df_show, use_container_width=True, hide_index=True)

            # Acción de retiro rápido
            with st.expander("⚠️ Registrar retiro de empleado"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    doc_ret = st.text_input("Documento del empleado a retirar")
                with c2:
                    fecha_ret_inp = st.date_input("Fecha de retiro", date.today())
                with c3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Registrar retiro", type="primary"):
                        ok, msg = empleado_retirar(
                            email_usr, doc_ret,
                            fecha_ret_inp.strftime("%d/%m/%Y"))
                        if ok: st.success(msg); st.rerun()
                        else:  st.error(msg)

# ══════════════════════════════════════════════════════════════════════════════
# DISEÑO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🎨  Diseño":
    from utils.preview_disenios import generar_previews, limpiar_previews, EMPRESA_DEMO
    st.markdown("# Diseño de plantillas")
    st.caption("Vista previa real de cada diseño. Elige el que mejor represente tu empresa.")

    c1, c2 = st.columns([3,1])
    with c1:
        tipo_prev = st.radio("Previsualizar:", ["📋 Certificado","💰 Liquidación"], horizontal=True)
    with c2:
        if st.button("🔄 Regenerar"):
            limpiar_previews()
            st.session_state.previews_cert = None
            st.session_state.previews_liq  = None
            st.rerun()
    st.divider()

    if not st.session_state.previews_cert:
        with st.spinner("Generando previsualizaciones..."):
            c, l = generar_previews(forzar=False)
            st.session_state.previews_cert = c
            st.session_state.previews_liq  = l

    previews = (st.session_state.previews_cert if "Certificado" in tipo_prev
                else st.session_state.previews_liq)
    d_actual = st.session_state.disenio_seleccionado

    st.markdown(f"<p style='color:#374151;font-size:.9rem'>✅ Diseño activo: "
                f"<b>#{d_actual} — {nombre_disenio(d_actual)}</b></p>",
                unsafe_allow_html=True)

    for fila_d in [[1,2,3],[4,5]]:
        cols = st.columns(len(fila_d))
        for col, d in zip(cols, fila_d):
            selec = d_actual == d
            borde = "#2D6BE4" if selec else "#E5E7EB"
            png   = previews.get(d) if previews else None
            with col:
                st.markdown(f'<div style="border:3px solid {borde};border-radius:14px;'
                            f'overflow:hidden;margin-bottom:8px">',
                            unsafe_allow_html=True)
                if png and Path(png).exists():
                    st.image(png, use_container_width=True)
                else:
                    st.markdown('<div style="height:220px;background:#F9FAFB;'
                                'display:flex;align-items:center;justify-content:center;'
                                'color:#9CA3AF">Sin preview</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:.8rem;'
                            f'font-weight:{"700" if selec else "400"};'
                            f'color:{"#1B3F6E" if selec else "#6B7280"}">'
                            f'{"✅ " if selec else ""}#{d} {PALETAS[d]["nombre"]}</div>',
                            unsafe_allow_html=True)
                if selec:
                    emp_d = st.session_state.datos_empresa if empresa_ok else EMPRESA_DEMO
                    from utils.preview_disenios import EMPLEADO_DEMO
                    ruta_m = str(CARPETA_SALIDAS / f"muestra_d{d}.pdf")
                    try:
                        generar_certificado(EMPLEADO_DEMO, emp_d, ruta_m, d)
                        with open(ruta_m,"rb") as fp:
                            st.download_button("⬇️ Muestra PDF", fp,
                                file_name=f"muestra_{PALETAS[d]['nombre'].replace(' ','_')}.pdf",
                                mime="application/pdf", use_container_width=True)
                    except Exception:
                        pass
                else:
                    if st.button("Usar este diseño", key=f"d{d}",
                                 use_container_width=True, type="secondary"):
                        st.session_state.disenio_seleccionado = d
                        st.session_state.datos_empresa["disenio_seleccionado"] = d
                        empresa_guardar(u["email"], st.session_state.datos_empresa)
                        st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GENERAR DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "⚡  Generar":
    st.markdown("# Generar documentos")
    if not empresa_ok:
        st.error("⚠️ Configura primero los datos de tu empresa."); st.stop()
    if st.session_state.df_empleados is None:
        st.error("⚠️ Carga primero la base de empleados."); st.stop()

    df            = st.session_state.df_empleados
    de            = st.session_state.datos_empresa
    disenio       = st.session_state.disenio_seleccionado
    plan_info     = PLANES.get(u["plan"], PLANES["gratuito"])
    sin_limite    = not plan_info["limite"]
    docs_rest     = None if sin_limite else max(0, plan_info["max_documentos"] - u.get("documentos_usados",0))

    c1,c2,c3 = st.columns(3)
    c1.metric("Empresa", de.get("nombre",""))
    c2.metric("Empleados", len(df))
    c3.metric("Diseño", f"#{disenio} {nombre_disenio(disenio)}")
    st.divider()

    st.markdown("### Selecciona documentos")
    c1,c2,c3 = st.columns(3)
    with c1: gen_cert = st.checkbox("📋 Certificados laborales")
    with c2: gen_vac  = st.checkbox("🏖️ Cartas de vacaciones")
    with c3: gen_liq  = st.checkbox("💰 Liquidaciones")

    ing_var_global = 0
    tiene_variable = "No"
    if gen_cert:
        tiene_variable = st.radio("¿Ingresos variables?",
            ["No","Sí — del Excel por empleado","Sí — valor global para todos"],
            horizontal=True)
        if tiene_variable == "Sí — valor global para todos":
            ing_var_global = st.number_input("Promedio mensual ($)", min_value=0,
                value=0, step=50000)

    fecha_ini_vac = fecha_fin_vac = None
    if gen_vac:
        c1,c2 = st.columns(2)
        with c1: fecha_ini_vac = st.date_input("Inicio vacaciones", date.today())
        with c2: fecha_fin_vac = st.date_input("Fin vacaciones",    date.today())

    fecha_corte_liq = None; motivo_retiro = "renuncia"
    if gen_liq:
        c1,c2 = st.columns(2)
        with c1: fecha_corte_liq = st.date_input("Fecha de corte", date.today())
        with c2:
            MOTIVOS = {
                "renuncia":              "Renuncia voluntaria",
                "despido_sin_justa_causa":"Despido sin justa causa (Art.64 CST)",
                "mutuo_acuerdo":         "Mutuo acuerdo",
                "vencimiento_contrato":  "Vencimiento de contrato",
            }
            motivo_retiro = st.selectbox("Motivo de retiro",
                list(MOTIVOS.keys()), format_func=lambda x: MOTIVOS[x])

    st.divider()

    # ── Opciones de entrega ──────────────────────────────────────────────────
    st.markdown("### Forma de entrega")
    c1, c2 = st.columns(2)
    with c1:
        descargar = st.checkbox("⬇️ Descargar ZIP", value=True)
    with c2:
        puede_enviar = smtp_configurado() and "Correo" in (df.columns.tolist() if df is not None else [])
        enviar_correo = st.checkbox("📧 Enviar por correo a cada empleado",
            disabled=not puede_enviar,
            help="Requiere SMTP configurado y columna 'Correo' en el Excel")
    if not puede_enviar:
        st.caption("Para habilitar envío por correo: configura SMTP en Render y agrega columna 'Correo' al Excel")

    st.divider()
    tipos = sum([gen_cert, gen_vac, gen_liq])

    if st.button("🚀 Generar documentos", type="primary"):
        if tipos == 0:
            st.error("Selecciona al menos un tipo."); st.stop()

        archivos_generados = []; errores = []; contador = 0
        limite = docs_rest if not sin_limite else 99999
        barra  = st.progress(0, text="Generando…")

        rep  = de.get("representante","")
        d_cert = {**de, "representante": de.get("firmante_cert_nombre") or rep,
                  "_cargo_firmante": de.get("firmante_cert_cargo") or "Representante Legal"}
        d_vac  = {**de, "representante": de.get("firmante_vac_nombre") or rep,
                  "_cargo_firmante": de.get("firmante_vac_cargo") or "Representante Legal"}
        d_liq  = {**de, "representante": de.get("firmante_liq_nombre") or rep,
                  "_cargo_firmante": de.get("firmante_liq_cargo") or "Representante Legal"}
        membrete = st.session_state.get("membrete_path")
        usar_mda = st.session_state.get("usar_marca_agua", False)
        usar_logo= st.session_state.get("usar_logo_enc", True)
        firma_emp= st.session_state.get("firma_empleado_liq", True)

        for paso, (_, fila) in enumerate(df.iterrows()):
            if contador >= limite: break
            empleado = fila.to_dict()
            nb = str(fila.get("Nombre","x")).strip().replace(" ","_")
            pdfs_empleado = []

            if gen_cert and contador < limite:
                if "global" in tiene_variable:
                    empleado["Ingreso promedio variable"] = ing_var_global
                elif "Excel" in tiene_variable:
                    empleado["Ingreso promedio variable"] = fila.get("Ingreso promedio variable",0) or 0
                try:
                    ruta = str(CARPETA_SALIDAS / f"Certificado_{nb}.pdf")
                    generar_certificado(empleado, d_cert, ruta, disenio, usar_mda, membrete, usar_logo)
                    archivos_generados.append(Path(ruta)); pdfs_empleado.append(ruta)
                    contador += 1
                except Exception as e: errores.append(f"Cert {fila.get('Nombre')}: {e}")

            if gen_vac and contador < limite:
                try:
                    ruta = str(CARPETA_SALIDAS / f"Vacaciones_{nb}.pdf")
                    generar_vacaciones(empleado, d_vac, ruta,
                        fecha_ini_vac.strftime("%d/%m/%Y"),
                        fecha_fin_vac.strftime("%d/%m/%Y"),
                        disenio, usar_mda, membrete, usar_logo)
                    archivos_generados.append(Path(ruta)); pdfs_empleado.append(ruta)
                    contador += 1
                except Exception as e: errores.append(f"Vac {fila.get('Nombre')}: {e}")

            if enviar_correo and pdfs_empleado:
                correo_dest = str(fila.get("Correo","")).strip()
                if correo_dest and "@" in correo_dest:
                    ok_m, msg_m = enviar_documentos(correo_dest, str(fila.get("Nombre","")),
                        de.get("nombre",""), "Documentos laborales",
                        pdfs_empleado, de.get("correo_empresa",""))
                    if not ok_m: errores.append(f"Correo {fila.get('Nombre')}: {msg_m}")

            barra.progress(min((paso+1)/len(df), 0.9))

        if gen_liq and contador < limite:
            df_res, err_liq = calcular_liquidacion_df(df.copy(),
                fecha_corte_default=datetime(fecha_corte_liq.year,
                    fecha_corte_liq.month, fecha_corte_liq.day),
                motivo_retiro=motivo_retiro)
            errores.extend(err_liq)
            for _, res in df_res.iterrows():
                if contador >= limite: break
                nb2 = str(res["Nombre"]).strip().replace(" ","_")
                try:
                    ruta = str(CARPETA_SALIDAS / f"Liquidacion_{nb2}.pdf")
                    generar_liquidacion(res.to_dict(), d_liq, ruta, disenio,
                        usar_mda, membrete, firma_emp, usar_logo)
                    archivos_generados.append(Path(ruta))
                    contador += 1
                    if enviar_correo and "Correo" in df.columns:
                        mask = df["Nombre"] == res["Nombre"]
                        correo_dest = str(df.loc[mask,"Correo"].values[0] if mask.any() else "").strip()
                        if correo_dest and "@" in correo_dest:
                            enviar_documentos(correo_dest, res["Nombre"],
                                de.get("nombre",""), "Liquidación de Prestaciones Sociales",
                                [ruta], de.get("correo_empresa",""))
                except Exception as e: errores.append(f"Liq {res['Nombre']}: {e}")
            if not df_res.empty:
                ruta_xls = str(CARPETA_SALIDAS / "Resumen_Liquidaciones.xlsx")
                df_res.to_excel(ruta_xls, index=False)
                archivos_generados.append(Path(ruta_xls))

        barra.progress(1.0, text="¡Listo!")
        usuario_registrar_uso(u["email"], contador)
        u["documentos_usados"] = u.get("documentos_usados",0) + contador
        st.session_state.archivos_generados = archivos_generados

        if errores:
            st.warning(f"{len(errores)} error(es):")
            for e in errores: st.write(f"- {e}")
        if archivos_generados:
            st.success(f"✅ {contador} documento(s) generados.")

    # ── Descargar ────────────────────────────────────────────────────────────
    if st.session_state.archivos_generados and descargar:
        st.divider()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf,"w") as zf:
            for p in st.session_state.archivos_generados:
                if Path(p).exists(): zf.write(p, Path(p).name)
        buf.seek(0)
        st.download_button("⬇️ Descargar ZIP con todos los documentos", buf,
            file_name=f"RHFacil_{de.get('nombre','').replace(' ','_')}_{date.today()}.zip",
            mime="application/zip", type="primary")

# ══════════════════════════════════════════════════════════════════════════════
# PLANES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "💎  Planes":
    st.markdown("# Planes y precios")
    st.caption("Activa tu plan por WhatsApp. Activación en menos de 2 horas hábiles.")
    st.divider()
    cols = st.columns(4)
    for col, key in zip(cols, ["gratuito","basico","pro","empresarial"]):
        plan = PLANES[key]
        precio = "Gratis" if plan["precio"]==0 else f"${plan['precio']:,}".replace(",",".")
        periodo = "" if plan["precio"]==0 else "/mes"
        activo  = u["plan"] == key
        feats   = "".join([f'<div class="plan-feature">✓ {f}</div>' for f in plan["features"]])
        with col:
            st.markdown(f"""
            <div class="plan-card {'destacado' if key in ('basico','pro') else ''}">
                <div style="font-weight:700;margin-bottom:.5rem">{plan['nombre']}</div>
                <div class="plan-precio">{precio}</div>
                <div class="plan-periodo">{periodo}</div>
                <hr style="border-color:#E5E7EB;margin:.6rem 0">
                {feats}
            </div>""", unsafe_allow_html=True)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if activo:
                st.markdown("<p style='text-align:center;color:#059669;font-size:.8rem'>"
                            "✅ Plan actual</p>", unsafe_allow_html=True)
            else:
                msg = (f"Hola, quiero activar el plan {plan['nombre']} de RH Fácil. "
                       f"Mi correo es {u['email']}.")
                st.link_button("💬 Activar por WhatsApp",
                    link_whatsapp(msg), use_container_width=True)
    st.divider()
    st.markdown("<p style='text-align:center;color:#6B7280;font-size:.85rem'>"
                "💳 Transferencia, Nequi y PSE · Cancela cuando quieras</p>",
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🛡️  Admin" and u.get("es_admin"):
    st.markdown("# Panel de Administrador")
    stats = admin_stats()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total usuarios",   stats["total"])
    c2.metric("Activos",          stats["activos"])
    c3.metric("Pendientes",       stats["pendientes"])
    c4.metric("Docs generados",   stats["total_docs"])

    st.divider()
    st.markdown("### Usuarios registrados")
    usuarios = admin_listar()
    pendientes = [x for x in usuarios if not x.get("activado_por_admin")]
    if pendientes:
        st.warning(f"⏳ {len(pendientes)} usuario(s) esperando activación")
        if st.button(f"✅ Activar todos ({len(pendientes)})", type="primary"):
            for pu in pendientes: admin_activar(pu["email"])
            st.rerun()

    for usr in usuarios:
        badge = ("⏳ Pendiente" if not usr.get("activado_por_admin")
                 else "✅ Activo" if usr.get("activo") else "🔴 Inactivo")
        with st.expander(f"{usr.get('nombre','?')} · {usr['email']} · {badge}"):
            c1, c2 = st.columns([3,2])
            with c1:
                st.markdown(f"""
                **Empresa:** {usr.get('empresa') or usr.get('empresa_nombre_inicial','—')}  
                **Plan:** {usr.get('plan','gratuito')}  
                **Docs generados:** {usr.get('documentos_usados',0)}  
                **Registro:** {str(usr.get('fecha_registro',''))[:10]}  
                **Onboarding:** {'✅' if usr.get('onboarding_completo') else '⏳'}
                """)
            with c2:
                if not usr.get("activado_por_admin"):
                    if st.button("✅ Activar", key=f"act_{usr['email']}", type="primary"):
                        admin_activar(usr["email"]); st.rerun()
                elif usr.get("activo"):
                    if st.button("🔴 Desactivar", key=f"des_{usr['email']}"):
                        from utils.db import admin_listar
                        pass
                nuevo_plan = st.selectbox("Plan", list(PLANES.keys()),
                    index=list(PLANES.keys()).index(usr.get("plan","gratuito")),
                    format_func=lambda x: PLANES[x]["nombre"],
                    key=f"plan_{usr['email']}")
                if st.button("Guardar plan", key=f"gp_{usr['email']}"):
                    admin_cambiar_plan(usr["email"], nuevo_plan); st.rerun()
