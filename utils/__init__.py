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
                # Retirar la regla CSS temporal que podía generar espacios o
                # recortes al intentar mostrar el logo como fondo externo.
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
                        <div style="width:100%;text-align:center;padding:0.25rem 0 1.15rem;overflow:visible;">
                            <img
                                src="data:image/png;base64,{contenido}"
                                alt="Gestor RH IA"
                                style="display:block;width:100%;max-width:680px;height:auto;max-height:none;object-fit:contain;margin:0 auto;"
                            />
                        </div>
                        """
                        return markdown_original(html_logo, unsafe_allow_html=True)

            return markdown_original(body, *args, **kwargs)

        markdown_gestorrh._gestorrh_logo_patch = True
        st.markdown = markdown_gestorrh

    except Exception:
        # Una mejora visual nunca debe impedir que la aplicación inicie.
        pass


_configurar_logo_acceso()
