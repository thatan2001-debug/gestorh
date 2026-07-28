"""Utilidades compartidas y compatibilidad visual de Gestor RH IA."""

from pathlib import Path
import base64


def _configurar_logo_acceso() -> None:
    """Sustituye el encabezado antiguo del acceso por el logo local completo."""
    try:
        import streamlit as st

        if getattr(st.markdown, "_gestorrh_logo_patch", False):
            return

        markdown_original = st.markdown

        def markdown_gestorrh(body, *args, **kwargs):
            if isinstance(body, str):
                # Eliminar el intento anterior basado en una imagen externa.
                marcador_css = "/* ── Logo corporativo en la pantalla de acceso ── */"
                if marcador_css in body:
                    inicio = body.find(marcador_css)
                    cierre = body.find("</style>", inicio)
                    if cierre != -1:
                        body = body[:inicio] + body[cierre:]

                es_encabezado_acceso = (
                    "font-size:2.5rem" in body
                    and "Gestor RH IA" in body
                    and "Documentos laborales para PYMES colombianas" in body
                )

                if es_encabezado_acceso:
                    logo = Path("assets/logo_gestorrh.png")
                    if logo.exists():
                        contenido = base64.b64encode(logo.read_bytes()).decode("ascii")
                        html_logo = f"""
                        <style>
                            .gestorrh-login-logo {{
                                width: 100%;
                                max-width: 700px;
                                height: 180px;
                                margin: 0 auto 0.8rem auto;
                                background-image: url('data:image/png;base64,{contenido}');
                                background-repeat: no-repeat;
                                background-position: center center;
                                background-size: contain;
                            }}
                            @media (max-width: 640px) {{
                                .gestorrh-login-logo {{
                                    height: 115px;
                                    margin-bottom: 0.45rem;
                                }}
                            }}
                        </style>
                        <div class="gestorrh-login-logo" role="img" aria-label="Gestor RH IA"></div>
                        """
                        return markdown_original(html_logo, unsafe_allow_html=True)

            return markdown_original(body, *args, **kwargs)

        markdown_gestorrh._gestorrh_logo_patch = True
        st.markdown = markdown_gestorrh

    except Exception:
        # Una mejora visual nunca debe impedir que la aplicación inicie.
        pass


_configurar_logo_acceso()
