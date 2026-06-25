"""Validación de la base de empleados cargada en Excel."""

import pandas as pd

COLUMNAS_REQUERIDAS = [
    "Nombre", "Documento", "Cargo", "Salario", "Fecha ingreso",
]

COLUMNAS_OPCIONALES = ["Fecha retiro", "Tipo contrato", "Correo"]


def validar_columnas(df: pd.DataFrame):
    """Devuelve lista de errores (vacía si todo OK)."""
    errores = []
    columnas = [c.strip() for c in df.columns]
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in columnas]
    if faltantes:
        errores.append(
            "Faltan columnas obligatorias en el Excel: " + ", ".join(faltantes) +
            ". Descarga la plantilla y verifica los encabezados."
        )
    return errores


def validar_filas(df: pd.DataFrame):
    """Valida fila por fila campos críticos. Devuelve lista de strings de error."""
    errores = []
    for idx, fila in df.iterrows():
        n_fila = idx + 2  # +2: encabezado + índice base 0
        nombre = str(fila.get("Nombre", "")).strip()

        if not nombre or nombre.lower() == "nan":
            errores.append(f"Fila {n_fila}: falta el nombre del empleado.")
            continue  # sin nombre, mejor no seguir validando esa fila

        try:
            salario = float(fila.get("Salario", 0))
            if salario <= 0:
                errores.append(f"Fila {n_fila} ({nombre}): el salario debe ser mayor a 0.")
        except (ValueError, TypeError):
            errores.append(f"Fila {n_fila} ({nombre}): el salario no es un número válido.")

        documento = str(fila.get("Documento", "")).strip()
        if not documento or documento.lower() == "nan":
            errores.append(f"Fila {n_fila} ({nombre}): falta el número de documento.")

        fecha_ingreso = fila.get("Fecha ingreso")
        if pd.isna(fecha_ingreso) or str(fecha_ingreso).strip() == "":
            errores.append(f"Fila {n_fila} ({nombre}): falta la fecha de ingreso.")

    return errores


def cargar_y_validar(archivo):
    """
    Lee el Excel y devuelve (df, errores_columnas, errores_filas).
    Si hay errores de columnas, df puede ser None.
    """
    try:
        df = pd.read_excel(archivo, dtype={"Documento": str, "NIT": str})
    except Exception as e:
        return None, [f"No se pudo leer el archivo Excel: {e}"], []

    df.columns = [str(c).strip() for c in df.columns]

    errores_columnas = validar_columnas(df)
    if errores_columnas:
        return df, errores_columnas, []

    errores_filas = validar_filas(df)
    return df, [], errores_filas
