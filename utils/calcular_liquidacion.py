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

from datetime import datetime, date, timedelta
import pandas as pd

from utils.parametros_legales import (
    obtener_parametros, SALARIO_MINIMO_2026, AUXILIO_TRANSPORTE_2026,
    TOPE_AUXILIO_TRANSPORTE,
)

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



def _periodos_intereses_cesantias(fecha_ingreso: datetime, fecha_corte: datetime) -> list[dict]:
    """
    Divide el tiempo trabajado en periodos por año calendario usando la misma
    convención 30/360 del motor. La suma de los periodos coincide exactamente
    con ``_dias_360(fecha_ingreso, fecha_corte)`` y evita aplicar la tasa a un
    saldo acumulado de varios años como si fuera un solo periodo.
    """
    if fecha_corte < fecha_ingreso:
        return []

    total = _dias_360(fecha_ingreso, fecha_corte)
    periodos = []
    acumulado_anterior = 0
    for anio in range(fecha_ingreso.year, fecha_corte.year + 1):
        fin_periodo = fecha_corte if anio == fecha_corte.year else datetime(anio, 12, 31)
        acumulado = min(_dias_360(fecha_ingreso, fin_periodo), total)
        dias = max(acumulado - acumulado_anterior, 0)
        if dias:
            inicio = fecha_ingreso if anio == fecha_ingreso.year else datetime(anio, 1, 1)
            periodos.append({
                "anio": anio,
                "inicio": inicio,
                "fin": fin_periodo,
                "dias": dias,
            })
        acumulado_anterior = acumulado
    return periodos


def _calcular_intereses_cesantias_periodizados(
    base_prestacional: float,
    fecha_ingreso: datetime,
    fecha_corte: datetime,
    porcentaje: float = 0.12,
    divisor: int = 360,
) -> tuple[float, list[dict]]:
    """Calcula intereses de cesantías por cada año o fracción anual.

    Para cada periodo: cesantías causadas del periodo × 12 % × días / 360.
    El resultado no incluye sanciones por consignación tardía ni intereses de
    mora; esas excepciones requieren un cálculo separado y revisión jurídica.
    """
    detalle = []
    total_intereses = 0.0
    for periodo in _periodos_intereses_cesantias(fecha_ingreso, fecha_corte):
        dias = periodo["dias"]
        cesantias_periodo = round(base_prestacional * dias / divisor, 2)
        intereses_periodo = round(cesantias_periodo * porcentaje * dias / divisor, 2)
        total_intereses += intereses_periodo
        detalle.append({
            **periodo,
            "cesantias_periodo": cesantias_periodo,
            "intereses_periodo": intereses_periodo,
        })
    return round(total_intereses, 2), detalle

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
    fecha_corte = fecha_retiro_parsed or fecha_corte_default
    if fecha_corte is None:
        raise ValueError(
            f"'{nombre}': falta la Fecha de retiro o una fecha de corte confirmada. "
            "No se asigna la fecha actual de forma implícita."
        )
    fecha_corte = _parsear_fecha(fecha_corte)

    if fecha_ingreso is None:
        raise ValueError(
            f"'{nombre}': falta la Fecha de ingreso. No se puede calcular la liquidación."
        )
    if fecha_corte < fecha_ingreso:
        raise ValueError(
            f"'{nombre}': la Fecha de retiro ({fecha_corte.date()}) "
            f"es anterior a la Fecha de ingreso ({fecha_ingreso.date()})."
        )

    parametros = obtener_parametros(fecha_corte.year)

    # ── Días trabajados ────────────────────────────────────────────────────
    dias_total = _dias_360(fecha_ingreso, fecha_corte)
    dias_semestre = _dias_semestre_actual(fecha_ingreso, fecha_corte)

    # ── Bases de cálculo ───────────────────────────────────────────────────
    # Auxilio de transporte: incluye en base prestacional solo si salario ≤ 2 SMMLV
    aplica_auxilio = salario <= parametros.tope_auxilio_transporte
    auxilio = parametros.auxilio_transporte if aplica_auxilio else 0
    base_prestacional = salario + auxilio   # Para cesantías y prima

    # ── Fórmulas CST ──────────────────────────────────────────────────────
    # Cesantías: Art. 249 CST — base prestacional × días totales / 360
    cesantias = round(base_prestacional * dias_total / parametros.divisor_prestaciones, 2)

    # Intereses de cesantías: se periodizan por año calendario. Aplicar la
    # tasa a las cesantías acumuladas de varios años y volver a multiplicar por
    # todos los días sobrestima el resultado.
    intereses_cesantias_brutos, detalle_intereses = _calcular_intereses_cesantias_periodizados(
        base_prestacional, fecha_ingreso, fecha_corte,
        porcentaje=parametros.porcentaje_intereses_cesantias,
        divisor=parametros.divisor_prestaciones,
    )

    # Prima: Art. 306 CST — por SEMESTRE (no año completo)
    prima = round(base_prestacional * dias_semestre / parametros.divisor_prestaciones, 2)

    # Vacaciones: Art. 186 CST — solo salario base (sin auxilio), divisor 720
    vacaciones = round(salario * dias_total / parametros.divisor_vacaciones, 2)

    # Salario pendiente: solo se incluye cuando el usuario registra los días.
    # Antes se asumía todo el mes transcurrido, lo que podía duplicar nómina ya pagada.
    dias_mes_pendiente = int(fila.get("Dias salario pendiente", 0) or 0)
    if dias_mes_pendiente < 0 or dias_mes_pendiente > 30:
        raise ValueError(f"'{nombre}': los días de salario pendiente deben estar entre 0 y 30.")
    salario_pendiente = round(salario / 30 * dias_mes_pendiente, 2)

    # Conciliación de aportes del periodo final. Los aportes se calculan
    # únicamente sobre el salario pendiente y nunca sobre prestaciones,
    # vacaciones o indemnizaciones.
    estado_aportes_raw = str(fila.get("Estado aportes periodo final", "") or "").strip().lower()
    aliases_aportes = {
        "si": "descontados_completamente",
        "sí": "descontados_completamente",
        "completo": "descontados_completamente",
        "completamente": "descontados_completamente",
        "parcial": "descontados_parcialmente",
        "parcialmente": "descontados_parcialmente",
        "no": "no_descontados",
        "ninguno": "no_descontados",
        "no_salary": "no_existe_salario_pendiente",
        "sin_salario_pendiente": "no_existe_salario_pendiente",
        "manual": "revision_manual",
    }
    estado_aportes = aliases_aportes.get(estado_aportes_raw, estado_aportes_raw)
    if dias_mes_pendiente <= 0:
        estado_aportes = "no_existe_salario_pendiente"
    elif estado_aportes not in {
        "descontados_completamente", "descontados_parcialmente",
        "no_descontados", "revision_manual"
    }:
        raise ValueError(
            f"'{nombre}': indique si los aportes del periodo final fueron descontados completamente, "
            "parcialmente, no fueron descontados o requieren revisión manual."
        )

    tarifa_salud = float(fila.get("Tarifa salud trabajador", 0.04) or 0.04)
    tarifa_pension = float(fila.get("Tarifa pension trabajador", 0.04) or 0.04)
    salud_causada = round(salario_pendiente * tarifa_salud, 2)
    pension_causada = round(salario_pendiente * tarifa_pension, 2)
    salud_descontada = float(fila.get("Aporte salud ya descontado", 0) or 0)
    pension_descontada = float(fila.get("Aporte pension ya descontado", 0) or 0)
    if min(salud_descontada, pension_descontada) < 0:
        raise ValueError(f"'{nombre}': los aportes ya descontados no pueden ser negativos.")
    if estado_aportes == "descontados_parcialmente" and (
        salud_descontada > salud_causada or pension_descontada > pension_causada
    ):
        raise ValueError(
            f"'{nombre}': un aporte ya descontado no puede superar el aporte causado "
            "sobre el salario pendiente."
        )
    if estado_aportes == "descontados_completamente":
        salud_descontada = max(salud_descontada, salud_causada)
        pension_descontada = max(pension_descontada, pension_causada)
        salud_pendiente = pension_pendiente = 0.0
    elif estado_aportes == "descontados_parcialmente":
        salud_pendiente = round(max(salud_causada - salud_descontada, 0), 2)
        pension_pendiente = round(max(pension_causada - pension_descontada, 0), 2)
    elif estado_aportes == "no_descontados":
        salud_descontada = pension_descontada = 0.0
        salud_pendiente = salud_causada
        pension_pendiente = pension_causada
    else:  # revisión manual: no se aplica una deducción automática
        salud_pendiente = pension_pendiente = 0.0

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

    # Pagos previos y deducciones se registran explícitamente; nunca se descuenta
    # salud/pensión sobre el total de prestaciones o indemnizaciones.
    prima_pagada = float(fila.get("Prima pagada", 0) or 0)
    cesantias_consignadas = float(fila.get("Cesantias consignadas", 0) or 0)
    vacaciones_pagadas = float(fila.get("Vacaciones pagadas", 0) or 0)
    intereses_cesantias_pagados = float(fila.get("Intereses cesantias pagados", 0) or 0)
    deducciones_autorizadas = float(fila.get("Deducciones autorizadas", 0) or 0)
    for etiqueta, valor in (
        ("Prima pagada", prima_pagada),
        ("Cesantías consignadas", cesantias_consignadas),
        ("Vacaciones pagadas", vacaciones_pagadas),
        ("Intereses de cesantías pagados", intereses_cesantias_pagados),
        ("Deducciones autorizadas", deducciones_autorizadas),
    ):
        if valor < 0:
            raise ValueError(f"'{nombre}': {etiqueta} no puede ser negativo.")

    cesantias_pendientes = max(cesantias - cesantias_consignadas, 0)
    intereses_cesantias = round(max(intereses_cesantias_brutos - intereses_cesantias_pagados, 0), 2)
    prima_pendiente = max(prima - prima_pagada, 0)
    vacaciones_pendientes = max(vacaciones - vacaciones_pagadas, 0)
    subtotal_prestaciones = round(cesantias_pendientes + intereses_cesantias + prima_pendiente + vacaciones_pendientes, 2)
    total_devengado = round(subtotal_prestaciones + salario_pendiente + indem, 2)
    deducciones_ley = []
    if salud_pendiente > 0:
        deducciones_ley.append({
            "concepto": "Salud trabajador", "base": salario_pendiente,
            "tarifa": tarifa_salud, "valor": salud_pendiente,
        })
    if pension_pendiente > 0:
        deducciones_ley.append({
            "concepto": "Pensión trabajador", "base": salario_pendiente,
            "tarifa": tarifa_pension, "valor": pension_pendiente,
        })
    total_deducciones_ley = round(sum(x["valor"] for x in deducciones_ley), 2)
    detalle_autorizadas = fila.get("Deducciones autorizadas detalle", []) or []
    if deducciones_autorizadas > 0 and not detalle_autorizadas:
        detalle_autorizadas = [{
            "concepto": "Descuentos autorizados registrados",
            "base": deducciones_autorizadas, "tarifa": "", "valor": deducciones_autorizadas,
        }]
    total = round(total_devengado - total_deducciones_ley - deducciones_autorizadas, 2)

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
        "Auxilio transporte valor": auxilio,
        "Base prestacional (salario + auxilio)": base_prestacional if aplica_auxilio else salario,
        "Base vacaciones": salario,
        # Conceptos
        "Cesantias (Art. 249 CST)": cesantias,
        "Intereses cesantias causados": intereses_cesantias_brutos,
        "Intereses cesantias pagados": intereses_cesantias_pagados,
        "Intereses cesantias 12% (Ley 52/75)": intereses_cesantias,
        "Dias intereses cesantias": sum(x["dias"] for x in detalle_intereses),
        "Detalle periodos intereses": [
            {
                "anio": x["anio"],
                "inicio": x["inicio"].strftime("%d/%m/%Y"),
                "fin": x["fin"].strftime("%d/%m/%Y"),
                "dias": x["dias"],
                "cesantias": x["cesantias_periodo"],
                "intereses": x["intereses_periodo"],
            }
            for x in detalle_intereses
        ],
        "Prima semestral (Art. 306 CST)": prima,
        "Vacaciones (Art. 186 CST)": vacaciones,
        "Dias salario pendiente": dias_mes_pendiente,
        "Salario pendiente (estimado)": salario_pendiente,
        "Periodo salario inicio": (fecha_corte - timedelta(days=dias_mes_pendiente - 1)).strftime("%d/%m/%Y") if dias_mes_pendiente else "",
        "Periodo salario fin": fecha_corte.strftime("%d/%m/%Y") if dias_mes_pendiente else "",
        "Estado aportes periodo final": estado_aportes,
        "Base sujeta a aporte": salario_pendiente,
        "Salud causada": salud_causada,
        "Salud ya descontada": salud_descontada,
        "Salud pendiente": salud_pendiente,
        "Pension causada": pension_causada,
        "Pension ya descontada": pension_descontada,
        "Pension pendiente": pension_pendiente,
        "Deducciones de ley": deducciones_ley,
        "Prima pagada": prima_pagada,
        "Cesantias consignadas": cesantias_consignadas,
        "Vacaciones pagadas": vacaciones_pagadas,
        "Indemnizacion (Art. 64 CST)": indem,
        "Indemnizacion dias": indem_dias,
        "Indemnizacion articulo": indem_articulo,
        "Indemnizacion detalle": indem_detalle,
        # Total
        "Subtotal prestaciones": subtotal_prestaciones,
        "TOTAL DEVENGADO": total_devengado,
        "TOTAL DEDUCCIONES DE LEY": total_deducciones_ley,
        "TOTAL DEDUCCIONES AUTORIZADAS": deducciones_autorizadas,
        "Deducciones autorizadas detalle": detalle_autorizadas,
        "NETO A PAGAR": total,
        "TOTAL LIQUIDACION ESTIMADA": total,
        # Meta
        "Motivo retiro": motivo_lower,  # ya normalizado (minúsculas, sin espacios)
        "Genera indemnizacion": genera_indem,
        "Version reglas": parametros.version,
        "Metodo dias": "Año comercial 360; vacaciones divisor 720",
        "Referencia legal": f"CST + {parametros.fuente_salario} + {parametros.fuente_auxilio}",
        "Advertencias": [
            "Los aportes del periodo final se conciliaron únicamente sobre el salario pendiente.",
            "Los intereses de cesantías se periodizaron por año; no incluyen sanciones ni mora.",
        ] + (["Los aportes del periodo final requieren revisión manual."] if estado_aportes == "revision_manual" else []),
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
