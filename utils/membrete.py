"""
Procesamiento de membrete desde Word (.docx).
Extrae el encabezado/membrete del Word del usuario y lo convierte
en imagen PNG para usarlo en los PDFs generados por GestorRH Colombia.
"""

import zipfile
import shutil
from pathlib import Path
from PIL import Image
import io
import subprocess
import tempfile

CARPETA_MEMBRETES = Path("assets/membretes")


def extraer_membrete_word(ruta_docx: str) -> tuple[str | None, str]:
    """
    Extrae el encabezado del Word como imagen PNG.
    Estrategia:
    1. Convierte el Word a PDF con LibreOffice (si disponible)
    2. Toma solo la primera página (donde está el membrete)
    3. Recorta la parte superior (~25% de la página = membrete)
    4. Guarda como PNG en assets/membretes/

    Retorna (ruta_png | None, mensaje).
    """
    CARPETA_MEMBRETES.mkdir(parents=True, exist_ok=True)
    ruta = Path(ruta_docx)
    nombre_base = ruta.stem

    # ── Intentar con LibreOffice ─────────────────────────────────────────
    try:
        with tempfile.TemporaryDirectory() as tmp:
            resultado = subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf",
                 "--outdir", tmp, str(ruta)],
                capture_output=True, timeout=30,
            )
            pdf_tmp = Path(tmp) / f"{nombre_base}.pdf"
            if resultado.returncode == 0 and pdf_tmp.exists():
                # Convertir primera página a imagen
                png_base = str(CARPETA_MEMBRETES / f"membrete_{nombre_base}")
                subprocess.run(
                    ["pdftoppm", "-png", "-r", "150", "-l", "1", str(pdf_tmp), png_base],
                    capture_output=True, timeout=20,
                )
                png_full = Path(f"{png_base}-1.png")
                if png_full.exists():
                    # Recortar solo el membrete (30% superior de la página)
                    img = Image.open(str(png_full))
                    w, h = img.size
                    alto_membrete = int(h * 0.28)
                    membrete = img.crop((0, 0, w, alto_membrete))
                    ruta_membrete = CARPETA_MEMBRETES / f"membrete_{nombre_base}.png"
                    membrete.save(str(ruta_membrete))
                    png_full.unlink(missing_ok=True)
                    return str(ruta_membrete), "Membrete extraído correctamente desde Word."
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # LibreOffice no disponible — intentar método alternativo

    # ── Método alternativo: extraer imágenes embebidas del Word ─────────
    try:
        imagenes = _extraer_imagenes_word(ruta_docx)
        if imagenes:
            # Usar la primera imagen como membrete (normalmente es el logo)
            ruta_membrete = CARPETA_MEMBRETES / f"membrete_{nombre_base}.png"
            shutil.copy2(imagenes[0], str(ruta_membrete))
            return str(ruta_membrete), (
                "Se extrajo la imagen del Word como membrete. "
                "Si no es el correcto, sube directamente el logo en 'Mi empresa'."
            )
    except Exception as e:
        pass

    return None, (
        "No se pudo extraer el membrete automáticamente. "
        "Puedes subir tu logo directamente en la sección 'Mi empresa' "
        "y el sistema lo usará en todos los documentos."
    )


def _extraer_imagenes_word(ruta_docx: str) -> list[str]:
    """Extrae imágenes embebidas de un archivo .docx."""
    imagenes = []
    CARPETA_MEMBRETES.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(ruta_docx, "r") as z:
            for nombre in z.namelist():
                if nombre.startswith("word/media/") and any(
                    nombre.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]
                ):
                    ext = Path(nombre).suffix
                    destino = str(CARPETA_MEMBRETES / f"img_{len(imagenes)}{ext}")
                    with z.open(nombre) as src, open(destino, "wb") as dst:
                        dst.write(src.read())
                    imagenes.append(destino)
    except Exception:
        pass
    return imagenes


def crear_marca_agua(logo_path: str, opacidad: float = 0.12) -> str | None:
    """
    Crea versión semitransparente del logo para usar como marca de agua.
    opacidad: 0.0 = invisible, 1.0 = completamente opaco. Default 12%.
    Retorna ruta de la imagen de marca de agua.
    """
    try:
        img = Image.open(logo_path).convert("RGBA")
        # Aplicar opacidad al canal alpha
        r, g, b, a = img.split()
        a = a.point(lambda x: int(x * opacidad))
        img_transparente = Image.merge("RGBA", (r, g, b, a))
        ruta_mda = str(CARPETA_MEMBRETES / "marca_agua.png")
        img_transparente.save(ruta_mda, "PNG")
        return ruta_mda
    except Exception as e:
        print(f"Error creando marca de agua: {e}")
        return None
