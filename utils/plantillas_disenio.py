"""
5 diseños profesionales de plantillas PDF para RH Fácil.
Encabezado: Nombre empresa (izq) + NIT debajo | Logo (der)
Opciones: logo como marca de agua, membrete personalizado desde Word
Liquidación: firma de representante legal Y empleado
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether,
)
from reportlab.pdfgen import canvas as pdfcanvas
from pathlib import Path
from datetime import datetime
from utils.numero_letras import numero_a_letras
from utils.calcular_liquidacion import AUXILIO_TRANSPORTE_2026
from utils.fecha_utils import fmt_fecha, fecha_hoy_larga

# ── Paletas ──────────────────────────────────────────────────────────────────
PALETAS = {
    1: {"primario": colors.HexColor("#1B3F6E"), "secundario": colors.HexColor("#2D6BE4"),
        "acento": colors.HexColor("#E8F0FD"), "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"), "borde": colors.HexColor("#DBEAFE"),
        "nombre": "Clásico Corporativo"},
    2: {"primario": colors.HexColor("#1F2937"), "secundario": colors.HexColor("#B45309"),
        "acento": colors.HexColor("#FEF3C7"), "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"), "borde": colors.HexColor("#E5E7EB"),
        "nombre": "Ejecutivo Oscuro"},
    3: {"primario": colors.HexColor("#064E3B"), "secundario": colors.HexColor("#059669"),
        "acento": colors.HexColor("#ECFDF5"), "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"), "borde": colors.HexColor("#D1FAE5"),
        "nombre": "Verde Institucional"},
    4: {"primario": colors.HexColor("#111827"), "secundario": colors.HexColor("#DC2626"),
        "acento": colors.HexColor("#FEF2F2"), "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"), "borde": colors.HexColor("#FEE2E2"),
        "nombre": "Moderno Minimalista"},
    5: {"primario": colors.HexColor("#4C1D95"), "secundario": colors.HexColor("#7C3AED"),
        "acento": colors.HexColor("#F5F3FF"), "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"), "borde": colors.HexColor("#EDE9FE"),
        "nombre": "Profesional Violeta"},
}

# ── Márgenes ICONTEC/corporativos ────────────────────────────────────────────
# Norma ICONTEC / APA adaptada para documentos corporativos colombianos:
#   Superior:   3.0cm (4.0cm si hay membrete/logo grande en encabezado)
#   Inferior:   3.0cm
#   Izquierdo:  3.5cm (extra para archivado/carpeteado sin dañar texto)
#   Derecho:    2.5cm
MARGEN_SUP_NORMAL   = 2.5 * cm   # margen compacto estándar
MARGEN_SUP_MEMBRETE = 2.5 * cm   # igual — el membrete va dentro del flujo Platypus
# Nota: antes se usaba 4.0cm cuando había logo, pero como el encabezado
# (con logo incluido) va dentro del flujo de contenido, el margen superior
# debe ser el mismo siempre. El espacio extra lo da el propio bloque del encabezado.
MARGEN_INF          = 3.0 * cm
MARGEN_IZQ          = 3.5 * cm
MARGEN_DER          = 2.5 * cm
ANCHO_UTIL          = letter[0] - MARGEN_IZQ - MARGEN_DER  # ~12.5cm de texto útil

ANCHO_PAGINA = letter[0]
ALTO_PAGINA  = letter[1]


def _fmt(valor):
    try:
        return f"$ {float(valor):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(valor)


def _causa_retiro(motivo: str) -> str:
    return {"renuncia":"Retiro Voluntario","despido_sin_justa_causa":"Despido Sin Justa Causa",
            "mutuo_acuerdo":"Mutuo Acuerdo","vencimiento_contrato":"Vencimiento de Contrato"
            }.get(str(motivo).lower(), motivo.replace("_"," ").title())


def _estilos_para(paleta: dict) -> dict:
    base = getSampleStyleSheet()
    # Fuente 11pt, interlineado 1.5 (16.5pt), tipografía limpia — norma ICONTEC
    return {
        "empresa": ParagraphStyle("empresa", parent=base["Normal"],
            fontSize=13, fontName="Helvetica-Bold",
            textColor=paleta["primario"], spaceAfter=1),
        "nit": ParagraphStyle("nit", parent=base["Normal"],
            fontSize=9, textColor=paleta["gris"], spaceAfter=4),
        "titulo": ParagraphStyle("titulo", parent=base["Normal"],
            fontSize=13, fontName="Helvetica-Bold", alignment=TA_CENTER,
            textColor=paleta["primario"],
            spaceBefore=33,   # doble espacio APA = 2 × 16.5pt antes del título
            spaceAfter=33),   # doble espacio APA = 2 × 16.5pt después del título
        "cuerpo": ParagraphStyle("cuerpo", parent=base["Normal"],
            fontSize=11, leading=16.5,
            alignment=TA_JUSTIFY, spaceAfter=16.5,  # 1 interlineado entre párrafos
            textColor=paleta["texto"]),
        "firma_nombre": ParagraphStyle("firma_nombre", parent=base["Normal"],
            fontSize=10.5, fontName="Helvetica-Bold", textColor=paleta["texto"]),
        "firma_cargo": ParagraphStyle("firma_cargo", parent=base["Normal"],
            fontSize=9.5, textColor=paleta["gris"]),
        "nota": ParagraphStyle("nota", parent=base["Normal"],
            fontSize=8.5, textColor=paleta["gris"],
            alignment=TA_JUSTIFY, spaceBefore=12),
        "paz_salvo": ParagraphStyle("paz_salvo", parent=base["Normal"],
            fontSize=10, leading=15, alignment=TA_JUSTIFY, spaceAfter=8),
        "tabla_enc": ParagraphStyle("tabla_enc", parent=base["Normal"],
            fontSize=9, textColor=paleta["gris"]),
    }


# ── Logo con transparencia real via PIL ──────────────────────────────────────
def _logo_con_opacidad(logo_path: str, opacidad: float = 0.45) -> str:
    """
    Genera una copia del logo con opacidad reducida a nivel de píxel (PIL).
    El caché se invalida comparando la fecha de modificación del logo fuente.
    """
    try:
        from PIL import Image as PILImage
        Path("assets").mkdir(exist_ok=True)
        logo_mtime = int(Path(logo_path).stat().st_mtime)
        cache = str(Path("assets") / f"logo_enc_{int(opacidad*100)}_{logo_mtime}.png")

        if Path(cache).exists():
            return cache

        # Limpiar caches anteriores del mismo tipo para no acumular archivos
        for old in Path("assets").glob(f"logo_enc_{int(opacidad*100)}_*.png"):
            try:
                old.unlink()
            except Exception:
                pass

        img = PILImage.open(logo_path).convert("RGBA")
        r, g, b, a = img.split()
        a_nuevo = a.point(lambda px: int(px * opacidad))
        PILImage.merge("RGBA", (r, g, b, a_nuevo)).save(cache, "PNG")
        return cache
    except Exception as e:
        print(f"Aviso: no se pudo aplicar transparencia al logo ({e}). Usando original.")
        return logo_path


def _dibujar_logo_encabezado(canvas_obj, doc, logo_path: str,
                              x: float, y: float, w: float, h: float,
                              opacidad: float = 0.45):
    """
    Dibuja el logo semitransparente en el encabezado.
    Usa PIL para modificar el canal alpha real de la imagen.
    """
    if not logo_path or not Path(logo_path).exists():
        return
    try:
        logo_proc = _logo_con_opacidad(logo_path, opacidad)
        canvas_obj.saveState()
        canvas_obj.drawImage(
            logo_proc, x, y, width=w, height=h,
            mask="auto", preserveAspectRatio=True, anchor="c",
        )
        canvas_obj.restoreState()
    except Exception as e:
        print(f"Error dibujando logo: {e}")


def _dibujar_marca_agua(canvas_obj, doc, logo_path: str):
    """Logo centrado al 7% de opacidad como fondo de página."""
    _dibujar_logo_encabezado(
        canvas_obj, doc, logo_path,
        x=(ANCHO_PAGINA - 10*cm) / 2,
        y=(ALTO_PAGINA  - 10*cm) / 2,
        w=10*cm, h=10*cm, opacidad=0.07,
    )


def _pie(canvas_obj, doc, paleta: dict, logo_path: str = None,
         usar_marca_agua: bool = False,
         logo_enc_x: float = None, logo_enc_y: float = None,
         logo_enc_w: float = 2.8*cm, logo_enc_h: float = 2.8*cm):
    """
    Dibuja pie de página. También dibuja:
    - Logo en encabezado (semitransparente, 45%) si logo_enc_x/y están definidos
    - Marca de agua de fondo si usar_marca_agua=True
    """
    # Logo en encabezado (semitransparente)
    if logo_path and logo_enc_x is not None:
        _dibujar_logo_encabezado(
            canvas_obj, doc, logo_path,
            x=logo_enc_x, y=logo_enc_y,
            w=logo_enc_w, h=logo_enc_h,
            opacidad=0.45,
        )
    # Marca de agua de fondo
    if usar_marca_agua and logo_path:
        _dibujar_marca_agua(canvas_obj, doc, logo_path)

    canvas_obj.saveState()
    canvas_obj.setStrokeColor(paleta["borde"])
    canvas_obj.line(2*cm, 1.6*cm, letter[0]-2*cm, 1.6*cm)
    canvas_obj.setFont("Helvetica", 7.5)
    canvas_obj.setFillColor(paleta["gris"])
    canvas_obj.drawString(2*cm, 1.2*cm,
        f"Generado el {datetime.today().strftime('%d/%m/%Y %H:%M')} — RH Fácil")
    canvas_obj.drawRightString(letter[0]-2*cm, 1.2*cm,
        "Estimación de referencia. Validar con contador o abogado laboral.")
    canvas_obj.restoreState()


# ── Encabezado: Nombre+NIT izquierda | Logo derecha ───────────────────────────
def _logo_platypus(logo_path: str, w: float, h: float, opacidad: float = 0.45):
    """
    Devuelve un elemento Image con el logo procesado a la opacidad indicada.
    Usa PIL para aplicar transparencia real al canal alpha del PNG.
    """
    if not logo_path or not Path(logo_path).exists():
        return Paragraph("", ParagraphStyle("vacio"))
    try:
        logo_proc = _logo_con_opacidad(logo_path, opacidad)
        img = Image(logo_proc, width=w, height=h)
        img.hAlign = "RIGHT"
        return img
    except Exception:
        return Paragraph("", ParagraphStyle("vacio"))


def _encabezado(el, datos_empresa, estilos, paleta, disenio,
                logo_derecha: bool = True, membrete_path: str = None):
    """
    Estructura real según imagen de referencia:
    1. Logo en esquina superior derecha (tamaño generoso, semitrasp.)
    2. Bloque de color ancho con Nombre + NIT en blanco debajo del logo
    3. Pequeño espacio antes del título
    """
    nombre = datos_empresa.get("nombre", "")
    nit    = datos_empresa.get("nit", "")
    logo   = datos_empresa.get("logo_path") if logo_derecha else None
    tiene_logo = bool(logo and Path(logo).exists())

    # ── Membrete personalizado desde Word (reemplaza todo el encabezado) ──
    if membrete_path and Path(membrete_path).exists():
        try:
            img_elem = Image(membrete_path, width=ANCHO_UTIL, height=3.5*cm)
            img_elem.hAlign = "CENTER"
            el.append(img_elem)
            el.append(HRFlowable(width="100%", thickness=1,
                color=paleta["primario"], spaceAfter=8))
            return
        except Exception:
            pass

    # ── FILA 1: Logo derecha, celda vacía izquierda ───────────────────────
    if tiene_logo:
        logo_img = _logo_platypus(logo, w=3.6*cm, h=3.6*cm, opacidad=1.0)
        # Logo al 100% de opacidad en encabezado — como un membrete real
        fila_logo = Table(
            [["", logo_img]],
            colWidths=[ANCHO_UTIL - 4.0*cm, 4.0*cm],
        )
        fila_logo.setStyle(TableStyle([
            ("ALIGN",        (1,0), (1,0),   "RIGHT"),
            ("VALIGN",       (0,0), (-1,-1), "BOTTOM"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 0),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]))
        el.append(fila_logo)

    # ── FILA 2: Bloque de color ancho con Nombre + NIT ────────────────────
    PAD_LR = 14  # padding izquierdo y derecho del wrapper en puntos
    ANCHO_INTERNO = ANCHO_UTIL - PAD_LR * 2  # ancho real disponible para texto

    if disenio == 1:
        # Fondo azul oscuro, texto blanco
        bloque_nombre = Table([[
            Paragraph(f"<b><font color='white'>{nombre}</font></b>",
                ParagraphStyle("hn", fontSize=13, fontName="Helvetica-Bold",
                    textColor=colors.white, leading=16)),
            Paragraph(f"<font color='white'>Nit #{nit}</font>",
                ParagraphStyle("nn", fontSize=10, textColor=colors.white,
                    alignment=TA_RIGHT)),
        ]], colWidths=[ANCHO_INTERNO * 0.58, ANCHO_INTERNO * 0.42])
        bloque_nombre.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 0),
            ("BOTTOMPADDING",(0,0), (-1,-1), 0),
        ]))
        wrapper = Table([[bloque_nombre]], colWidths=[ANCHO_UTIL])
        wrapper.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), paleta["primario"]),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), PAD_LR),
            ("RIGHTPADDING",  (0,0), (-1,-1), PAD_LR),
        ]))
        el.append(wrapper)

    elif disenio == 2:
        # Borde dorado inferior
        t = Table([[
            Paragraph(f"<b>{nombre}</b>",
                ParagraphStyle("hn", fontSize=13, fontName="Helvetica-Bold",
                    textColor=paleta["primario"])),
            Paragraph(f"Nit #{nit}",
                ParagraphStyle("nn", fontSize=10, textColor=paleta["gris"],
                    alignment=TA_RIGHT)),
        ]], colWidths=[ANCHO_UTIL * 0.65, ANCHO_UTIL * 0.35])
        t.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]))
        el.append(t)
        el.append(HRFlowable(width="100%", thickness=2.5,
            color=paleta["secundario"], spaceAfter=6))

    elif disenio == 3:
        # Borde izquierdo verde
        t = Table([[
            Paragraph(f"<b>{nombre}</b>",
                ParagraphStyle("hn", fontSize=13, fontName="Helvetica-Bold",
                    textColor=paleta["primario"])),
            Paragraph(f"Nit #{nit}",
                ParagraphStyle("nn", fontSize=10, textColor=paleta["gris"],
                    alignment=TA_RIGHT)),
        ]], colWidths=[ANCHO_UTIL * 0.65, ANCHO_UTIL * 0.35])
        t.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (0,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("LINEBEFORE",   (0,0), (0,-1), 4, paleta["secundario"]),
        ]))
        el.append(t)
        el.append(HRFlowable(width="100%", thickness=0.5,
            color=paleta["borde"], spaceAfter=6))

    else:
        # Diseños 4 y 5: línea gruesa de color
        t = Table([[
            Paragraph(f"<b>{nombre}</b>",
                ParagraphStyle("hn", fontSize=13, fontName="Helvetica-Bold",
                    textColor=paleta["primario"])),
            Paragraph(f"Nit #{nit}",
                ParagraphStyle("nn", fontSize=10, textColor=paleta["gris"],
                    alignment=TA_RIGHT)),
        ]], colWidths=[ANCHO_UTIL * 0.65, ANCHO_UTIL * 0.35])
        t.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]))
        el.append(t)
        el.append(HRFlowable(width="100%", thickness=2,
            color=paleta["secundario"], spaceAfter=6))

    # Sin Spacer adicional aquí — el spaceBefore=33 del título
    # ya aplica el doble espacio APA entre encabezado y título


# ── Bloque de firmas dobles ───────────────────────────────────────────────────
def _firmas_dobles(el, representante: str, empresa: str,
                   nombre_empleado: str, cedula: str, paleta: dict, estilos: dict,
                   cargo_firmante: str = "Representante Legal"):
    """
    Dos firmas lado a lado con línea separada encima de cada una.
    """
    from reportlab.platypus import KeepTogether

    bloque_rep = [
        HRFlowable(width=7*cm, thickness=0.8,
                   color=paleta["primario"], spaceAfter=5),
        Paragraph(f"<b>{representante}</b>", estilos["firma_nombre"]),
        Paragraph(cargo_firmante, estilos["firma_cargo"]),
        Paragraph(empresa, estilos["firma_cargo"]),
    ]

    # Bloque firma derecha: línea + nombre + cédula
    bloque_emp = [
        HRFlowable(width=7*cm, thickness=0.8,
                   color=paleta["primario"], spaceAfter=5),
        Paragraph(f"<b>{nombre_empleado}</b>", estilos["firma_nombre"]),
        Paragraph(f"C.C.: {cedula}", estilos["firma_cargo"]),
    ]

    # Tabla que ubica los dos bloques lado a lado
    t_firmas = Table(
        [[bloque_rep, bloque_emp]],
        colWidths=[8.5*cm, 8.5*cm],
    )
    t_firmas.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    el.append(Spacer(1, 36))
    el.append(t_firmas)


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICADO LABORAL
# ══════════════════════════════════════════════════════════════════════════════
def generar_certificado(empleado: dict, datos_empresa: dict, ruta_salida: str,
                         disenio: int = 1, usar_marca_agua: bool = False,
                         membrete_path: str = None, usar_logo_enc: bool = True):
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    logo    = datos_empresa.get("logo_path") if usar_logo_enc else None
    # Margen superior mayor si hay membrete o logo
    tiene_membrete = bool(membrete_path and Path(membrete_path).exists())
    tiene_logo     = bool(logo and Path(logo).exists())
    margen_sup = MARGEN_SUP_MEMBRETE if (tiene_membrete or tiene_logo) else MARGEN_SUP_NORMAL
    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=margen_sup,  bottomMargin=MARGEN_INF,
        leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER)
    el = []
    _encabezado(el, datos_empresa, estilos, paleta, disenio,
                membrete_path=membrete_path)
    el.append(Paragraph("CERTIFICACIÓN LABORAL", estilos["titulo"]))

    fi = fmt_fecha(empleado.get("Fecha ingreso",""))
    tipo = empleado.get("Tipo contrato","")
    contrato_t = f", bajo contrato {tipo.lower()}," if tipo else ","
    ing_var = float(empleado.get("Ingreso promedio variable", 0) or 0)
    texto_var = (f" Adicionalmente, recibe ingresos variables con un promedio mensual "
                 f"de <b>{_fmt(ing_var)}</b>.") if ing_var > 0 else ""

    # Fecha de expedición del documento
    fecha_expedicion = datetime.today().strftime("%d de %B de %Y").replace(
        "January","enero").replace("February","febrero").replace("March","marzo"
        ).replace("April","abril").replace("May","mayo").replace("June","junio"
        ).replace("July","julio").replace("August","agosto").replace("September","septiembre"
        ).replace("October","octubre").replace("November","noviembre").replace("December","diciembre")

    el.append(Paragraph(
        f"La empresa <b>{datos_empresa.get('nombre','')}</b>, identificada con NIT "
        f"<b>{datos_empresa.get('nit','')}</b>, certifica que "
        f"<b>{empleado.get('Nombre','')}</b>, identificado(a) con cédula No. "
        f"<b>{empleado.get('Documento','')}</b>, labora en la compañía desde el "
        f"<b>{fi}</b>{contrato_t} desempeñando el cargo de "
        f"<b>{empleado.get('Cargo','')}</b>, con un salario mensual de "
        f"<b>{_fmt(empleado.get('Salario',0))}</b>.{texto_var}",
        estilos["cuerpo"]))
    el.append(Paragraph(
        f"Se expide la presente certificación a solicitud del interesado(a), "
        f"el día <b>{fecha_expedicion}</b>, para los fines que estime pertinentes.",
        estilos["cuerpo"]))
    el.append(Spacer(1, 33))   # doble espacio APA antes de "Cordialmente"
    el.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    el.append(Spacer(1, 49))   # triple espacio para área de firma (≈3 líneas)
    # Línea alineada a la izquierda, del mismo ancho que el nombre del representante
    t_firma_cert = Table(
        [["", ""]],
        colWidths=[8*cm, 9*cm],
    )
    t_firma_cert.setStyle(TableStyle([
        ("LINEABOVE",     (0,0), (0,0), 0.8, paleta["primario"]),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    el.append(t_firma_cert)
    el.append(Paragraph(datos_empresa.get("representante",""), estilos["firma_nombre"]))
    el.append(Paragraph(
        f"{datos_empresa.get('_cargo_firmante','Representante Legal')} — {datos_empresa.get('nombre','')}",
        estilos["firma_cargo"]))
    el.append(Paragraph(
        "Documento generado automáticamente. Verifique los datos antes del uso oficial.",
        estilos["nota"]))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


# ══════════════════════════════════════════════════════════════════════════════
# CARTA DE VACACIONES
# ══════════════════════════════════════════════════════════════════════════════
def generar_vacaciones(empleado: dict, datos_empresa: dict, ruta_salida: str,
                        fecha_inicio: str, fecha_fin: str, disenio: int = 1,
                        usar_marca_agua: bool = False, membrete_path: str = None,
                        usar_logo_enc: bool = True):
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    logo    = datos_empresa.get("logo_path") if usar_logo_enc else None
    tiene_membrete = bool(membrete_path and Path(membrete_path).exists())
    tiene_logo     = bool(logo and Path(logo).exists())
    margen_sup = MARGEN_SUP_MEMBRETE if (tiene_membrete or tiene_logo) else MARGEN_SUP_NORMAL
    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=margen_sup,  bottomMargin=MARGEN_INF,
        leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER)
    el = []
    _encabezado(el, datos_empresa, estilos, paleta, disenio,
                membrete_path=membrete_path)
    el.append(Paragraph("CARTA DE VACACIONES", estilos["titulo"]))

    fecha_expedicion = datetime.today().strftime("%d de %B de %Y").replace(
        "January","enero").replace("February","febrero").replace("March","marzo"
        ).replace("April","abril").replace("May","mayo").replace("June","junio"
        ).replace("July","julio").replace("August","agosto").replace("September","septiembre"
        ).replace("October","octubre").replace("November","noviembre").replace("December","diciembre")

    el.append(Paragraph(
        f"Señor(a) <b>{empleado.get('Nombre','')}</b>:", estilos["cuerpo"]))
    el.append(Paragraph(
        f"Por medio de la presente se le informa que disfrutará su período de "
        f"vacaciones desde el <b>{fecha_inicio}</b> hasta el <b>{fecha_fin}</b>, "
        f"de acuerdo con lo establecido en el Art. 186 del Código Sustantivo del Trabajo.",
        estilos["cuerpo"]))
    el.append(Paragraph(
        "Le solicitamos entregar sus responsabilidades antes de iniciar el período "
        "de descanso. Para cualquier inquietud, comuníquese con el área administrativa.",
        estilos["cuerpo"]))
    el.append(Paragraph(
        f"La presente carta se expide el día <b>{fecha_expedicion}</b>.",
        estilos["cuerpo"]))
    el.append(Spacer(1, 32))
    el.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    el.append(Spacer(1, 28))
    t_firma_vac = Table(
        [["", ""]],
        colWidths=[8*cm, 9*cm],
    )
    t_firma_vac.setStyle(TableStyle([
        ("LINEABOVE",     (0,0), (0,0), 0.8, paleta["primario"]),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    el.append(t_firma_vac)
    el.append(Paragraph(datos_empresa.get("representante",""), estilos["firma_nombre"]))
    el.append(Paragraph(
        f"{datos_empresa.get('_cargo_firmante','Representante Legal')} — {datos_empresa.get('nombre','')}",
        estilos["firma_cargo"]))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


# ══════════════════════════════════════════════════════════════════════════════
# LIQUIDACIÓN — con FIRMA DOBLE (representante legal + empleado)
# ══════════════════════════════════════════════════════════════════════════════
def generar_liquidacion(resultado: dict, datos_empresa: dict, ruta_salida: str,
                         disenio: int = 1, usar_marca_agua: bool = False,
                         membrete_path: str = None, firma_empleado: bool = True,
                         usar_logo_enc: bool = True):
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    logo    = datos_empresa.get("logo_path") if usar_logo_enc else None
    tiene_membrete = bool(membrete_path and Path(membrete_path).exists())
    tiene_logo     = bool(logo and Path(logo).exists())
    margen_sup = MARGEN_SUP_MEMBRETE if (tiene_membrete or tiene_logo) else MARGEN_SUP_NORMAL
    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=margen_sup,  bottomMargin=MARGEN_INF,
        leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER)
    el = []
    _encabezado(el, datos_empresa, estilos, paleta, disenio,
                membrete_path=membrete_path)
    el.append(Paragraph("LIQUIDACION DE PRESTACIONES SOCIALES", estilos["titulo"]))

    salario     = float(resultado.get("Salario base", 0))
    auxilio_si  = resultado.get("Auxilio transporte incluido","No") == "Sí"
    auxilio_val = AUXILIO_TRANSPORTE_2026 if auxilio_si else 0
    dias_total  = resultado.get("Dias totales (base 360)", 0)
    dias_semi   = resultado.get("Dias semestre actual (prima)", 0)
    cesantias   = resultado.get("Cesantias (Art. 249 CST)", 0)
    intereses   = resultado.get("Intereses cesantias 12% (Ley 52/75)", 0)
    vacaciones  = resultado.get("Vacaciones (Art. 186 CST)", 0)
    prima       = resultado.get("Prima semestral (Art. 306 CST)", 0)
    sal_pend    = resultado.get("Salario pendiente (estimado)", 0)
    indem       = resultado.get("Indemnizacion (Art. 64 CST)", 0)
    total_liq   = resultado.get("TOTAL LIQUIDACION ESTIMADA", 0)
    eps_val     = round(salario * 0.04, 2)
    pension_val = round(salario * 0.04, 2)
    total_desc  = round(eps_val + pension_val, 2)
    total_neto  = round(total_liq - total_desc, 2)

    # Datos empleado
    t_emp = Table([
        ["Apellidos y Nombre", resultado.get("Nombre","")],
        ["Cédula No.",         resultado.get("Documento","")],
        ["Cuenta Bancaria",    resultado.get("Cuenta bancaria","")],
        ["Causa Liquidación",  _causa_retiro(resultado.get("Motivo retiro","renuncia"))],
        ["Fecha de Retiro",    fmt_fecha(resultado.get("Fecha corte",""))],
        ["Fecha de Ingreso",   fmt_fecha(resultado.get("Fecha ingreso",""))],
        ["Total días a liquidar", str(dias_total)],
    ], colWidths=[5*cm, 11.5*cm])
    t_emp.setStyle(TableStyle([
        ("FONTNAME", (0,0),(0,-1),"Helvetica-Bold"),
        ("FONTSIZE", (0,0),(-1,-1),9),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("GRID",(0,0),(-1,-1),0.5,paleta["borde"]),
        ("BACKGROUND",(0,0),(0,-1),paleta["acento"]),
        ("TEXTCOLOR",(0,0),(0,-1),paleta["primario"]),
    ]))
    el.append(t_emp); el.append(Spacer(1,8))

    # Sueldo
    t_s = Table([
        ["SUELDO MENSUAL","",_fmt(salario)],
        ["Auxilio de transporte","",_fmt(auxilio_val) if auxilio_si else "No aplica"],
        ["Base prestacional","",_fmt(salario+auxilio_val) if auxilio_si else _fmt(salario)],
    ], colWidths=[10*cm,1*cm,5.5*cm])
    t_s.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,0),"Helvetica-Bold"),("FONTNAME",(0,2),(-1,2),"Helvetica-Bold"),
        ("BACKGROUND",(0,2),(-1,2),paleta["acento"]),
        ("FONTSIZE",(0,0),(-1,-1),9),("ALIGN",(2,0),(2,-1),"RIGHT"),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("GRID",(0,0),(-1,-1),0.5,paleta["borde"]),
    ]))
    el.append(t_s); el.append(Spacer(1,8))

    # Prestaciones
    filas = [["Concepto","Días","Valor"],
        [f"Cesantías (8.33%)",str(dias_total),_fmt(cesantias)],
        ["Intereses Cesantías (12% anual)",str(dias_total),_fmt(intereses)],
        ["Vacaciones (4.17%)",str(dias_total),_fmt(vacaciones)],
        [f"Prima de Servicios (8.33% — {dias_semi} días)",str(dias_semi),_fmt(prima)],
        ["Salario pendiente del período","–",_fmt(sal_pend)],
    ]
    if indem > 0:
        filas.append(["Indemnización (Art. 64 CST)","–",_fmt(indem)])
    filas.append(["TOTAL LIQUIDACIÓN","",_fmt(total_liq)])

    t_p = Table(filas, colWidths=[10*cm,2*cm,4.5*cm])
    t_p.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),paleta["primario"]),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("BACKGROUND",(0,-1),(-1,-1),paleta["acento"]),
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,-1),(-1,-1),paleta["primario"]),
        ("FONTSIZE",(0,0),(-1,-1),9),("ALIGN",(1,0),(2,-1),"RIGHT"),
        ("GRID",(0,0),(-1,-1),0.5,paleta["borde"]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    el.append(t_p); el.append(Spacer(1,8))

    # Descuentos
    t_d = Table([
        ["Menos:","",""],
        ["EPS (4%)","4%",_fmt(eps_val)],
        ["Pensión (4%)","4%",_fmt(pension_val)],
        ["TOTAL DESCUENTOS SEGURIDAD SOCIAL","",_fmt(total_desc)],
        ["LIQUIDACIÓN NETA A PAGAR","",_fmt(total_neto)],
    ], colWidths=[10*cm,2*cm,4.5*cm])
    t_d.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,0),"Helvetica-Bold"),
        ("FONTNAME",(0,3),(-1,4),"Helvetica-Bold"),
        ("BACKGROUND",(0,4),(-1,4),paleta["secundario"]),
        ("TEXTCOLOR",(0,4),(-1,4),colors.white),
        ("FONTSIZE",(0,0),(-1,-1),9),("ALIGN",(1,0),(2,-1),"RIGHT"),
        ("GRID",(0,0),(-1,-1),0.5,paleta["borde"]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    el.append(t_d); el.append(Spacer(1,10))

    # Paz y salvo
    letras = numero_a_letras(total_neto)
    empresa  = datos_empresa.get("nombre","")
    nit      = datos_empresa.get("nit","")
    nombre_e = resultado.get("Nombre","")
    cedula_e = resultado.get("Documento","")

    el.append(Paragraph(
        f"La suma de: <b>{letras} M/Cte {_fmt(total_neto)}</b>",
        estilos["paz_salvo"]))
    el.append(Spacer(1,6))
    el.append(Paragraph(
        f"Declaro que a la Fecha la Empresa <b>{empresa}</b> con Nit#<b>{nit}</b>, "
        f"queda a <b>PAZ y SALVO</b> por concepto de <b>PRESTACIONES SOCIALES</b>.",
        estilos["paz_salvo"]))

    # ── FIRMAS DOBLES: línea encima, luego info ───────────────────────────
    _firmas_dobles(el,
        representante=datos_empresa.get("representante",""),
        empresa=empresa,
        nombre_empleado=nombre_e,
        cedula=cedula_e,
        paleta=paleta,
        estilos=estilos,
        cargo_firmante=datos_empresa.get("_cargo_firmante","Representante Legal"))

    el.append(Paragraph(
        "<b>Aviso:</b> Liquidación ESTIMADA (base 360 días). No incluye mora en "
        "cesantías, embargos ni casos especiales. Valide con su contador.",
        estilos["nota"]))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


def nombre_disenio(d: int) -> str:
    return PALETAS.get(d, PALETAS[1])["nombre"]


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICADO LABORAL SIN SALARIO
# ══════════════════════════════════════════════════════════════════════════════
def generar_certificado_sin_salario(empleado: dict, datos_empresa: dict,
                                     ruta_salida: str, disenio: int = 1,
                                     usar_marca_agua: bool = False,
                                     membrete_path: str = None,
                                     usar_logo_enc: bool = True):
    """
    Certificado laboral que NO incluye el valor del salario.
    Útil cuando el empleado solicita certificado solo para verificar cargo y tiempo.
    """
    from utils.fecha_utils import fmt_fecha, fecha_hoy_larga
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    logo    = datos_empresa.get("logo_path") if usar_logo_enc else None
    tiene_logo     = bool(logo and Path(logo).exists())
    tiene_membrete = bool(membrete_path and Path(membrete_path).exists())
    margen_sup = MARGEN_SUP_MEMBRETE if (tiene_logo or tiene_membrete) else MARGEN_SUP_NORMAL

    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=margen_sup, bottomMargin=MARGEN_INF,
        leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER)
    el = []
    _encabezado(el, datos_empresa, estilos, paleta, disenio,
                membrete_path=membrete_path)
    el.append(Paragraph("CERTIFICACIÓN LABORAL", estilos["titulo"]))

    fi   = fmt_fecha(empleado.get("Fecha ingreso",""))
    tipo = empleado.get("Tipo contrato","")
    contrato_t = f", bajo contrato {tipo.lower()}," if tipo else ","
    fecha_expedicion = fecha_hoy_larga()

    el.append(Paragraph(
        f"La empresa <b>{datos_empresa.get('nombre','')}</b>, identificada con NIT "
        f"<b>{datos_empresa.get('nit','')}</b>, certifica que "
        f"<b>{empleado.get('Nombre','')}</b>, identificado(a) con cédula No. "
        f"<b>{empleado.get('Documento','')}</b>, labora en la compañía desde el "
        f"<b>{fi}</b>{contrato_t} desempeñando el cargo de "
        f"<b>{empleado.get('Cargo','')}</b>.",
        estilos["cuerpo"]))
    el.append(Paragraph(
        f"Se expide la presente certificación a solicitud del interesado(a), "
        f"el día <b>{fecha_expedicion}</b>, para los fines que estime pertinentes.",
        estilos["cuerpo"]))

    el.append(Spacer(1, 33))
    el.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    el.append(Spacer(1, 49))
    t_firma = Table([["", ""]], colWidths=[8*cm, 9*cm])
    t_firma.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (0,0), 0.8, paleta["primario"]),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))
    el.append(t_firma)
    el.append(Paragraph(datos_empresa.get("representante",""), estilos["firma_nombre"]))
    el.append(Paragraph(
        f"{datos_empresa.get('_cargo_firmante','Representante Legal')} — "
        f"{datos_empresa.get('nombre','')}",
        estilos["firma_cargo"]))
    el.append(Paragraph(
        "Documento generado automáticamente. Verifique los datos antes del uso oficial.",
        estilos["nota"]))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


# ══════════════════════════════════════════════════════════════════════════════
# PAZ Y SALVO LABORAL
# ══════════════════════════════════════════════════════════════════════════════
def generar_paz_salvo(empleado: dict, datos_empresa: dict,
                       ruta_salida: str, disenio: int = 1,
                       usar_marca_agua: bool = False,
                       membrete_path: str = None,
                       usar_logo_enc: bool = True,
                       conceptos_pendientes: str = "",
                       observaciones: str = ""):
    """
    Paz y salvo laboral — certifica que el empleado no tiene pendientes con la empresa.
    """
    from utils.fecha_utils import fmt_fecha, fecha_hoy_larga
    from utils.numero_letras import numero_a_letras
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    logo    = datos_empresa.get("logo_path") if usar_logo_enc else None
    tiene_logo     = bool(logo and Path(logo).exists())
    tiene_membrete = bool(membrete_path and Path(membrete_path).exists())
    margen_sup = MARGEN_SUP_MEMBRETE if (tiene_logo or tiene_membrete) else MARGEN_SUP_NORMAL

    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=margen_sup, bottomMargin=MARGEN_INF,
        leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER)
    el = []
    _encabezado(el, datos_empresa, estilos, paleta, disenio,
                membrete_path=membrete_path)
    el.append(Paragraph("PAZ Y SALVO LABORAL", estilos["titulo"]))

    fi   = fmt_fecha(empleado.get("Fecha ingreso",""))
    fr   = fmt_fecha(empleado.get("Fecha retiro","") or empleado.get("fecha_retiro",""))
    fecha_expedicion = fecha_hoy_larga()
    nombre  = empleado.get("Nombre","")
    doc_emp = empleado.get("Documento","")
    cargo   = empleado.get("Cargo","")
    empresa = datos_empresa.get("nombre","")
    nit     = datos_empresa.get("nit","")

    # Texto principal
    pendientes_txt = (
        f"Al momento de su retiro, el trabajador presenta los siguientes conceptos "
        f"pendientes: {conceptos_pendientes}."
        if conceptos_pendientes else
        "Al momento de su retiro, el trabajador no presenta pendientes de ningún "
        "tipo con la empresa."
    )

    el.append(Paragraph(
        f"La empresa <b>{empresa}</b>, identificada con NIT <b>{nit}</b>, hace "
        f"constar que <b>{nombre}</b>, identificado(a) con cédula No. "
        f"<b>{doc_emp}</b>, quien se desempeñó como <b>{cargo}</b> desde el "
        f"<b>{fi}</b>{f' hasta el <b>{fr}</b>' if fr else ''}, "
        f"se encuentra <b>A PAZ Y SALVO</b> con la empresa por los siguientes conceptos:",
        estilos["cuerpo"]))

    # Tabla de conceptos
    conceptos = [
        ["Concepto", "Estado"],
        ["Devolución de elementos, equipos y dotación", "✓ Sin pendientes"],
        ["Entrega de documentos y archivos a cargo", "✓ Sin pendientes"],
        ["Cartera, anticipos o préstamos de nómina", "✓ Sin pendientes"],
        ["Obligaciones laborales y contractuales", "✓ Sin pendientes"],
        ["Otros conceptos", "✓ Sin pendientes"],
    ]
    t_conceptos = Table(conceptos, colWidths=[10*cm, 6.5*cm])
    t_conceptos.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  paleta["primario"]),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("BACKGROUND",    (0,1), (-1,-1), paleta["acento"]),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("GRID",          (0,0), (-1,-1), 0.5, paleta["borde"]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("ALIGN",         (1,0), (1,-1),  "CENTER"),
    ]))
    el.append(Spacer(1, 8))
    el.append(t_conceptos)

    if observaciones:
        el.append(Spacer(1, 8))
        el.append(Paragraph(f"<b>Observaciones:</b> {observaciones}", estilos["cuerpo"]))

    el.append(Spacer(1, 16))
    el.append(Paragraph(
        f"Se expide el presente paz y salvo el día <b>{fecha_expedicion}</b>, "
        f"para los fines que estime pertinentes.",
        estilos["cuerpo"]))

    # Firmas dobles — empresa y empleado
    _firmas_dobles(el,
        representante=datos_empresa.get("representante",""),
        empresa=empresa,
        nombre_empleado=nombre,
        cedula=doc_emp,
        paleta=paleta,
        estilos=estilos,
        cargo_firmante=datos_empresa.get("_cargo_firmante","Representante Legal"))

    el.append(Paragraph(
        "<b>Aviso:</b> Este documento no libera al trabajador de obligaciones "
        "no declaradas al momento del retiro. Conserve copia de este documento.",
        estilos["nota"]))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)
