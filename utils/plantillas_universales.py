"""
Generador universal de documentos laborales.

Cubre 16 tipos de documentos con un patrón común:
- Cartas de comunicación (cambio salario, cargo, sede, ascenso)
- Certificados adicionales (funciones, ingresos)
- Actas de entrega (cargo, equipos, dotación)
- Autorizaciones (paz y salvo, descuento, tratamiento de datos)
- Disciplinarios (llamado atención, citación descargos)
- Permisos y licencias (remunerados, no remunerados)

Cada documento se genera con el mismo estilo visual del certificado laboral
(consistencia de marca), pero con contenido personalizado.

Uso:
    from utils.plantillas_universales import generar_documento

    ruta = generar_documento(
        tipo="carta_cambio_salario",
        empleado={"nombre": "Juan", "documento": "123", "cargo": "Analista"},
        datos_empresa={"nombre": "ACME SAS", "nit": "900...", "logo_path": "..."},
        datos_extra={"salario_anterior": 2_000_000, "salario_nuevo": 2_500_000,
                      "fecha_efectiva": "01/03/2026", "motivo": "Desempeño"},
        ruta_salida="salidas/CambioSalario.pdf",
    )
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.units import cm

from utils.plantillas_disenio import (
    PALETAS, _estilos_para as _estilos, _pie, _logo_con_opacidad,
)
from utils.numero_letras import numero_a_letras
from utils.fecha_utils import fmt_fecha_larga


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE FORMATO
# ══════════════════════════════════════════════════════════════════════════════

def _fecha_hoy_larga():
    """Retorna la fecha de hoy en formato largo español."""
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
              "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    hoy = datetime.now()
    return f"{hoy.day} de {meses[hoy.month-1]} de {hoy.year}"


def _fmt_pesos(valor: float) -> str:
    """Formatea un número como pesos colombianos."""
    try:
        return f"${float(valor):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"


def _pesos_letras(valor: float) -> str:
    """Convierte a letras: '$2.000.000 (dos millones de pesos m/cte)'."""
    try:
        v = float(valor)
        letras = numero_a_letras(int(v))
        return f"{_fmt_pesos(v)} ({letras} pesos m/cte)"
    except Exception:
        return _fmt_pesos(valor)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTOR BASE DEL DOCUMENTO
# ══════════════════════════════════════════════════════════════════════════════

def _crear_documento_base(ruta_salida: str, datos_empresa: dict, disenio: int = 1,
                            usar_marca_agua: bool = False, membrete=None,
                            usar_logo: bool = True):
    """
    Crea un SimpleDocTemplate y retorna (doc, elementos, estilos, paleta, pie_fn).

    Este es el "esqueleto" común a todos los documentos universales.
    """
    paleta = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos(paleta)

    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=3 * cm, bottomMargin=2.5 * cm,
        title="Gestor RH IA",
    )

    elementos = []
    logo_path = datos_empresa.get("logo_path") if usar_logo else None

    def pie_fn(canvas, doc_):
        _pie(canvas, doc_, paleta, logo_path, usar_marca_agua)

    return doc, elementos, estilos, paleta, pie_fn


def _agregar_encabezado(elementos, estilos, datos_empresa: dict, titulo: str,
                          consecutivo: str = None):
    """Agrega encabezado con datos de la empresa, título y fecha."""
    # Datos empresa
    elementos.append(Paragraph(
        f"<b>{datos_empresa.get('nombre', 'Empresa')}</b>",
        estilos["empresa"]
    ))
    if datos_empresa.get("nit"):
        elementos.append(Paragraph(
            f"NIT: {datos_empresa['nit']}",
            estilos["nit"]
        ))
    elementos.append(Spacer(1, 6))

    # Título
    elementos.append(Paragraph(titulo.upper(), estilos["titulo"]))

    # Ciudad y fecha
    ciudad = datos_empresa.get("ciudad", "")
    fecha_txt = _fecha_hoy_larga()
    if ciudad:
        elementos.append(Paragraph(
            f"{ciudad}, {fecha_txt}",
            estilos["cuerpo"]
        ))
    else:
        elementos.append(Paragraph(fecha_txt, estilos["cuerpo"]))

    if consecutivo:
        elementos.append(Paragraph(
            f"Consecutivo: <b>{consecutivo}</b>",
            estilos["cuerpo"]
        ))

    elementos.append(Spacer(1, 12))


def _agregar_firma(elementos, estilos, datos_empresa: dict, empleado: dict = None,
                    doble_firma: bool = False, cargo_firmante: str = None):
    """
    Agrega bloques de firma al final del documento.

    doble_firma=True agrega también línea para firma del empleado.
    """
    elementos.append(Spacer(1, 60))

    firmante_nombre = datos_empresa.get("representante", "Representante Legal")
    firmante_cargo = cargo_firmante or datos_empresa.get(
        "firmante_cert_cargo", "Representante Legal"
    )

    if not doble_firma:
        # Firma centrada del representante
        elementos.append(Paragraph(
            "_" * 45,
            estilos["cuerpo"]
        ))
        elementos.append(Paragraph(
            f"<b>{firmante_nombre}</b>",
            estilos["firma_nombre"]
        ))
        elementos.append(Paragraph(
            firmante_cargo,
            estilos["firma_cargo"]
        ))
        elementos.append(Paragraph(
            f"{datos_empresa.get('nombre', '')}",
            estilos["firma_cargo"]
        ))
    else:
        # Doble firma: empresa | empleado
        tabla_firmas = Table([
            ["_" * 30, "_" * 30],
            [f"<b>{firmante_nombre}</b>", f"<b>{empleado.get('nombre', '')}</b>"],
            [firmante_cargo, f"CC {empleado.get('documento', '')}"],
            [datos_empresa.get('nombre', ''), "Empleado"],
        ], colWidths=[7 * cm, 7 * cm])

        tabla_firmas.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elementos.append(tabla_firmas)


# ══════════════════════════════════════════════════════════════════════════════
# PLANTILLAS ESPECÍFICAS
# ══════════════════════════════════════════════════════════════════════════════

def _plantilla_cambio_salarial(elementos, estilos, empleado, datos_empresa, extra):
    """Comunicación de cambio de salario."""
    sal_ant = extra.get("salario_anterior", empleado.get("salario", 0))
    sal_nuevo = extra.get("salario_nuevo", 0)
    fecha_efectiva = extra.get("fecha_efectiva", _fecha_hoy_larga())
    motivo = extra.get("motivo", "")

    elementos.append(Paragraph(
        f"Señor(a)<br/><b>{empleado.get('nombre', '')}</b><br/>"
        f"C.C. {empleado.get('documento', '')}<br/>"
        f"Cargo: {empleado.get('cargo', '')}<br/>"
        f"E. S. D.",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(
        "Asunto: <b>Comunicación de cambio salarial</b>",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    texto = (
        f"Reciba un cordial saludo. Por medio de la presente comunicación, "
        f"le informamos que a partir del <b>{fecha_efectiva}</b>, su salario "
        f"mensual se modificará de <b>{_pesos_letras(sal_ant)}</b> a "
        f"<b>{_pesos_letras(sal_nuevo)}</b>."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    if motivo:
        elementos.append(Paragraph(
            f"<b>Motivo del cambio:</b> {motivo}",
            estilos["cuerpo"]
        ))

    elementos.append(Paragraph(
        "Las demás condiciones de su contrato de trabajo permanecen "
        "inalteradas. Agradecemos su compromiso y dedicación con la empresa.",
        estilos["cuerpo"]
    ))
    elementos.append(Paragraph(
        "Solicitamos firmar como constancia de recibido y aceptación de esta "
        "modificación salarial.",
        estilos["cuerpo"]
    ))


def _plantilla_cambio_cargo(elementos, estilos, empleado, datos_empresa, extra):
    """Comunicación de cambio de cargo (promoción o reubicación)."""
    cargo_ant = extra.get("cargo_anterior", empleado.get("cargo", ""))
    cargo_nuevo = extra.get("cargo_nuevo", "")
    fecha_efectiva = extra.get("fecha_efectiva", _fecha_hoy_larga())
    es_promocion = extra.get("es_promocion", False)

    titulo_carta = "COMUNICACIÓN DE PROMOCIÓN" if es_promocion else "COMUNICACIÓN DE CAMBIO DE CARGO"
    elementos[2] = Paragraph(titulo_carta, estilos["titulo"])  # reemplazar título

    elementos.append(Paragraph(
        f"Señor(a)<br/><b>{empleado.get('nombre', '')}</b><br/>"
        f"C.C. {empleado.get('documento', '')}<br/>E. S. D.",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    texto = (
        f"Reciba un cordial saludo. Nos complace comunicarle que, "
        f"como reconocimiento a su desempeño y compromiso, "
        f"a partir del <b>{fecha_efectiva}</b> su cargo se modificará de "
        f"<b>{cargo_ant}</b> a <b>{cargo_nuevo}</b>."
    ) if es_promocion else (
        f"Por medio de la presente le informamos que a partir del "
        f"<b>{fecha_efectiva}</b> su cargo se modificará de "
        f"<b>{cargo_ant}</b> a <b>{cargo_nuevo}</b>."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    if extra.get("nuevo_salario"):
        elementos.append(Paragraph(
            f"Su salario mensual se ajustará a <b>{_pesos_letras(extra['nuevo_salario'])}</b>.",
            estilos["cuerpo"]
        ))

    if extra.get("nuevas_funciones"):
        elementos.append(Paragraph(
            f"<b>Nuevas funciones:</b><br/>{extra['nuevas_funciones']}",
            estilos["cuerpo"]
        ))

    elementos.append(Paragraph(
        "Las demás condiciones de su contrato permanecen inalteradas. "
        "Solicitamos firmar como constancia de aceptación.",
        estilos["cuerpo"]
    ))


def _plantilla_cambio_sede(elementos, estilos, empleado, datos_empresa, extra):
    """Comunicación de cambio de sede o traslado."""
    sede_ant = extra.get("sede_anterior", empleado.get("sede", ""))
    sede_nueva = extra.get("sede_nueva", "")
    fecha_efectiva = extra.get("fecha_efectiva", _fecha_hoy_larga())
    direccion_nueva = extra.get("direccion_nueva", "")

    elementos.append(Paragraph(
        f"Señor(a)<br/><b>{empleado.get('nombre', '')}</b><br/>"
        f"C.C. {empleado.get('documento', '')}<br/>E. S. D.",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    texto = (
        f"Por medio de la presente le comunicamos que a partir del "
        f"<b>{fecha_efectiva}</b> su lugar de trabajo cambiará de "
        f"<b>{sede_ant}</b> a <b>{sede_nueva}</b>."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    if direccion_nueva:
        elementos.append(Paragraph(
            f"<b>Dirección de la nueva sede:</b> {direccion_nueva}",
            estilos["cuerpo"]
        ))

    if extra.get("motivo"):
        elementos.append(Paragraph(
            f"<b>Motivo del traslado:</b> {extra['motivo']}",
            estilos["cuerpo"]
        ))

    elementos.append(Paragraph(
        "Las demás condiciones de su contrato de trabajo permanecen inalteradas. "
        "Agradecemos su comprensión y colaboración.",
        estilos["cuerpo"]
    ))


def _plantilla_paz_y_salvo(elementos, estilos, empleado, datos_empresa, extra):
    """Paz y salvo laboral."""
    fecha_retiro = empleado.get("fecha_retiro") or _fecha_hoy_larga()

    elementos.append(Paragraph(
        "A QUIEN INTERESE:",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    texto = (
        f"La empresa <b>{datos_empresa.get('nombre', '')}</b>, "
        f"identificada con NIT {datos_empresa.get('nit', '')}, hace constar que "
        f"el señor(a) <b>{empleado.get('nombre', '')}</b>, "
        f"identificado(a) con documento No. {empleado.get('documento', '')}, "
        f"quien se desempeñó como <b>{empleado.get('cargo', '')}</b>, "
        f"se encuentra a paz y salvo con esta empresa por todo concepto laboral, "
        f"prestacional y económico a la fecha."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    elementos.append(Paragraph(
        f"Su vínculo laboral finalizó el <b>{fecha_retiro}</b>.",
        estilos["cuerpo"]
    ))

    conceptos = extra.get("conceptos_incluidos", [
        "Salarios pendientes", "Prestaciones sociales", "Vacaciones",
        "Cesantías e intereses", "Aportes a seguridad social",
    ])
    if conceptos:
        elementos.append(Paragraph(
            "<b>Conceptos incluidos:</b>",
            estilos["cuerpo"]
        ))
        for c in conceptos:
            elementos.append(Paragraph(f"• {c}", estilos["cuerpo"]))

    elementos.append(Paragraph(
        "Este documento se expide a solicitud del interesado para los fines que "
        "considere convenientes.",
        estilos["cuerpo"]
    ))


def _plantilla_autorizacion_descuento(elementos, estilos, empleado, datos_empresa, extra):
    """Autorización de descuento de nómina."""
    valor = extra.get("valor_descuento", 0)
    concepto = extra.get("concepto", "")
    cuotas = extra.get("numero_cuotas", 1)
    valor_cuota = valor / cuotas if cuotas > 0 else valor

    texto = (
        f"Yo, <b>{empleado.get('nombre', '')}</b>, identificado(a) con documento "
        f"No. {empleado.get('documento', '')}, en mi calidad de trabajador(a) "
        f"de la empresa <b>{datos_empresa.get('nombre', '')}</b>, "
        f"autorizo de manera libre, expresa y voluntaria a mi empleador para "
        f"que descuente de mi salario mensual la suma de "
        f"<b>{_pesos_letras(valor_cuota)}</b>, "
        f"durante <b>{cuotas}</b> mensualidades, "
        f"por concepto de: <b>{concepto}</b>."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    elementos.append(Paragraph(
        f"<b>Valor total a descontar:</b> {_pesos_letras(valor)}",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        "Esta autorización se otorga en cumplimiento del artículo 149 del "
        "Código Sustantivo del Trabajo, que permite los descuentos "
        "autorizados previamente por escrito.",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        "Firmo en constancia de aceptación.",
        estilos["cuerpo"]
    ))


def _plantilla_autorizacion_datos(elementos, estilos, empleado, datos_empresa, extra):
    """Autorización de tratamiento de datos personales (Ley 1581/2012)."""
    texto1 = (
        f"Yo, <b>{empleado.get('nombre', '')}</b>, identificado(a) con documento "
        f"No. {empleado.get('documento', '')}, "
        f"en cumplimiento de la Ley 1581 de 2012 y el Decreto 1377 de 2013, "
        f"autorizo a <b>{datos_empresa.get('nombre', '')}</b>, "
        f"identificada con NIT {datos_empresa.get('nit', '')}, "
        f"para el tratamiento de mis datos personales."
    )
    elementos.append(Paragraph(texto1, estilos["cuerpo"]))

    elementos.append(Paragraph(
        "<b>FINALIDADES:</b> Los datos personales serán utilizados para las "
        "siguientes finalidades:",
        estilos["cuerpo"]
    ))

    finalidades = [
        "Gestión del contrato laboral y cumplimiento de obligaciones patronales",
        "Pago de nómina y prestaciones sociales",
        "Afiliación a EPS, ARL, fondo de pensiones y caja de compensación",
        "Emisión de certificados y documentos laborales",
        "Comunicaciones internas relacionadas con el vínculo laboral",
        "Cumplimiento de obligaciones tributarias y de seguridad social",
    ]
    for f in finalidades:
        elementos.append(Paragraph(f"• {f}", estilos["cuerpo"]))

    elementos.append(Paragraph(
        "<b>DERECHOS DEL TITULAR:</b> Como titular de los datos, tengo derecho a "
        "conocer, actualizar, rectificar y solicitar la supresión de mis datos "
        "personales, así como revocar esta autorización, dirigiendo mi solicitud "
        f"a la empresa a través de {datos_empresa.get('correo_empresa', '[correo empresa]')}.",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        "Declaro que he sido informado(a) sobre las finalidades del tratamiento "
        "y otorgo mi autorización de manera libre y voluntaria.",
        estilos["cuerpo"]
    ))


def _plantilla_acta_entrega(elementos, estilos, empleado, datos_empresa, extra):
    """Acta genérica de entrega (cargo, equipos, dotación)."""
    tipo_entrega = extra.get("tipo_entrega", "cargo")  # cargo / equipos / dotacion
    items = extra.get("items", [])

    intro = {
        "cargo": (
            f"En cumplimiento de la desvinculación laboral, el señor(a) "
            f"<b>{empleado.get('nombre', '')}</b>, identificado(a) con "
            f"documento No. {empleado.get('documento', '')}, "
            f"quien desempeñaba el cargo de <b>{empleado.get('cargo', '')}</b>, "
            f"hace entrega formal del cargo al Sr(a). "
            f"<b>{extra.get('recibe_nombre', '[Nombre]')}</b>, "
            f"con documento No. {extra.get('recibe_documento', '')}, "
            f"quien lo asumirá a partir de la fecha."
        ),
        "equipos": (
            f"El señor(a) <b>{empleado.get('nombre', '')}</b>, "
            f"identificado(a) con documento No. {empleado.get('documento', '')}, "
            f"hace entrega formal de los siguientes equipos y elementos de "
            f"trabajo asignados durante su vínculo laboral con la empresa."
        ),
        "dotacion": (
            f"El señor(a) <b>{empleado.get('nombre', '')}</b>, "
            f"identificado(a) con documento No. {empleado.get('documento', '')}, "
            f"declara haber recibido de la empresa la dotación completa "
            f"correspondiente al período laboral, en cumplimiento del artículo "
            f"230 del Código Sustantivo del Trabajo."
        ),
    }.get(tipo_entrega, "Acta de entrega.")

    elementos.append(Paragraph(intro, estilos["cuerpo"]))

    if items:
        # Tabla de items
        elementos.append(Spacer(1, 12))
        header_label = {
            "cargo": ["Documento / Actividad", "Estado", "Observaciones"],
            "equipos": ["Equipo / Elemento", "Serial / Descripción", "Estado"],
            "dotacion": ["Elemento", "Cantidad", "Fecha entrega"],
        }.get(tipo_entrega, ["Item", "Descripción", "Estado"])

        tabla_data = [header_label]
        for it in items:
            if isinstance(it, dict):
                tabla_data.append([
                    it.get("item", "") or it.get("nombre", ""),
                    it.get("descripcion", "") or it.get("cantidad", "") or it.get("serial", ""),
                    it.get("estado", "") or it.get("fecha", ""),
                ])
            else:
                tabla_data.append([str(it), "", ""])

        tabla = Table(tabla_data, colWidths=[6*cm, 6*cm, 4*cm])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B3F6E")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elementos.append(tabla)

    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(
        "Ambas partes firman como constancia de conformidad con lo aquí descrito.",
        estilos["cuerpo"]
    ))


def _plantilla_llamado_atencion(elementos, estilos, empleado, datos_empresa, extra):
    """Llamado de atención por incumplimiento."""
    motivo = extra.get("motivo", "")
    hechos = extra.get("hechos", "")
    consecuencias = extra.get(
        "consecuencias",
        "En caso de reincidir en la conducta descrita, la empresa podrá "
        "iniciar el procedimiento disciplinario correspondiente conforme al "
        "Reglamento Interno de Trabajo."
    )

    elementos.append(Paragraph(
        f"Señor(a)<br/><b>{empleado.get('nombre', '')}</b><br/>"
        f"C.C. {empleado.get('documento', '')}<br/>"
        f"Cargo: {empleado.get('cargo', '')}<br/>E. S. D.",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(
        f"Asunto: <b>Llamado de atención escrito - {motivo}</b>",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(
        f"Por medio de la presente, se le hace un llamado de atención por "
        f"escrito debido a los siguientes hechos:",
        estilos["cuerpo"]
    ))
    elementos.append(Paragraph(
        f"<b>Hechos:</b><br/>{hechos}",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        f"Estos hechos constituyen un incumplimiento a sus obligaciones "
        f"laborales y a lo establecido en el Reglamento Interno de Trabajo.",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(consecuencias, estilos["cuerpo"]))

    elementos.append(Paragraph(
        "Se solicita firmar como constancia de recibido. La firma no implica "
        "aceptación de los hechos, y usted tiene derecho a presentar "
        "descargos por escrito dentro de los siguientes cinco (5) días hábiles.",
        estilos["cuerpo"]
    ))


def _plantilla_citacion_descargos(elementos, estilos, empleado, datos_empresa, extra):
    """Citación a diligencia de descargos."""
    fecha_diligencia = extra.get("fecha_diligencia", "")
    hora_diligencia = extra.get("hora_diligencia", "")
    lugar = extra.get("lugar", "las instalaciones de la empresa")
    hechos = extra.get("hechos", "")

    elementos.append(Paragraph(
        f"Señor(a)<br/><b>{empleado.get('nombre', '')}</b><br/>"
        f"C.C. {empleado.get('documento', '')}<br/>E. S. D.",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(
        "Asunto: <b>Citación a diligencia de descargos</b>",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(
        f"En cumplimiento del debido proceso y su derecho a la defensa, "
        f"se le cita a diligencia de descargos que se llevará a cabo el "
        f"<b>{fecha_diligencia}</b> a las <b>{hora_diligencia}</b> en {lugar}.",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        f"<b>Hechos objeto de la diligencia:</b><br/>{hechos}",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        "Durante la diligencia usted podrá exponer los hechos, presentar "
        "pruebas y ser asistido por dos (2) representantes de los "
        "trabajadores si así lo desea, conforme al artículo 115 del "
        "Código Sustantivo del Trabajo.",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        "Su asistencia es de carácter obligatorio.",
        estilos["cuerpo"]
    ))


def _plantilla_permiso(elementos, estilos, empleado, datos_empresa, extra):
    """Permiso remunerado o no remunerado."""
    remunerado = extra.get("remunerado", True)
    fecha_inicio = extra.get("fecha_inicio", "")
    fecha_fin = extra.get("fecha_fin", "")
    dias = extra.get("dias", 1)
    motivo = extra.get("motivo", "")

    tipo_txt = "REMUNERADO" if remunerado else "NO REMUNERADO"

    elementos.append(Paragraph(
        f"Señor(a)<br/><b>{empleado.get('nombre', '')}</b><br/>"
        f"C.C. {empleado.get('documento', '')}<br/>"
        f"Cargo: {empleado.get('cargo', '')}<br/>E. S. D.",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(
        f"Asunto: <b>Concesión de permiso {tipo_txt.lower()}</b>",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    texto = (
        f"Por medio de la presente le informamos que se le concede permiso "
        f"<b>{tipo_txt}</b> por <b>{dias}</b> día(s), "
        f"comprendidos entre el <b>{fecha_inicio}</b> y el <b>{fecha_fin}</b>."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    if motivo:
        elementos.append(Paragraph(
            f"<b>Motivo:</b> {motivo}",
            estilos["cuerpo"]
        ))

    if remunerado:
        elementos.append(Paragraph(
            "Durante este período usted continuará devengando su salario normal.",
            estilos["cuerpo"]
        ))
    else:
        elementos.append(Paragraph(
            "Durante este período no se causará salario ni prestaciones sociales, "
            "conforme al artículo 51 del Código Sustantivo del Trabajo.",
            estilos["cuerpo"]
        ))

    elementos.append(Paragraph(
        "Al finalizar el permiso, deberá reintegrarse a sus labores habituales.",
        estilos["cuerpo"]
    ))


def _plantilla_licencia_no_remunerada(elementos, estilos, empleado, datos_empresa, extra):
    """Licencia no remunerada."""
    extra["remunerado"] = False
    _plantilla_permiso(elementos, estilos, empleado, datos_empresa, extra)


def _plantilla_certificacion_funciones(elementos, estilos, empleado, datos_empresa, extra):
    """Certificación de funciones del cargo."""
    funciones = extra.get("funciones", "")

    elementos.append(Paragraph(
        "LA EMPRESA CERTIFICA QUE:",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 6))

    elementos.append(Paragraph(
        f"El señor(a) <b>{empleado.get('nombre', '')}</b>, "
        f"identificado(a) con documento No. {empleado.get('documento', '')}, "
        f"se desempeña en el cargo de <b>{empleado.get('cargo', '')}</b> "
        f"desde el <b>{empleado.get('fecha_ingreso', '')}</b>.",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        "En su cargo, tiene asignadas las siguientes funciones y "
        "responsabilidades:",
        estilos["cuerpo"]
    ))

    if funciones:
        # Si funciones viene como texto con saltos de línea, mostrarlo así
        elementos.append(Paragraph(
            funciones.replace("\n", "<br/>"),
            estilos["cuerpo"]
        ))
    else:
        elementos.append(Paragraph(
            "• Las funciones propias del cargo según el manual interno de "
            "responsabilidades de la empresa.",
            estilos["cuerpo"]
        ))

    elementos.append(Paragraph(
        "Se expide esta certificación a solicitud del interesado para los "
        "fines que estime convenientes.",
        estilos["cuerpo"]
    ))


def _plantilla_carta_ingresos(elementos, estilos, empleado, datos_empresa, extra):
    """Carta de ingresos para trámites bancarios o arrendamientos."""
    salario = empleado.get("salario", 0)
    ing_variable = empleado.get("ingreso_promedio_variable", 0) or 0
    total = float(salario) + float(ing_variable)

    elementos.append(Paragraph(
        "A QUIEN INTERESE:",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    texto = (
        f"La empresa <b>{datos_empresa.get('nombre', '')}</b>, "
        f"identificada con NIT {datos_empresa.get('nit', '')}, "
        f"certifica que el señor(a) "
        f"<b>{empleado.get('nombre', '')}</b>, "
        f"identificado(a) con documento No. {empleado.get('documento', '')}, "
        f"se desempeña en el cargo de <b>{empleado.get('cargo', '')}</b> "
        f"desde el <b>{empleado.get('fecha_ingreso', '')}</b> "
        f"con un contrato a término {empleado.get('tipo_contrato', 'Indefinido').lower()}."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    elementos.append(Paragraph(
        "<b>DETALLE DE INGRESOS MENSUALES:</b>",
        estilos["cuerpo"]
    ))

    tabla_ingresos = [
        ["Concepto", "Valor mensual"],
        ["Salario básico", _fmt_pesos(salario)],
    ]
    if ing_variable > 0:
        tabla_ingresos.append(["Promedio variable", _fmt_pesos(ing_variable)])
        tabla_ingresos.append(["<b>Total mensual</b>", f"<b>{_fmt_pesos(total)}</b>"])

    tabla = Table(tabla_ingresos, colWidths=[8*cm, 6*cm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B3F6E")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabla)

    elementos.append(Spacer(1, 12))
    proposito = extra.get("proposito", "")
    if proposito:
        elementos.append(Paragraph(
            f"<b>Propósito:</b> {proposito}",
            estilos["cuerpo"]
        ))

    elementos.append(Paragraph(
        "Se expide este certificado a solicitud del interesado.",
        estilos["cuerpo"]
    ))


def _plantilla_solicitud_vacaciones(elementos, estilos, empleado, datos_empresa, extra):
    """Solicitud de vacaciones (del empleado a la empresa)."""
    fecha_inicio = extra.get("fecha_inicio", "")
    fecha_fin = extra.get("fecha_fin", "")
    dias = extra.get("dias", 15)
    saldo_disponible = extra.get("dias_disponibles", "")

    elementos.append(Paragraph(
        f"Señores<br/><b>{datos_empresa.get('nombre', '')}</b><br/>"
        f"Departamento de Recursos Humanos<br/>E. S. D.",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(
        "Asunto: <b>Solicitud de vacaciones</b>",
        estilos["cuerpo"]
    ))
    elementos.append(Spacer(1, 12))

    texto = (
        f"Yo, <b>{empleado.get('nombre', '')}</b>, identificado(a) con documento "
        f"No. {empleado.get('documento', '')}, "
        f"en mi calidad de <b>{empleado.get('cargo', '')}</b>, "
        f"solicito respetuosamente autorización para disfrutar <b>{dias}</b> día(s) "
        f"hábiles de vacaciones, entre el <b>{fecha_inicio}</b> "
        f"y el <b>{fecha_fin}</b>."
    )
    elementos.append(Paragraph(texto, estilos["cuerpo"]))

    if saldo_disponible:
        elementos.append(Paragraph(
            f"<b>Días disponibles:</b> {saldo_disponible}",
            estilos["cuerpo"]
        ))

    elementos.append(Paragraph(
        "Agradezco su gestión y aprobación oportuna.",
        estilos["cuerpo"]
    ))

    elementos.append(Paragraph(
        "Cordialmente,",
        estilos["cuerpo"]
    ))


# ══════════════════════════════════════════════════════════════════════════════
# MAPEO DE TIPOS DE DOCUMENTO
# ══════════════════════════════════════════════════════════════════════════════

# Mapeo: tipo → (título del documento, función de plantilla, doble_firma)
PLANTILLAS = {
    # Cartas laborales
    "carta_cambio_salario":  ("COMUNICACIÓN DE CAMBIO SALARIAL",
                                _plantilla_cambio_salarial, True),
    "carta_cambio_cargo":    ("COMUNICACIÓN DE CAMBIO DE CARGO",
                                _plantilla_cambio_cargo, True),
    "carta_ascenso":         ("COMUNICACIÓN DE PROMOCIÓN",
                                _plantilla_cambio_cargo, True),
    "carta_cambio_sede":     ("COMUNICACIÓN DE CAMBIO DE SEDE",
                                _plantilla_cambio_sede, True),
    # Autorizaciones
    "paz_y_salvo":            ("PAZ Y SALVO LABORAL",
                                _plantilla_paz_y_salvo, False),
    "autorizacion_descuento": ("AUTORIZACIÓN DE DESCUENTO DE NÓMINA",
                                _plantilla_autorizacion_descuento, True),
    "autorizacion_datos":     ("AUTORIZACIÓN TRATAMIENTO DE DATOS PERSONALES",
                                _plantilla_autorizacion_datos, True),
    # Actas
    "acta_entrega_cargo":    ("ACTA DE ENTREGA DE CARGO",
                                _plantilla_acta_entrega, True),
    "acta_entrega_equipos":  ("ACTA DE ENTREGA DE EQUIPOS",
                                _plantilla_acta_entrega, True),
    "acta_entrega_dotacion": ("ACTA DE ENTREGA DE DOTACIÓN",
                                _plantilla_acta_entrega, True),
    # Disciplinarios
    "llamado_atencion":      ("LLAMADO DE ATENCIÓN",
                                _plantilla_llamado_atencion, True),
    "citacion_descargos":    ("CITACIÓN A DILIGENCIA DE DESCARGOS",
                                _plantilla_citacion_descargos, False),
    # Permisos
    "permiso_remunerado":     ("PERMISO REMUNERADO",
                                _plantilla_permiso, False),
    "permiso_no_remunerado":  ("PERMISO NO REMUNERADO",
                                _plantilla_permiso, False),
    "licencia_no_remunerada": ("LICENCIA NO REMUNERADA",
                                _plantilla_licencia_no_remunerada, False),
    # Certificados adicionales
    "certificacion_funciones": ("CERTIFICACIÓN DE FUNCIONES",
                                  _plantilla_certificacion_funciones, False),
    "carta_ingresos":          ("CARTA DE INGRESOS",
                                  _plantilla_carta_ingresos, False),
    # Vacaciones
    "solicitud_vacaciones":  ("SOLICITUD DE VACACIONES",
                                _plantilla_solicitud_vacaciones, False),
}


# ══════════════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ══════════════════════════════════════════════════════════════════════════════

def generar_documento(
    tipo: str,
    empleado: dict,
    datos_empresa: dict,
    ruta_salida: str,
    datos_extra: dict = None,
    disenio: int = 1,
    usar_marca_agua: bool = False,
    membrete=None,
    usar_logo: bool = True,
) -> str:
    """
    Genera un documento del catálogo universal.

    Args:
        tipo: código del documento (ver PLANTILLAS)
        empleado: dict con datos del empleado
        datos_empresa: dict con datos de la empresa
        ruta_salida: dónde guardar el PDF
        datos_extra: información específica del tipo de documento
        disenio: 1 a 5 (paletas de colores)

    Returns:
        Ruta del archivo generado (o None si falló).

    Raises:
        ValueError: si el tipo no está en PLANTILLAS.
    """
    if tipo not in PLANTILLAS:
        raise ValueError(
            f"Tipo '{tipo}' no soportado. "
            f"Disponibles: {list(PLANTILLAS.keys())}"
        )

    titulo, plantilla_fn, doble_firma = PLANTILLAS[tipo]
    datos_extra = datos_extra or {}

    doc, elementos, estilos, paleta, pie_fn = _crear_documento_base(
        ruta_salida, datos_empresa, disenio, usar_marca_agua, membrete, usar_logo
    )

    # Encabezado
    _agregar_encabezado(elementos, estilos, datos_empresa, titulo)

    # Cuerpo específico
    plantilla_fn(elementos, estilos, empleado, datos_empresa, datos_extra)

    # Firma
    _agregar_firma(elementos, estilos, datos_empresa, empleado, doble_firma)

    # Generar PDF
    doc.build(elementos, onFirstPage=pie_fn, onLaterPages=pie_fn)
    return ruta_salida


def tipos_disponibles() -> list:
    """Retorna la lista de tipos de documento soportados."""
    return list(PLANTILLAS.keys())
