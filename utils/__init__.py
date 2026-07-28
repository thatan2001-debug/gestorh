"""Utilidades compartidas de Gestor RH IA.

Este módulo aplica una corrección de compatibilidad visual para la pantalla de
acceso sin modificar la lógica de autenticación. Sustituye el encabezado HTML
anterior por el logo local del repositorio y elimina la regla CSS temporal que
producía un espacio vacío cuando la imagen externa no cargaba.
"""

from pathlib import Path


def _configurar_logo_acceso() -> None:
    """Muestra el logo local en el encabezado de acceso de forma estable."""
    try:
        import streamlit as st

        if getattr(st.markdown, "_gestorrh_logo_patch", False):
            return

        markdown_original = st.markdown

        def markdown_gestorrh(body, *args, **kwargs):
            if isinstance(body, str):
                # Retirar el bloque CSS temporal que ocultaba el icono pero
                # dependía de una imagen externa y generaba un espacio vacío.
                marcador_css = "/* ── Logo corporativo en la pantalla de acceso ── */"
                if marcador_css in body:
                    inicio = body.find(marcador_css)
                    cierre = body.find("</style>", inicio)
                    if cierre != -1:
                        body = body[:inicio] + body[cierre:]

                # Reemplazar únicamente el encabezado antiguo del login.
                es_encabezado_acceso = (
                    "font-size:2.5rem" in body
                    and "Gestor RH IA" in body
                    and "Documentos laborales para PYMES colombianas" in body
                )
                if es_encabezado_acceso:
                    logo = Path("assets/logo_gestorrh.png")
                    if logo.exists():
                        st.image(str(logo), use_container_width=True)
                        return None

            return markdown_original(body, *args, **kwargs)

        markdown_gestorrh._gestorrh_logo_patch = True
        st.markdown = markdown_gestorrh

    except Exception:
        # La app debe seguir iniciando aunque falle una mejora visual.
        pass


_configurar_logo_acceso()
