from datetime import date

from utils.validaciones_documentales import Nivel, validar_documento, hay_errores

EMPRESA = {"nombre": "Empresa SAS", "nit": "900123456-7", "representante": "Ana Pérez"}
EMPLEADO = {"Nombre": "Marco Álvarez", "Documento": "123456", "Cargo": "Analista", "Salario": 2_500_000, "Fecha ingreso": "2026-01-10"}


def test_contrato_bloquea_fecha_precargada_no_confirmada():
    hs = validar_documento("contrato_indefinido", EMPLEADO, EMPRESA, {
        "fecha_inicio_contrato": date(2026, 1, 10),
        "fecha_inicio_precargada": True,
        "fecha_inicio_confirmada": False,
        "periodicidad_pago": "Mensual", "forma_pago": "Transferencia",
    })
    assert hay_errores(hs)
    assert any(h.codigo == "INICIO_NO_CONFIRMADO" and h.nivel == Nivel.ERROR for h in hs)


def test_certificado_exige_decidir_salario():
    hs = validar_documento("certificado", EMPLEADO, EMPRESA, {})
    assert any(h.codigo == "SALARIO_NO_DECIDIDO" for h in hs)


def test_retiro_anterior_ingreso_es_error():
    emp = {**EMPLEADO, "Fecha retiro": "2025-12-31"}
    hs = validar_documento("certificado", emp, EMPRESA, {"incluir_salario": False})
    assert any(h.codigo == "FECHA_RETIRO_ANTERIOR" and h.nivel == Nivel.ERROR for h in hs)


def test_dotacion_sin_items_es_error():
    hs = validar_documento("dotacion", EMPLEADO, EMPRESA, {
        "fecha_entrega": date.today(), "tipo_entrega": "uniforme_corporativo", "items": []
    })
    assert any(h.codigo == "DOTACION_SIN_ITEMS" for h in hs)


def test_liquidacion_exige_estado_aportes_cuando_hay_salario_pendiente():
    hs = validar_documento("liquidacion", EMPLEADO, EMPRESA, {
        "fecha_corte": date(2026, 7, 30),
        "motivo_retiro": "renuncia",
        "pagos_previos_confirmados": True,
        "novedades_confirmadas": True,
        "dias_salario_pendiente": 15,
    })
    assert any(h.codigo == "APORTES_PERIODO_FINAL_SIN_CONCILIAR" and h.nivel == Nivel.ERROR for h in hs)


def test_liquidacion_aportes_parciales_exige_valores_retenidos():
    hs = validar_documento("liquidacion", EMPLEADO, EMPRESA, {
        "fecha_corte": date(2026, 7, 30),
        "motivo_retiro": "renuncia",
        "pagos_previos_confirmados": True,
        "novedades_confirmadas": True,
        "dias_salario_pendiente": 15,
        "estado_aportes_periodo_final": "descontados_parcialmente",
        "aporte_salud_ya_descontado": 0,
        "aporte_pension_ya_descontado": 0,
    })
    assert any(h.codigo == "APORTES_PARCIALES_SIN_VALORES" and h.nivel == Nivel.ERROR for h in hs)


def test_liquidacion_sin_salario_define_aportes_no_aplican():
    hs = validar_documento("liquidacion", EMPLEADO, EMPRESA, {
        "fecha_corte": date(2026, 7, 30),
        "motivo_retiro": "renuncia",
        "pagos_previos_confirmados": True,
        "novedades_confirmadas": True,
        "dias_salario_pendiente": 0,
        "estado_aportes_periodo_final": "no_existe_salario_pendiente",
    })
    assert not any(h.nivel == Nivel.ERROR for h in hs)
