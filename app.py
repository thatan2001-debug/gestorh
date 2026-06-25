"""
RH Fácil — Generador de documentos laborales para PYMES (Colombia)

Ejecutar con: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime
import zipfile
import io

from utils.validar_datos import cargar_y_validar
from utils.calcular_liquidacion import calcular_liquidacion_df, SALARIO_MINIMO_2026, AUXILIO_TRANSPORTE_2026
from utils.generar_pdf import (
    generar_certificado_laboral, generar_carta_vacaciones, generar_pdf_liquidacion,
)

st.set_page_config(page_title="RH Fácil", page_icon="📄", layout="wide")

CARPETA_SALIDAS = Path("salidas")
CARPETA_SALIDAS.mkdir(exist_ok=True)
CARPETA_ASSETS = Path("assets")
CARPETA_ASSETS.mkdir(exist_ok=True)
PLANTILLA_EXCEL = Path("plantillas/Base_Empleados.xlsx")

# ---------- Estado de sesión ----------
if "datos_empresa" not in st.session_state:
    st.session_state.datos_empresa = {
        "nombre": "", "nit": "", "representante": "", "logo_path": None,
    }
if "df_empleados" not in st.session_state:
    st.session_state.df_empleados = None
if "archivos_generados" not in st.session_state:
    st.session_state.archivos_generados = []

# ---------- Sidebar: navegación ----------
st.sidebar.title("📄 RH Fácil")
st.sidebar.caption("Documentos laborales en minutos")
pagina = st.sidebar.radio(
    "Navegación",
    ["1. Inicio", "2. Datos de tu empresa", "3. Cargar empleados", "4. Generar documentos"],
    label_visibility="collapsed",
)

empresa_lista = bool(st.session_state.datos_empresa["nombre"] and st.session_state.datos_empresa["nit"])
st.sidebar.divider()
st.sidebar.write("✅ Empresa configurada" if empresa_lista else "⬜ Empresa sin configurar")
st.sidebar.write("✅ Empleados cargados" if st.session_state.df_empleados is not None else "⬜ Sin empleados cargados")

# =========================================================
# PANTALLA 1: INICIO
# =========================================================
if pagina == "1. Inicio":
    st.title("RH Fácil")
    st.subheader("Genera certificados laborales, cartas de vacaciones y liquidaciones básicas en minutos.")
    st.write(
        "Ideal para pequeñas empresas, contadores y áreas administrativas que necesitan "
        "producir documentos laborales en lote, a partir de un solo archivo Excel."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1️⃣ Configura tu empresa")
        st.write("Nombre, NIT, representante legal y logo.")
    with col2:
        st.markdown("### 2️⃣ Carga tus empleados")
        st.write("Sube un Excel con los datos básicos del personal.")
    with col3:
        st.markdown("### 3️⃣ Genera y descarga")
        st.write("Certificados, cartas de vacaciones y liquidaciones en PDF, listos en un ZIP.")

    st.divider()
    st.warning(
        "⚠️ **Importante**: las liquidaciones generadas son una **estimación básica** "
        "(cesantías, intereses, prima y vacaciones). No reemplazan el cálculo de un "
        "contador o abogado laboral, y no cubren casos especiales (salario integral, "
        "incapacidades, fuero, embargos, etc.). Compáralas con la calculadora oficial "
        "del Ministerio del Trabajo antes de usarlas para un pago real."
    )
    st.caption(
        f"Datos de referencia 2026: Salario mínimo ${SALARIO_MINIMO_2026:,.0f} · "
        f"Auxilio de transporte ${AUXILIO_TRANSPORTE_2026:,.0f}".replace(",", ".")
    )

    st.divider()
    if st.button("👉 Empezar: configurar mi empresa", type="primary"):
        st.session_state["_ir_a_empresa"] = True
        st.rerun()

# =========================================================
# PANTALLA 2: DATOS DE LA EMPRESA
# =========================================================
elif pagina == "2. Datos de tu empresa":
    st.title("Datos de tu empresa")
    st.write("Esta información aparecerá en el encabezado y la firma de todos los documentos generados.")

    with st.form("form_empresa"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre o razón social *", value=st.session_state.datos_empresa["nombre"])
            nit = st.text_input("NIT *", value=st.session_state.datos_empresa["nit"])
        with col2:
            representante = st.text_input(
                "Representante legal (para la firma) *",
                value=st.session_state.datos_empresa["representante"],
            )
            logo = st.file_uploader("Logo de la empresa (opcional, PNG o JPG)", type=["png", "jpg", "jpeg"])

        guardar = st.form_submit_button("Guardar datos de la empresa", type="primary")

        if guardar:
            if not nombre or not nit or not representante:
                st.error("Por favor completa nombre, NIT y representante legal.")
            else:
                logo_path = st.session_state.datos_empresa.get("logo_path")
                if logo is not None:
                    logo_path = str(CARPETA_ASSETS / f"logo_empresa.{logo.name.split('.')[-1]}")
                    with open(logo_path, "wb") as f:
                        f.write(logo.getbuffer())

                st.session_state.datos_empresa = {
                    "nombre": nombre, "nit": nit, "representante": representante,
                    "logo_path": logo_path,
                }
                st.success("✅ Datos de la empresa guardados. Ahora puedes cargar tus empleados.")

    if st.session_state.datos_empresa.get("logo_path"):
        st.image(st.session_state.datos_empresa["logo_path"], width=120, caption="Logo actual")

# =========================================================
# PANTALLA 3: CARGAR EMPLEADOS
# =========================================================
elif pagina == "3. Cargar empleados":
    st.title("Cargar base de empleados")

    if PLANTILLA_EXCEL.exists():
        with open(PLANTILLA_EXCEL, "rb") as f:
            st.download_button(
                "⬇️ Descargar plantilla Excel (Base_Empleados.xlsx)",
                f, file_name="Base_Empleados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    st.caption(
        "Columnas obligatorias: Nombre, Documento, Cargo, Salario, Fecha ingreso. "
        "Opcionales: Fecha retiro, Tipo contrato, Correo."
    )

    st.divider()
    archivo = st.file_uploader("Sube tu archivo Excel de empleados", type=["xlsx"])

    if archivo:
        df, errores_columnas, errores_filas = cargar_y_validar(archivo)

        if errores_columnas:
            for err in errores_columnas:
                st.error(err)
        else:
            if errores_filas:
                st.warning(f"Se encontraron {len(errores_filas)} problema(s) en los datos:")
                for err in errores_filas:
                    st.write(f"- {err}")
                st.info("Corrige el Excel y vuelve a subirlo, o continúa solo con las filas válidas (no recomendado).")
            else:
                st.success(f"✅ {len(df)} empleado(s) cargados correctamente, sin errores.")

            st.dataframe(df, use_container_width=True)
            st.session_state.df_empleados = df if not errores_filas else None

            if errores_filas and st.button("Continuar de todas formas (se omitirán filas con error)"):
                st.session_state.df_empleados = df
                st.rerun()

# =========================================================
# PANTALLA 4: GENERAR DOCUMENTOS
# =========================================================
elif pagina == "4. Generar documentos":
    st.title("Generar documentos")

    if not empresa_lista:
        st.error("⚠️ Primero completa los **datos de tu empresa** (pantalla 2).")
        st.stop()
    if st.session_state.df_empleados is None:
        st.error("⚠️ Primero carga una base de **empleados válida** (pantalla 3).")
        st.stop()

    df = st.session_state.df_empleados
    datos_empresa = st.session_state.datos_empresa

    st.write(f"Empresa: **{datos_empresa['nombre']}** · Empleados cargados: **{len(df)}**")

    st.subheader("Selecciona los documentos a generar")
    col1, col2, col3 = st.columns(3)
    with col1:
        gen_certificados = st.checkbox("📋 Certificados laborales", value=True)
    with col2:
        gen_vacaciones = st.checkbox("🏖️ Cartas de vacaciones")
    with col3:
        gen_liquidacion = st.checkbox("💰 Liquidaciones básicas")

    fecha_inicio_vac, fecha_fin_vac = None, None
    if gen_vacaciones:
        st.write("**Periodo de vacaciones** (se aplicará igual a todos los empleados seleccionados; "
                  "puedes editar cartas individuales después si varía por persona):")
        c1, c2 = st.columns(2)
        with c1:
            fecha_inicio_vac = st.date_input("Fecha inicio", value=date.today())
        with c2:
            fecha_fin_vac = st.date_input("Fecha fin", value=date.today())

    fecha_corte_liq = None
    if gen_liquidacion:
        usar_retiro = st.checkbox(
            "Usar 'Fecha retiro' del Excel cuando exista (si está vacía, se usa la fecha de corte de abajo)",
            value=True,
        )
        fecha_corte_liq = st.date_input("Fecha de corte para liquidación (empleados activos)", value=date.today())

    st.divider()

    if st.button("🚀 Generar documentos", type="primary"):
        if not (gen_certificados or gen_vacaciones or gen_liquidacion):
            st.error("Selecciona al menos un tipo de documento.")
            st.stop()

        archivos_generados = []
        errores_generacion = []
        barra = st.progress(0, text="Generando documentos...")
        total_pasos = len(df) * sum([gen_certificados, gen_vacaciones]) + (1 if gen_liquidacion else 0)
        paso_actual = 0

        # Certificados y vacaciones, por empleado
        for _, fila in df.iterrows():
            nombre_archivo_base = str(fila.get("Nombre", "empleado")).strip().replace(" ", "_")
            empleado = fila.to_dict()

            if gen_certificados:
                try:
                    ruta = CARPETA_SALIDAS / f"Certificado_{nombre_archivo_base}.pdf"
                    generar_certificado_laboral(empleado, datos_empresa, str(ruta))
                    archivos_generados.append(ruta)
                except Exception as e:
                    errores_generacion.append(f"Certificado de {fila.get('Nombre')}: {e}")
                paso_actual += 1
                barra.progress(min(paso_actual / max(total_pasos, 1), 1.0))

            if gen_vacaciones:
                try:
                    ruta = CARPETA_SALIDAS / f"Vacaciones_{nombre_archivo_base}.pdf"
                    generar_carta_vacaciones(
                        empleado, datos_empresa, str(ruta),
                        fecha_inicio=fecha_inicio_vac.strftime("%d/%m/%Y"),
                        fecha_fin=fecha_fin_vac.strftime("%d/%m/%Y"),
                    )
                    archivos_generados.append(ruta)
                except Exception as e:
                    errores_generacion.append(f"Carta de vacaciones de {fila.get('Nombre')}: {e}")
                paso_actual += 1
                barra.progress(min(paso_actual / max(total_pasos, 1), 1.0))

        # Liquidaciones (calculadas en bloque)
        if gen_liquidacion:
            df_calculo = df.copy()
            if not usar_retiro:
                df_calculo["Fecha retiro"] = None

            df_resultados, errores_calculo = calcular_liquidacion_df(
                df_calculo,
                fecha_corte_default=datetime(fecha_corte_liq.year, fecha_corte_liq.month, fecha_corte_liq.day),
            )
            errores_generacion.extend(errores_calculo)

            for _, resultado in df_resultados.iterrows():
                nombre_archivo_base = str(resultado["Nombre"]).strip().replace(" ", "_")
                try:
                    ruta = CARPETA_SALIDAS / f"Liquidacion_{nombre_archivo_base}.pdf"
                    generar_pdf_liquidacion(resultado.to_dict(), datos_empresa, str(ruta))
                    archivos_generados.append(ruta)
                except Exception as e:
                    errores_generacion.append(f"Liquidación de {resultado['Nombre']}: {e}")

            if not df_resultados.empty:
                ruta_excel = CARPETA_SALIDAS / "Resumen_Liquidaciones.xlsx"
                df_resultados.to_excel(ruta_excel, index=False)
                archivos_generados.append(ruta_excel)

            paso_actual += 1
            barra.progress(1.0)

        barra.empty()
        st.session_state.archivos_generados = archivos_generados

        if errores_generacion:
            st.warning(f"Se generaron documentos, pero hubo {len(errores_generacion)} error(es):")
            for err in errores_generacion:
                st.write(f"- {err}")

        if archivos_generados:
            st.success(f"✅ Se generaron {len(archivos_generados)} documento(s) correctamente.")

    # Empaquetar y descargar
    if st.session_state.archivos_generados:
        st.divider()
        st.subheader("Descargar resultados")

        buffer_zip = io.BytesIO()
        with zipfile.ZipFile(buffer_zip, "w") as zipf:
            for ruta in st.session_state.archivos_generados:
                if Path(ruta).exists():
                    zipf.write(ruta, Path(ruta).name)
        buffer_zip.seek(0)

        st.download_button(
            "⬇️ Descargar todos los documentos (ZIP)",
            data=buffer_zip,
            file_name=f"documentos_{datos_empresa['nombre'].replace(' ', '_')}.zip",
            mime="application/zip",
            type="primary",
        )

        with st.expander("Ver lista de archivos generados"):
            for ruta in st.session_state.archivos_generados:
                st.write(f"- {Path(ruta).name}")
