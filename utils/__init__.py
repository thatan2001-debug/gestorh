"""Utilidades compartidas de Gestor RH IA."""
from __future__ import annotations

import re


def _strip_legacy_logo_css(css: str) -> str:
    """Elimina el bloque CSS legado que incrustaba un logo remoto fijo."""
    marker = "/* ── Logo corporativo en la pantalla de acceso ── */"
    if marker not in css:
        return css
    before, after = css.split(marker, 1)
    # El bloque legado terminaba antes del cierre style; conservar el cierre y
    # cualquier regla anterior para evitar invalidar la hoja completa.
    closing = "</style>" if "</style>" in after else ""
    return before.rstrip() + ("\n" + closing if closing else "")


def _is_auth_header(html: str) -> bool:
    """Detecta únicamente el encabezado completo de autenticación."""
    text = re.sub(r"\s+", " ", str(html or "")).lower()
    required = (
        "text-align:center" in text or "text-align: center" in text,
        "gestor rh ia" in text,
        "documentos laborales para pymes colombianas" in text,
        "<div" in text,
    )
    return all(required)


__all__ = ["_strip_legacy_logo_css", "_is_auth_header"]
