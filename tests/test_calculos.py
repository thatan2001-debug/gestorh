"""
Suite de tests automáticos de los cálculos legales de Gestor RH IA.

Ejecutar:
    python -m pytest tests/test_calculos.py -v

O sin pytest:
    python tests/test_calculos.py

Estos tests protegen los cálculos legales críticos. Si algún cambio
rompe una fórmula del CST, este test lo detectará antes de que llegue
a producción.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import pandas as pd
from utils.calcular_liquidacion import (
    _indemnizacion,
    calcular_liquidacion_fila,
)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE INDEMNIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def test_renuncia_no_genera_indemnizacion():
    """Renuncia voluntaria NO debe generar indemnización."""
    r = _indemnizacion(2_000_000, 720, "indefinido", motivo_retiro="renuncia")
    assert r["monto"] == 0, f"Renuncia debería ser 0, dio {r['monto']}"


def test_con_justa_causa_no_genera_indemnizacion():
    """Despido con justa causa NO genera indemnización."""
    r = _indemnizacion(2_000_000, 720, "indefinido", motivo_retiro="con_justa_causa")
    assert r["monto"] == 0, f"Con justa causa debería ser 0, dio {r['monto']}"


def test_mutuo_acuerdo_no_genera_indemnizacion():
    """Mutuo acuerdo NO genera indemnización (salvo pacto)."""
    r = _indemnizacion(2_000_000, 720, "indefinido", motivo_retiro="mutuo_acuerdo")
    assert r["monto"] == 0


def test_vencimiento_no_genera_indemnizacion():
    """Vencimiento de contrato con preaviso NO genera indemnización."""
    r = _indemnizacion(2_000_000, 720, "fijo", motivo_retiro="vencimiento_contrato")
    assert r["monto"] == 0


def test_obra_terminada_no_genera_indemnizacion():
    """Obra terminada correctamente NO genera indemnización."""
    r = _indemnizacion(2_000_000, 720, "obra", motivo_retiro="obra_terminada")
    assert r["monto"] == 0


def test_despido_sin_justa_causa_indefinido_bajo_smmlv():
    """
    Despido sin justa causa, indefinido, salario < 10 SMMLV, 2 años:
    30 días primer año + 20 días segundo año = 50 días × (2M/30) ≈ $3,333,333
    """
    r = _indemnizacion(2_000_000, 720, "indefinido",
                        motivo_retiro="despido_sin_justa_causa")
    esperado = 2_000_000 / 30 * 50  # 50 días
    assert abs(r["monto"] - esperado) < 1000, \
        f"Esperado ~{esperado}, dio {r['monto']}"


def test_despido_sin_justa_causa_primer_año():
    """
    Despido sin justa causa, indefinido, salario < 10 SMMLV, 6 meses:
    En primer año → 30 días = $2M
    """
    r = _indemnizacion(2_000_000, 180, "indefinido",
                        motivo_retiro="despido_sin_justa_causa")
    esperado = 2_000_000  # 30 días de salario
    assert abs(r["monto"] - esperado) < 1000, \
        f"Esperado ~{esperado}, dio {r['monto']}"


def test_despido_sin_justa_causa_alto_smmlv():
    """
    Salario >= 10 SMMLV (2026: 10 × ~1.56M = ~15.6M), 5 años:
    20 días primer año + 15 × 4 años = 80 días adicionales = 80 días total
    Con salario 20M: 20M/30 * 80 = ~$53.3M
    """
    r = _indemnizacion(20_000_000, 1800, "indefinido",
                        motivo_retiro="despido_sin_justa_causa")
    esperado = 20_000_000 / 30 * 80
    assert abs(r["monto"] - esperado) < 10000, \
        f"Esperado ~{esperado}, dio {r['monto']}"


def test_despido_contrato_fijo_dias_pendientes():
    """
    Despido sin justa causa en contrato fijo con 90 días pendientes:
    Indemnización = 90 días × salario diario = 90 × (2M/30) = $6M
    """
    r = _indemnizacion(2_000_000, 180, "fijo",
                        motivo_retiro="despido_sin_justa_causa",
                        dias_pendientes_fijo=90)
    esperado = 2_000_000 / 30 * 90
    assert abs(r["monto"] - esperado) < 100, \
        f"Esperado ~{esperado}, dio {r['monto']}"


def test_despido_contrato_fijo_minimo_15_dias():
    """
    Contrato fijo con menos de 15 días pendientes → mínimo 15 días (Ley 789/2002).
    """
    r = _indemnizacion(2_000_000, 180, "fijo",
                        motivo_retiro="despido_sin_justa_causa",
                        dias_pendientes_fijo=5)
    esperado = 2_000_000 / 30 * 15  # mínimo 15
    assert abs(r["monto"] - esperado) < 100, \
        f"Mínimo debe ser 15 días. Esperado {esperado}, dio {r['monto']}"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE LIQUIDACIÓN COMPLETA
# ══════════════════════════════════════════════════════════════════════════════

def _fila_test(salario=2_000_000, fecha_ingreso="15/07/2024",
                tipo_contrato="Indefinido", fecha_retiro=""):
    return pd.Series({
        "Nombre": "Test", "Documento": "123", "Cargo": "Test",
        "Salario": salario,
        "Fecha ingreso": fecha_ingreso,
        "Fecha retiro":  fecha_retiro,
        "Tipo contrato": tipo_contrato,
    })


def test_liquidacion_completa_renuncia_dos_años():
    """
    Liquidación completa por renuncia — 2 años, 2M salario (< 2 SMMLV 2026).
    Como salario < 2 SMMLV, se incluye auxilio de transporte en base prestacional.
    Base = 2M + auxilio 2026. Cesantías ≈ base × 720/360.
    Solo verificamos que sea >= al mínimo sin auxilio (4M).
    """
    fila = _fila_test()
    fc = datetime(2026, 7, 15)
    r = calcular_liquidacion_fila(fila, fc, motivo_retiro="renuncia")

    ces = r["Cesantias (Art. 249 CST)"]
    # Con auxilio: cesantías > 4M (base sola). Sin auxilio: = 4M.
    assert ces >= 4_000_000, f"Cesantías: debe ser >= 4M (2 años × 2M), dio {ces}"
    # No más de 5M (que sería muy excesivo)
    assert ces < 5_000_000, f"Cesantías: excesivas ({ces})"

    vac = r["Vacaciones (Art. 186 CST)"]
    # Vacaciones NO incluyen auxilio de transporte (Art. 192 CST)
    assert abs(vac - 2_000_000) < 5000, f"Vacaciones (sin aux): esperado 2M, dio {vac}"

    indem = r["Indemnizacion (Art. 64 CST)"]
    assert indem == 0, f"Sin justa causa NO debe tener indem, dio {indem}"


def test_liquidacion_completa_despido_sin_justa_causa():
    """
    Liquidación completa con despido sin justa causa.
    Debe tener TODO lo de la renuncia + indemnización.
    """
    fila = _fila_test()
    fc = datetime(2026, 7, 15)
    r = calcular_liquidacion_fila(fila, fc, motivo_retiro="despido_sin_justa_causa")

    indem = r["Indemnizacion (Art. 64 CST)"]
    assert indem > 0, f"Despido sin justa causa DEBE tener indem, dio {indem}"

    # Debe ser aproximadamente 50 días de salario
    esperado = 2_000_000 / 30 * 50
    assert abs(indem - esperado) < 5000, \
        f"Indem esperada ~{esperado}, dio {indem}"


def test_liquidacion_motivo_afecta_resultado():
    """
    El mismo empleado con motivos diferentes debe dar TOTALES diferentes.
    Este test protege el bug que llevamos días persiguiendo.
    """
    fc = datetime(2026, 7, 15)
    fila = _fila_test()

    r_renuncia = calcular_liquidacion_fila(fila, fc, motivo_retiro="renuncia")
    r_despido  = calcular_liquidacion_fila(fila, fc, motivo_retiro="despido_sin_justa_causa")

    total_r = r_renuncia["TOTAL LIQUIDACION ESTIMADA"]
    total_d = r_despido["TOTAL LIQUIDACION ESTIMADA"]

    assert total_d > total_r, \
        f"Despido ({total_d}) debe ser mayor que renuncia ({total_r})"

    # La diferencia debe ser aproximadamente la indemnización
    diferencia = total_d - total_r
    indem = r_despido["Indemnizacion (Art. 64 CST)"]
    assert abs(diferencia - indem) < 1, \
        f"Diferencia ({diferencia}) debe ser la indem ({indem})"


def test_liquidacion_cero_dias_no_falla():
    """Liquidar exactamente el día que entró NO debe fallar."""
    fila = _fila_test(fecha_ingreso="15/07/2026")
    fc = datetime(2026, 7, 15)
    r = calcular_liquidacion_fila(fila, fc, motivo_retiro="renuncia")
    assert r["Cesantias (Art. 249 CST)"] == 0


def test_liquidacion_fechas_incoherentes():
    """Fecha de corte antes que fecha de ingreso debe lanzar excepción clara."""
    fila = _fila_test(fecha_ingreso="15/07/2026")
    fc = datetime(2020, 1, 1)
    try:
        calcular_liquidacion_fila(fila, fc, motivo_retiro="renuncia")
        assert False, "Debería haber lanzado excepción"
    except ValueError as e:
        assert "anterior" in str(e).lower() or "fecha" in str(e).lower()


def test_motivo_se_preserva_en_resultado():
    """
    El motivo enviado debe aparecer en el campo 'Motivo retiro' del resultado.
    Este test protege el bug donde el PDF decía 'Retiro Voluntario' con cualquier motivo.
    """
    fila = _fila_test()
    fc = datetime(2026, 7, 15)

    r = calcular_liquidacion_fila(fila, fc, motivo_retiro="despido_sin_justa_causa")
    motivo_guardado = r.get("Motivo retiro", "")
    assert motivo_guardado == "despido_sin_justa_causa", \
        f"El motivo debe preservarse. Enviado: 'despido_sin_justa_causa', " \
        f"guardado: '{motivo_guardado}'"

    # Verificar que _causa_retiro lo mapea al texto correcto
    from utils.plantillas_disenio import _causa_retiro
    texto = _causa_retiro(motivo_guardado)
    assert "Sin Justa Causa" in texto, \
        f"El texto debe reflejar 'Sin Justa Causa', dio: '{texto}'"


def test_motivo_mapeo_todos_los_casos():
    """Cada motivo debe mapear a un texto legible correcto en el PDF."""
    from utils.plantillas_disenio import _causa_retiro

    casos = {
        "renuncia":                "Retiro Voluntario",
        "con_justa_causa":         "Despido con Justa Causa (Art. 62 CST)",
        "despido_sin_justa_causa": "Despido Sin Justa Causa (Art. 64 CST)",
        "mutuo_acuerdo":           "Mutuo Acuerdo",
        "vencimiento_contrato":    "Vencimiento de Contrato",
        "obra_terminada":          "Finalización de Obra o Labor",
        "jubilacion":              "Jubilación",
    }
    for motivo, esperado in casos.items():
        resultado = _causa_retiro(motivo)
        assert resultado == esperado, \
            f"Motivo '{motivo}': esperado '{esperado}', dio '{resultado}'"


# ══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _run_all():
    """Ejecuta todos los tests y reporta resultado."""
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
            print(f"  ❌ {name}\n     {e}")
        except Exception as e:
            fallados.append((name, f"Excepción: {e}"))
            print(f"  💥 {name}\n     Excepción: {e}")

    print()
    print(f"{'='*60}")
    print(f"RESULTADO: {pasados}/{len(tests)} tests pasaron")
    if fallados:
        print(f"{'='*60}")
        print(f"❌ {len(fallados)} FALLARON:")
        for name, msg in fallados:
            print(f"  • {name}: {msg}")
    else:
        print("🎉 Todos los tests pasaron")
    print(f"{'='*60}")
    return len(fallados) == 0


if __name__ == "__main__":
    print("Ejecutando tests de cálculos legales...\n")
    exito = _run_all()
    sys.exit(0 if exito else 1)
