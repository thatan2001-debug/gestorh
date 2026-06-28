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
MARGEN_SUP_NORMAL   = 3.0 * cm
MARGEN_SUP_MEMBRETE = 4.0 * cm   # cuando hay membrete/logo grande
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
            textColor=paleta["primario"], spaceBefore=8, spaceAfter=14),
        "cuerpo": ParagraphStyle("cuerpo", parent=base["Normal"],
            fontSize=11, leading=16.5,           # 11pt × 1.5 = 16.5pt interlineado
            alignment=TA_JUSTIFY, spaceAfter=11,
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
    setFillAlpha de ReportLab NO afecta imágenes rasterizadas — hay que
    modificar el canal alpha directamente con PIL.
    Cachea el resultado en assets/ para no regenerarlo en cada llamada.
    """
    try:
        from PIL import Image as PILImage
        Path("assets").mkdir(exist_ok=True)
        cache = str(Path("assets") / f"logo_enc_{int(opacidad*100)}.png")
        # Usar caché si ya existe y el logo no cambió
        if Path(cache).exists():
            return cache
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
def _encabezado(el, datos_empresa, estilos, paleta, disenio,
                logo_derecha: bool = True, membrete_path: str = None):
    """
    Encabezado: Nombre+NIT a la izquierda.
    El logo se reserva como espacio vacío — lo dibuja el canvas con opacidad 45%
    para lograr el efecto de membrete suave.
    """
    nombre = datos_empresa.get("nombre", "")
    nit    = datos_empresa.get("nit", "")
    logo   = datos_empresa.get("logo_path")

    # ── Membrete personalizado desde Word ────────────────────────────────
    if membrete_path and Path(membrete_path).exists():
        try:
            img_elem = Image(membrete_path, width=17*cm, height=3.5*cm)
            img_elem.hAlign = "CENTER"
            el.append(img_elem)
            el.append(HRFlowable(width="100%", thickness=1,
                color=paleta["primario"], spaceAfter=10))
            return
        except Exception:
            pass

    col_logo_w  = 4.5*cm
    col_texto_w = ANCHO_UTIL - col_logo_w
    # Celda derecha vacía — el canvas dibujará el logo ahí semitransparente
    celda_logo = Paragraph("", ParagraphStyle("vacio"))

    texto_izq = [
        Paragraph(f"<b>{nombre}</b>",
            ParagraphStyle("hn", fontSize=13, fontName="Helvetica-Bold",
                textColor=paleta["primario"])),
        Paragraph(f"Nit #{nit}",
            ParagraphStyle("nn", fontSize=9, textColor=paleta["gris"])),
    ]

    fila = [[texto_izq, celda_logo]]
    t = Table(fila, colWidths=[col_texto_w, col_logo_w])
    t.setStyle(TableStyle([
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        # Reservar altura mínima para el logo (2.8cm = ~79pt)
        ("MINROWHEIGHT", (0,0), (-1,-1), 2.8*cm),
    ]))

    if disenio == 1:
        # Fondo azul — texto en blanco
        texto_blanco = [
            Paragraph(f"<b><font color='white'>{nombre}</font></b>",
                ParagraphStyle("hb", fontSize=13, fontName="Helvetica-Bold",
                    textColor=colors.white)),
            Paragraph(f"<font color='white'>Nit #{nit}</font>",
                ParagraphStyle("nb", fontSize=9, textColor=colors.white)),
        ]
        t_b = Table([[texto_blanco, celda_logo]],
                    colWidths=[col_texto_w, col_logo_w])
        t_b.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 0),
            ("BOTTOMPADDING",(0,0), (-1,-1), 0),
            ("MINROWHEIGHT", (0,0), (-1,-1), 2.8*cm),
        ]))
        wrapper = Table([[t_b]], colWidths=[17*cm])
        wrapper.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), paleta["primario"]),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ]))
        el.append(wrapper)
        el.append(Spacer(1, 8))
    elif disenio in (4, 5):
        el.append(t)
        el.append(HRFlowable(width="100%", thickness=2,
            color=paleta["secundario"], spaceAfter=8))
    else:
        el.append(t)
        el.append(HRFlowable(width="100%", thickness=1.5,
            color=paleta["primario"], spaceAfter=8))


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

    fi = empleado.get("Fecha ingreso","")
    if hasattr(fi,"strftime"): fi = fi.strftime("%d/%m/%Y")
    tipo = empleado.get("Tipo contrato","")
    contrato_t = f", bajo contrato {tipo.lower()}," if tipo else ","
    ing_var = float(empleado.get("Ingreso promedio variable", 0) or 0)
    texto_var = (f" Adicionalmente, recibe ingresos variables con un promedio mensual "
                 f"de <b>{_fmt(ing_var)}</b>.") if ing_var > 0 else ""

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
        "Se expide a solicitud del interesado(a) para los fines que estime pertinentes.",
        estilos["cuerpo"]))
    el.append(Spacer(1, 32))
    el.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    el.append(Spacer(1, 28))
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
        ["Fecha de Retiro",    resultado.get("Fecha corte","")],
        ["Fecha de Ingreso",   resultado.get("Fecha ingreso","")],
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
