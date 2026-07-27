"""
Procesamiento de membretes (Etapa Opción "Solo membrete").

Permite a las empresas subir su propio formato oficial y que el sistema
solo escriba el texto encima, sin agregar logos, encabezados o diseños.

Formatos soportados:
- JPG / JPEG
- PNG
- PDF de UNA sola página

Al subir un PDF, se convierte a imagen de fondo con alta resolución.
Al subir una imagen, se usa directamente como fondo.

El resultado es un archivo PNG optimizado que se usa como marca de agua
completa (fondo de página) en la generación de documentos.
"""

from pathlib import Path
from typing import Optional
import io


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

FORMATOS_SOPORTADOS = {".jpg", ".jpeg", ".png", ".pdf"}
DPI_CONVERSION_PDF = 200  # 200 DPI = calidad buena, tamaño razonable
MAX_ANCHO_MEMBRETE_PX = 2500  # Redimensiona si es mayor
MEMBRETE_DIR = Path("salidas/membretes")


# ══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def validar_membrete(archivo_bytes: bytes, nombre_archivo: str) -> tuple:
    """
    Valida un membrete subido por el usuario.

    Retorna: (ok: bool, mensaje: str, extension: str)
    """
    if not archivo_bytes:
        return False, "Archivo vacío", ""

    # Extensión
    ext = Path(nombre_archivo).suffix.lower()
    if ext not in FORMATOS_SOPORTADOS:
        return False, (
            f"Formato no soportado ({ext}). "
            f"Usa JPG, PNG o PDF de una página."
        ), ""

    # Tamaño razonable (máximo 10 MB)
    if len(archivo_bytes) > 10 * 1024 * 1024:
        return False, "El archivo excede 10 MB. Comprímelo o usa menor resolución.", ""

    if len(archivo_bytes) < 1024:
        return False, "El archivo es demasiado pequeño (<1 KB). Verifica que no esté vacío.", ""

    return True, "", ext


# ══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO
# ══════════════════════════════════════════════════════════════════════════════

def procesar_membrete(archivo_bytes: bytes, nombre_archivo: str,
                        email_empresa: str) -> tuple:
    """
    Procesa el membrete subido y lo guarda como PNG listo para usar.

    Args:
        archivo_bytes: contenido del archivo
        nombre_archivo: nombre original (para saber la extensión)
        email_empresa: para nombrar el archivo destino

    Retorna: (ok: bool, mensaje: str, ruta_png: str)
    """
    ok, msg, ext = validar_membrete(archivo_bytes, nombre_archivo)
    if not ok:
        return False, msg, ""

    MEMBRETE_DIR.mkdir(parents=True, exist_ok=True)

    # Nombre del archivo destino (uno por empresa)
    email_safe = email_empresa.replace("@", "_").replace(".", "_")
    ruta_destino = MEMBRETE_DIR / f"membrete_{email_safe}.png"

    try:
        if ext == ".pdf":
            imagen_bytes = _pdf_a_imagen(archivo_bytes)
            if not imagen_bytes:
                return False, (
                    "No se pudo convertir el PDF a imagen. "
                    "Verifica que sea una página válida."
                ), ""
        else:
            # JPG / PNG — usar directo
            imagen_bytes = archivo_bytes

        # Redimensionar si es muy grande y guardar como PNG
        _optimizar_y_guardar(imagen_bytes, ruta_destino)

        return True, "Membrete cargado correctamente", str(ruta_destino)

    except Exception as e:
        return False, f"Error procesando membrete: {e}", ""


def _pdf_a_imagen(pdf_bytes: bytes) -> Optional[bytes]:
    """Convierte la primera página de un PDF a imagen PNG."""
    try:
        # pdf2image requiere poppler instalado
        # Alternativa: usar PyMuPDF (fitz) que trae todo incluido
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        if len(doc) < 1:
            doc.close()
            return None

        pagina = doc[0]
        # Renderizar a la resolución configurada
        matriz = fitz.Matrix(DPI_CONVERSION_PDF / 72, DPI_CONVERSION_PDF / 72)
        pix = pagina.get_pixmap(matrix=matriz, alpha=False)
        img_bytes = pix.tobytes("png")
        doc.close()
        return img_bytes
    except ImportError:
        # PyMuPDF no está instalado, intentar con pdf2image
        try:
            from pdf2image import convert_from_bytes
            imagenes = convert_from_bytes(
                pdf_bytes, dpi=DPI_CONVERSION_PDF, first_page=1, last_page=1
            )
            if not imagenes:
                return None
            buf = io.BytesIO()
            imagenes[0].save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return None
    except Exception:
        return None


def _optimizar_y_guardar(imagen_bytes: bytes, ruta_destino: Path):
    """
    Optimiza la imagen (redimensiona si es demasiado grande) y guarda como PNG.
    """
    from PIL import Image
    img = Image.open(io.BytesIO(imagen_bytes))

    # Convertir a RGB si tiene canal alfa (para JPG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Redimensionar si excede ancho máximo (proporcional)
    if img.width > MAX_ANCHO_MEMBRETE_PX:
        ratio = MAX_ANCHO_MEMBRETE_PX / img.width
        nuevo_alto = int(img.height * ratio)
        img = img.resize(
            (MAX_ANCHO_MEMBRETE_PX, nuevo_alto),
            Image.Resampling.LANCZOS
        )

    img.save(ruta_destino, format="PNG", optimize=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTAS
# ══════════════════════════════════════════════════════════════════════════════

def obtener_membrete_empresa(email_empresa: str) -> Optional[str]:
    """
    Retorna la ruta del membrete guardado para esta empresa, o None.
    """
    if not email_empresa:
        return None
    email_safe = email_empresa.replace("@", "_").replace(".", "_")
    ruta = MEMBRETE_DIR / f"membrete_{email_safe}.png"
    if ruta.exists():
        return str(ruta)
    return None


def eliminar_membrete_empresa(email_empresa: str) -> bool:
    """Elimina el membrete guardado (si existe)."""
    ruta = obtener_membrete_empresa(email_empresa)
    if ruta and Path(ruta).exists():
        try:
            Path(ruta).unlink()
            return True
        except Exception:
            return False
    return False
