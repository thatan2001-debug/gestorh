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


def _indemnizacion(salario: float, dias_totales: int, tipo_contrato: str,
                    motivo_retiro: str = "despido_sin_justa_causa",
                    dias_pendientes_fijo: int = 0) -> dict:
    """
    Cálculo completo de indemnización según CST colombiano.

    Retorna dict con: {monto, dias, base_calculo, articulo, detalle}

    Casos que generan indemnización:
    ─────────────────────────────────────────────────────────────
    • despido_sin_justa_causa      → Art. 64 CST (según tipo contrato)
    • despido_por_incapacidad      → Art. 62 CST + Ley 361/1997
    • terminacion_unilateral_empleador → mismo que sin justa causa
    • fuero_maternidad             → Ley 1468/2011 (60 días + indem.)
    • terminacion_periodo_prueba   → sin indemnización (Art. 78 CST)
    • quiebra_empresa              → Art. 466 Código de Comercio

    Casos SIN indemnización (retornan 0):
    ─────────────────────────────────────────────────────────────
    • renuncia_voluntaria          → Art. 47 CST
    • con_justa_causa              → Art. 62 CST literal A
    • mutuo_acuerdo                → Art. 61.b CST (salvo pacto)
    • vencimiento_contrato         → Art. 46 CST (con preaviso 30 días)
    • jubilacion                   → Art. 62.14 CST
    """
    motivo = str(motivo_retiro).strip().lower()
    tipo_lower = str(tipo_contrato).strip().lower()

    # Casos SIN indemnización
    sin_indem = {
        "renuncia", "renuncia_voluntaria", "con_justa_causa",
        "mutuo_acuerdo", "vencimiento_contrato", "vencimiento",
        "jubilacion", "periodo_prueba", "terminacion_periodo_prueba",
        "obra_terminada",  # obra terminada correctamente = no indemnización
    }
    if motivo in sin_indem:
        return {
            "monto": 0.0, "dias": 0,
            "base_calculo": salario,
            "articulo": "N/A",
            "detalle": "Sin indemnización según causal de terminación",
        }

    salario_diario = salario / 30

    # ── CONTRATO A TÉRMINO FIJO ─────────────────────────────────────
    # Art. 64 CST: días pendientes hasta terminación pactada
    if tipo_lower in TIPOS_CONTRATO_FIJO or "fijo" in tipo_lower:
        # Si no hay fecha fin, mínimo 15 días (Ley 789/2002)
        dias_indem = max(dias_pendientes_fijo, 15)
        return {
            "monto": round(salario_diario * dias_indem, 2),
            "dias": dias_indem,
            "base_calculo": salario,
            "articulo": "Art. 64 CST · Ley 789/2002",
            "detalle": f"Días pendientes hasta terminación pactada: {dias_indem} días",
        }

    # ── CONTRATO POR OBRA O LABOR ───────────────────────────────────
    if "obra" in tipo_lower or "labor" in tipo_lower:
        # Días pendientes de la obra o labor (mínimo 15)
        dias_indem = max(dias_pendientes_fijo, 15)
        return {
            "monto": round(salario_diario * dias_indem, 2),
            "dias": dias_indem,
            "base_calculo": salario,
            "articulo": "Art. 64 CST · Contrato por obra",
            "detalle": f"Días para terminar la obra o labor: {dias_indem} días",
        }

    # ── CONTRATO INDEFINIDO ─────────────────────────────────────────
    # Ley 789/2002 modificó Art. 64 CST
    # Distingue entre salarios < 10 SMMLV y >= 10 SMMLV
    umbral_10smmlv = 10 * SALARIO_MINIMO_2026

    años = dias_totales / 360
    años_completos = int(años)
    fraccion = años - años_completos

    if salario < umbral_10smmlv:
        # Salario < 10 SMMLV: 30 días primer año + 20 días por cada año adicional (proporcional)
        if años < 1:
            dias_indem = 30
            detalle = "Primer año (< 10 SMMLV): 30 días"
        else:
            # Años posteriores al primero (con fracción proporcional)
            años_adicionales = años - 1
            dias_adicionales = 20 * años_adicionales
            dias_indem = 30 + dias_adicionales
            detalle = (f"30 días (primer año) + {dias_adicionales:.1f} días "
                       f"({años_adicionales:.2f} años adicionales × 20 días)")
    else:
        # Salario >= 10 SMMLV: 20 días primer año + 15 días por año adicional (proporcional)
        if años < 1:
            dias_indem = 20
            detalle = "Primer año (>= 10 SMMLV): 20 días"
        else:
            años_adicionales = años - 1
            dias_adicionales = 15 * años_adicionales
            dias_indem = 20 + dias_adicionales
            detalle = (f"20 días (primer año) + {dias_adicionales:.1f} días "
                       f"({años_adicionales:.2f} años adicionales × 15 días)")

    return {
        "monto": round(salario_diario * dias_indem, 2),
        "dias": round(dias_indem, 1),
        "base_calculo": salario,
        "articulo": "Art. 64 CST · Ley 789/2002",
        "detalle": detalle,
    }


def calcular_liquidacion_fila(
    fila,
    fecha_corte_default=None,
    incluir_indemnizacion: bool = False,
    motivo_retiro: str = "renuncia",
    dias_pendientes_fijo: int = 0,
):
    """
    Calcula la liquidación completa de un empleado.

    Parámetros:
        fila: dict o pd.Series con los campos del Excel.
        fecha_corte_default: fecha de corte si no hay Fecha retiro.
        incluir_indemnizacion: True solo si fue despido sin justa causa.
        motivo_retiro: motivo específico de terminación (renuncia, despido_sin_justa_causa,
                       con_justa_causa, mutuo_acuerdo, vencimiento_contrato, obra_terminada,
                       periodo_prueba, jubilacion)
        dias_pendientes_fijo: días que faltaban para terminar el contrato fijo o la obra
                              (solo aplica si es despido sin justa causa en contrato fijo/obra)

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

    # Indemnización: Art. 64 CST — según motivo de retiro
    # Casos que la generan: despido sin justa causa, terminación unilateral, etc.
    MOTIVOS_CON_INDEMNIZACION = {
        "despido_sin_justa_causa",
        "sin_justa_causa",
        "terminacion_unilateral_empleador",
        "despido_por_incapacidad",
    }
    motivo_lower = str(motivo_retiro).strip().lower()
    genera_indem = incluir_indemnizacion or motivo_lower in MOTIVOS_CON_INDEMNIZACION

    if genera_indem:
        info_indem = _indemnizacion(salario, dias_total, tipo_contrato,
                                     motivo_retiro=motivo_lower,
                                     dias_pendientes_fijo=dias_pendientes_fijo)
        indem = info_indem["monto"]
        indem_dias = info_indem["dias"]
        indem_articulo = info_indem["articulo"]
        indem_detalle = info_indem["detalle"]
    else:
        indem = 0.0
        indem_dias = 0
        indem_articulo = "N/A"
        indem_detalle = "Sin indemnización según causal"

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
        "Indemnizacion dias": indem_dias,
        "Indemnizacion articulo": indem_articulo,
        "Indemnizacion detalle": indem_detalle,
        # Total
        "Subtotal prestaciones": subtotal_prestaciones,
        "TOTAL LIQUIDACION ESTIMADA": total,
        # Meta
        "Motivo retiro": motivo_lower,  # ya normalizado (minúsculas, sin espacios)
        "Genera indemnizacion": genera_indem,
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
