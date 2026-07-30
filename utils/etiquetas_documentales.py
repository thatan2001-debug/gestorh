"""Etiquetas formales para convertir códigos internos en lenguaje documental."""
from __future__ import annotations

import re
import unicodedata

_ETIQUETAS = {
    "renuncia": "Renuncia voluntaria",
    "despido_sin_justa_causa": "Despido sin justa causa",
    "sin_justa_causa": "Despido sin justa causa",
    "terminacion_unilateral_empleador": "Terminación unilateral por parte del empleador",
    "despido_por_incapacidad": "Terminación por incapacidad, según soporte registrado",
    "mutuo_acuerdo": "Terminación por mutuo acuerdo",
    "terminacion_con_justa_causa": "Terminación con justa causa",
    "vencimiento_termino": "Vencimiento del término pactado",
    "finalizacion_obra": "Finalización de la obra o labor contratada",
    "pension": "Reconocimiento de pensión",
    "muerte_trabajador": "Fallecimiento de la persona trabajadora",
}


def etiqueta_formal(valor: object, default: str = "Causa registrada por la empresa") -> str:
    """Convierte códigos snake_case y valores técnicos en etiquetas legibles."""
    texto = str(valor or "").strip()
    if not texto:
        return default
    clave = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    clave = re.sub(r"[^a-zA-Z0-9]+", "_", clave).strip("_").lower()
    if clave in _ETIQUETAS:
        return _ETIQUETAS[clave]
    legible = re.sub(r"[_-]+", " ", texto).strip()
    legible = re.sub(r"\s+", " ", legible)
    return legible[:1].upper() + legible[1:]
