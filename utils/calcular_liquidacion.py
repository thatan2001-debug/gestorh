"""
Módulo de cálculo de liquidación laboral básica (Colombia).

IMPORTANTE: Estas son fórmulas de ESTIMACIÓN simplificadas para PYMES.
No reemplazan el cálculo oficial de un contador o abogado laboral.
No incluyen: sanciones por no consignación de cesantías, intereses
moratorios, incapacidades, libranzas, embargos, ni casos especiales
(fuero, maternidad, accidentes laborales, etc.)
"""

from datetime import datetime, date
import pandas as pd

SALARIO_MINIMO_2026 = 1_750_905
AUXILIO_TRANSPORTE_2026 = 249_095
# El auxilio de transporte solo aplica a quienes ganan hasta 2 SMMLV
TOPE_AUXILIO_TRANSPORTE = SALARIO_MINIMO_2026 * 2


def _parsear_fecha(valor):
    """Acepta datetime, date, string dd/mm/yyyy o yyyy-mm-dd."""
    if pd.isna(valor) or valor in ("", None):
        return None
    if isinstance(valor, (datetime, date)):
        return datetime(valor.year, valor.month, valor.day)
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime()

    texto = str(valor).strip()
    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    raise ValueError(f"No se pudo interpretar la fecha: '{valor}'. Usa formato dd/mm/aaaa.")


def dias_trabajados_360(fecha_ingreso, fecha_corte):
    """
    Calcula días trabajados bajo el año comercial de 360 días (12 meses de 30 días),
    convención estándar en Colombia para liquidaciones laborales.
    """
    fi, fc = fecha_ingreso, fecha_corte
    dia_i = min(fi.day, 30)
    dia_c = min(fc.day, 30)

    años = fc.year - fi.year
    meses = fc.month - fi.month
    dias = dia_c - dia_i

    total = años * 360 + meses * 30 + dias
    return max(total, 0)


def calcular_liquidacion_fila(fila, fecha_corte_default=None):
    """
    Calcula la liquidación básica de un empleado a partir de una fila del Excel.
    Devuelve un diccionario con cada concepto y el total.
    """
    nombre = fila.get("Nombre", "")
    salario = float(fila.get("Salario", 0) or 0)
    fecha_ingreso = _parsear_fecha(fila.get("Fecha ingreso"))

    fecha_retiro_raw = fila.get("Fecha retiro")
    if fecha_retiro_raw and not pd.isna(fecha_retiro_raw) and str(fecha_retiro_raw).strip() != "":
        fecha_corte = _parsear_fecha(fecha_retiro_raw)
    else:
        fecha_corte = fecha_corte_default or datetime.today()

    if fecha_ingreso is None:
        raise ValueError(f"'{nombre}': falta la Fecha ingreso, no se puede calcular la liquidación.")
    if fecha_corte < fecha_ingreso:
        raise ValueError(f"'{nombre}': la fecha de retiro es anterior a la fecha de ingreso.")

    dias = dias_trabajados_360(fecha_ingreso, fecha_corte)

    # Auxilio de transporte: se suma a la base de cesantías y prima si el
    # salario es de hasta 2 SMMLV (regla simplificada, no incluye salario integral).
    aplica_auxilio = salario <= TOPE_AUXILIO_TRANSPORTE
    base_prestacional = salario + (AUXILIO_TRANSPORTE_2026 if aplica_auxilio else 0)

    cesantias = round(base_prestacional * dias / 360, 2)
    intereses_cesantias = round(cesantias * 0.12 * dias / 360, 2)
    prima = round(base_prestacional * dias / 360, 2)
    vacaciones = round(salario * dias / 720, 2)  # las vacaciones NO incluyen auxilio de transporte

    total = round(cesantias + intereses_cesantias + prima + vacaciones, 2)

    return {
        "Nombre": nombre,
        "Documento": fila.get("Documento", ""),
        "Cargo": fila.get("Cargo", ""),
        "Salario": salario,
        "Fecha ingreso": fecha_ingreso.strftime("%d/%m/%Y"),
        "Fecha corte": fecha_corte.strftime("%d/%m/%Y"),
        "Dias trabajados (360)": dias,
        "Auxilio transporte aplica": "Sí" if aplica_auxilio else "No",
        "Cesantias": cesantias,
        "Intereses cesantias": intereses_cesantias,
        "Prima": prima,
        "Vacaciones": vacaciones,
        "Total liquidacion": total,
    }


def calcular_liquidacion_df(df, fecha_corte_default=None):
    """Aplica el cálculo a todas las filas de un DataFrame y devuelve un DataFrame de resultados."""
    resultados = []
    errores = []
    for idx, fila in df.iterrows():
        try:
            resultados.append(calcular_liquidacion_fila(fila, fecha_corte_default))
        except ValueError as e:
            errores.append(f"Fila {idx + 2}: {e}")  # +2 por encabezado + índice base 0
    return pd.DataFrame(resultados), errores
