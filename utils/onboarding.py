"""
Onboarding de empresa para RH Fácil.
Cuando una PYME se registra, completa su perfil completo en un flujo
de 3 pasos antes de poder usar la app.
Todos los datos se persisten en Supabase (o JSON local como fallback).
"""

import streamlit as st
from pathlib import Path
from utils.supabase_db import empresa_guardar, empresa_cargar, empresa_onboarding_completo

SECTORES = [
    "Selecciona...",
    "Alimentos y bebidas", "Comercio al por menor", "Comercio al por mayor",
    "Construcción", "Educación", "Manufactura", "Salud",
    "Servicios profesionales", "Tecnología", "Transporte y logística",
    "Turismo y hotelería", "Otro",
]

RANGOS_EMPLEADOS = [
    "Selecciona...", "1 a 5", "6 a 15", "16 a 30", "31 a 50",
    "51 a 100", "101 a 200", "Más de 200",
]


def mostrar_onboarding(email: str, nombre_usuario: str) -> bool:
    """
    Muestra el flujo de onboarding de 3 pasos.
    Retorna True cuando el usuario completa todo y puede usar la app.
    """
    st.markdown("""
    <style>
    .ob-header { background:linear-gradient(135deg,#1B3F6E,#2D6BE4);
        color:white; border-radius:14px; padding:28px 32px; margin-bottom:28px; }
    .ob-step { display:flex; align-items:center; gap:12px; margin-bottom:10px; }
    .ob-num { width:32px; height:32px; border-radius:50%; display:flex;
        align-items:center; justify-content:center; font-weight:700; flex-shrink:0; }
    .ob-num.active { background:#2D6BE4; color:white; }
    .ob-num.done { background:#059669; color:white; }
    .ob-num.pending { background:rgba(255,255,255,.2); color:rgba(255,255,255,.7); }
    </style>
    """, unsafe_allow_html=True)

    paso = st.session_state.get("ob_paso", 1)

    # Encabezado
    pasos_labels = ["Datos de tu empresa", "Firmantes y responsables", "Diseño de documentos"]
    st.markdown(f"""
    <div class="ob-header">
        <h2 style="margin:0 0 6px;font-size:1.3rem">
            👋 Bienvenido, {nombre_usuario.split()[0]}
        </h2>
        <p style="margin:0 0 20px;opacity:.85;font-size:.95rem">
            Configura tu empresa una sola vez. Tus datos quedarán guardados
            y se usarán automáticamente en todos tus documentos.
        </p>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
    """, unsafe_allow_html=True)

    for i, label in enumerate(pasos_labels, 1):
        cls = "done" if i < paso else ("active" if i == paso else "pending")
        icono = "✓" if i < paso else str(i)
        st.markdown(f"""
            <div class="ob-step">
                <div class="ob-num {cls}">{icono}</div>
                <span style="font-size:.88rem;{'font-weight:700' if i==paso else 'opacity:.75'};color:white">
                    {label}
                </span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Cargar datos previos si existen
    if "ob_datos" not in st.session_state:
        datos_previos = empresa_cargar(email) or {}
        st.session_state.ob_datos = datos_previos

    ob = st.session_state.ob_datos

    # ══════════════════════════════════════════════════════
    # PASO 1: Datos de la empresa
    # ══════════════════════════════════════════════════════
    if paso == 1:
        st.markdown("### 🏢 Datos legales de tu empresa")
        st.caption("Esta información aparecerá en el encabezado de todos tus documentos.")

        with st.form("ob_paso1"):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Razón social o nombre comercial *",
                    value=ob.get("nombre",""), placeholder="Distribuciones ABC SAS")
                nit = st.text_input("NIT *",
                    value=ob.get("nit",""), placeholder="900.123.456-7")
                ciudad = st.text_input("Ciudad *",
                    value=ob.get("ciudad",""), placeholder="Medellín")
                sector = st.selectbox("Sector económico *",
                    SECTORES, index=SECTORES.index(ob.get("sector","Selecciona..."))
                    if ob.get("sector") in SECTORES else 0)
            with c2:
                direccion = st.text_input("Dirección",
                    value=ob.get("direccion",""), placeholder="Cra 45 #50-30")
                telefono = st.text_input("Teléfono empresa",
                    value=ob.get("telefono_empresa",""), placeholder="(604) 123 4567")
                correo_emp = st.text_input("Correo corporativo *",
                    value=ob.get("correo_empresa",""), placeholder="rrhh@miempresa.com")
                num_empleados = st.selectbox("Número de empleados *",
                    RANGOS_EMPLEADOS, index=RANGOS_EMPLEADOS.index(ob.get("num_empleados","Selecciona..."))
                    if ob.get("num_empleados") in RANGOS_EMPLEADOS else 0)

            logo = st.file_uploader("Logo de la empresa (PNG o JPG recomendado)",
                type=["png","jpg","jpeg"],
                help="Aparecerá en la esquina superior derecha de todos tus documentos")

            continuar = st.form_submit_button("Continuar →", type="primary")

            if continuar:
                errores = []
                if not nombre: errores.append("Razón social requerida")
                if not nit: errores.append("NIT requerido")
                if not ciudad: errores.append("Ciudad requerida")
                if sector == "Selecciona...": errores.append("Selecciona un sector")
                if not correo_emp: errores.append("Correo corporativo requerido")
                if num_empleados == "Selecciona...": errores.append("Número de empleados requerido")

                if errores:
                    for e in errores: st.error(e)
                else:
                    # Guardar logo si lo subió
                    logo_nombre = ob.get("logo_nombre","")
                    if logo:
                        Path("assets").mkdir(exist_ok=True)
                        ext = logo.name.split(".")[-1].lower()
                        logo_nombre = f"logo_{email.split('@')[0]}.{ext}"
                        with open(f"assets/{logo_nombre}", "wb") as f:
                            f.write(logo.getbuffer())
                        # Guardar también en session_state para uso inmediato
                        st.session_state.datos_empresa = st.session_state.get("datos_empresa", {})
                        st.session_state.datos_empresa["logo_path"] = f"assets/{logo_nombre}"

                    st.session_state.ob_datos.update({
                        "nombre": nombre, "nit": nit, "ciudad": ciudad,
                        "direccion": direccion, "telefono_empresa": telefono,
                        "correo_empresa": correo_emp, "sector": sector,
                        "num_empleados": num_empleados, "logo_nombre": logo_nombre,
                    })
                    st.session_state.ob_paso = 2
                    st.rerun()

    # ══════════════════════════════════════════════════════
    # PASO 2: Firmantes
    # ══════════════════════════════════════════════════════
    elif paso == 2:
        st.markdown("### ✍️ Representante legal y firmantes")
        st.caption("Define quién firma cada tipo de documento. Si es la misma persona para todo, escríbela una vez arriba.")

        with st.form("ob_paso2"):
            representante = st.text_input("Representante legal *",
                value=ob.get("representante",""),
                placeholder="Nombre completo — aparece en documentos legales")

            st.markdown("**Firmantes por tipo de documento** *(dejar vacío = usa el representante legal)*")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("📋 **Certificados**")
                fcn = st.text_input("Nombre", value=ob.get("firmante_cert_nombre",""),
                    key="fcn", placeholder=ob.get("representante","Nombre"))
                fcc = st.text_input("Cargo", value=ob.get("firmante_cert_cargo",""),
                    key="fcc", placeholder="Líder de Recursos Humanos")
            with c2:
                st.markdown("🏖️ **Vacaciones**")
                fvn = st.text_input("Nombre", value=ob.get("firmante_vac_nombre",""),
                    key="fvn", placeholder=ob.get("representante","Nombre"))
                fvc = st.text_input("Cargo", value=ob.get("firmante_vac_cargo",""),
                    key="fvc", placeholder="Gerente Administrativo")
            with c3:
                st.markdown("💰 **Liquidaciones**")
                fln = st.text_input("Nombre", value=ob.get("firmante_liq_nombre",""),
                    key="fln", placeholder=ob.get("representante","Nombre"))
                flc = st.text_input("Cargo", value=ob.get("firmante_liq_cargo",""),
                    key="flc", placeholder="Representante Legal")

            c1, c2 = st.columns(2)
            with c1:
                atras = st.form_submit_button("← Atrás")
            with c2:
                continuar = st.form_submit_button("Continuar →", type="primary")

            if atras:
                st.session_state.ob_paso = 1; st.rerun()

            if continuar:
                if not representante:
                    st.error("El representante legal es obligatorio.")
                else:
                    rep = representante
                    st.session_state.ob_datos.update({
                        "representante": rep,
                        "firmante_cert_nombre": fcn.strip() or rep,
                        "firmante_cert_cargo":  fcc.strip() or "Representante Legal",
                        "firmante_vac_nombre":  fvn.strip() or rep,
                        "firmante_vac_cargo":   fvc.strip() or "Representante Legal",
                        "firmante_liq_nombre":  fln.strip() or rep,
                        "firmante_liq_cargo":   flc.strip() or "Representante Legal",
                    })
                    st.session_state.ob_paso = 3; st.rerun()

    # ══════════════════════════════════════════════════════
    # PASO 3: Diseño
    # ══════════════════════════════════════════════════════
    elif paso == 3:
        st.markdown("### 🎨 Diseño de tus documentos")
        st.caption("Puedes cambiarlo después en cualquier momento.")

        from utils.plantillas_disenio import PALETAS
        disenio_actual = ob.get("disenio_seleccionado", 1)

        # Preview rápido de diseños
        cols = st.columns(5)
        for i, col in enumerate(cols, 1):
            p = PALETAS[i]
            p_hex = p["primario"].hexval() if hasattr(p["primario"],"hexval") else "#1B3F6E"
            s_hex = p["secundario"].hexval() if hasattr(p["secundario"],"hexval") else "#2D6BE4"
            sel = disenio_actual == i
            with col:
                st.markdown(f"""
                <div style="border:3px solid {'#2D6BE4' if sel else '#E5E7EB'};
                    border-radius:10px;overflow:hidden;margin-bottom:6px;cursor:pointer">
                    <div style="background:{p_hex};padding:8px;text-align:center">
                        <div style="color:white;font-size:.65rem;font-weight:700">EMPRESA</div>
                        <div style="color:rgba(255,255,255,.7);font-size:.6rem">Nit #900</div>
                    </div>
                    <div style="background:white;padding:6px">
                        <div style="background:{s_hex};height:3px;border-radius:2px;width:60%;margin-bottom:3px"></div>
                        <div style="height:2px;background:#E5E7EB;border-radius:2px;width:80%"></div>
                    </div>
                </div>
                <div style="text-align:center;font-size:.72rem;
                    font-weight:{'700' if sel else '400'};color:{'#1B3F6E' if sel else '#6B7280'}">
                    {'✅ ' if sel else ''}{p['nombre']}
                </div>""", unsafe_allow_html=True)
                if st.button("Elegir" if not sel else "✓ Activo",
                    key=f"ob_d{i}", use_container_width=True,
                    type="primary" if sel else "secondary"):
                    st.session_state.ob_datos["disenio_seleccionado"] = i
                    st.rerun()

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            usar_logo = st.checkbox("✅ Mostrar logo en encabezado",
                value=ob.get("usar_logo_encabezado", True))
        with c2:
            usar_mda = st.checkbox("💧 Logo como marca de agua",
                value=ob.get("usar_marca_agua", False))

        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Atrás"):
                st.session_state.ob_paso = 2; st.rerun()
        with c2:
            if st.button("🚀 ¡Listo! Ir a mi app", type="primary", use_container_width=True):
                # Guardar todo
                datos_finales = {**st.session_state.ob_datos,
                    "usar_logo_encabezado": usar_logo,
                    "usar_marca_agua": usar_mda,
                    "disenio_seleccionado": st.session_state.ob_datos.get("disenio_seleccionado", 1),
                    "onboarding_completo": True,
                }
                if empresa_guardar(email, datos_finales):
                    # Sincronizar con session_state principal
                    logo_nombre = datos_finales.get("logo_nombre","")
                    logo_path = f"assets/{logo_nombre}" if logo_nombre and Path(f"assets/{logo_nombre}").exists() else None
                    rep = datos_finales.get("representante","")
                    st.session_state.datos_empresa = {
                        **datos_finales,
                        "logo_path": logo_path,
                        "_cargo_firmante": datos_finales.get("firmante_cert_cargo","Representante Legal"),
                    }
                    st.session_state.disenio_seleccionado = datos_finales.get("disenio_seleccionado", 1)
                    st.session_state.usar_logo_enc     = usar_logo
                    st.session_state.usar_marca_agua   = usar_mda
                    st.session_state.ob_paso = 1
                    del st.session_state["ob_datos"]
                    st.success("✅ Empresa configurada. ¡Bienvenido a RH Fácil!")
                    st.rerun()
                else:
                    st.error("Error guardando los datos. Intenta de nuevo.")

    return empresa_onboarding_completo(email)
