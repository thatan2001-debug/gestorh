"""Validaciones previas a la generación de documentos laborales.

Diferencia errores que bloquean, advertencias que requieren confirmación e
información explicativa. No sustituye revisión jurídica de la empresa.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from enum import Enum
from typing import Iterable


class Nivel(str, Enum):
    ERROR = "ERROR"
    ADVERTENCIA = "ADVERTENCIA"
    INFORMACION = "INFORMACION"


@dataclass(frozen=True)
class Hallazgo:
    nivel: Nivel
    codigo: str
    mensaje: str
    campo: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["nivel"] = self.nivel.value
        return data


def _valor(datos: dict, *claves, default=""):
    for clave in claves:
        if clave in datos and datos.get(clave) not in (None, ""):
            return datos.get(clave)
    return default


def _fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _sumar_meses(fecha: date, meses: int) -> date:
    import calendar
    mes_base = fecha.month - 1 + meses
    anio = fecha.year + mes_base // 12
    mes = mes_base % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def validar_documento(tipo: str, empleado: dict, empresa: dict,
                       config: dict | None = None, contexto: dict | None = None) -> list[Hallazgo]:
    config = config or {}
    contexto = contexto or {}
    hallazgos: list[Hallazgo] = []

    nombre = _valor(empleado, "Nombre", "nombre")
    documento = _valor(empleado, "Documento", "documento")
    cargo = _valor(empleado, "Cargo", "cargo")
    salario = _valor(empleado, "Salario", "salario", default=0)
    ingreso = _fecha(_valor(empleado, "Fecha ingreso", "fecha_ingreso"))
    retiro = _fecha(_valor(empleado, "Fecha retiro", "fecha_retiro"))

    for campo, valor, etiqueta in (
        ("trabajador.nombre", nombre, "nombre del trabajador"),
        ("trabajador.documento", documento, "identificación del trabajador"),
        ("empresa.nombre", _valor(empresa, "nombre", "razon_social"), "razón social"),
        ("empresa.nit", _valor(empresa, "nit"), "NIT de la empresa"),
    ):
        if not str(valor or "").strip():
            hallazgos.append(Hallazgo(Nivel.ERROR, "CAMPO_OBLIGATORIO", f"Falta {etiqueta}.", campo))

    if documento and not str(documento).replace(".", "").replace("-", "").isalnum():
        hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "IDENTIFICACION_FORMATO",
            "La identificación contiene caracteres inusuales; verifique el dato.", "trabajador.documento"))

    if retiro and ingreso and retiro < ingreso:
        hallazgos.append(Hallazgo(Nivel.ERROR, "FECHA_RETIRO_ANTERIOR",
            "La fecha de retiro no puede ser anterior a la fecha de ingreso.", "trabajador.fecha_retiro"))

    if tipo.startswith("contrato"):
        inicio = _fecha(config.get("fecha_inicio_contrato"))
        if not inicio:
            hallazgos.append(Hallazgo(Nivel.ERROR, "INICIO_CONTRATO_FALTANTE",
                "La fecha real de inicio contractual es obligatoria.", "contrato.fecha_inicio"))
        if inicio and ingreso and inicio != ingreso:
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "INICIO_DIFIERE_INGRESO",
                "La fecha de inicio contractual difiere de la fecha de ingreso registrada.", "contrato.fecha_inicio"))
        if inicio and inicio < date.today():
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "CONTRATO_RETROACTIVO",
                "El contrato se generará con una fecha de inicio anterior a la fecha actual.", "contrato.fecha_inicio"))
        if config.get("fecha_inicio_precargada") and not config.get("fecha_inicio_confirmada"):
            hallazgos.append(Hallazgo(Nivel.ERROR, "INICIO_NO_CONFIRMADO",
                "Confirme explícitamente que la fecha propuesta corresponde al inicio real.", "contrato.fecha_inicio"))
        firma = _fecha(config.get("fecha_celebracion")) or date.today()
        if inicio and config.get("periodo_prueba") and firma > _sumar_meses(inicio, 2):
            hallazgos.append(Hallazgo(
                Nivel.ERROR, "PERIODO_PRUEBA_RETROACTIVO",
                "La relación laboral inició hace más de dos meses. No se recomienda pactar retroactivamente un periodo de prueba; retírelo o envíe el caso a revisión.",
                "contrato.periodo_prueba",
            ))
        if not cargo:
            hallazgos.append(Hallazgo(Nivel.ERROR, "CARGO_FALTANTE", "El cargo es obligatorio para el contrato.", "trabajador.cargo"))
        if float(salario or 0) <= 0:
            hallazgos.append(Hallazgo(Nivel.ERROR, "SALARIO_INVALIDO", "El salario debe ser mayor que cero.", "trabajador.salario"))
        if not config.get("periodicidad_pago") or not config.get("forma_pago"):
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "PAGO_INCOMPLETO",
                "Defina periodicidad, forma y día habitual de pago.", "contrato.forma_pago"))

    elif tipo == "certificado":
        if not ingreso:
            hallazgos.append(Hallazgo(Nivel.ERROR, "INGRESO_FALTANTE",
                "La fecha de ingreso es obligatoria para certificar la vinculación.", "trabajador.fecha_ingreso"))
        if retiro and retiro <= date.today() and config.get("estado_redaccion", "auto") == "activo":
            hallazgos.append(Hallazgo(Nivel.ERROR, "REDACCION_ACTIVO_INCONSISTENTE",
                "No puede afirmarse vinculación actual cuando existe una fecha de retiro efectiva.", "certificado.estado"))
        if config.get("incluir_salario") is None:
            hallazgos.append(Hallazgo(Nivel.ERROR, "SALARIO_NO_DECIDIDO",
                "Indique explícitamente si el certificado debe incluir salario.", "certificado.incluir_salario"))
        if contexto.get("liquidacion_mismo_dia"):
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "CERTIFICADO_Y_LIQUIDACION_MISMO_DIA",
                "Existe una liquidación generada el mismo día; confirme el estado laboral y la redacción.", "certificado.estado"))

    elif tipo == "dotacion":
        items = config.get("items") or []
        if not items:
            hallazgos.append(Hallazgo(Nivel.ERROR, "DOTACION_SIN_ITEMS",
                "Registre al menos un elemento entregado.", "dotacion.items"))
        if not _fecha(config.get("fecha_entrega")):
            hallazgos.append(Hallazgo(Nivel.ERROR, "FECHA_ENTREGA_FALTANTE",
                "La fecha efectiva de entrega es obligatoria.", "dotacion.fecha_entrega"))
        tipo_entrega = config.get("tipo_entrega", "").strip().lower()
        if not tipo_entrega:
            hallazgos.append(Hallazgo(Nivel.ERROR, "TIPO_ENTREGA_FALTANTE",
                "Clasifique la entrega: dotación legal, uniforme, herramienta, EPP u otra.", "dotacion.tipo_entrega"))
        if tipo_entrega == "dotacion_legal" and not config.get("cumple_requisitos_dotacion"):
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "DOTACION_LEGAL_NO_CONFIRMADA",
                "No se confirmó el cumplimiento de los requisitos parametrizados para dotación legal.", "dotacion.tipo_entrega"))
        for idx, item in enumerate(items, 1):
            if not str(item.get("descripcion") or "").strip():
                hallazgos.append(Hallazgo(Nivel.ERROR, "DOTACION_DESCRIPCION_FALTANTE",
                    f"Falta la descripción del elemento {idx}.", f"dotacion.items.{idx}.descripcion"))
            if item.get("cantidad") in (None, "") or float(item.get("cantidad") or 0) <= 0:
                hallazgos.append(Hallazgo(Nivel.ERROR, "DOTACION_CANTIDAD_INVALIDA",
                    f"La cantidad del elemento {idx} debe ser mayor que cero.", f"dotacion.items.{idx}.cantidad"))
            if not str(item.get("estado") or "").strip():
                hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "DOTACION_ESTADO_FALTANTE",
                    f"Confirme el estado del elemento {idx}.", f"dotacion.items.{idx}.estado"))

    elif tipo == "liquidacion":
        corte = _fecha(_valor(config, "fecha_corte", default=_valor(empleado, "Fecha retiro", "fecha_retiro")))
        if not ingreso:
            hallazgos.append(Hallazgo(Nivel.ERROR, "INGRESO_FALTANTE",
                "La fecha de ingreso es obligatoria para liquidar.", "trabajador.fecha_ingreso"))
        if not corte:
            hallazgos.append(Hallazgo(Nivel.ERROR, "CORTE_FALTANTE",
                "La fecha efectiva de terminación o corte debe indicarse explícitamente.", "liquidacion.fecha_corte"))
        if ingreso and corte and corte < ingreso:
            hallazgos.append(Hallazgo(Nivel.ERROR, "CORTE_ANTERIOR_INGRESO",
                "La fecha de corte no puede ser anterior a la fecha de ingreso.", "liquidacion.fecha_corte"))
        if not config.get("motivo_retiro"):
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "CAUSA_TERMINACION_FALTANTE",
                "Registre o confirme la causa de terminación.", "liquidacion.motivo_retiro"))
        if config.get("pagos_previos_confirmados") is not True:
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "PAGOS_PREVIOS_NO_CONFIRMADOS",
                "Confirme prima pagada, cesantías consignadas, vacaciones y otros pagos previos.", "liquidacion.pagos_previos"))
        if not config.get("novedades_confirmadas"):
            hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "NOVEDADES_NO_CONFIRMADAS",
                "Confirme si existen licencias, suspensiones, incapacidades, comisiones o cambios salariales.", "liquidacion.novedades"))
        dias_salario = int(config.get("dias_salario_pendiente", 0) or 0)
        estado_aportes = str(config.get("estado_aportes_periodo_final") or "").strip().lower()
        if dias_salario > 0 and not estado_aportes:
            hallazgos.append(Hallazgo(Nivel.ERROR, "APORTES_PERIODO_FINAL_SIN_CONCILIAR",
                "Indique si los aportes del periodo final ya fueron descontados en nómina.", "liquidacion.aportes_periodo_final"))
        if dias_salario <= 0 and estado_aportes and estado_aportes not in {"no_existe_salario_pendiente", "no_salary", "sin_salario_pendiente"}:
            hallazgos.append(Hallazgo(Nivel.INFORMACION, "APORTES_NO_APLICAN",
                "No existe salario pendiente; no se calculan aportes del periodo final.", "liquidacion.aportes_periodo_final"))

    if not _valor(empresa, "representante", "firmante_cert_nombre"):
        hallazgos.append(Hallazgo(Nivel.ADVERTENCIA, "FIRMANTE_FALTANTE",
            "No existe firmante configurado; el documento quedará pendiente de firma.", "empresa.firmante"))

    return hallazgos


def separar_hallazgos(hallazgos: Iterable[Hallazgo]) -> dict[str, list[Hallazgo]]:
    salida = {n.value: [] for n in Nivel}
    for hallazgo in hallazgos:
        salida[hallazgo.nivel.value].append(hallazgo)
    return salida


def hay_errores(hallazgos: Iterable[Hallazgo]) -> bool:
    return any(h.nivel == Nivel.ERROR for h in hallazgos)
