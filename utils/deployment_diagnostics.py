"""Diagnóstico seguro del despliegue activo de Render.

La vista solo se activa con ``?deployment_diagnostics=1`` y muestra
metadatos no sensibles que Render inyecta automáticamente en servicios
respaldados por Git. También reproduce el selector de aportes para verificar
visualmente que la versión desplegada contiene la interfaz esperada.
"""
from __future__ import annotations

import os
from typing import Final

import streamlit as st

DIAGNOSTIC_MARKER: Final = "GESTOR_RH_DEPLOYMENT_DIAGNOSTICS_V2"
_SELECTOR_LABEL: Final = "¿Los aportes del periodo final ya fueron descontados en nómina? *"
_APORTES_OPTIONS: Final = {
    "descontados_completamente": "Sí, fueron descontados completamente",
    "descontados_parcialmente": "Fueron descontados parcialmente",
    "no_descontados": "No fueron descontados",
    "revision_manual": "Requiere revisión manual",
}


def _query_enabled() -> bool:
    value = st.query_params.get("deployment_diagnostics", "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def deployment_metadata() -> dict[str, str]:
    """Retorna únicamente metadatos públicos del despliegue Git de Render."""
    return {
        "branch": os.getenv("RENDER_GIT_BRANCH", "NO_DISPONIBLE"),
        "commit": os.getenv("RENDER_GIT_COMMIT", "NO_DISPONIBLE"),
        "repository": os.getenv("RENDER_GIT_REPO_SLUG", "NO_DISPONIBLE"),
        "external_url": os.getenv("RENDER_EXTERNAL_URL", "NO_DISPONIBLE"),
        "service_name": os.getenv("RENDER_SERVICE_NAME", "NO_DISPONIBLE"),
    }


def mostrar_diagnostico_despliegue() -> bool:
    """Muestra una página de diagnóstico y retorna ``True`` si fue activada."""
    if not _query_enabled():
        return False

    metadata = deployment_metadata()
    st.title("Diagnóstico del despliegue activo")
    st.caption(
        "Esta pantalla muestra metadatos no sensibles del proceso de despliegue "
        "y una prueba visual del componente de conciliación de aportes."
    )

    st.code(
        "\n".join(
            [
                f"marker={DIAGNOSTIC_MARKER}",
                f"branch={metadata['branch']}",
                f"commit={metadata['commit']}",
                f"repository={metadata['repository']}",
                f"external_url={metadata['external_url']}",
                f"service_name={metadata['service_name']}",
            ]
        ),
        language="text",
    )

    st.divider()
    st.subheader("Prueba del selector de aportes del periodo final")
    dias = st.number_input(
        "Días de salario realmente pendientes",
        min_value=0,
        max_value=30,
        value=15,
        step=1,
        key="deployment_diag_days",
    )

    if dias <= 0:
        st.info(
            "No existe salario pendiente. Salud y pensión del periodo final no aplican."
        )
    else:
        estado = st.selectbox(
            _SELECTOR_LABEL,
            options=list(_APORTES_OPTIONS),
            index=None,
            placeholder="Selecciona una opción",
            format_func=lambda option: _APORTES_OPTIONS[option],
            key="deployment_diag_contributions",
        )
        if estado == "descontados_parcialmente":
            col_salud, col_pension = st.columns(2)
            with col_salud:
                st.number_input(
                    "Salud ya descontada ($)",
                    min_value=0.0,
                    step=1000.0,
                    key="deployment_diag_health",
                )
            with col_pension:
                st.number_input(
                    "Pensión ya descontada ($)",
                    min_value=0.0,
                    step=1000.0,
                    key="deployment_diag_pension",
                )

    st.success("Diagnóstico cargado desde el proceso activo de la aplicación.")
    return True
