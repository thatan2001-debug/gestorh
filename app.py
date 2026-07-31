"""
Gestor RH IA v16 — App principal con Supabase, onboarding y dashboard
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

# Favicon dinámico: prefiere icono cuadrado si existe, sino usa logo completo, sino emoji
from pathlib import Path as _Path
_icono_path = _Path("assets/logo_icono.png")
_marca_path = _Path("assets/logo_gestorrh.png")
if _icono_path.exists():
    _favicon = str(_icono_path)
elif _marca_path.exists():
    _favicon = str(_marca_path)
else:
    _favicon = "📄"
st.set_page_config(page_title="Gestor RH IA", page_icon=_favicon, layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# Diagnóstico seguro del proceso activo de Render. Solo se muestra con
# ?deployment_diagnostics=1 y no expone secretos.
from utils.deployment_diagnostics import mostrar_diagnostico_despliegue
if mostrar_diagnostico_despliegue():
    st.stop()

CARPETA_SALIDAS = Path("salidas"); CARPETA_SALIDAS.mkdir(exist_ok=True)
CARPETA_ASSETS  = Path("assets");  CARPETA_ASSETS.mkdir(exist_ok=True)
PLANTILLA_EXCEL = Path("plantillas/Base_Empleados.xlsx")
ADMIN_EMAIL     = "admin@gestorrh.co"

# ── Activación por enlace de correo (URL ?activar=xxxxxx) ────────────────────
_query_params = st.query_params
if "activar" in _query_params and not st.session_state.get("_activacion_procesada"):
    from utils.tokens import validar_por_link
    from utils.db import usuario_activar
    _token_url = _query_params["activar"]
    _ok_link, _msg_link, _email_activado = validar_por_link(_token_url)
    if _ok_link and _email_activado:
        usuario_activar(_email_activado)
        st.session_state["_activacion_procesada"] = True
        st.session_state["_activacion_exitosa"] = _email_activado
    else:
        st.session_state["_activacion_procesada"] = True
        st.session_state["_activacion_error"] = _msg_link
    # Limpiar el parámetro de la URL
    st.query_params.clear()
    st.rerun()

# Mostrar mensajes de activación por enlace
if st.session_state.get("_activacion_exitosa"):
    _email_act = st.session_state["_activacion_exitosa"]
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#059669,#10B981);color:white;
        padding:28px 32px;border-radius:14px;margin:16px 0;
        box-shadow:0 4px 20px rgba(5,150,105,.25);text-align:center">
        <div style="font-size:3rem;margin-bottom:8px">🎉</div>
        <h2 style="margin:0 0 8px;font-size:1.5rem;color:white">
            ¡Registro exitoso!
        </h2>
        <p style="margin:0 0 6px;opacity:.95;font-size:1rem">
            La cuenta <b>{_email_act}</b> fue activada correctamente.
        </p>
        <p style="margin:0;opacity:.9;font-size:.95rem">
            ✅ Ya puedes iniciar sesión con tu correo y contraseña.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.balloons()
    del st.session_state["_activacion_exitosa"]

# Mostrar mensaje cuando activó por código (formulario en pantalla)
if st.session_state.get("_activacion_exitosa_completa"):
    _datos_act = st.session_state["_activacion_exitosa_completa"]
    _nombre_corto = _datos_act["nombre"].split()[0] if _datos_act.get("nombre") else ""
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#059669,#10B981);color:white;
        padding:32px 36px;border-radius:14px;margin:20px 0;
        box-shadow:0 4px 20px rgba(5,150,105,.25);text-align:center">
        <div style="font-size:3.5rem;margin-bottom:10px">✅</div>
        <h2 style="margin:0 0 10px;font-size:1.6rem;color:white">
            ¡Bienvenido{f", {_nombre_corto}" if _nombre_corto else ""}!
        </h2>
        <p style="margin:0 0 8px;opacity:.95;font-size:1.05rem">
            Tu cuenta <b>{_datos_act['email']}</b> fue activada exitosamente.
        </p>
        <div style="background:rgba(255,255,255,.15);border-radius:8px;
            padding:14px 20px;margin-top:16px;font-size:.95rem">
            👉 <b>Ya puedes iniciar sesión</b> con tu correo y contraseña
            en el formulario de abajo.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.balloons()
    del st.session_state["_activacion_exitosa_completa"]

if st.session_state.get("_activacion_error"):
    st.error(f"❌ Error al activar por enlace: {st.session_state['_activacion_error']}")
    st.info("Puedes ingresar tu código de 6 dígitos manualmente en la pantalla de registro.")
    del st.session_state["_activacion_error"]

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
        # ═══ Encabezado con logo (si existe) ═══════════════════════
        from pathlib import Path as _P
        logo_marca = _P("assets/logo_gestorrh.png")

        if logo_marca.exists():
            # Logo GRANDE centrado. El tagline ya viene incluido en el logo,
            # no lo repetimos abajo para no duplicar.
            st.markdown("<div style='text-align:center;padding:1.5rem 0 1rem'>",
                          unsafe_allow_html=True)
            _c1, _c2, _c3 = st.columns([1, 4, 1])  # más ancho para el logo
            with _c2:
                st.image(str(logo_marca), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # Fallback: emoji simple + título si el logo no está subido
            st.markdown("""
            <div style='text-align:center;padding:2rem 0 1rem'>
                <div style='font-size:2.5rem'>📄</div>
                <h1 style='color:#1B3F6E;margin:0'>Gestor RH IA</h1>
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

                    # ─── Etapa 4: Cargar perfil y empresas del sistema nuevo ───
                    try:
                        from services.perfil_service import perfil_service
                        from utils.selector_empresa import cargar_empresas_del_usuario

                        perfil = perfil_service.obtener_por_email(email_l)
                        if perfil:
                            st.session_state.usuario["perfil_id"] = perfil["id"]
                            st.session_state.usuario["es_superadmin"] = perfil.get("es_superadmin", False)
                            # Registrar el login
                            perfil_service.registrar_login(perfil["id"])
                            # Cargar sus empresas
                            cargar_empresas_del_usuario()
                    except Exception:
                        # Si algo falla, el usuario sigue con el flujo legacy
                        pass

                    # Cargar empresa guardada (legacy — se usa como fallback)
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
                        # Enviar token de activación automáticamente
                        from utils.tokens import enviar_activacion_completa
                        ok_envio, msg_envio, datos = enviar_activacion_completa(
                            email=email_r, nombre=nombre_r
                        )
                        # Guardar en session para el flujo de activación
                        st.session_state["registro_pendiente"] = {
                            "email":  email_r,
                            "nombre": nombre_r,
                            "codigo_debug": datos.get("codigo") if not ok_envio else None,
                        }
                        if ok_envio:
                            st.success(
                                f"✅ Cuenta creada. Te enviamos un correo a "
                                f"**{email_r}** con el código de activación."
                            )
                        else:
                            st.warning(
                                f"⚠️ Cuenta creada, pero no pudimos enviar el correo: {msg_envio}"
                            )
                            if datos.get("codigo"):
                                st.info(f"🔑 Tu código de activación es: **{datos['codigo']}** "
                                        f"(guárdalo, expira en 24 horas)")
                        st.rerun()
                    else:
                        st.error(msg)

        # ── Formulario de activación (aparece si hay registro pendiente) ────
        registro = st.session_state.get("registro_pendiente")
        if registro:
            st.divider()
            st.markdown("### 🔑 Activa tu cuenta")
            st.caption(
                f"Ingresa el código de 6 dígitos que enviamos a **{registro['email']}**. "
                f"Si no lo encuentras, revisa la carpeta de spam."
            )
            with st.form("activar_cuenta_form"):
                codigo_input = st.text_input(
                    "Código de 6 dígitos",
                    placeholder="123456",
                    max_chars=6,
                    key="codigo_activacion",
                )
                cc1, cc2 = st.columns(2)
                with cc1:
                    activar_btn = st.form_submit_button("✅ Activar mi cuenta",
                                                         type="primary",
                                                         use_container_width=True)
                with cc2:
                    reenviar_btn = st.form_submit_button("📧 Reenviar código",
                                                          use_container_width=True)

                if activar_btn and codigo_input:
                    from utils.tokens import validar_por_codigo
                    from utils.db import usuario_activar
                    ok_val, msg_val = validar_por_codigo(registro["email"], codigo_input)
                    if ok_val:
                        usuario_activar(registro["email"])
                        st.session_state["_activacion_exitosa_completa"] = {
                            "email":  registro["email"],
                            "nombre": registro["nombre"],
                        }
                        del st.session_state["registro_pendiente"]
                        st.rerun()
                    else:
                        st.error(f"❌ {msg_val}")

                if reenviar_btn:
                    from utils.tokens import enviar_activacion_completa
                    ok_re, msg_re, datos_re = enviar_activacion_completa(
                        email=registro["email"], nombre=registro["nombre"]
                    )
                    if ok_re:
                        st.success(f"✅ Enviamos un nuevo código a {registro['email']}")
                    else:
                        st.warning(f"⚠️ {msg_re}")
                        if datos_re.get("codigo"):
                            st.info(f"🔑 Tu nuevo código es: **{datos_re['codigo']}**")

            if st.button("← Cancelar y volver al login"):
                del st.session_state["registro_pendiente"]
                st.rerun()


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

# ═══════════════════════════════════════════════════════════════════════════
# ETAPA 4 — Selector de empresa (si el usuario tiene más de una)
# ═══════════════════════════════════════════════════════════════════════════
# Este bloque es NO-BLOQUEANTE en modo legacy: si el usuario no está en el
# nuevo sistema de multiempresa (no tiene perfil_id), el selector se salta.
try:
    if u.get("perfil_id") and not u.get("es_admin"):
        # Solo aplicar selector si estamos en el sistema nuevo
        from utils.selector_empresa import (
            mostrar_selector_si_necesario,
            obtener_empresa_activa,
        )

        if mostrar_selector_si_necesario():
            st.stop()

        # Actualizar datos_empresa con la empresa activa
        activa = obtener_empresa_activa()
        if activa and activa.get("id"):
            # Sincronizar los datos de la empresa activa con datos_empresa
            from services.empresa_service import empresa_service
            emp_full = empresa_service.obtener(activa["id"])
            if emp_full:
                st.session_state.datos_empresa.update({
                    "nombre":         emp_full.get("razon_social", ""),
                    "nit":            emp_full.get("nit", ""),
                    "ciudad":         emp_full.get("ciudad", ""),
                    "correo_empresa": emp_full.get("correo", ""),
                    "telefono_empresa": emp_full.get("telefono", ""),
                    "representante":  emp_full.get("representante_legal", ""),
                    "logo_path":      emp_full.get("logo_url", ""),
                    "membrete_path":  emp_full.get("membrete_url", ""),
                    "_empresa_id":    activa["id"],  # Marker para servicios
                })
except Exception as e:
    # Cualquier error → seguir con flujo legacy sin romper la app
    try:
        from utils.logs import log_warn
        log_warn("selector_empresa.fallo", error=str(e))
    except Exception:
        pass

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
    # ═══ Logo o título ═══════════════════════════════════════════
    from pathlib import Path as _P
    logo_icono = _P("assets/logo_icono.png")
    logo_marca = _P("assets/logo_gestorrh.png")

    if logo_icono.exists():
        # Ícono compacto ideal para sidebar
        c_l, c_r = st.columns([1, 3])
        with c_l:
            st.image(str(logo_icono), width=48)
        with c_r:
            st.markdown("### Gestor RH IA")
    elif logo_marca.exists():
        # Logo completo (más grande, pero mejor que nada)
        st.image(str(logo_marca), use_container_width=True)
    else:
        st.markdown("## 📄 Gestor RH IA")

    st.caption(f"Hola, **{u['nombre'].split()[0]}** 👋")
    if usar_supabase():
        st.caption("🟢 Base de datos activa")

    # ─── Etapa 4: Widget de empresa activa ─────────────────────────
    try:
        if u.get("perfil_id"):
            from utils.selector_empresa import mostrar_cambio_empresa_en_sidebar
            mostrar_cambio_empresa_en_sidebar()
    except Exception:
        pass

    # ─── Modo beta: aviso visible ───────────────────────────────────
    try:
        from utils.plan_control import _modo_beta_activo
        if _modo_beta_activo():
            st.warning("🧪 **Modo Beta activo**\n\nTodos los documentos desbloqueados para pruebas. Los límites de plan están desactivados.", icon="🧪")
    except Exception:
        pass

    st.divider()

    nav_opciones = [
        ("🏠", "Inicio",       "🏠  Inicio"),
        ("👥", "Empleados",    "👥  Empleados"),
        ("📄", "Documentos",   "📄  Documentos"),
        ("💰", "Liquidaciones","💰  Liquidaciones"),
        ("📊", "Reportes",     "📊  Reportes"),
        ("🏢", "Mi empresa",   "🏢  Mi empresa"),
        ("⚙️", "Configuración","⚙️  Configuración"),
        ("💎", "Planes",       "💎  Planes"),
    ]
    if u.get("es_admin"):
        nav_opciones.append(("🛡️", "Admin", "🛡️  Admin"))

    # Inicializar página seleccionada
    if "pagina_actual" not in st.session_state:
        st.session_state.pagina_actual = "🏠  Inicio"
    # Permitir cambio programático desde otras partes de la app
    if "ir_a" in st.session_state:
        st.session_state.pagina_actual = st.session_state.pop("ir_a")

    # CSS para botones grandes tipo tarjeta con contraste
    st.markdown("""
    <style>
    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1B3F6E 0%, #0F2A4F 100%) !important;
    }

    /* Contenedor de botones */
    section[data-testid="stSidebar"] div.stButton {
        margin-bottom: 6px !important;
    }

    /* Botones del sidebar — reglas para TODAS las capas anidadas */
    section[data-testid="stSidebar"] div.stButton button,
    section[data-testid="stSidebar"] div.stButton button p,
    section[data-testid="stSidebar"] div.stButton button div,
    section[data-testid="stSidebar"] div.stButton button span {
        text-align: left !important;
        font-size: 0.98rem !important;
        font-weight: 600 !important;
    }

    section[data-testid="stSidebar"] div.stButton > button {
        padding: 14px 18px !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        justify-content: flex-start !important;
        display: flex !important;
    }

    /* Botón INACTIVO: fondo BLANCO, texto AZUL OSCURO */
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        border: 2px solid #E5E7EB !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] p,
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] span,
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] div {
        color: #1B3F6E !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
        background-color: #EFF6FF !important;
        border-color: #2D6BE4 !important;
        transform: translateX(2px) !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover p,
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover span,
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover div {
        color: #1B3F6E !important;
    }

    /* Botón ACTIVO (primary): fondo AZUL DEGRADADO, texto BLANCO */
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2D6BE4, #1B3F6E) !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(45, 107, 228, 0.5) !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] p,
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] span,
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] div {
        color: #FFFFFF !important;
    }

    /* Cabecera del sidebar (nombre, hola usuario) — que sean blancos */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span:not(button span) {
        color: #FFFFFF !important;
    }

    /* Pestañas (st.tabs) */
    div[data-testid="stTabs"] button[role="tab"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        border-radius: 8px 8px 0 0 !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #2D6BE4, #1B3F6E) !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Renderizar botones grandes
    for icono, label, key in nav_opciones:
        activo = st.session_state.pagina_actual == key
        if st.button(
            f"{icono}   {label}",
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if activo else "secondary",
        ):
            st.session_state.pagina_actual = key
            st.rerun()

    pagina = st.session_state.pagina_actual
    st.divider()

    from utils.plan_control import obtener_limite_plan
    plan_info_sidebar = obtener_limite_plan(u["plan"])
    docs_usados       = u.get("documentos_usados", 0)
    max_docs          = plan_info_sidebar["max_docs"]
    sin_limite        = not plan_info_sidebar["tiene_limite"]

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
        border-radius:16px;padding:2.2rem 2.5rem;margin-bottom:1.5rem;color:white'>
        <h1 style='margin:0 0 .5rem;font-size:1.75rem'>
            ¡Bienvenido, {u['nombre'].split()[0]}! 👋</h1>
        <p style='margin:0;opacity:.9;font-size:1.05rem'>
            {nombre_emp} · Plan <b>{u['plan'].capitalize()}</b></p>
    </div>""", unsafe_allow_html=True)

    # ── Calcular métricas del dashboard ─────────────────────────────────
    from utils.empleados_db import empleados_listar
    from utils.historial import obtener
    empleados_all = empleados_listar(u["email"])
    empleados_activos_num = sum(1 for e in empleados_all if e.get("activo", True))
    empleados_retirados_num = sum(1 for e in empleados_all if not e.get("activo", True))

    # Contratos por vencer (fijos con fecha_fin en próximos 30 días)
    from datetime import date as _date, timedelta as _td, datetime as _datetime
    contratos_por_vencer = 0
    hoy = _date.today()
    limite = hoy + _td(days=30)
    for e in empleados_all:
        if e.get("activo", True):
            fecha_fin_c = str(e.get("fecha_fin_contrato","") or "").strip()
            if fecha_fin_c:
                # Intentar varios formatos comunes
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                    try:
                        ff = _datetime.strptime(fecha_fin_c[:10], fmt).date()
                        if hoy <= ff <= limite:
                            contratos_por_vencer += 1
                        break
                    except Exception:
                        continue

    # Documentos generados este mes
    hist = obtener(u["email"], limite=1000)
    docs_este_mes = 0
    mes_actual = hoy.strftime("%Y-%m")
    for h in hist:
        fecha_h = str(h.get("fecha","") or h.get("timestamp","") or "")[:7]
        if fecha_h == mes_actual:
            docs_este_mes += 1

    # ── Dashboard principal ────────────────────────────────────────────
    st.markdown("### 📊 Panel de control")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("👥 Empleados activos", empleados_activos_num)
    m2.metric("📅 Contratos por vencer", contratos_por_vencer,
              help="Contratos fijos que terminan en los próximos 30 días")
    m3.metric("🏖️ Vacaciones pendientes", "—",
              help="Función próxima")
    m4.metric("📄 Docs este mes", docs_este_mes)
    m5.metric("⭕ Retirados", empleados_retirados_num)

    st.divider()

    # ── Botones rápidos ────────────────────────────────────────────────
    st.markdown("### ⚡ Acciones rápidas")
    st.caption("Genera documentos rápidamente seleccionando el empleado")
    b1, b2, b3, b4, b5 = st.columns(5)
    with b1:
        if st.button("➕ Registrar empleado", use_container_width=True,
                     type="primary", key="btn_reg_emp"):
            st.session_state["ir_a"] = "👥  Empleados"
            st.session_state["emp_tab"] = "editar"
            st.rerun()
    with b2:
        if st.button("📋 Crear certificado", use_container_width=True,
                     key="btn_cert"):
            st.session_state["accion_rapida"] = "certificado_con_salario"
            st.rerun()
    with b3:
        if st.button("💰 Calcular liquidación", use_container_width=True,
                     key="btn_liq"):
            st.session_state["accion_rapida"] = "liquidacion_prestaciones"
            st.rerun()
    with b4:
        if st.button("🏖️ Generar vacaciones", use_container_width=True,
                     key="btn_vac"):
            st.session_state["accion_rapida"] = "carta_vacaciones"
            st.rerun()
    with b5:
        if st.button("📊 Ver reportes", use_container_width=True,
                     key="btn_rep"):
            st.session_state["ir_a"] = "📊  Reportes"
            st.rerun()

    # ── Modal de acción rápida ────────────────────────────────────────
    accion = st.session_state.get("accion_rapida")
    if accion:
        NOMBRES = {
            "certificado_con_salario":  "📋 Certificado laboral con salario",
            "carta_vacaciones":         "🏖️ Carta de vacaciones",
            "liquidacion_prestaciones": "💰 Liquidación de prestaciones",
        }
        st.divider()
        st.markdown(f"### {NOMBRES.get(accion, accion)}")

        if not empleados_all:
            st.warning("No tienes empleados registrados aún. Registra uno primero.")
            if st.button("← Cerrar", key="close_no_emp"):
                del st.session_state["accion_rapida"]
                st.rerun()
        else:
            # Filtro por tipo de documento
            if accion == "liquidacion_prestaciones":
                # Solo empleados activos (los retirados ya fueron liquidados)
                emps_disponibles = [e for e in empleados_all if e.get("activo", True)]
                if not emps_disponibles:
                    st.warning("Todos los empleados están retirados. No hay liquidaciones pendientes.")
            else:
                emps_disponibles = empleados_all

            if emps_disponibles:
                # Selector de empleado por nombre
                opciones_emp = {
                    e.get("documento",""): f"{e.get('nombre','')} · {e.get('cargo','')} · CC {e.get('documento','')}"
                    for e in emps_disponibles
                }
                doc_seleccionado = st.selectbox(
                    "👤 Selecciona el empleado",
                    list(opciones_emp.keys()),
                    format_func=lambda x: opciones_emp[x],
                    key="selectbox_accion_rapida"
                )

                # Ir al flujo completo
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("🚀 Continuar", type="primary",
                                 use_container_width=True, key="ir_flujo_rapido"):
                        # Cargar el empleado en el carrito
                        emp_sel = next(e for e in emps_disponibles
                                       if e.get("documento","") == doc_seleccionado)
                        st.session_state["accion_rapida_empleado"] = emp_sel
                        st.session_state["accion_rapida_doc"] = accion
                        st.session_state["ir_a"] = "📄  Documentos"
                        st.session_state["doc_preseleccionado"] = accion
                        del st.session_state["accion_rapida"]
                        st.rerun()
                with cc2:
                    if st.button("← Cancelar", use_container_width=True,
                                 key="cancel_accion_rapida"):
                        del st.session_state["accion_rapida"]
                        st.rerun()

    st.divider()

    # Consumo del plan
    docs_rest = max(0, max_docs - docs_usados) if not sin_limite else None
    st.markdown("### 💎 Tu plan")
    p1, p2, p3 = st.columns(3)
    p1.metric("📄 Documentos usados", docs_usados)
    p2.metric("📋 Disponibles", "∞" if sin_limite else docs_rest)
    p3.metric("💾 Base de datos", "Supabase ☁️" if usar_supabase() else "Local 💻")

    st.divider()

    # ── ¿Qué puedes hacer? (bloque existente conservado) ─────────────────
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

    # ── Multiempresa (para contadores) ────────────────────────────────
    from utils.db import empresas_listar, empresa_agregar, empresa_eliminar_id
    empresas_extra = empresas_listar(u["email"])

    with st.expander(
        f"👥 Multiempresa — Gestionar varias empresas ({len(empresas_extra)} adicional{'es' if len(empresas_extra)!=1 else ''})",
        expanded=False
    ):
        st.caption(
            "**Para contadores y gestores:** puedes administrar los documentos de "
            "varias empresas desde una sola cuenta. La empresa principal es la del "
            "formulario de abajo. Aquí puedes agregar las adicionales."
        )

        # Listar empresas adicionales
        if empresas_extra:
            st.markdown("**Empresas adicionales configuradas:**")
            for e in empresas_extra:
                ec1, ec2, ec3 = st.columns([4, 3, 1])
                with ec1:
                    st.markdown(f"🏢 **{e.get('nombre','')}**")
                with ec2:
                    st.caption(f"NIT: {e.get('nit','—')}")
                with ec3:
                    if st.button("🗑️", key=f"del_emp_{e.get('id','')}"):
                        empresa_eliminar_id(e.get("id",""))
                        st.rerun()
            st.divider()

        # Formulario para agregar nueva empresa
        st.markdown("**➕ Agregar nueva empresa:**")
        with st.form("form_nueva_empresa"):
            nc1, nc2 = st.columns(2)
            with nc1:
                new_nombre = st.text_input("Razón social *", key="ne_nombre",
                    placeholder="Distribuciones XYZ SAS")
                new_nit    = st.text_input("NIT *", key="ne_nit",
                    placeholder="900987654-3")
            with nc2:
                new_rep    = st.text_input("Representante legal *", key="ne_rep")
                new_ciudad = st.text_input("Ciudad", key="ne_ciudad",
                    placeholder="Bogotá")

            add_emp = st.form_submit_button("💾 Agregar empresa", type="primary")
            if add_emp:
                if not new_nombre or not new_nit or not new_rep:
                    st.error("Completa los campos obligatorios (*)")
                else:
                    ok, msg, id_new = empresa_agregar(u["email"], {
                        "nombre":         new_nombre,
                        "nit":            new_nit,
                        "representante":  new_rep,
                        "ciudad":         new_ciudad,
                    })
                    if ok:
                        st.success(f"✅ Empresa '{new_nombre}' agregada.")
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()

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

        # ── Formatos personalizados ─────────────────────────────────────
        # ═══════════════════════════════════════════════════════════════════
        # MODO DE GENERACIÓN DE PDF (nuevo)
        # ═══════════════════════════════════════════════════════════════════
        st.divider()
        st.markdown("### 🎨 Modo de generación de PDF")
        st.caption(
            "Decide cómo se ven tus documentos. Puedes cambiarlo en cualquier momento."
        )

        modo_actual = de.get("modo_generacion", "diseño_automatico")
        modo_seleccionado = st.radio(
            "¿Cómo quieres que se generen los PDFs?",
            options=["diseño_automatico", "solo_texto_membrete"],
            format_func=lambda x: {
                "diseño_automatico":    "🎨 Diseño automático (recomendado)",
                "solo_texto_membrete":  "📄 Solo texto sobre mi membrete oficial",
            }[x],
            index=0 if modo_actual == "diseño_automatico" else 1,
            key="modo_generacion_radio",
            horizontal=False,
        )

        if modo_seleccionado == "diseño_automatico":
            st.info(
                "✨ **Diseño automático:** El sistema arma el PDF completo con encabezado, "
                "logo, colores corporativos y pie de página. Ideal si no tienes membrete oficial."
            )
        else:
            st.info(
                "📄 **Solo texto sobre membrete:** Subes tu formato oficial (JPG, PNG o PDF de "
                "una página) y el sistema solo escribe el texto encima, respetando tu diseño. "
                "Ideal para empresas con identidad visual establecida."
            )

        # ─── Uploader adaptado según modo ─────────────────────────────
        if modo_seleccionado == "solo_texto_membrete":
            st.markdown("**📎 Sube tu membrete oficial:**")
            st.caption("Acepta JPG, PNG o PDF de una sola página. Máximo 10 MB.")

            membrete_oficial_up = st.file_uploader(
                "Membrete oficial",
                type=["png", "jpg", "jpeg", "pdf"],
                key="up_membrete_oficial",
                help="Se usa como fondo de página completa. El texto del documento "
                     "se escribirá encima respetando los márgenes."
            )

            # Verificar si ya tiene membrete oficial guardado
            from utils.membretes import obtener_membrete_empresa
            membrete_oficial_existente = obtener_membrete_empresa(u["email"])

            if membrete_oficial_existente:
                st.success("✅ Ya tienes un membrete oficial cargado")
                col_prev, col_del = st.columns([3, 1])
                with col_prev:
                    try:
                        st.image(membrete_oficial_existente, caption="Vista previa", width=300)
                    except Exception:
                        st.caption("No se pudo mostrar vista previa")
                with col_del:
                    if st.button("🗑️ Eliminar", key="del_membrete_oficial"):
                        from utils.membretes import eliminar_membrete_empresa
                        eliminar_membrete_empresa(u["email"])
                        st.session_state["_eliminar_membrete_oficial"] = True
                        st.rerun()
        else:
            membrete_oficial_up = None

        # ─── Formatos personalizados (diseño automático) ──────────────
        if modo_seleccionado == "diseño_automatico":
            with st.expander("📎 Formatos personalizados (opcional)", expanded=False):
                st.caption(
                    "Sube tu propio membrete parcial o plantilla de liquidación para "
                    "personalizar la identidad visual de tus documentos."
                )
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.markdown("**🎨 Membrete parcial**")
                    st.caption("Imagen con el header/pie que aparecerá en la parte superior")
                    membrete_up = st.file_uploader(
                        "Membrete (PNG o JPG)",
                        type=["png","jpg","jpeg"],
                        key="up_membrete",
                        help="Recomendado: 2550x300px (ancho carta)."
                    )
                    if de.get("membrete_path"):
                        st.success("✅ Ya tienes membrete cargado")
                        if st.checkbox("🗑️ Eliminar membrete actual", key="del_membrete"):
                            st.session_state["_eliminar_membrete"] = True
                with cc2:
                    st.markdown("**📊 Plantilla de liquidación**")
                    st.caption("Excel de referencia para tu formato interno")
                    plantilla_liq_up = st.file_uploader(
                        "Plantilla XLSX",
                        type=["xlsx"],
                        key="up_plantilla_liq",
                        help="Se usará como base para exportar liquidaciones a Excel."
                    )
                    if de.get("plantilla_liq_path"):
                        st.success("✅ Plantilla cargada")
        else:
            membrete_up = None
            plantilla_liq_up = None

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

                # Guardar membrete personalizado
                membrete_path = de.get("membrete_path")
                if st.session_state.get("_eliminar_membrete"):
                    membrete_path = None
                    st.session_state["_eliminar_membrete"] = False
                if membrete_up is not None:
                    ext_m = membrete_up.name.split(".")[-1]
                    membrete_path = str(CARPETA_ASSETS / f"membrete_{u['email'].split('@')[0]}.{ext_m}")
                    with open(membrete_path,"wb") as f: f.write(membrete_up.getbuffer())

                # Guardar plantilla de liquidación personalizada
                plantilla_liq_path = de.get("plantilla_liq_path")
                if plantilla_liq_up is not None:
                    plantilla_liq_path = str(CARPETA_ASSETS / f"plantilla_liq_{u['email'].split('@')[0]}.xlsx")
                    with open(plantilla_liq_path,"wb") as f: f.write(plantilla_liq_up.getbuffer())

                # ─── Procesar membrete oficial (modo "solo texto") ───
                membrete_oficial_path = None
                if modo_seleccionado == "solo_texto_membrete":
                    if membrete_oficial_up:
                        # Guardar y procesar
                        from utils.membretes import procesar_membrete
                        ok_m, msg_m, ruta_m = procesar_membrete(
                            membrete_oficial_up.getbuffer(),
                            membrete_oficial_up.name,
                            u["email"]
                        )
                        if ok_m:
                            membrete_oficial_path = ruta_m
                            st.success(f"📄 Membrete oficial cargado")
                        else:
                            st.error(f"Error con membrete oficial: {msg_m}")
                    else:
                        # Ya existía uno guardado
                        from utils.membretes import obtener_membrete_empresa
                        membrete_oficial_path = obtener_membrete_empresa(u["email"])

                datos_nuevo = {
                    "nombre":nombre,"nit":nit,"representante":representante,
                    "correo_empresa":correo_emp,"ciudad":ciudad,
                    "telefono_empresa":tel_emp,"logo_path":logo_path,
                    "membrete_path":       membrete_path,
                    "membrete_oficial_path": membrete_oficial_path,
                    "modo_generacion":      modo_seleccionado,
                    "plantilla_liq_path":  plantilla_liq_path,
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
                st.session_state["membrete_path"] = membrete_path
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
        empleado_desactivar, empleado_eliminar, importar_desde_excel,
        empleados_stats,
    )
    from utils.pantalla_empleados import pantalla_empleados

    email_usr = st.session_state.usuario["email"]
    pantalla_empleados(email_usr)


# ══════════════════════════════════════════════════════════════════════════════
# DISEÑO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "⚙️  Configuración":
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
elif pagina == "📄  Documentos":
    if not empresa_ok:
        st.error("⚠️ Configura primero los datos de tu empresa."); st.stop()

    # Usar la pantalla nueva y unificada de generación de documentos
    from utils.pantalla_documentos import pantalla_generar
    pantalla_generar(u, st.session_state.datos_empresa)

elif pagina == "💰  Liquidaciones":
    st.markdown("# 💰 Liquidaciones")
    st.caption(
        "Calcula liquidaciones definitivas conforme al CST colombiano: cesantías, "
        "intereses de cesantías, prima, vacaciones e indemnización según motivo de retiro."
    )
    st.info(
        "💡 Esta sección te lleva directamente al flujo de liquidación. "
        "Selecciona los empleados a liquidar en la pantalla siguiente."
    )
    if st.button("🚀 Iniciar liquidación", type="primary", use_container_width=False):
        st.session_state["ir_a"] = "📄  Documentos"
        st.session_state["doc_preseleccionado"] = "liquidacion_prestaciones"
        st.rerun()

    st.divider()
    st.markdown("### 📖 Guía rápida — Motivos de retiro y sus efectos")
    st.markdown("""
| Motivo de retiro | Prestaciones sociales | Indemnización |
|---|---|---|
| **Renuncia voluntaria** | ✅ Se paga | ❌ No aplica |
| **Con justa causa (Art. 62)** | ✅ Se paga | ❌ No aplica |
| **Sin justa causa (Art. 64)** | ✅ Se paga | ✅ **SÍ aplica** |
| **Mutuo acuerdo** | ✅ Se paga | ❌ No aplica (salvo pacto) |
| **Vencimiento contrato fijo** | ✅ Se paga | ❌ No aplica (con preaviso) |
| **Finalización de obra** | ✅ Se paga | ❌ No aplica (obra terminó) |
| **Período de prueba** | ✅ Se paga | ❌ No aplica (Art. 78 CST) |
| **Jubilación** | ✅ Se paga | ❌ No aplica |
""")


# ══════════════════════════════════════════════════════════════════════════════
# REPORTES Y DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📊  Reportes":
    from utils.reportes import mostrar_reportes
    mostrar_reportes(u["email"])


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
                <div style="color:#6B7280;font-size:.85rem">{periodo}</div>
                <div style="margin:1rem 0">{feats}</div>
                {'<div style="color:#059669;font-weight:600">✓ Plan actual</div>' if activo else ''}
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.info("💬 Contacta al administrador por WhatsApp para actualizar tu plan.")


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

    # ── Panel de LOGS del sistema ─────────────────────────────────────
    st.divider()
    st.markdown("### 🩺 Diagnóstico del sistema (logs)")

    from utils.logs import ver_logs, stats_logs, limpiar_logs
    stats_l = stats_logs()

    cl1, cl2, cl3, cl4 = st.columns(4)
    cl1.metric("📊 Logs totales", stats_l["total"])
    cl2.metric("✅ Info", stats_l["por_nivel"].get("info", 0))
    cl3.metric("⚠️ Advertencias", stats_l["por_nivel"].get("warn", 0))
    cl4.metric("❌ Errores", stats_l["por_nivel"].get("error", 0))

    # Filtros
    fl1, fl2, fl3 = st.columns([2, 2, 1])
    with fl1:
        nivel_filtro = st.selectbox("Nivel",
            ["Todos", "error", "warn", "info", "debug"], key="log_nivel")
    with fl2:
        evento_filtro = st.text_input("Filtrar evento (ej: liquidacion)",
            key="log_evento")
    with fl3:
        limite_filtro = st.number_input("Ver últimos",
            min_value=10, max_value=500, value=50, step=10, key="log_limite")

    if st.button("🗑️ Limpiar todos los logs", key="btn_limpiar_logs"):
        limpiar_logs()
        st.success("Logs eliminados")
        st.rerun()

    logs = ver_logs(
        limite=limite_filtro,
        nivel=nivel_filtro if nivel_filtro != "Todos" else None,
        evento_contiene=evento_filtro.strip() or None,
    )

    if not logs:
        st.info("No hay logs que coincidan con los filtros.")
    else:
        for log in logs:
            nivel_icono = {
                "error": "❌", "warn": "⚠️",
                "info": "✅", "debug": "🔍"
            }.get(log.get("nivel","?"), "•")
            ts = log.get("ts","")[:19].replace("T"," ")
            evento = log.get("evento","?")
            with st.expander(f"{nivel_icono} `{ts}` · **{evento}**"):
                st.json({k: v for k, v in log.items()
                         if k not in ("ts","nivel","evento")})
