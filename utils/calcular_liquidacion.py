"""
Módulo de cálculo de liquidación laboral (Colombia) — Actualizado 2026.

Base legal:
- Art. 249 CST: Cesantías (1 mes/año o proporcional)
- Ley 52/1975 + Art. 99 Ley 50/1990: Intereses cesantías 12% anual
- Art. 306 CST: Prima de servicios (15 días por semestre)
- Art. 186 CST: Vacaciones (15 días hábiles/año, base = solo salario)
- Art. 64 CST + Ley 789/2002: Indemnización por despido sin justa causa
- Decreto 1469/2025 + Decreto 159/2026: SMMLV $1.750.905
- Decreto 1470/2025: Auxilio de transporte $249.095

IMPORTANTE: Estimación de referencia. No reemplaza concepto de contador
o abogado laboral. No cubre: salario integral, incapacidades, fuero,
embargos, licencias, comisiones variables, horas extras ni mora.
"""

from datetime import datetime, date
import pandas as pd

# ── Valores oficiales 2026 ──────────────────────────────────────────────────
SALARIO_MINIMO_2026 = 1_750_905
AUXILIO_TRANSPORTE_2026 = 249_095
TOPE_AUXILIO_TRANSPORTE = SALARIO_MINIMO_2026 * 2   # 2 SMMLV = $3.501.810

TIPOS_CONTRATO_FIJO = {"fijo", "término fijo", "termino fijo", "a término fijo"}


def _parsear_fecha(valor):
    """
    Acepta datetime, date, Timestamp, y strings en múltiples formatos.
    Maneja timestamps de Supabase: '2026-05-01 00:00:00' o '2026-05-01T00:00:00'.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(valor, datetime):
        return valor.replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime().replace(hour=0, minute=0, second=0, microsecond=0)

    texto = str(valor).strip()
    if not texto or texto.lower() in ("none","nan","nat","null",""):
        return None

    # Quitar la parte de hora si existe (Supabase: "2026-05-01 00:00:00")
    if " " in texto:
        texto = texto.split(" ")[0]
    if "T" in texto:
        texto = texto.split("T")[0]

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None


def _dias_360(fecha_ingreso: datetime, fecha_corte: datetime) -> int:
    """
    Año comercial de 360 días (12 meses × 30 días).
    Convención estándar CST para prestaciones sociales en Colombia.
    """
    di, dc = fecha_ingreso, fecha_corte
    d1 = min(di.day, 30)
    d2 = min(dc.day, 30)
    total = (dc.year - di.year) * 360 + (dc.month - di.month) * 30 + (d2 - d1)
    return max(total, 0)


def _dias_semestre_actual(fecha_ingreso: datetime, fecha_corte: datetime) -> int:
    """
    Días trabajados dentro del semestre en curso al momento del corte.
    Semestre 1: ene–jun (inicio 1 ene), Semestre 2: jul–dic (inicio 1 jul).
    Art. 306 CST: prima se calcula por semestre, no por año completo.
    """
    mes_corte = fecha_corte.month
    if mes_corte <= 6:
        inicio_semestre = datetime(fecha_corte.year, 1, 1)
    else:
        inicio_semestre = datetime(fecha_corte.year, 7, 1)

    inicio_calculo = max(fecha_ingreso, inicio_semestre)
    return _dias_360(inicio_calculo, fecha_corte)


def _indemnizacion(salario: float, dias_totales: int, tipo_contrato: str) -> float:
    """
    Indemnización por despido sin justa causa — Art. 64 CST + Ley 789/2002.

    Contrato indefinido:
      - Primer año: 30 días de salario.
      - A partir del 2° año: 20 días adicionales por año o fracción.
    Contrato a término fijo:
      - Días pendientes hasta el vencimiento pactado (estimado).
    """
    salario_diario = salario / 30
    años = dias_totales / 360

    tipo_lower = str(tipo_contrato).strip().lower()
    if tipo_lower in TIPOS_CONTRATO_FIJO:
        # Estimación: promedio de medio período restante (sin fecha fin exacta)
        dias_indem = max(30, 90)   # mínimo orientativo; requiere fecha fin real
        return round(salario_diario * dias_indem, 2)

    # Contrato indefinido
    if años <= 1:
        return round(salario_diario * 30, 2)
    else:
        dias_adicionales = 20 * (años - 1)
        return round(salario_diario * (30 + dias_adicionales), 2)


def calcular_liquidacion_fila(
    fila,
    fecha_corte_default=None,
    incluir_indemnizacion: bool = False,
    motivo_retiro: str = "renuncia",
):
    """
    Calcula la liquidación completa de un empleado.

    Parámetros:
        fila: dict o pd.Series con los campos del Excel.
        fecha_corte_default: fecha de corte si no hay Fecha retiro.
        incluir_indemnizacion: True solo si fue despido sin justa causa.
        motivo_retiro: 'renuncia' | 'despido_sin_justa_causa' | 'mutuo_acuerdo' | 'vencimiento'

    Retorna: dict con cada concepto desglosado y el total.
    """
    nombre = str(fila.get("Nombre", "")).strip()
    salario = float(fila.get("Salario", 0) or 0)
    tipo_contrato = str(fila.get("Tipo contrato", "Indefinido") or "Indefinido")

    fecha_ingreso = _parsear_fecha(fila.get("Fecha ingreso"))
    fecha_retiro_raw = fila.get("Fecha retiro")
    fecha_retiro_parsed = _parsear_fecha(fecha_retiro_raw)
    fecha_corte = fecha_retiro_parsed or fecha_corte_default or datetime.today()

    if fecha_ingreso is None:
        raise ValueError(
            f"'{nombre}': falta la Fecha de ingreso. No se puede calcular la liquidación."
        )
    if fecha_corte < fecha_ingreso:
        raise ValueError(
            f"'{nombre}': la Fecha de retiro ({fecha_corte.date()}) "
            f"es anterior a la Fecha de ingreso ({fecha_ingreso.date()})."
        )

    # ── Días trabajados ────────────────────────────────────────────────────
    dias_total = _dias_360(fecha_ingreso, fecha_corte)
    dias_semestre = _dias_semestre_actual(fecha_ingreso, fecha_corte)

    # ── Bases de cálculo ───────────────────────────────────────────────────
    # Auxilio de transporte: incluye en base prestacional solo si salario ≤ 2 SMMLV
    aplica_auxilio = salario <= TOPE_AUXILIO_TRANSPORTE
    auxilio = AUXILIO_TRANSPORTE_2026 if aplica_auxilio else 0
    base_prestacional = salario + auxilio   # Para cesantías y prima

    # ── Fórmulas CST ──────────────────────────────────────────────────────
    # Cesantías: Art. 249 CST — base prestacional × días totales / 360
    cesantias = round(base_prestacional * dias_total / 360, 2)

    # Intereses cesantías: Ley 52/1975 — 12% anual proporcional
    intereses_cesantias = round(cesantias * 0.12 * dias_total / 360, 2)

    # Prima: Art. 306 CST — por SEMESTRE (no año completo)
    prima = round(base_prestacional * dias_semestre / 360, 2)

    # Vacaciones: Art. 186 CST — solo salario base (sin auxilio), divisor 720
    vacaciones = round(salario * dias_total / 720, 2)

    # Salario pendiente: días del mes en curso no pagados (estimado simple)
    dias_mes_pendiente = min(fecha_corte.day, 30)
    salario_pendiente = round(salario / 30 * dias_mes_pendiente, 2)

    # Indemnización: Art. 64 CST — solo si despido sin justa causa
    indem = 0.0
    if incluir_indemnizacion or str(motivo_retiro).strip().lower() == "despido_sin_justa_causa":
        indem = _indemnizacion(salario, dias_total, tipo_contrato)

    subtotal_prestaciones = round(cesantias + intereses_cesantias + prima + vacaciones, 2)
    total = round(subtotal_prestaciones + salario_pendiente + indem, 2)

    return {
        # Identificación
        "Nombre": nombre,
        "Documento": str(fila.get("Documento", "")).strip(),
        "Cargo": fila.get("Cargo", ""),
        "Tipo contrato": tipo_contrato,
        "Salario base": salario,
        "Fecha ingreso": fecha_ingreso.strftime("%d/%m/%Y"),
        "Fecha corte": fecha_corte.strftime("%d/%m/%Y"),
        # Días
        "Dias totales (base 360)": dias_total,
        "Dias semestre actual (prima)": dias_semestre,
        # Base
        "Auxilio transporte incluido": "Sí" if aplica_auxilio else "No",
        "Base prestacional (salario + auxilio)": base_prestacional if aplica_auxilio else salario,
        # Conceptos
        "Cesantias (Art. 249 CST)": cesantias,
        "Intereses cesantias 12% (Ley 52/75)": intereses_cesantias,
        "Prima semestral (Art. 306 CST)": prima,
        "Vacaciones (Art. 186 CST)": vacaciones,
        "Salario pendiente (estimado)": salario_pendiente,
        "Indemnizacion (Art. 64 CST)": indem,
        # Total
        "Subtotal prestaciones": subtotal_prestaciones,
        "TOTAL LIQUIDACION ESTIMADA": total,
        # Meta
        "Motivo retiro": motivo_retiro,
        "Referencia legal": "CST + Decretos 1469/2025 y 159/2026 — SMMLV $1.750.905",
    }


def calcular_liquidacion_df(
    df: "pd.DataFrame",
    fecha_corte_default=None,
    motivo_retiro: str = "renuncia",
):
    """
    Calcula la liquidación para todas las filas de un DataFrame.
    Retorna (df_resultados, lista_errores).
    """
    resultados = []
    errores = []
    incluir_indem = str(motivo_retiro).strip().lower() == "despido_sin_justa_causa"

    for idx, fila in df.iterrows():
        try:
            resultados.append(
                calcular_liquidacion_fila(
                    fila,
                    fecha_corte_default=fecha_corte_default,
                    incluir_indemnizacion=incluir_indem,
                    motivo_retiro=motivo_retiro,
                )
            )
        except ValueError as e:
            errores.append(f"Fila {idx + 2}: {e}")

    return pd.DataFrame(resultados), errores
