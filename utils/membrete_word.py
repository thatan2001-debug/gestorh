"""
Extrae el membrete/encabezado de un archivo Word (.docx) para usarlo
como encabezado en los PDFs generados por GestorRH Colombia.

Estrategia:
1. Intenta extraer la imagen del encabezado del Word (si existe)
2. Si no hay imagen, extrae el texto del encabezado
3. Convierte el resultado en un objeto usable por reportlab
"""

import io
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from PIL import Image as PILImage
import zipfile


def extraer_membrete_word(ruta_docx: str) -> dict:
    """
    Extrae el membrete de un archivo Word.
    
    Retorna dict con:
    - tipo: 'imagen' | 'texto' | 'nada'
    - imagen_bytes: bytes PNG de la imagen del encabezado (si tipo='imagen')
    - texto_lineas: lista de strings del encabezado (si tipo='texto')
    - ruta_imagen_guardada: ruta donde se guardó la imagen (para reusar)
    """
    resultado = {"tipo": "nada", "imagen_bytes": None, 
                 "texto_lineas": [], "ruta_imagen_guardada": None}
    
    try:
        doc = Document(ruta_docx)
        
        # ── Intentar extraer imagen del encabezado ───────────────────────────
        for seccion in doc.sections:
            header = seccion.header
            if header is None:
                continue
            
            # Buscar imágenes en el encabezado
            for rel in header.part.rels.values():
                if "image" in rel.reltype:
                    try:
                        img_bytes = rel.target_part.blob
                        # Convertir a PNG normalizado
                        img = PILImage.open(io.BytesIO(img_bytes))
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        resultado["imagen_bytes"] = buf.getvalue()
                        resultado["tipo"] = "imagen"
                        
                        # Guardar en assets para reusar
                        ruta_guardada = "assets/membrete_word.png"
                        Path("assets").mkdir(exist_ok=True)
                        with open(ruta_guardada, "wb") as f:
                            f.write(buf.getvalue())
                        resultado["ruta_imagen_guardada"] = ruta_guardada
                        return resultado
                    except Exception:
                        continue
            
            # ── Si no hay imagen, extraer texto del encabezado ───────────────
            textos = []
            for para in header.paragraphs:
                texto = para.text.strip()
                if texto:
                    textos.append(texto)
            
            if textos:
                resultado["tipo"] = "texto"
                resultado["texto_lineas"] = textos
                return resultado
        
        # ── Si no hay sección con encabezado, buscar imágenes en el cuerpo ──
        # (algunas empresas ponen el membrete como imagen al inicio del doc)
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                try:
                    img_bytes = rel.target_part.blob
                    img = PILImage.open(io.BytesIO(img_bytes))
                    # Solo usar si es horizontal (parece membrete)
                    w, h = img.size
                    if w > h * 2:  # ratio horizontal = membrete
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        resultado["imagen_bytes"] = buf.getvalue()
                        resultado["tipo"] = "imagen"
                        ruta_guardada = "assets/membrete_word.png"
                        with open(ruta_guardada, "wb") as f:
                            f.write(buf.getvalue())
                        resultado["ruta_imagen_guardada"] = ruta_guardada
                        return resultado
                except Exception:
                    continue
                    
    except Exception as e:
        print(f"Error extrayendo membrete de Word: {e}")
    
    return resultado


def obtener_dimensiones_membrete(ruta_imagen: str, 
                                  ancho_maximo_cm: float = 17.0) -> tuple[float, float]:
    """Calcula dimensiones proporcionales para el membrete en el PDF."""
    try:
        from reportlab.lib.units import cm
        img = PILImage.open(ruta_imagen)
        w, h = img.size
        ratio = h / w
        ancho = ancho_maximo_cm * cm
        alto  = ancho * ratio
        # Limitar altura máxima a 4cm para que no ocupe demasiado
        if alto > 4 * cm:
            alto  = 4 * cm
            ancho = alto / ratio
        return ancho, alto
    except Exception:
        from reportlab.lib.units import cm
        return 17 * cm, 2.5 * cm
