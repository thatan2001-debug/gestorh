# RH Fácil — Generador de documentos laborales para PYMES

App web (Streamlit) que genera, a partir de un Excel de empleados:
- ✅ Certificados laborales (PDF)
- ✅ Cartas de vacaciones (PDF)
- ✅ Liquidaciones básicas estimadas (PDF + resumen Excel)

Pensada para pequeñas empresas, contadores y áreas administrativas en Colombia.

## ⚠️ Aviso importante

Las liquidaciones son una **estimación básica** (cesantías, intereses de cesantías,
prima y vacaciones sobre año comercial de 360 días). **No reemplazan** el cálculo de
un contador o abogado laboral, y no cubren casos especiales: salario integral,
incapacidades, fuero, embargos, sanciones moratorias, etc. Valídalas siempre antes
de usarlas para un pago real. Puedes contrastarlas con la calculadora oficial del
Ministerio del Trabajo.

## Requisitos

- Python 3.10 o superior
- No necesita LibreOffice ni ninguna instalación adicional del sistema: los PDF se
  generan directamente en Python con `reportlab`.

## Instalación local

```bash
# 1. Crear y activar un entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. (Solo la primera vez) generar la plantilla Excel descargable
python utils/crear_plantilla_excel.py

# 4. Ejecutar la app
streamlit run app.py
```

La app se abrirá en tu navegador, normalmente en `http://localhost:8501`.

## Flujo de uso

1. **Datos de tu empresa**: nombre, NIT, representante legal y logo (opcional).
2. **Cargar empleados**: descarga la plantilla `Base_Empleados.xlsx`, llénala y súbela.
   Columnas obligatorias: `Nombre`, `Documento`, `Cargo`, `Salario`, `Fecha ingreso`.
   Opcionales: `Fecha retiro`, `Tipo contrato`, `Correo`.
3. **Generar documentos**: elige qué documentos crear, ajusta fechas si aplica, y
   genera. Descarga todo en un solo ZIP.

## Estructura del proyecto

```
rh_facil/
├── app.py                          # App principal de Streamlit (4 pantallas)
├── requirements.txt
├── plantillas/
│   └── Base_Empleados.xlsx         # Plantilla descargable (generada por el script)
├── salidas/                        # PDFs generados (se crea automáticamente)
├── assets/                         # Logo de empresa subido por el usuario
└── utils/
    ├── validar_datos.py            # Validación del Excel cargado
    ├── calcular_liquidacion.py     # Fórmulas de liquidación básica (Colombia)
    ├── generar_pdf.py              # Generación de los 3 tipos de PDF (reportlab)
    └── crear_plantilla_excel.py    # Script para (re)generar la plantilla Excel
```

## Despliegue en Streamlit Cloud

1. Sube este proyecto a un repositorio de GitHub.
2. Entra a [share.streamlit.io](https://share.streamlit.io), conecta el repo.
3. Define `app.py` como archivo principal.
4. Streamlit Cloud instalará automáticamente lo que esté en `requirements.txt`.

## Próximos pasos sugeridos (no incluidos en este MVP)

- Contratos laborales completos.
- Firma electrónica.
- Multiempresa / multiusuario con login.
- Plantillas personalizables por el usuario.
- Persistencia en base de datos (SQLite / Supabase) en vez de sesión en memoria.
- Validación de fechas/topes de auxilio de transporte para años distintos a 2026
  (hoy estos valores están fijos en el código, en `utils/calcular_liquidacion.py`).
