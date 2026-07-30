"""Parámetros legales versionados para cálculos laborales colombianos.

Una única fuente evita que salario mínimo, auxilio, porcentajes y vigencias se
repitan en los generadores. Las referencias deben revisarse al iniciar cada año.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict


@dataclass(frozen=True)
class ParametrosLegales:
    anio: int
    vigente_desde: date
    salario_minimo: int
    auxilio_transporte: int
    tope_auxilio_smmlv: float = 2.0
    porcentaje_intereses_cesantias: float = 0.12
    divisor_prestaciones: int = 360
    divisor_vacaciones: int = 720
    jornada_maxima_semanal: int = 42
    version: str = "2026.1"
    estado: str = "activo"
    fuente_salario: str = "Decretos 1469 de 2025 y 159 de 2026"
    fuente_auxilio: str = "Decreto 1470 de 2025"

    @property
    def tope_auxilio_transporte(self) -> float:
        return self.salario_minimo * self.tope_auxilio_smmlv


_PARAMETROS: Dict[int, ParametrosLegales] = {
    2026: ParametrosLegales(
        anio=2026,
        vigente_desde=date(2026, 1, 1),
        salario_minimo=1_750_905,
        auxilio_transporte=249_095,
    )
}


def obtener_parametros(anio: int | None = None) -> ParametrosLegales:
    """Obtiene parámetros del año solicitado; falla de forma explícita si falta."""
    anio = anio or date.today().year
    try:
        return _PARAMETROS[int(anio)]
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"No existen parámetros legales activos para el año {anio}. "
            "Regístrelos y revíselos antes de generar cálculos."
        ) from exc


def registrar_parametros(parametros: ParametrosLegales) -> None:
    """Permite registrar un año desde configuración/migraciones sin duplicar lógica."""
    _PARAMETROS[parametros.anio] = parametros


# Compatibilidad con imports existentes.
PARAMETROS_2026 = _PARAMETROS[2026]
SALARIO_MINIMO_2026 = PARAMETROS_2026.salario_minimo
AUXILIO_TRANSPORTE_2026 = PARAMETROS_2026.auxilio_transporte
TOPE_AUXILIO_TRANSPORTE = PARAMETROS_2026.tope_auxilio_transporte
