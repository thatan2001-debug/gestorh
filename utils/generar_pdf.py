"""
Generación de documentos PDF: certificados laborales, cartas de vacaciones
y reportes de liquidación. Usa reportlab directamente (sin LibreOffice).
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)
from pathlib import Path
from datetime import datetime
import locale

AZUL = colors.HexColor("#1F3B73")
GRIS = colors.HexColor("#555555")
GRIS_CLARO = colors.HexColor("#F2F4F7")


def _formato_moneda(valor):
    try:
        return f"${float(valor):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(valor)


def _estilos():
    base = getSampleStyleSheet()
    estilos = {
        "titulo_empresa": ParagraphStyle(
            "titulo_empresa", parent=base["Heading1"], fontSize=14, textColor=AZUL,
            spaceAfter=2, fontName="Helvetica-Bold",
        ),
        "subtitulo_empresa": ParagraphStyle(
            "subtitulo_empresa", parent=base["Normal"], fontSize=9, textColor=GRIS,
            spaceAfter=14,
        ),
        "titulo_doc": ParagraphStyle(
            "titulo_doc", parent=base["Heading2"], fontSize=13, alignment=TA_CENTER,
            textColor=AZUL, spaceBefore=10, spaceAfter=18, fontName="Helvetica-Bold",
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=base["Normal"], fontSize=11, leading=17,
            alignment=TA_JUSTIFY, spaceAfter=12,
        ),
        "firma_nombre": ParagraphStyle(
            "firma_nombre", parent=base["Normal"], fontSize=11, fontName="Helvetica-Bold",
        ),
        "firma_cargo": ParagraphStyle(
            "firma_cargo", parent=base["Normal"], fontSize=10, textColor=GRIS,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontSize=8, textColor=GRIS, alignment=TA_CENTER,
        ),
        "nota": ParagraphStyle(
            "nota", parent=base["Normal"], fontSize=8, textColor=GRIS, alignment=TA_JUSTIFY,
            spaceBefore=16,
        ),
    }
    return estilos


def _encabezado(elementos, datos_empresa, estilos):
    logo_path = datos_empresa.get("logo_path")
    if logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path, width=3.2 * cm, height=3.2 * cm)
            img.hAlign = "LEFT"
            elementos.append(img)
            elementos.append(Spacer(1, 6))
        except Exception:
            pass

    elementos.append(Paragraph(datos_empresa.get("nombre", "Empresa"), estilos["titulo_empresa"]))
    nit = datos_empresa.get("nit", "")
    if nit:
        elementos.append(Paragraph(f"NIT: {nit}", estilos["subtitulo_empresa"]))
    elementos.append(HRFlowable(width="100%", thickness=1.2, color=AZUL, spaceAfter=14))


def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DDDDDD"))
    canvas.line(2 * cm, 1.6 * cm, letter[0] - 2 * cm, 1.6 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRIS)
    fecha_gen = datetime.today().strftime("%d/%m/%Y")
    canvas.drawString(2 * cm, 1.2 * cm, f"Generado automáticamente el {fecha_gen} — RH Fácil")
    canvas.drawRightString(letter[0] - 2 * cm, 1.2 * cm, "Página 1")
    canvas.restoreState()


def generar_certificado_laboral(empleado: dict, datos_empresa: dict, ruta_salida: str):
    """
    empleado: dict con Nombre, Documento, Cargo, Salario, Fecha ingreso, Tipo contrato
    datos_empresa: dict con nombre, nit, representante, logo_path (opcional)
    """
    estilos = _estilos()
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2.2 * cm, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    elementos = []
    _encabezado(elementos, datos_empresa, estilos)
    elementos.append(Paragraph("CERTIFICACIÓN LABORAL", estilos["titulo_doc"]))

    fecha_ingreso = empleado.get("Fecha ingreso", "")
    if hasattr(fecha_ingreso, "strftime"):
        fecha_ingreso = fecha_ingreso.strftime("%d/%m/%Y")

    salario_fmt = _formato_moneda(empleado.get("Salario", 0))
    tipo_contrato = empleado.get("Tipo contrato", "")
    cargo = empleado.get("Cargo", "")
    nombre = empleado.get("Nombre", "")
    documento = empleado.get("Documento", "")

    texto_contrato = f", bajo un contrato de tipo {tipo_contrato.lower()}," if tipo_contrato else ","

    cuerpo = (
        f"La empresa <b>{datos_empresa.get('nombre', '')}</b>, identificada con NIT "
        f"<b>{datos_empresa.get('nit', '')}</b>, certifica que <b>{nombre}</b>, "
        f"identificado(a) con cédula de ciudadanía No. <b>{documento}</b>, labora actualmente "
        f"en la compañía desde el <b>{fecha_ingreso}</b>{texto_contrato} desempeñando el cargo de "
        f"<b>{cargo}</b>, con un salario mensual de <b>{salario_fmt}</b>."
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
    elementos.append(Paragraph(f"Representante - {datos_empresa.get('nombre', '')}", estilos["firma_cargo"]))

    elementos.append(Paragraph(
        "Este documento fue generado automáticamente y no requiere firma manuscrita para su validez interna. "
        "Verifique los datos antes de su uso oficial.",
        estilos["nota"],
    ))

    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)


def generar_carta_vacaciones(empleado: dict, datos_empresa: dict, ruta_salida: str,
                              fecha_inicio: str, fecha_fin: str):
    estilos = _estilos()
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2.2 * cm, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    elementos = []
    _encabezado(elementos, datos_empresa, estilos)
    elementos.append(Paragraph("CARTA DE VACACIONES", estilos["titulo_doc"]))

    nombre = empleado.get("Nombre", "")
    elementos.append(Paragraph(f"Señor(a) <b>{nombre}</b>:", estilos["cuerpo"]))
    elementos.append(Paragraph(
        f"Por medio de la presente se le informa que disfrutará su periodo de vacaciones "
        f"desde el <b>{fecha_inicio}</b> hasta el <b>{fecha_fin}</b>, de acuerdo con lo "
        f"establecido por la compañía y la normatividad laboral vigente.",
        estilos["cuerpo"],
    ))
    elementos.append(Paragraph(
        "Le solicitamos dejar sus pendientes debidamente entregados antes de iniciar su "
        "periodo de descanso. Cualquier inquietud, no dude en comunicarse con el área "
        "administrativa.",
        estilos["cuerpo"],
    ))

    elementos.append(Spacer(1, 40))
    elementos.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    elementos.append(Spacer(1, 30))
    elementos.append(Paragraph(datos_empresa.get("representante", ""), estilos["firma_nombre"]))
    elementos.append(Paragraph(f"Representante - {datos_empresa.get('nombre', '')}", estilos["firma_cargo"]))

    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)


def generar_pdf_liquidacion(resultado: dict, datos_empresa: dict, ruta_salida: str):
    """resultado: una fila (dict) producida por calcular_liquidacion_fila()."""
    estilos = _estilos()
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2.2 * cm, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    elementos = []
    _encabezado(elementos, datos_empresa, estilos)
    elementos.append(Paragraph("LIQUIDACIÓN BÁSICA ESTIMADA", estilos["titulo_doc"]))

    elementos.append(Paragraph(
        f"Empleado: <b>{resultado['Nombre']}</b> &nbsp;&nbsp; Cédula: <b>{resultado['Documento']}</b>",
        estilos["cuerpo"],
    ))
    elementos.append(Paragraph(
        f"Cargo: {resultado['Cargo']} &nbsp;&nbsp; Periodo liquidado: "
        f"{resultado['Fecha ingreso']} a {resultado['Fecha corte']} "
        f"({resultado['Dias trabajados (360)']} días, base 360)",
        estilos["cuerpo"],
    ))

    filas = [
        ["Concepto", "Valor"],
        ["Salario base", _formato_moneda(resultado["Salario"])],
        ["Auxilio de transporte aplica", resultado["Auxilio transporte aplica"]],
        ["Cesantías", _formato_moneda(resultado["Cesantias"])],
        ["Intereses sobre cesantías (12%)", _formato_moneda(resultado["Intereses cesantias"])],
        ["Prima de servicios", _formato_moneda(resultado["Prima"])],
        ["Vacaciones", _formato_moneda(resultado["Vacaciones"])],
        ["TOTAL ESTIMADO", _formato_moneda(resultado["Total liquidacion"])],
    ]
    tabla = Table(filas, colWidths=[10 * cm, 6 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), GRIS_CLARO),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elementos.append(Spacer(1, 10))
    elementos.append(tabla)

    elementos.append(Paragraph(
        "<b>Aviso importante:</b> esta es una liquidación ESTIMADA con fórmulas básicas "
        "(cesantías, intereses de cesantías, prima y vacaciones sobre año comercial de 360 días). "
        "No incluye salario integral, incapacidades, embargos, sanciones moratorias ni casos "
        "especiales. Debe ser validada por un contador o abogado laboral antes de cualquier pago "
        "o uso oficial. Puede contrastarla con la calculadora del Ministerio del Trabajo.",
        estilos["nota"],
    ))

    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
