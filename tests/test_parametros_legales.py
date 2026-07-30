import pytest
from utils.parametros_legales import obtener_parametros


def test_parametros_2026_centralizados():
    p = obtener_parametros(2026)
    assert p.salario_minimo == 1_750_905
    assert p.auxilio_transporte == 249_095
    assert p.tope_auxilio_transporte == 3_501_810
    assert p.version == "2026.1"


def test_anio_sin_parametros_falla_explicito():
    with pytest.raises(ValueError, match="parámetros legales"):
        obtener_parametros(2031)
