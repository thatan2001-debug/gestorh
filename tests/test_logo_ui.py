"""Pruebas de regresión para el logo de la pantalla de autenticación."""

from pathlib import Path

from PIL import Image

from utils import _is_auth_header, _strip_legacy_logo_css


LEGACY_MARKER = "/* ── Logo corporativo en la pantalla de acceso ── */"
LEGACY_URL = (
    "https://raw.githubusercontent.com/thatan2001-debug/gestorh/"
    "f29b39d9150ed4e27e6941bb4114ef3deffd6879/assets/logo_gestorrh.png"
)


def test_legacy_logo_css_is_removed() -> None:
    css = f"""
    <style>
    body {{ background: white; }}
    {LEGACY_MARKER}
    .old-logo {{ background-image: url('{LEGACY_URL}'); }}
    </style>
    """

    cleaned = _strip_legacy_logo_css(css)

    assert LEGACY_MARKER not in cleaned
    assert LEGACY_URL not in cleaned
    assert "body { background: white; }" in cleaned
    assert "</style>" in cleaned


def test_auth_header_detection_is_specific() -> None:
    auth_header = """
    <div style='text-align:center;padding:2rem 0 1rem'>
        <div style='font-size:2.5rem'>📄</div>
        <h1>Gestor RH IA</h1>
        <p>Documentos laborales para PYMES colombianas</p>
    </div>
    """

    assert _is_auth_header(auth_header)
    assert not _is_auth_header("<h1>Gestor RH IA</h1>")


def test_official_logo_asset_is_complete_and_landscape() -> None:
    logo = Path(__file__).resolve().parents[1] / "assets" / "logo_gestorrh.png"

    assert logo.is_file(), "Falta assets/logo_gestorrh.png"

    with Image.open(logo) as image:
        width, height = image.size
        bbox = image.getbbox()

    assert width >= 600
    assert height >= 150
    assert width / height >= 3.0
    assert bbox is not None
    assert bbox[2] - bbox[0] >= width * 0.90
    assert bbox[3] - bbox[1] >= height * 0.85
