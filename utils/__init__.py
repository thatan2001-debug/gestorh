"""Utilidades compartidas y compatibilidad visual de Gestor RH IA.

La pantalla de autenticación todavía se construye en ``app.py`` con un bloque
HTML antiguo. Este módulo mantiene la compatibilidad sin alterar la lógica de
login o registro, pero elimina la regla CSS heredada que cargaba un logo desde
un commit fijo y sustituye únicamente ese encabezado por el PNG local actual.
"""

from pathlib import Path


_LEGACY_LOGO_MARKER = "/* ── Logo corporativo en la pantalla de acceso ── */"
_AUTH_TITLE = "Gestor RH IA"
_AUTH_SUBTITLE = "Documentos laborales para PYMES colombianas"


def _strip_legacy_logo_css(css: str) -> str:
    """Elimina la regla que apuntaba al logo recortado de un commit antiguo."""
    if not isinstance(css, str):
        return css

    start = css.find(_LEGACY_LOGO_MARKER)
    if start == -1:
        return css

    end = css.find("</style>", start)
    if end == -1:
        return css[:start].rstrip() + "\n</style>\n"

    return css[:start].rstrip() + "\n" + css[end:]


def _is_auth_header(body: str) -> bool:
    """Identifica exclusivamente el encabezado antiguo de login/registro."""
    return (
        isinstance(body, str)
        and "font-size:2.5rem" in body
        and _AUTH_TITLE in body
        and _AUTH_SUBTITLE in body
    )


def _clean_global_styles() -> None:
    """Limpia el CSS antes de que ``app.py`` lo importe y lo envíe al navegador."""
    try:
        from . import estilos

        estilos.CSS = _strip_legacy_logo_css(estilos.CSS)
    except Exception:
        # Una corrección visual nunca debe impedir que la aplicación arranque.
        pass


def _configure_auth_logo() -> None:
    """Renderiza el logo local completo en las pestañas Ingresar y Crear cuenta."""
    try:
        import streamlit as st

        if getattr(st.markdown, "_gestorrh_auth_logo_patch", False):
            return

        markdown_original = st.markdown
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo_gestorrh.png"

        def markdown_gestorrh(body, *args, **kwargs):
            if isinstance(body, str):
                body = _strip_legacy_logo_css(body)

                if _is_auth_header(body) and logo_path.is_file():
                    # st.image conserva la proporción original y no usa un
                    # contenedor de altura fija ni una imagen remota cacheada.
                    st.image(str(logo_path), use_container_width=True)
                    markdown_original(
                        '<div aria-hidden="true" style="height:0.65rem"></div>',
                        unsafe_allow_html=True,
                    )
                    return None

            return markdown_original(body, *args, **kwargs)

        markdown_gestorrh._gestorrh_auth_logo_patch = True
        st.markdown = markdown_gestorrh

    except Exception:
        # Mantener operativa la autenticación aunque falle una mejora visual.
        pass


_clean_global_styles()
_configure_auth_logo()
