"""
Generación de documentos PDF: certificados laborales, cartas de vacaciones
y liquidaciones de prestaciones sociales. Usa reportlab directamente.
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
from pathlib import Path
from datetime import datetime

# ── Paleta ──────────────────────────────────────────────────────────────────
AZUL       = colors.HexColor("#1B3F6E")
AZUL_CLARO = colors.HexColor("#2D6BE4")
GRIS       = colors.HexColor("#555555")
GRIS_CLARO = colors.HexColor("#F2F4F7")
GRIS_BORDE = colors.HexColor("#DDDDDD")
NEGRO      = colors.HexColor("#111827")
VERDE      = colors.HexColor("#065F46")
VERDE_BG   = colors.HexColor("#D1FAE5")


def _fmt(valor):
    """Formatea número como moneda colombiana."""
    try:
        return f"$ {float(valor):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(valor)


def _estilos():
    base = getSampleStyleSheet()
    return {
        "empresa": ParagraphStyle(
            "empresa", parent=base["Normal"], fontSize=13,
            fontName="Helvetica-Bold", textColor=AZUL, spaceAfter=1,
        ),
        "nit": ParagraphStyle(
            "nit", parent=base["Normal"], fontSize=9,
            textColor=GRIS, spaceAfter=10,
        ),
        "titulo_doc": ParagraphStyle(
            "titulo_doc", parent=base["Normal"], fontSize=13,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
            textColor=AZUL, spaceBefore=8, spaceAfter=14,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=base["Normal"], fontSize=10.5,
            leading=16, alignment=TA_JUSTIFY, spaceAfter=10,
        ),
        "firma_nombre": ParagraphStyle(
            "firma_nombre", parent=base["Normal"], fontSize=10.5,
            fontName="Helvetica-Bold",
        ),
        "firma_cargo": ParagraphStyle(
            "firma_cargo", parent=base["Normal"], fontSize=9.5,
            textColor=GRIS,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontSize=7.5,
            textColor=GRIS, alignment=TA_CENTER,
        ),
        "nota": ParagraphStyle(
            "nota", parent=base["Normal"], fontSize=8,
            textColor=GRIS, alignment=TA_JUSTIFY, spaceBefore=14,
        ),
        "paz_salvo": ParagraphStyle(
            "paz_salvo", parent=base["Normal"], fontSize=9.5,
            leading=14, alignment=TA_JUSTIFY, spaceAfter=10,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Normal"], fontSize=9,
            fontName="Helvetica-Bold", textColor=AZUL,
            spaceBefore=8, spaceAfter=4,
        ),
    }


def _encabezado(elementos, datos_empresa, estilos, mostrar_logo=True):
    logo_path = datos_empresa.get("logo_path")
    if mostrar_logo and logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path, width=2.8 * cm, height=2.8 * cm)
            img.hAlign = "LEFT"
            elementos.append(img)
            elementos.append(Spacer(1, 4))
        except Exception:
            pass

    nombre = datos_empresa.get("nombre", "")
    nit = datos_empresa.get("nit", "")

    # Encabezado con empresa y NIT en tabla para alinear bien
    fila_header = [
        Paragraph(f"<b>{nombre}</b>", estilos["empresa"]),
        Paragraph(f"Nit #{nit}", estilos["empresa"]),
    ]
    t = Table([fila_header], colWidths=[10 * cm, 7 * cm])
    t.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementos.append(t)
    elementos.append(HRFlowable(width="100%", thickness=1.5, color=AZUL, spaceAfter=10))


def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRIS_BORDE)
    canvas.line(2 * cm, 1.6 * cm, letter[0] - 2 * cm, 1.6 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    fecha_gen = datetime.today().strftime("%d/%m/%Y %H:%M")
    canvas.drawString(2 * cm, 1.2 * cm,
                      f"Generado automáticamente el {fecha_gen} — RH Fácil")
    canvas.drawRightString(letter[0] - 2 * cm, 1.2 * cm,
                           "Estimación de referencia. Validar con contador o abogado laboral.")
    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICADO LABORAL
# ══════════════════════════════════════════════════════════════════════════════
def generar_certificado_laboral(empleado: dict, datos_empresa: dict, ruta_salida: str):
    estilos = _estilos()
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2.2 * cm,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    elementos = []
    _encabezado(elementos, datos_empresa, estilos)
    elementos.append(Paragraph("CERTIFICACIÓN LABORAL", estilos["titulo_doc"]))

    fi = empleado.get("Fecha ingreso", "")
    if hasattr(fi, "strftime"):
        fi = fi.strftime("%d/%m/%Y")

    salario_fmt = _fmt(empleado.get("Salario", 0))
    tipo = empleado.get("Tipo contrato", "")
    texto_contrato = f", bajo contrato {tipo.lower()}," if tipo else ","

    cuerpo = (
        f"La empresa <b>{datos_empresa.get('nombre', '')}</b>, identificada con NIT "
        f"<b>{datos_empresa.get('nit', '')}</b>, certifica que <b>{empleado.get('Nombre', '')}</b>, "
        f"identificado(a) con cédula de ciudadanía No. <b>{empleado.get('Documento', '')}</b>, "
        f"labora en la compañía desde el <b>{fi}</b>{texto_contrato} "
        f"desempeñando el cargo de <b>{empleado.get('Cargo', '')}</b>, con un salario mensual "
        f"de <b>{salario_fmt}</b>."
    )
    elementos.append(Paragraph(cuerpo, estilos["cuerpo"]))
    elementos.append(Paragraph(
        "Se expide la presente certificación a solicitud del interesado(a), para los fines "
        "que estime pertinentes, en la fecha indicada al pie de este documento.",
        estilos["cuerpo"],
    ))
    elementos.append(Spacer(1, 40))
    elementos.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    elementos.append(Spacer(1, 30))
    elementos.append(Paragraph(datos_empresa.get("representante", ""), estilos["firma_nombre"]))
    elementos.append(Paragraph(
        f"Representante Legal — {datos_empresa.get('nombre', '')}",
        estilos["firma_cargo"],
    ))
    elementos.append(Paragraph(
        "Este documento fue generado automáticamente. Verifique los datos antes de su uso oficial.",
        estilos["nota"],
    ))
    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)


# ══════════════════════════════════════════════════════════════════════════════
# CARTA DE VACACIONES
# ══════════════════════════════════════════════════════════════════════════════
def generar_carta_vacaciones(empleado: dict, datos_empresa: dict, ruta_salida: str,
                              fecha_inicio: str, fecha_fin: str):
    estilos = _estilos()
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2.2 * cm,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    elementos = []
    _encabezado(elementos, datos_empresa, estilos)
    elementos.append(Paragraph("CARTA DE VACACIONES", estilos["titulo_doc"]))
    elementos.append(Paragraph(
        f"Señor(a) <b>{empleado.get('Nombre', '')}</b>:", estilos["cuerpo"]
    ))
    elementos.append(Paragraph(
        f"Por medio de la presente se le informa que disfrutará su período de vacaciones "
        f"desde el <b>{fecha_inicio}</b> hasta el <b>{fecha_fin}</b>, de acuerdo con lo "
        f"establecido por la compañía y la normatividad laboral vigente (Art. 186 CST).",
        estilos["cuerpo"],
    ))
    elementos.append(Paragraph(
        "Le solicitamos dejar sus responsabilidades debidamente entregadas antes de iniciar "
        "su período de descanso. Para cualquier inquietud, comuníquese con el área "
        "administrativa.",
        estilos["cuerpo"],
    ))
    elementos.append(Spacer(1, 40))
    elementos.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    elementos.append(Spacer(1, 30))
    elementos.append(Paragraph(datos_empresa.get("representante", ""), estilos["firma_nombre"]))
    elementos.append(Paragraph(
        f"Representante Legal — {datos_empresa.get('nombre', '')}",
        estilos["firma_cargo"],
    ))
    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)


# ══════════════════════════════════════════════════════════════════════════════
# LIQUIDACIÓN DE PRESTACIONES SOCIALES
# ══════════════════════════════════════════════════════════════════════════════
def generar_pdf_liquidacion(resultado: dict, datos_empresa: dict, ruta_salida: str):
    """
    Genera la liquidación con el formato de la plantilla oficial:
    datos empleado → tabla de prestaciones → descuentos SS → total neto → paz y salvo → firma.
    """
    estilos = _estilos()
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        topMargin=1.8 * cm, bottomMargin=2.2 * cm,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
    )
    elementos = []
    _encabezado(elementos, datos_empresa, estilos)
    elementos.append(Paragraph(
        "LIQUIDACION DE PRESTACIONES SOCIALES", estilos["titulo_doc"]
    ))

    # ── 1. Datos del empleado ──────────────────────────────────────────────
    salario = float(resultado.get("Salario base", 0))
    auxilio_aplica = resultado.get("Auxilio transporte incluido", "No") == "Sí"
    from utils.calcular_liquidacion import AUXILIO_TRANSPORTE_2026
    auxilio_val = AUXILIO_TRANSPORTE_2026 if auxilio_aplica else 0

    datos_emp = [
        ["Apellidos y Nombre", resultado.get("Nombre", "")],
        ["Cédula No.", resultado.get("Documento", "")],
        ["Cuenta Bancaria", resultado.get("Cuenta bancaria", "")],
        ["Causa Liquidación", _causa_retiro(resultado.get("Motivo retiro", "renuncia"))],
        ["Fecha de Retiro", resultado.get("Fecha corte", "")],
        ["Fecha de Ingreso", resultado.get("Fecha ingreso", "")],
        ["Total días a liquidar", str(resultado.get("Dias totales (base 360)", 0))],
    ]
    t_datos = Table(datos_emp, colWidths=[5.5 * cm, 11 * cm])
    t_datos.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("BACKGROUND", (0, 0), (0, -1), GRIS_CLARO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(t_datos)
    elementos.append(Spacer(1, 10))

    # ── 2. Sueldo mensual ─────────────────────────────────────────────────
    t_sueldo = Table([
        ["SUELDO MENSUAL", "", _fmt(salario)],
        ["Auxilio de transporte", "", _fmt(auxilio_val) if auxilio_aplica else ""],
        ["Sueldo Mensual base prestacional", "",
         _fmt(salario + auxilio_val) if auxilio_aplica else _fmt(salario)],
    ], colWidths=[10 * cm, 1 * cm, 5.5 * cm])
    t_sueldo.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (0, 2), "Helvetica-Bold"),
        ("FONTNAME", (2, 2), (2, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("BACKGROUND", (0, 2), (-1, 2), GRIS_CLARO),
        ("LINEBELOW", (0, 1), (-1, 1), 1, AZUL),
    ]))
    elementos.append(t_sueldo)
    elementos.append(Spacer(1, 10))

    # ── 3. Tabla de prestaciones ──────────────────────────────────────────
    dias_total  = resultado.get("Dias totales (base 360)", 0)
    dias_semi   = resultado.get("Dias semestre actual (prima)", 0)
    cesantias   = resultado.get("Cesantias (Art. 249 CST)", 0)
    intereses   = resultado.get("Intereses cesantias 12% (Ley 52/75)", 0)
    vacaciones  = resultado.get("Vacaciones (Art. 186 CST)", 0)
    prima       = resultado.get("Prima semestral (Art. 306 CST)", 0)
    sal_pend    = resultado.get("Salario pendiente (estimado)", 0)
    indem       = resultado.get("Indemnizacion (Art. 64 CST)", 0)
    subtotal    = resultado.get("Subtotal prestaciones", 0)
    total_liq   = resultado.get("TOTAL LIQUIDACION ESTIMADA", 0)

    filas_prest = [
        ["Concepto", "Días", "Valor"],
        [f"Cesantías (8.33% — salario ${salario:,.0f})".replace(",", "."),
         str(dias_total), _fmt(cesantias)],
        ["Intereses de Cesantías (12% anual)", str(dias_total), _fmt(intereses)],
        ["Vacaciones (4.17%)", str(dias_total), _fmt(vacaciones)],
        [f"Prima de Servicios (8.33% — semestre {dias_semi} días)",
         str(dias_semi), _fmt(prima)],
        ["Salario pendiente del período", "–", _fmt(sal_pend)],
    ]
    if indem > 0:
        filas_prest.append(
            ["Indemnización por despido sin justa causa (Art. 64 CST)",
             "–", _fmt(indem)]
        )
    filas_prest.append(["TOTAL LIQUIDACIÓN", "", _fmt(total_liq)])

    t_prest = Table(filas_prest, colWidths=[10 * cm, 2 * cm, 4.5 * cm])
    estilo_prest = [
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        # Total final
        ("BACKGROUND", (0, -1), (-1, -1), GRIS_CLARO),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        # General
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (2, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]
    t_prest.setStyle(TableStyle(estilo_prest))
    elementos.append(t_prest)
    elementos.append(Spacer(1, 10))

    # ── 4. Descuentos seguridad social ────────────────────────────────────
    eps_val     = round(salario * 0.04, 2)
    pension_val = round(salario * 0.04, 2)
    total_desc  = round(eps_val + pension_val, 2)
    total_neto  = round(total_liq - total_desc, 2)

    t_desc = Table([
        ["Menos:", "", ""],
        ["EPS (4%)", "4%", _fmt(eps_val)],
        ["Pensión (4%)", "4%", _fmt(pension_val)],
        ["TOTAL DESCUENTOS SEGURIDAD SOCIAL", "", _fmt(total_desc)],
        ["Liquidación prestaciones sociales NETA", "", _fmt(total_neto)],
    ], colWidths=[10 * cm, 2 * cm, 4.5 * cm])
    t_desc.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#E0F2FE")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (2, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(t_desc)
    elementos.append(Spacer(1, 14))

    # ── 5. Total en letras + paz y salvo ──────────────────────────────────
    from utils.numero_letras import numero_a_letras
    total_letras = numero_a_letras(total_neto)
    empresa = datos_empresa.get("nombre", "")
    nit     = datos_empresa.get("nit", "")
    nombre  = resultado.get("Nombre", "")
    cedula  = resultado.get("Documento", "")

    elementos.append(KeepTogether([
        Paragraph(
            f"La suma de: <b>{total_letras} M/Cte {_fmt(total_neto)}</b>",
            estilos["paz_salvo"],
        ),
        Spacer(1, 6),
        Paragraph(
            f"Declaro que a la Fecha la Empresa <b>{empresa}</b> con Nit#<b>{nit}</b>, "
            f"queda a <b>PAZ y SALVO</b> por concepto de <b>PRESTACIONES SOCIALES</b>.",
            estilos["paz_salvo"],
        ),
        Spacer(1, 30),
        # Línea de firma
        HRFlowable(width=7 * cm, thickness=0.8, color=NEGRO, spaceAfter=4),
        Paragraph(f"<b>Recibí</b>", estilos["firma_nombre"]),
        Paragraph(nombre, estilos["firma_nombre"]),
        Paragraph(f"C.C.: {cedula}", estilos["firma_cargo"]),
    ]))

    elementos.append(Paragraph(
        "<b>Aviso:</b> Esta es una liquidación ESTIMADA (base 360 días). No incluye: salario "
        "integral, mora en cesantías, embargos, licencias, horas extras ni casos especiales. "
        "Valide con su contador antes de realizar el pago.",
        estilos["nota"],
    ))

    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)


def _causa_retiro(motivo: str) -> str:
    mapa = {
        "renuncia": "Retiro Voluntario",
        "despido_sin_justa_causa": "Despido Sin Justa Causa",
        "mutuo_acuerdo": "Mutuo Acuerdo",
        "vencimiento_contrato": "Vencimiento de Contrato",
    }
    return mapa.get(str(motivo).strip().lower(), motivo.replace("_", " ").title())
