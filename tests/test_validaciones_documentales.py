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
