"""
Tests de validaciones de empleado (services/validaciones_empleado.py).

Ejecutar:
    python tests/test_validaciones_empleado.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE DOCUMENTO
# ══════════════════════════════════════════════════════════════════════════════

def test_cc_valida():
    from services.validaciones_empleado import validar_documento
    ok, _ = validar_documento("1234567890", "CC")
    assert ok, "CC de 10 dígitos debe pasar"


def test_cc_con_puntos():
    from services.validaciones_empleado import validar_documento
    ok, _ = validar_documento("1.234.567.890", "CC")
    assert ok, "CC con puntos debe pasar (se limpian)"


def test_cc_vacia_falla():
    from services.validaciones_empleado import validar_documento
    ok, msg = validar_documento("", "CC")
    assert not ok


def test_cc_con_letras_falla():
    from services.validaciones_empleado import validar_documento
    ok, msg = validar_documento("ABC123", "CC")
    assert not ok, "CC con letras debe fallar"


def test_pasaporte_alfanumerico():
    from services.validaciones_empleado import validar_documento
    ok, _ = validar_documento("AB1234567", "PP")
    assert ok, "Pasaporte alfanumérico debe pasar"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE CORREO
# ══════════════════════════════════════════════════════════════════════════════

def test_correo_valido():
    from services.validaciones_empleado import validar_correo
    ok, _ = validar_correo("juan@empresa.com")
    assert ok


def test_correo_invalido():
    from services.validaciones_empleado import validar_correo
    ok, _ = validar_correo("no_es_correo")
    assert not ok


def test_correo_vacio_no_obligatorio():
    from services.validaciones_empleado import validar_correo
    ok, _ = validar_correo("", obligatorio=False)
    assert ok, "Correo vacío no obligatorio debe pasar"


def test_correo_vacio_obligatorio():
    from services.validaciones_empleado import validar_correo
    ok, _ = validar_correo("", obligatorio=True)
    assert not ok


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE SALARIO
# ══════════════════════════════════════════════════════════════════════════════

def test_salario_valido():
    from services.validaciones_empleado import validar_salario
    ok, _ = validar_salario(2_500_000)
    assert ok


def test_salario_string_valido():
    from services.validaciones_empleado import validar_salario
    ok, _ = validar_salario("2500000")
    assert ok


def test_salario_cero_falla():
    from services.validaciones_empleado import validar_salario
    ok, _ = validar_salario(0)
    assert not ok, "Salario 0 debe fallar"


def test_salario_negativo_falla():
    from services.validaciones_empleado import validar_salario
    ok, _ = validar_salario(-1000)
    assert not ok


def test_salario_no_numerico_falla():
    from services.validaciones_empleado import validar_salario
    ok, _ = validar_salario("abc")
    assert not ok


def test_salario_bajo_smmlv_da_warning():
    """Salario por debajo del SMMLV genera warning pero es válido."""
    from services.validaciones_empleado import validar_salario
    ok, msg = validar_salario(500_000)  # muy por debajo del SMMLV 2026
    assert ok, "El salario menor al SMMLV pasa pero con warning"
    assert "⚠️" in msg or "SMMLV" in msg


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE FECHAS
# ══════════════════════════════════════════════════════════════════════════════

def test_fecha_formato_dmy():
    from services.validaciones_empleado import validar_fecha
    ok, _ = validar_fecha("15/07/2024", "ingreso")
    assert ok


def test_fecha_formato_ymd():
    from services.validaciones_empleado import validar_fecha
    ok, _ = validar_fecha("2024-07-15", "ingreso")
    assert ok


def test_fecha_invalida():
    from services.validaciones_empleado import validar_fecha
    ok, _ = validar_fecha("no es fecha", "ingreso")
    assert not ok


def test_fecha_retiro_antes_ingreso():
    from services.validaciones_empleado import validar_fechas_coherentes
    ok, msg = validar_fechas_coherentes("15/07/2024", "01/01/2024")
    assert not ok
    assert "anterior" in msg.lower()


def test_fecha_retiro_despues_ingreso():
    from services.validaciones_empleado import validar_fechas_coherentes
    ok, _ = validar_fechas_coherentes("15/07/2024", "20/12/2024")
    assert ok


def test_sin_fecha_retiro_ok():
    from services.validaciones_empleado import validar_fechas_coherentes
    ok, _ = validar_fechas_coherentes("15/07/2024", "")
    assert ok, "Sin fecha retiro está bien (empleado activo)"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE VALIDACIÓN INTEGRAL
# ══════════════════════════════════════════════════════════════════════════════

def test_empleado_completo_valido():
    from services.validaciones_empleado import validar_empleado
    datos = {
        "tipo_documento": "CC",
        "documento": "1234567890",
        "nombre": "Juan Pérez",
        "correo": "juan@empresa.com",
        "telefono": "3001234567",
        "salario": 2_500_000,
        "cargo": "Analista",
        "fecha_ingreso": "15/07/2024",
        "tipo_contrato": "Indefinido",
    }
    ok, errores = validar_empleado(datos)
    assert ok, f"Empleado válido falló: {errores}"


def test_empleado_sin_documento_falla():
    from services.validaciones_empleado import validar_empleado
    datos = {
        "nombre": "Juan Pérez",
        "salario": 2_000_000,
        "cargo": "Analista",
        "fecha_ingreso": "15/07/2024",
    }
    ok, errores = validar_empleado(datos)
    assert not ok
    assert "documento" in errores


def test_empleado_con_fechas_incoherentes_falla():
    from services.validaciones_empleado import validar_empleado
    datos = {
        "tipo_documento": "CC",
        "documento": "1234567890",
        "nombre": "Juan Pérez",
        "cargo": "Analista",
        "salario": 2_000_000,
        "fecha_ingreso": "15/07/2024",
        "fecha_retiro": "01/01/2024",  # antes que ingreso
        "tipo_contrato": "Indefinido",
    }
    ok, errores = validar_empleado(datos)
    assert not ok
    assert "fecha_retiro" in errores


def test_empleado_con_emergencia_incompleta_falla():
    from services.validaciones_empleado import validar_empleado
    datos = {
        "tipo_documento": "CC",
        "documento": "1234567890",
        "nombre": "Juan Pérez",
        "cargo": "Analista",
        "salario": 2_000_000,
        "fecha_ingreso": "15/07/2024",
        "tipo_contrato": "Indefinido",
        "emergencia_nombre": "María",  # nombre sin teléfono
    }
    ok, errores = validar_empleado(datos)
    assert not ok
    assert "emergencia_telefono" in errores


# ══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _run_all():
    tests = [(name, fn) for name, fn in globals().items()
              if name.startswith("test_") and callable(fn)]
    pasados = 0
    fallados = []
    for name, fn in tests:
        try:
            fn()
            pasados += 1
            print(f"  ✅ {name}")
        except AssertionError as e:
            fallados.append((name, str(e)))
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            fallados.append((name, f"Excepción: {e}"))
            print(f"  💥 {name}: {type(e).__name__}: {e}")

    print()
    print(f"{'=' * 60}")
    print(f"RESULTADO: {pasados}/{len(tests)} tests pasaron")
    if fallados:
        print("❌ FALLARON:")
        for n, m in fallados:
            print(f"  • {n}: {m}")
    else:
        print("🎉 Todos los tests de validaciones pasaron")
    print(f"{'=' * 60}")
    return len(fallados) == 0


if __name__ == "__main__":
    exito = _run_all()
    sys.exit(0 if exito else 1)
