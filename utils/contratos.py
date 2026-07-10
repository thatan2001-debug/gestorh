"""
Contratos laborales y carta de terminación según CST colombiano.
Documentos incluidos:
- Contrato a término indefinido (Art. 47 CST)
- Contrato a término fijo (Art. 46 CST, Ley 2466/2025)
- Contrato por obra o labor (Art. 46 CST)
- Contrato de prestación de servicios (contrato civil, NO laboral)
- Carta de terminación: renuncia voluntaria / con justa causa (Art. 62) / sin justa causa (Art. 64)
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle

from utils.plantillas_disenio import (
    PALETAS, _estilos_para, _encabezado, _firmas_dobles, _pie,
    MARGEN_SUP_NORMAL, MARGEN_SUP_MEMBRETE, MARGEN_INF,
    MARGEN_IZQ, MARGEN_DER,
)
from utils.fecha_utils import fmt_fecha, fecha_hoy_larga


# ══════════════════════════════════════════════════════════════════════════════
# CONTRATOS
# ══════════════════════════════════════════════════════════════════════════════

def generar_contrato_indefinido(empleado, datos_empresa, ruta_salida, config,
                                  disenio=1, usar_marca_agua=False,
                                  membrete_path=None, usar_logo_enc=True):
    _generar_contrato_base(
        empleado, datos_empresa, ruta_salida, config,
        tipo="INDEFINIDO",
        titulo="CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO",
        articulo_cst="Art. 47 CST",
        clausulas_fn=_clausulas_indefinido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc)


def generar_contrato_fijo(empleado, datos_empresa, ruta_salida, config,
                            disenio=1, usar_marca_agua=False,
                            membrete_path=None, usar_logo_enc=True):
    _generar_contrato_base(
        empleado, datos_empresa, ruta_salida, config,
        tipo="FIJO",
        titulo="CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO FIJO",
        articulo_cst="Art. 46 CST · Ley 2466/2025",
        clausulas_fn=_clausulas_fijo,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc)


def generar_contrato_obra(empleado, datos_empresa, ruta_salida, config,
                            disenio=1, usar_marca_agua=False,
                            membrete_path=None, usar_logo_enc=True):
    _generar_contrato_base(
        empleado, datos_empresa, ruta_salida, config,
        tipo="OBRA",
        titulo="CONTRATO DE TRABAJO POR DURACIÓN DE OBRA O LABOR",
        articulo_cst="Art. 46 CST",
        clausulas_fn=_clausulas_obra,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc)


def generar_contrato_prestacion(empleado, datos_empresa, ruta_salida, config,
                                  disenio=1, usar_marca_agua=False,
                                  membrete_path=None, usar_logo_enc=True):
    _generar_contrato_base(
        empleado, datos_empresa, ruta_salida, config,
        tipo="PRESTACION",
        titulo="CONTRATO DE PRESTACIÓN DE SERVICIOS",
        articulo_cst="Contrato civil — NO laboral",
        clausulas_fn=_clausulas_prestacion,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc)


def _generar_contrato_base(empleado, datos_empresa, ruta_salida, config,
                            tipo, titulo, articulo_cst, clausulas_fn,
                            disenio, usar_marca_agua, membrete_path, usar_logo_enc):
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

    _encabezado(el, datos_empresa, estilos, paleta, disenio, membrete_path=membrete_path)
    el.append(Paragraph(titulo, estilos["titulo"]))
    el.append(Paragraph(f"<i>{articulo_cst}</i>", _estilo_articulo(estilos)))
    el.append(Spacer(1, 20))

    _agregar_partes(el, empleado, datos_empresa, estilos, tipo)
    el.append(Spacer(1, 16))

    if tipo == "PRESTACION":
        el.append(Paragraph(
            "Entre las partes se ha celebrado el presente <b>Contrato Civil "
            "de Prestación de Servicios</b>, el cual se regirá por las "
            "siguientes cláusulas:", estilos["cuerpo"]))
    else:
        el.append(Paragraph(
            "Entre las partes se ha celebrado el presente <b>Contrato "
            "Individual de Trabajo</b>, regido por las disposiciones del "
            "Código Sustantivo del Trabajo y las siguientes cláusulas:",
            estilos["cuerpo"]))

    clausulas_fn(el, empleado, datos_empresa, config, estilos)

    if tipo != "PRESTACION":
        _clausulas_comunes(el, config, estilos)

    el.append(Spacer(1, 12))
    if tipo == "PRESTACION":
        aviso = ("<b>Aviso importante:</b> Este contrato es de naturaleza CIVIL, "
                 "NO genera relación laboral. Si en la ejecución se configuran "
                 "elementos de subordinación, horario u órdenes, el trabajador "
                 "podrá reclamar contrato realidad (Art. 22 CST). Consulte a un "
                 "abogado antes de firmar.")
    else:
        aviso = ("<b>Aviso:</b> Este documento es un modelo de referencia generado "
                 "automáticamente. Antes de firmar, debe ser revisado por un abogado "
                 "laboral que verifique cláusulas específicas, cumplimiento de la "
                 "normatividad vigente y ajustes al caso particular.")
    el.append(Paragraph(aviso, estilos["nota"]))

    el.append(Spacer(1, 32))
    el.append(Paragraph(
        f"En señal de conformidad, las partes firman el presente contrato "
        f"el día <b>{fecha_hoy_larga()}</b>.", estilos["cuerpo"]))
    el.append(Spacer(1, 40))

    _firmas_dobles(el,
        representante=datos_empresa.get("representante",""),
        empresa=datos_empresa.get("nombre",""),
        nombre_empleado=empleado.get("Nombre",""),
        cedula=empleado.get("Documento",""),
        paleta=paleta, estilos=estilos,
        cargo_firmante=datos_empresa.get("_cargo_firmante","Representante Legal"))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


def _agregar_partes(el, empleado, datos_empresa, estilos, tipo):
    rol_1 = "EL CONTRATANTE" if tipo == "PRESTACION" else "EL EMPLEADOR"
    rol_2 = "EL CONTRATISTA" if tipo == "PRESTACION" else "EL TRABAJADOR"

    el.append(Paragraph("<b>ENTRE LAS PARTES:</b>", estilos["cuerpo"]))
    el.append(Spacer(1, 6))
    el.append(Paragraph(
        f"<b>{rol_1}:</b> {datos_empresa.get('nombre','')}, "
        f"identificada con NIT {datos_empresa.get('nit','')}, "
        f"domiciliada en {datos_empresa.get('ciudad','Colombia')}, "
        f"representada legalmente por {datos_empresa.get('representante','')}, "
        f"quien en adelante se denominará {rol_1}.", estilos["cuerpo"]))
    el.append(Paragraph(
        f"<b>{rol_2}:</b> {empleado.get('Nombre','')}, "
        f"identificado(a) con cédula de ciudadanía No. {empleado.get('Documento','')}, "
        f"quien en adelante se denominará {rol_2}.", estilos["cuerpo"]))


def _clausulas_indefinido(el, empleado, datos_empresa, config, estilos):
    fi = fmt_fecha(config.get("fecha_inicio_contrato",""))
    cargo   = empleado.get("Cargo","")
    salario = float(empleado.get("Salario",0))
    lugar   = config.get("lugar_trabajo", datos_empresa.get("ciudad","Colombia"))
    jornada = config.get("jornada","Diurna")
    sal_fmt = f"${salario:,.0f}".replace(",",".")

    el.append(Spacer(1, 10))
    el.append(Paragraph(f"<b>PRIMERA — OBJETO Y CARGO:</b> El TRABAJADOR se "
        f"obliga a prestar sus servicios personales al EMPLEADOR en el cargo de "
        f"<b>{cargo}</b>, con las funciones inherentes al mismo y aquellas que "
        f"le sean asignadas.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>SEGUNDA — DURACIÓN:</b> El presente contrato es a "
        f"<b>TÉRMINO INDEFINIDO</b> y su ejecución iniciará el día <b>{fi}</b>. "
        f"Podrá darse por terminado por cualquiera de las causas previstas en "
        f"los Arts. 61 a 65 del CST.", estilos["cuerpo"]))

    if config.get("periodo_prueba", True):
        el.append(Paragraph("<b>TERCERA — PERÍODO DE PRUEBA:</b> Las partes "
            "acuerdan un período de prueba de <b>DOS (2) MESES</b>, contados "
            "desde el inicio del contrato, durante el cual cualquiera de las "
            "partes podrá darlo por terminado unilateralmente sin lugar a "
            "indemnización (Art. 78 CST).", estilos["cuerpo"]))

    el.append(Paragraph(f"<b>CUARTA — SALARIO:</b> El EMPLEADOR pagará al "
        f"TRABAJADOR un salario mensual de <b>{sal_fmt}</b> COP, pagaderos en "
        f"las fechas y forma habituales del EMPLEADOR.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>QUINTA — LUGAR Y JORNADA:</b> El servicio se "
        f"prestará en <b>{lugar}</b>, en jornada laboral <b>{jornada}</b> "
        f"conforme a los horarios establecidos por el EMPLEADOR y ajustados a "
        f"la legislación vigente sobre jornada máxima de trabajo.", estilos["cuerpo"]))


def _clausulas_fijo(el, empleado, datos_empresa, config, estilos):
    fi = fmt_fecha(config.get("fecha_inicio_contrato",""))
    ff = fmt_fecha(config.get("fecha_fin_contrato",""))
    cargo   = empleado.get("Cargo","")
    salario = float(empleado.get("Salario",0))
    lugar   = config.get("lugar_trabajo", datos_empresa.get("ciudad","Colombia"))
    jornada = config.get("jornada","Diurna")
    sal_fmt = f"${salario:,.0f}".replace(",",".")

    el.append(Spacer(1, 10))
    el.append(Paragraph(f"<b>PRIMERA — OBJETO Y CARGO:</b> El TRABAJADOR se "
        f"obliga a prestar sus servicios personales al EMPLEADOR en el cargo de "
        f"<b>{cargo}</b>.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>SEGUNDA — DURACIÓN:</b> El presente contrato es a "
        f"<b>TÉRMINO FIJO</b>, con fecha de inicio el <b>{fi}</b> y fecha de "
        f"terminación el <b>{ff}</b>. Conforme a la Ley 2466/2025, este tipo de "
        f"contrato tiene una duración máxima de cuatro (4) años y podrá "
        f"prorrogarse cumpliendo los requisitos del Art. 46 CST.", estilos["cuerpo"]))
    el.append(Paragraph("<b>TERCERA — PREAVISO DE NO RENOVACIÓN:</b> Si el "
        "EMPLEADOR decide no renovar el contrato, deberá notificarlo por "
        "escrito al TRABAJADOR con una antelación mínima de <b>TREINTA (30) "
        "DÍAS CALENDARIO</b> a la fecha de terminación. En caso contrario, el "
        "contrato se entenderá prorrogado por un período igual al inicialmente "
        "pactado (Art. 46 CST).", estilos["cuerpo"]))

    if config.get("periodo_prueba", True):
        el.append(Paragraph("<b>CUARTA — PERÍODO DE PRUEBA:</b> Las partes "
            "acuerdan un período de prueba de <b>DOS (2) MESES</b>, o hasta la "
            "quinta parte del término del contrato cuando este sea inferior a "
            "un año (Art. 78 CST).", estilos["cuerpo"]))

    el.append(Paragraph(f"<b>QUINTA — SALARIO:</b> El EMPLEADOR pagará al "
        f"TRABAJADOR un salario mensual de <b>{sal_fmt}</b> COP.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>SEXTA — LUGAR Y JORNADA:</b> El servicio se "
        f"prestará en <b>{lugar}</b>, en jornada laboral <b>{jornada}</b>.",
        estilos["cuerpo"]))


def _clausulas_obra(el, empleado, datos_empresa, config, estilos):
    fi = fmt_fecha(config.get("fecha_inicio_contrato",""))
    descripcion = config.get("descripcion_obra", "la obra o labor específica encomendada")
    cargo   = empleado.get("Cargo","")
    salario = float(empleado.get("Salario",0))
    lugar   = config.get("lugar_trabajo", datos_empresa.get("ciudad","Colombia"))
    sal_fmt = f"${salario:,.0f}".replace(",",".")

    el.append(Spacer(1, 10))
    el.append(Paragraph(f"<b>PRIMERA — OBJETO:</b> El TRABAJADOR se obliga a "
        f"prestar sus servicios personales al EMPLEADOR para la ejecución de "
        f"la siguiente obra o labor determinada: <b>{descripcion}</b>, "
        f"desempeñando el cargo de <b>{cargo}</b>.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>SEGUNDA — DURACIÓN:</b> El presente contrato es por "
        f"<b>DURACIÓN DE OBRA O LABOR</b>, con fecha de inicio el <b>{fi}</b>. "
        f"Terminará automáticamente cuando concluya la obra o labor contratada, "
        f"sin necesidad de preaviso. La descripción de la obra debe ser específica "
        f"y determinada (Art. 46 CST).", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>TERCERA — SALARIO:</b> El EMPLEADOR pagará al "
        f"TRABAJADOR un salario mensual de <b>{sal_fmt}</b> COP por la "
        f"ejecución de la obra o labor pactada.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>CUARTA — LUGAR:</b> El servicio se prestará en "
        f"<b>{lugar}</b> o donde requiera la ejecución de la obra.", estilos["cuerpo"]))


def _clausulas_prestacion(el, empleado, datos_empresa, config, estilos):
    fi = fmt_fecha(config.get("fecha_inicio_contrato",""))
    ff = fmt_fecha(config.get("fecha_fin_contrato",""))
    objeto = config.get("objeto_contrato","los servicios profesionales pactados")
    honorarios = float(config.get("honorarios", 0))
    forma_pago = config.get("forma_pago","Mensual, contra entrega de factura o cuenta de cobro")
    hon_fmt = f"${honorarios:,.0f}".replace(",",".")

    el.append(Spacer(1, 10))
    el.append(Paragraph(f"<b>PRIMERA — OBJETO DEL CONTRATO:</b> El CONTRATISTA "
        f"prestará al CONTRATANTE los siguientes servicios: <b>{objeto}</b>. "
        f"El CONTRATISTA actuará con plena autonomía técnica, administrativa y "
        f"financiera, sin subordinación jurídica.", estilos["cuerpo"]))
    el.append(Paragraph("<b>SEGUNDA — NATURALEZA CIVIL:</b> Las partes declaran "
        "expresamente que este contrato es de naturaleza CIVIL y NO genera "
        "relación laboral. El CONTRATISTA no queda sometido a subordinación, "
        "horario ni órdenes del CONTRATANTE.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>TERCERA — DURACIÓN:</b> El presente contrato "
        f"iniciará el <b>{fi}</b> y terminará el <b>{ff}</b>, o cuando se "
        f"cumpla el objeto contractual.", estilos["cuerpo"]))
    el.append(Paragraph(f"<b>CUARTA — HONORARIOS:</b> El CONTRATANTE pagará al "
        f"CONTRATISTA la suma de <b>{hon_fmt}</b> COP por sus servicios. "
        f"<b>Forma de pago:</b> {forma_pago}.", estilos["cuerpo"]))
    el.append(Paragraph("<b>QUINTA — SEGURIDAD SOCIAL:</b> El CONTRATISTA es "
        "responsable de sus aportes a seguridad social como independiente "
        "(Art. 15 Ley 100/1993 y Ley 1955/2019).", estilos["cuerpo"]))
    el.append(Paragraph("<b>SEXTA — TERMINACIÓN:</b> Cualquiera de las partes "
        "podrá dar por terminado el contrato con quince (15) días de aviso "
        "previo, sin lugar a indemnización, salvo pacto en contrario.", estilos["cuerpo"]))


def _clausulas_comunes(el, config, estilos):
    el.append(Paragraph("<b>SÉPTIMA — OBLIGACIONES DEL TRABAJADOR:</b> Cumplir "
        "con las funciones del cargo, guardar reserva sobre información "
        "confidencial, respetar el reglamento interno de trabajo y las órdenes "
        "e instrucciones del EMPLEADOR.", estilos["cuerpo"]))
    el.append(Paragraph("<b>OCTAVA — PROTECCIÓN DE DATOS:</b> El TRABAJADOR "
        "autoriza al EMPLEADOR el tratamiento de sus datos personales para "
        "fines laborales, en cumplimiento de la Ley 1581 de 2012.",
        estilos["cuerpo"]))
    if config.get("funciones"):
        el.append(Paragraph(f"<b>NOVENA — FUNCIONES ESPECÍFICAS:</b> "
            f"{config['funciones']}", estilos["cuerpo"]))


# ══════════════════════════════════════════════════════════════════════════════
# CARTA DE TERMINACIÓN
# ══════════════════════════════════════════════════════════════════════════════

CAUSAL_JUSTA_CAUSA = {
    "1":  "Haber sufrido engaño por parte del trabajador mediante la presentación de certificados falsos para su admisión",
    "2":  "Todo acto de violencia, injuria, malos tratamientos o grave indisciplina",
    "3":  "Todo acto grave de violencia, injuria o malos tratamientos en que incurra el trabajador contra el empleador",
    "4":  "Todo daño material causado intencionalmente a los edificios, obras, maquinarias y materias primas",
    "5":  "Todo acto inmoral o delictuoso que el trabajador cometa en el taller, establecimiento o lugar de trabajo",
    "6":  "Cualquier violación grave de las obligaciones o prohibiciones especiales",
    "7":  "La detención preventiva del trabajador por más de treinta (30) días",
    "8":  "El que el trabajador revele los secretos técnicos o comerciales",
    "9":  "El deficiente rendimiento en el trabajo en relación con la capacidad del trabajador",
    "10": "La sistemática inejecución, sin razones válidas, de las obligaciones convencionales o legales",
    "11": "Todo vicio del trabajador que perturbe la disciplina del establecimiento",
    "12": "La renuencia sistemática del trabajador a aceptar las medidas preventivas o profilácticas",
    "13": "La ineptitud del trabajador para realizar la labor encomendada",
    "14": "El reconocimiento al trabajador de la pensión de jubilación o invalidez",
    "15": "La enfermedad contagiosa o crónica del trabajador que no tenga carácter profesional",
}


def generar_carta_terminacion(empleado, datos_empresa, ruta_salida, config,
                                disenio=1, usar_marca_agua=False,
                                membrete_path=None, usar_logo_enc=True):
    """
    Carta de terminación de contrato — 3 modalidades:
    config debe incluir:
      - modalidad: 'renuncia_voluntaria' | 'con_justa_causa' | 'sin_justa_causa'
      - fecha_retiro
      - causal_justa_causa: '1' a '15' (solo si con_justa_causa)
      - hechos: descripción (solo si con_justa_causa)
      - observaciones: opcional
    """
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
    _encabezado(el, datos_empresa, estilos, paleta, disenio, membrete_path=membrete_path)

    modalidad = config.get("modalidad","renuncia_voluntaria")
    fr = fmt_fecha(config.get("fecha_retiro",""))

    if modalidad == "renuncia_voluntaria":
        titulo   = "COMUNICACIÓN DE ACEPTACIÓN DE RENUNCIA"
        articulo = "Art. 47 CST · Renuncia voluntaria"
    elif modalidad == "con_justa_causa":
        titulo   = "CARTA DE TERMINACIÓN DE CONTRATO CON JUSTA CAUSA"
        articulo = "Art. 62 CST · Justa causa por el empleador"
    else:
        titulo   = "CARTA DE TERMINACIÓN DE CONTRATO SIN JUSTA CAUSA"
        articulo = "Art. 64 CST · Sin justa causa"

    el.append(Paragraph(titulo, estilos["titulo"]))
    el.append(Paragraph(f"<i>{articulo}</i>", _estilo_articulo(estilos)))
    el.append(Spacer(1, 20))

    el.append(Paragraph(
        f"{datos_empresa.get('ciudad','Colombia')}, {fecha_hoy_larga()}",
        estilos["cuerpo"]))
    el.append(Spacer(1, 14))

    el.append(Paragraph("<b>Señor(a):</b>", estilos["cuerpo"]))
    el.append(Paragraph(
        f"<b>{empleado.get('Nombre','').upper()}</b><br/>"
        f"C.C. {empleado.get('Documento','')}<br/>"
        f"{empleado.get('Cargo','')}", estilos["cuerpo"]))
    el.append(Spacer(1, 14))
    el.append(Paragraph(f"<b>ASUNTO:</b> {titulo}", estilos["cuerpo"]))
    el.append(Spacer(1, 14))

    fi = fmt_fecha(empleado.get("Fecha ingreso",""))
    cargo = empleado.get("Cargo","")
    empresa = datos_empresa.get("nombre","")

    if modalidad == "renuncia_voluntaria":
        el.append(Paragraph(
            f"Reciba un cordial saludo. Por medio de la presente comunicación, "
            f"la empresa <b>{empresa}</b> se permite informar que se ha aceptado "
            f"su carta de renuncia voluntaria, presentada por usted al cargo de "
            f"<b>{cargo}</b>, en el que se venía desempeñando desde el <b>{fi}</b>.",
            estilos["cuerpo"]))
        el.append(Paragraph(
            f"Su último día de labores será el <b>{fr}</b>, fecha en la cual se "
            f"procederá con la liquidación de prestaciones sociales, salarios "
            f"pendientes y demás conceptos a que haya lugar, conforme a lo "
            f"establecido en el Código Sustantivo del Trabajo.", estilos["cuerpo"]))
        el.append(Paragraph(
            "Le solicitamos hacer entrega formal de su cargo, elementos, equipos "
            "y documentos a su superior inmediato antes del último día laborado, "
            "con el fin de proceder al respectivo paz y salvo.", estilos["cuerpo"]))
        el.append(Paragraph(
            "Agradecemos su dedicación durante el tiempo que hizo parte de "
            "nuestro equipo y le deseamos éxitos en sus futuros proyectos.",
            estilos["cuerpo"]))

    elif modalidad == "con_justa_causa":
        causal_num = config.get("causal_justa_causa","6")
        causal_txt = CAUSAL_JUSTA_CAUSA.get(causal_num, "Violación grave de las obligaciones")
        hechos = config.get("hechos","conforme a las evaluaciones y comunicaciones previamente notificadas.")

        el.append(Paragraph(
            f"Reciba un cordial saludo. Por medio de la presente, la empresa "
            f"<b>{empresa}</b> le comunica que ha decidido dar por terminado "
            f"el contrato individual de trabajo suscrito entre las partes, "
            f"con efecto a partir del <b>{fr}</b>, con fundamento en <b>JUSTA "
            f"CAUSA</b>, de acuerdo con el numeral <b>{causal_num}</b> del "
            f"literal A del Artículo 62 del Código Sustantivo del Trabajo, "
            f"que consagra: <i>\"{causal_txt}\"</i>.", estilos["cuerpo"]))
        el.append(Paragraph(f"<b>Hechos:</b> {hechos}", estilos["cuerpo"]))
        el.append(Paragraph(
            "Por tratarse de una terminación con justa causa, no se genera "
            "indemnización por despido (Art. 64 CST). Se procederá a la "
            "liquidación de prestaciones sociales, salarios pendientes, "
            "cesantías, intereses, prima y vacaciones proporcionales.",
            estilos["cuerpo"]))
        el.append(Paragraph(
            "Le solicitamos hacer entrega formal de su cargo, elementos, "
            "equipos y documentos a su superior inmediato para el respectivo "
            "paz y salvo.", estilos["cuerpo"]))

    else:  # sin_justa_causa
        el.append(Paragraph(
            f"Reciba un cordial saludo. Por medio de la presente, la empresa "
            f"<b>{empresa}</b> le comunica su decisión de dar por terminado "
            f"el contrato individual de trabajo suscrito entre las partes, "
            f"con efecto a partir del <b>{fr}</b>, <b>SIN JUSTA CAUSA</b> "
            f"por parte del empleador.", estilos["cuerpo"]))
        el.append(Paragraph(
            "Por tratarse de una terminación sin justa causa, el trabajador "
            "tiene derecho a la <b>indemnización</b> establecida en el "
            "Artículo 64 del Código Sustantivo del Trabajo, la cual será "
            "liquidada y pagada conforme a la ley.", estilos["cuerpo"]))
        el.append(Paragraph(
            "Adicionalmente se procederá con la liquidación de prestaciones "
            "sociales, salarios pendientes, cesantías, intereses, prima y "
            "vacaciones proporcionales causadas hasta la fecha de retiro.",
            estilos["cuerpo"]))
        el.append(Paragraph(
            "Le solicitamos hacer entrega formal de su cargo, elementos y "
            "documentos a su superior inmediato para el respectivo paz y salvo.",
            estilos["cuerpo"]))

    if config.get("observaciones"):
        el.append(Paragraph(
            f"<b>Observaciones adicionales:</b> {config['observaciones']}",
            estilos["cuerpo"]))

    el.append(Spacer(1, 20))
    el.append(Paragraph("Atentamente,", estilos["cuerpo"]))
    el.append(Spacer(1, 40))

    _firmas_dobles(el,
        representante=datos_empresa.get("representante",""),
        empresa=datos_empresa.get("nombre",""),
        nombre_empleado=empleado.get("Nombre",""),
        cedula=empleado.get("Documento",""),
        paleta=paleta, estilos=estilos,
        cargo_firmante=datos_empresa.get("_cargo_firmante","Representante Legal"))

    el.append(Spacer(1, 14))
    el.append(Paragraph(
        "<b>Acuse de recibo:</b> Con la firma de este documento, el trabajador "
        "acepta haber recibido la presente comunicación en la fecha indicada.",
        estilos["nota"]))

    if modalidad == "con_justa_causa":
        aviso = ("<b>Advertencia legal:</b> La terminación con justa causa "
                 "requiere debido proceso previo (llamado de atención, citación "
                 "a descargos, evaluación de pruebas). Si el juez determina que "
                 "no hubo justa causa real, el empleador deberá pagar la "
                 "indemnización del Art. 64 CST. Consulte a un abogado laboral "
                 "antes de proceder.")
    else:
        aviso = ("<b>Aviso:</b> Este documento es un modelo de referencia. "
                 "Antes de notificar al trabajador, se recomienda validación "
                 "por abogado laboral, especialmente para garantizar el debido "
                 "proceso y la evidencia probatoria adecuada.")
    el.append(Paragraph(aviso, estilos["nota"]))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


def _estilo_articulo(estilos):
    return ParagraphStyle(
        "articulo", parent=estilos["cuerpo"],
        fontSize=9, textColor=colors.HexColor("#6B7280"),
        alignment=TA_CENTER, spaceBefore=0, spaceAfter=0)


# ══════════════════════════════════════════════════════════════════════════════
# OTROSÍ AL CONTRATO — Modificación por cambio de cargo, salario o lugar
# ══════════════════════════════════════════════════════════════════════════════

def generar_otrosi(empleado, datos_empresa, ruta_salida, config,
                    disenio=1, usar_marca_agua=False,
                    membrete_path=None, usar_logo_enc=True):
    """
    Otrosí al contrato de trabajo — modifica términos originales.
    config debe incluir:
      - tipo_cambio: lista con 'cargo' | 'salario' | 'lugar' (uno o varios)
      - fecha_vigencia: fecha desde la cual aplica
      - nuevo_cargo: (si cambia cargo)
      - nuevo_salario: (si cambia salario)
      - nuevas_funciones: (opcional si cambia cargo)
      - nuevo_lugar: (si cambia lugar)
      - motivo: motivo del cambio (opcional)
    """
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

    _encabezado(el, datos_empresa, estilos, paleta, disenio, membrete_path=membrete_path)
    el.append(Paragraph("OTROSÍ AL CONTRATO INDIVIDUAL DE TRABAJO",
                        estilos["titulo"]))
    el.append(Paragraph("<i>Art. 22 y 43 CST — Modificación de las condiciones contractuales</i>",
                        _estilo_articulo(estilos)))
    el.append(Spacer(1, 20))

    # Ciudad y fecha
    el.append(Paragraph(
        f"{datos_empresa.get('ciudad','Colombia')}, {fecha_hoy_larga()}",
        estilos["cuerpo"]))
    el.append(Spacer(1, 14))

    # Partes
    fi = fmt_fecha(empleado.get("Fecha ingreso",""))
    empresa   = datos_empresa.get("nombre","")
    nombre    = empleado.get("Nombre","")
    documento = empleado.get("Documento","")
    cargo_actual = empleado.get("Cargo","")

    el.append(Paragraph("<b>ENTRE LAS PARTES:</b>", estilos["cuerpo"]))
    el.append(Spacer(1, 6))
    el.append(Paragraph(
        f"<b>EL EMPLEADOR:</b> {empresa}, identificada con NIT "
        f"{datos_empresa.get('nit','')}, representada legalmente por "
        f"{datos_empresa.get('representante','')}.", estilos["cuerpo"]))
    el.append(Paragraph(
        f"<b>EL TRABAJADOR:</b> {nombre}, identificado(a) con cédula No. "
        f"{documento}, quien actualmente se desempeña como <b>{cargo_actual}</b> "
        f"en la empresa desde el <b>{fi}</b>.", estilos["cuerpo"]))
    el.append(Spacer(1, 14))

    # Preámbulo
    el.append(Paragraph(
        "Las partes, de común acuerdo, han decidido celebrar el presente "
        "<b>OTROSÍ</b> para modificar las siguientes condiciones del contrato "
        "individual de trabajo suscrito originalmente entre las partes, "
        "manteniendo vigentes las demás cláusulas que no sean expresamente "
        "modificadas por este documento:", estilos["cuerpo"]))
    el.append(Spacer(1, 8))

    # Fecha de vigencia
    fecha_vig = fmt_fecha(config.get("fecha_vigencia",""))

    # Cláusulas de cambios (numeración dinámica)
    tipos = config.get("tipo_cambio", [])
    num = 1

    # ── Cambio de cargo ─────────────────────────────────────────────────
    if "cargo" in tipos:
        nuevo_cargo = config.get("nuevo_cargo","")
        el.append(Paragraph(
            f"<b>CLÁUSULA {_num_romano(num)} — CAMBIO DE CARGO:</b> A partir "
            f"del <b>{fecha_vig}</b>, EL TRABAJADOR pasará a desempeñar el "
            f"cargo de <b>{nuevo_cargo}</b>, con las funciones inherentes al "
            f"mismo y aquellas que le sean asignadas por su superior inmediato. "
            f"Este cambio no implica desmejora en las condiciones laborales "
            f"del TRABAJADOR (Art. 23 CST).",
            estilos["cuerpo"]))

        if config.get("nuevas_funciones"):
            el.append(Paragraph(
                f"<b>Funciones específicas del nuevo cargo:</b> "
                f"{config['nuevas_funciones']}", estilos["cuerpo"]))
        num += 1

    # ── Cambio de salario ───────────────────────────────────────────────
    if "salario" in tipos:
        salario_actual = float(empleado.get("Salario",0))
        nuevo_salario  = float(config.get("nuevo_salario",0))
        sal_actual_fmt = f"${salario_actual:,.0f}".replace(",",".")
        sal_nuevo_fmt  = f"${nuevo_salario:,.0f}".replace(",",".")
        es_aumento = nuevo_salario > salario_actual

        el.append(Paragraph(
            f"<b>CLÁUSULA {_num_romano(num)} — CAMBIO DE SALARIO:</b> A partir "
            f"del <b>{fecha_vig}</b>, el salario mensual del TRABAJADOR se "
            f"modifica de <b>{sal_actual_fmt}</b> a <b>{sal_nuevo_fmt}</b> "
            f"pesos colombianos, pagaderos en las mismas fechas y forma "
            f"habituales del EMPLEADOR. "
            + ("Este incremento no implica renuncia a los derechos ya "
               "consolidados del TRABAJADOR."
               if es_aumento else
               "Esta modificación se realiza de común acuerdo entre las partes "
               "conforme al Art. 43 CST."),
            estilos["cuerpo"]))
        num += 1

    # ── Cambio de lugar ─────────────────────────────────────────────────
    if "lugar" in tipos:
        lugar_actual = config.get("lugar_actual",
                                   datos_empresa.get("ciudad","Colombia"))
        nuevo_lugar  = config.get("nuevo_lugar","")

        el.append(Paragraph(
            f"<b>CLÁUSULA {_num_romano(num)} — CAMBIO DE LUGAR DE TRABAJO:</b> "
            f"A partir del <b>{fecha_vig}</b>, EL TRABAJADOR prestará sus "
            f"servicios en <b>{nuevo_lugar}</b>, en reemplazo del lugar "
            f"anterior ({lugar_actual}). Este cambio no altera las demás "
            f"condiciones del contrato (Art. 32 CST — jus variandi).",
            estilos["cuerpo"]))
        num += 1

    # ── Motivo (opcional) ────────────────────────────────────────────────
    if config.get("motivo"):
        el.append(Paragraph(
            f"<b>MOTIVO DEL CAMBIO:</b> {config['motivo']}",
            estilos["cuerpo"]))

    # Cláusula de vigencia
    el.append(Paragraph(
        f"<b>CLÁUSULA {_num_romano(num)} — VIGENCIA Y DEMÁS CONDICIONES:</b> "
        f"Las modificaciones establecidas en el presente otrosí entran en "
        f"vigencia a partir del <b>{fecha_vig}</b> y las demás cláusulas del "
        f"contrato original permanecen inalteradas y vigentes. Este otrosí "
        f"forma parte integral del contrato individual de trabajo original.",
        estilos["cuerpo"]))

    el.append(Spacer(1, 12))
    el.append(Paragraph(
        "<b>Aviso:</b> Este documento es un modelo de referencia. Se recomienda "
        "revisión por abogado laboral para verificar el cumplimiento del "
        "Art. 43 CST (mutuo acuerdo) y evitar interpretaciones de desmejora "
        "que puedan generar reclamaciones futuras.",
        estilos["nota"]))

    el.append(Spacer(1, 32))
    el.append(Paragraph(
        f"En señal de conformidad, las partes firman el presente otrosí el "
        f"día <b>{fecha_hoy_larga()}</b>.", estilos["cuerpo"]))
    el.append(Spacer(1, 40))

    _firmas_dobles(el,
        representante=datos_empresa.get("representante",""),
        empresa=empresa,
        nombre_empleado=nombre,
        cedula=documento,
        paleta=paleta, estilos=estilos,
        cargo_firmante=datos_empresa.get("_cargo_firmante","Representante Legal"))

    _fn = lambda c,d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


def _num_romano(n: int) -> str:
    """Convierte 1-10 a números romanos para las cláusulas."""
    romanos = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    return romanos[n] if 0 < n < len(romanos) else str(n)
