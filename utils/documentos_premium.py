"""Motor premium para los cuatro documentos críticos de Gestor RH IA.

Mantiene separados datos, validación, contenido, diseño, control documental y
renderizado. Los textos son plantillas parametrizables sujetas a revisión
jurídica de cada empresa.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
    Image, PageBreak, CondPageBreak,
)

from utils.documento_control import crear_control_documental, canvas_factory
from utils.estilos_corporativos import (
    PALETAS, crear_estilos, crear_encabezado_corporativo,
    MARGEN_COMPACTO_SUP, MARGEN_COMPACTO_INF, MARGEN_COMPACTO_IZQ, MARGEN_COMPACTO_DER,
    MARGEN_NORMAL_SUP, MARGEN_NORMAL_INF, MARGEN_NORMAL_IZQ, MARGEN_NORMAL_DER,
    MARGEN_AMPLIO_SUP, MARGEN_AMPLIO_INF, MARGEN_AMPLIO_IZQ, MARGEN_AMPLIO_DER,
    formato_moneda, formato_fecha_larga,
)
from utils.validaciones_documentales import validar_documento, hay_errores, Nivel


ORDINALES = [
    "PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA",
    "OCTAVA", "NOVENA", "DÉCIMA", "DÉCIMA PRIMERA", "DÉCIMA SEGUNDA",
    "DÉCIMA TERCERA", "DÉCIMA CUARTA", "DÉCIMA QUINTA", "DÉCIMA SEXTA",
    "DÉCIMA SÉPTIMA", "DÉCIMA OCTAVA", "DÉCIMA NOVENA", "VIGÉSIMA",
]


def _get(data: dict, *keys, default=""):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def _txt(value) -> str:
    return escape(str(value or "").strip())


def _fecha(value) -> str:
    if isinstance(value, (date, datetime)):
        return formato_fecha_larga(value.strftime("%Y-%m-%d"))
    return formato_fecha_larga(str(value or ""))


def _empleado_normalizado(empleado: dict) -> dict:
    return {
        "nombre": _get(empleado, "Nombre", "nombre"),
        "documento": _get(empleado, "Documento", "documento"),
        "tipo_documento": _get(empleado, "Tipo documento", "tipo_documento", default="C.C."),
        "cargo": _get(empleado, "Cargo", "cargo"),
        "area": _get(empleado, "Área", "Area", "area"),
        "sede": _get(empleado, "Sede", "sede"),
        "centro_costos": _get(empleado, "Centro de costos", "centro_costos"),
        "fecha_ingreso": _get(empleado, "Fecha ingreso", "fecha_ingreso"),
        "fecha_retiro": _get(empleado, "Fecha retiro", "fecha_retiro"),
        "tipo_contrato": _get(empleado, "Tipo contrato", "tipo_contrato", default="Indefinido"),
        "salario": float(_get(empleado, "Salario", "salario", default=0) or 0),
        "correo": _get(empleado, "Correo", "correo"),
        "telefono": _get(empleado, "Teléfono", "Telefono", "telefono"),
        "cuenta_bancaria": _get(empleado, "Cuenta bancaria", "cuenta_bancaria"),
    }


def _empresa_normalizada(empresa: dict) -> dict:
    return {
        **empresa,
        "nombre": _get(empresa, "nombre", "razon_social"),
        "nit": _get(empresa, "nit"),
        "ciudad": _get(empresa, "ciudad", default="Colombia"),
        "direccion": _get(empresa, "direccion"),
        "telefono": _get(empresa, "telefono", "telefono_empresa"),
        "correo_empresa": _get(empresa, "correo_empresa", "correo"),
        "representante": _get(empresa, "representante", "firmante_cert_nombre"),
        "cargo_firmante": _get(empresa, "_cargo_firmante", "firmante_cert_cargo", default="Representante Legal"),
        "logo_path": _get(empresa, "logo_path"),
    }


def _margenes(perfil: str):
    if perfil == "compacto":
        return MARGEN_COMPACTO_SUP, MARGEN_COMPACTO_INF, MARGEN_COMPACTO_IZQ, MARGEN_COMPACTO_DER
    if perfil == "amplio":
        return MARGEN_AMPLIO_SUP, MARGEN_AMPLIO_INF, MARGEN_AMPLIO_IZQ, MARGEN_AMPLIO_DER
    return MARGEN_NORMAL_SUP, MARGEN_NORMAL_INF, MARGEN_NORMAL_IZQ, MARGEN_NORMAL_DER


def _crear_doc(ruta: str, titulo: str, perfil: str):
    sup, inf, izq, der = _margenes(perfil)
    return SimpleDocTemplate(
        ruta, pagesize=letter, topMargin=sup, bottomMargin=max(inf, 2.0 * cm),
        leftMargin=izq, rightMargin=der, title=titulo, author="Gestor RH IA",
        subject="Documento laboral generado por Gestor RH IA",
        allowSplitting=True,
    )


def _tabla_control(control, paleta: dict, estilos: dict, ancho: float) -> Table:
    micro = ParagraphStyle(
        "ControlMicro", parent=estilos["nota"], fontSize=7.2, leading=8.8,
        textColor=paleta["texto_suave"], spaceAfter=0,
    )
    generado = control.generado_en.strftime("%d/%m/%Y %H:%M COT")
    datos = [[
        Paragraph(f"<b>Código:</b> {_txt(control.codigo)}<br/><b>Documento:</b> {_txt(control.numero)}", micro),
        Paragraph(f"<b>Versión:</b> {_txt(control.version_plantilla)}<br/><b>Estado:</b> {_txt(control.estado)}", micro),
        Paragraph(f"<b>Generado:</b> {_txt(generado)}<br/><b>Reglas:</b> {_txt(control.version_reglas)}", micro),
    ]]
    tabla = Table(datos, colWidths=[ancho * .34, ancho * .26, ancho * .40])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), paleta["fondo_tabla"]),
        ("BOX", (0, 0), (-1, -1), .45, paleta["borde"]),
        ("INNERGRID", (0, 0), (-1, -1), .25, paleta["borde_suave"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _titulo(texto: str, estilos: dict, paleta: dict) -> Paragraph:
    style = ParagraphStyle(
        "TituloPremium", parent=estilos["titulo"], fontSize=15.5, leading=18,
        alignment=1, textColor=paleta["primario"], spaceBefore=7, spaceAfter=9,
    )
    return Paragraph(_txt(texto), style)


def _seccion(texto: str, estilos: dict, paleta: dict) -> Paragraph:
    style = ParagraphStyle(
        "SeccionPremium", parent=estilos["subtitulo"], fontSize=10.5, leading=12.5,
        textColor=paleta["primario"], spaceBefore=7, spaceAfter=4,
        keepWithNext=True,
    )
    return Paragraph(_txt(texto).upper(), style)


def _parrafo(texto: str, estilos: dict, compacto: bool = False) -> Paragraph:
    base = estilos["cuerpo_izq"]
    style = ParagraphStyle(
        "ParrafoPremiumCompacto" if compacto else "ParrafoPremium",
        parent=base,
        fontSize=9.4 if compacto else 10.0,
        leading=11.5 if compacto else 12.8,
        spaceAfter=4.5 if compacto else 6,
        alignment=0,
        splitLongWords=True,
        allowWidows=0,
        allowOrphans=0,
    )
    return Paragraph(texto, style)


def _tabla_datos(pares: Iterable[tuple[str, object]], estilos: dict, paleta: dict,
                 ancho: float, columnas: int = 2, compacto: bool = False) -> Table:
    etiqueta = ParagraphStyle("DatoEtiqueta", parent=estilos["nota"], fontSize=7.8,
                              leading=9.2, textColor=paleta["texto_suave"])
    valor = ParagraphStyle("DatoValor", parent=estilos["cuerpo_izq"], fontSize=8.7 if compacto else 9.2,
                           leading=10.5, textColor=paleta["texto"])
    pares = list(pares)
    filas = []
    if columnas == 2:
        for i in range(0, len(pares), 2):
            fila = []
            for etiqueta_txt, valor_txt in pares[i:i+2]:
                fila.append(Paragraph(f"<b>{_txt(etiqueta_txt)}</b><br/>{_txt(valor_txt) or '—'}", valor))
            while len(fila) < 2:
                fila.append(Paragraph("", valor))
            filas.append(fila)
        widths = [ancho / 2] * 2
    else:
        filas = [[Paragraph(f"<b>{_txt(e)}</b>", etiqueta), Paragraph(_txt(v) or "—", valor)] for e, v in pares]
        widths = [ancho * .32, ancho * .68]
    tabla = Table(filas, colWidths=widths, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), paleta["fondo_tabla"]),
        ("BOX", (0, 0), (-1, -1), .45, paleta["borde"]),
        ("INNERGRID", (0, 0), (-1, -1), .25, paleta["borde_suave"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _firma(empresa: dict, empleado: dict | None, estilos: dict, paleta: dict,
           incluir_empleado: bool, estado_firma: str = "pendiente") -> KeepTogether:
    rep = empresa.get("representante", "")
    cargo = empresa.get("cargo_firmante", "Representante Legal")
    firma_path = _get(empresa, "firma_path", "firma_digitalizada_path")
    firma_valida = bool(firma_path and Path(str(firma_path)).exists())
    nota_estado = "Firma digitalizada incorporada por usuario autorizado." if firma_valida else "Documento pendiente de firma."
    style_nombre = ParagraphStyle("FirmaNombrePremium", parent=estilos["firma_nombre"], fontSize=9.2, leading=11)
    style_cargo = ParagraphStyle("FirmaCargoPremium", parent=estilos["firma_cargo"], fontSize=8.1, leading=9.5)

    def bloque(nombre: str, subtitulo: str, extra: str = ""):
        elementos = []
        if firma_valida and nombre == rep:
            try:
                img = Image(str(firma_path), width=3.0*cm, height=0.8*cm, kind="proportional")
                img.hAlign = "LEFT"
                elementos.append(img)
            except Exception:
                elementos.append(Spacer(1, 0.35*cm))
        else:
            elementos.append(Spacer(1, 0.35*cm))
        elementos.extend([
            Table([[""]], colWidths=[6.5*cm], rowHeights=[1], style=TableStyle([("LINEABOVE", (0,0), (-1,-1), .65, paleta["primario"])])),
            Paragraph(f"<b>{_txt(nombre) or 'Firma pendiente'}</b>", style_nombre),
            Paragraph(_txt(subtitulo), style_cargo),
        ])
        if extra:
            elementos.append(Paragraph(_txt(extra), style_cargo))
        return elementos

    izquierda = bloque(rep, cargo, empresa.get("nombre", ""))
    if incluir_empleado and empleado:
        derecha = bloque(empleado.get("nombre", ""), f"{empleado.get('tipo_documento','C.C.')} {empleado.get('documento','')}")
        tabla = Table([[izquierda, derecha]], colWidths=[7.5*cm, 7.5*cm])
    else:
        tabla = Table([[izquierda]], colWidths=[8.0*cm], hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    estado = Paragraph(f"<b>Estado de firma:</b> {_txt(nota_estado)}", estilos["nota"])
    return KeepTogether([tabla, Spacer(1, 4), estado])


def _build(ruta: str, titulo: str, tipo: str, empleado_raw: dict, empresa_raw: dict,
           elementos: list, perfil: str, disenio: int, usar_marca_agua: bool,
           impresion_economica: bool = False, usuario: str = "Usuario autenticado",
           numero_documento: str | None = None, control=None):
    empresa = _empresa_normalizada(empresa_raw)
    empleado = _empleado_normalizado(empleado_raw)
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    control = control or crear_control_documental(
        tipo, empleado["documento"], empresa["nit"], usuario=usuario,
        numero=numero_documento,
    )
    doc = _crear_doc(ruta, titulo, perfil)
    ancho = doc.width
    estilos = crear_estilos(paleta, perfil="compacto" if perfil == "compacto" else "normal")
    cabecera = crear_encabezado_corporativo(empresa, paleta, perfil="compacto" if perfil == "compacto" else "normal")
    story = [*cabecera, _titulo(titulo, estilos, paleta), _tabla_control(control, paleta, estilos, ancho), Spacer(1, 7), *elementos]
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    doc.build(
        story,
        canvasmaker=canvas_factory(
            control, paleta, logo_path=empresa.get("logo_path"),
            usar_marca_agua=usar_marca_agua,
            impresion_economica=impresion_economica,
            titulo=titulo,
        ),
    )
    return control


def generar_certificado_premium(empleado_raw: dict, empresa_raw: dict, ruta: str,
                                 incluir_salario: bool, disenio: int = 1,
                                 usar_marca_agua: bool = False,
                                 config: dict | None = None):
    config = {**(config or {}), "incluir_salario": incluir_salario}
    hallazgos = validar_documento("certificado", empleado_raw, empresa_raw, config)
    if hay_errores(hallazgos):
        raise ValueError("; ".join(h.mensaje for h in hallazgos if h.nivel == Nivel.ERROR))
    empleado, empresa = _empleado_normalizado(empleado_raw), _empresa_normalizada(empresa_raw)
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    estilos = crear_estilos(paleta, perfil="compacto")
    retiro = empleado["fecha_retiro"]
    activo = not bool(str(retiro or "").strip())
    empresa_nombre = _txt(empresa["nombre"])
    nombre = _txt(empleado["nombre"])
    identificacion = f"{_txt(empleado['tipo_documento'])} {_txt(empleado['documento'])}"
    contrato = _txt(empleado["tipo_contrato"])
    cargo = _txt(empleado["cargo"])
    ingreso = _fecha(empleado["fecha_ingreso"])
    if activo:
        cuerpo = (
            f"<b>{empresa_nombre}</b>, identificada con NIT <b>{_txt(empresa['nit'])}</b>, certifica que "
            f"<b>{nombre}</b>, con identificación <b>{identificacion}</b>, actualmente se encuentra vinculado "
            f"desde el <b>{ingreso}</b>, mediante contrato <b>{contrato}</b>, y desempeña el cargo de <b>{cargo}</b>."
        )
    else:
        cuerpo = (
            f"<b>{empresa_nombre}</b>, identificada con NIT <b>{_txt(empresa['nit'])}</b>, certifica que "
            f"<b>{nombre}</b>, con identificación <b>{identificacion}</b>, laboró en la empresa desde el "
            f"<b>{ingreso}</b> hasta el <b>{_fecha(retiro)}</b>, mediante contrato <b>{contrato}</b>, "
            f"y desempeñó el cargo de <b>{cargo}</b>."
        )
    if incluir_salario:
        cuerpo += f" El último salario mensual registrado corresponde a <b>{formato_moneda(empleado['salario'])} COP</b>."
    proposito = _txt(config.get("proposito") or "los fines que la persona interesada considere pertinentes")
    dirigido = _txt(config.get("dirigido_a"))
    elementos = []
    if dirigido:
        elementos.append(_parrafo(f"<b>Dirigido a:</b> {dirigido}", estilos, compacto=True))
    elementos.extend([
        Spacer(1, 4),
        _parrafo(cuerpo, estilos),
        _parrafo(
            f"Se expide en <b>{_txt(empresa['ciudad'])}</b>, el <b>{_fecha(date.today())}</b>, para {proposito}.",
            estilos,
        ),
        Spacer(1, 14),
        _firma(empresa, None, estilos, paleta, incluir_empleado=False),
        Spacer(1, 5),
        _parrafo(
            f"Validación: {_txt(empresa.get('correo_empresa') or empresa.get('telefono') or 'canal corporativo no configurado')}. "
            "El código de verificación se muestra únicamente como identificador; no se incluye QR mientras no exista una página pública de validación.",
            estilos, compacto=True,
        ),
    ])
    return _build(ruta, "CERTIFICACIÓN LABORAL", "certificado", empleado_raw, empresa_raw,
                  elementos, "compacto", disenio, usar_marca_agua,
                  impresion_economica=bool(config.get("impresion_economica")),
                  usuario=config.get("usuario_generador", "Usuario autenticado"),
                  numero_documento=config.get("numero_documento"))


def generar_contrato_indefinido_premium(empleado_raw: dict, empresa_raw: dict, ruta: str,
                                         config: dict, disenio: int = 1,
                                         usar_marca_agua: bool = False):
    hallazgos = validar_documento("contrato_indefinido", empleado_raw, empresa_raw, config)
    if hay_errores(hallazgos):
        raise ValueError("; ".join(h.mensaje for h in hallazgos if h.nivel == Nivel.ERROR))
    empleado, empresa = _empleado_normalizado(empleado_raw), _empresa_normalizada(empresa_raw)
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    estilos = crear_estilos(paleta, perfil="normal")
    funciones = config.get("funciones") or []
    if isinstance(funciones, str):
        funciones = [x.strip(" -•\t") for x in funciones.replace(";", "\n").splitlines() if x.strip()]
    if not funciones:
        funciones = ["Ejecutar las responsabilidades definidas en el perfil de cargo vigente y las instrucciones compatibles con la naturaleza del puesto."]
    funciones_html = "".join(f"<br/>• {_txt(f)}" for f in funciones)
    pago = (
        f"periodicidad <b>{_txt(config.get('periodicidad_pago', 'mensual'))}</b>, mediante "
        f"<b>{_txt(config.get('forma_pago', 'transferencia bancaria'))}</b>, "
        f"el día o los días <b>{_txt(config.get('dia_pago', 'definidos en nómina'))}</b>"
    )
    horario = _txt(config.get("horario") or "según programación comunicada por el empleador")
    descanso = _txt(config.get("dia_descanso") or "según programación legal aplicable")
    modalidad = _txt(config.get("modalidad_laboral") or "presencial")
    lugar = _txt(config.get("lugar_trabajo") or empresa["ciudad"])

    clauses: list[tuple[str, str]] = [
        ("OBJETO, CARGO Y FUNCIONES",
         f"El TRABAJADOR prestará personalmente sus servicios en el cargo de <b>{_txt(empleado['cargo'])}</b>. "
         f"Sus funciones principales son:{funciones_html}<br/>El perfil o anexo de funciones corresponde a la versión "
         f"<b>{_txt(config.get('version_anexo_funciones', '1.0'))}</b> y forma parte integral del contrato."),
        ("DURACIÓN E INICIO",
         f"El contrato es a término indefinido. La fecha real de inicio confirmada por las partes es el "
         f"<b>{_fecha(config.get('fecha_inicio_contrato'))}</b>."),
    ]
    if config.get("periodo_prueba", True):
        clauses.append(("PERÍODO DE PRUEBA",
            f"Se pacta por escrito un período de prueba de <b>{_txt(config.get('duracion_periodo_prueba', 'dos (2) meses'))}</b>, "
            "sujeto a los límites y condiciones legales aplicables."))
    clauses.extend([
        ("LUGAR Y MODALIDAD DE TRABAJO",
         f"El servicio se prestará principalmente en <b>{lugar}</b>, bajo modalidad <b>{modalidad}</b>. "
         "Los cambios se comunicarán y documentarán cuando correspondan."),
        ("JORNADA Y DESCANSO",
         f"La jornada será <b>{_txt(config.get('jornada', 'diurna'))}</b>, con horario <b>{horario}</b>, "
         f"distribución semanal <b>{_txt(config.get('distribucion_semanal', 'conforme a programación'))}</b> y descanso <b>{descanso}</b>, "
         "sin exceder la jornada máxima legal vigente."),
        ("SALARIO Y FORMA DE PAGO",
         f"El salario mensual vigente es <b>{formato_moneda(empleado['salario'])} COP</b>, pagadero con {pago}. "
         f"Auxilios, comisiones o bonificaciones: <b>{_txt(config.get('otros_pagos') or 'no registrados')}</b>."),
        ("HERRAMIENTAS Y ELEMENTOS",
         f"El EMPLEADOR entregará las herramientas o elementos necesarios que se documenten en actas o inventarios separados. "
         f"Elementos iniciales: <b>{_txt(config.get('elementos_entregados') or 'según actas de entrega')}</b>."),
        ("OBLIGACIONES Y SEGURIDAD Y SALUD",
         "Las partes cumplirán las obligaciones legales, el Sistema de Gestión de Seguridad y Salud en el Trabajo, "
         "las instrucciones razonables, el reglamento interno y las políticas aplicables."),
        ("CONFIDENCIALIDAD Y PROPIEDAD INTELECTUAL",
         "El TRABAJADOR protegerá la información reservada a la que tenga acceso. Las reglas sobre propiedad intelectual "
         "se aplicarán según la naturaleza de las funciones y los anexos expresamente pactados."),
        ("TRATAMIENTO DE DATOS PERSONALES",
         f"Responsable: <b>{_txt(empresa['nombre'])}</b>. Finalidades: gestión de la relación laboral, nómina, seguridad social, "
         "bienestar, seguridad y cumplimiento legal. El titular puede conocer, actualizar, rectificar y ejercer los demás derechos "
         f"por el canal <b>{_txt(empresa.get('correo_empresa') or 'definido en la política')}</b>. La política aplicable es "
         f"<b>{_txt(config.get('politica_datos') or 'la vigente de la empresa')}</b>. El tratamiento de datos sensibles requerirá "
         "las condiciones y autorizaciones correspondientes."),
        ("TERMINACIÓN",
         "El contrato podrá terminar por las causas y procedimientos previstos en la ley. La empresa documentará la causa, "
         "la fecha efectiva y los valores que correspondan, sin afectar derechos ciertos e indiscutibles."),
        ("NOTIFICACIONES",
         f"Las comunicaciones se enviarán a los datos registrados por las partes. Canal corporativo: "
         f"<b>{_txt(empresa.get('correo_empresa') or 'no configurado')}</b>. El TRABAJADOR deberá informar cambios de contacto."),
        ("ANEXOS Y ENTREGA DE EJEMPLARES",
         f"Hacen parte del contrato los anexos expresamente relacionados, entre ellos: <b>{_txt(config.get('anexos') or 'perfil de cargo y políticas aceptadas')}</b>. "
         "Cada parte declara recibir un ejemplar o acceso verificable al documento."),
        ("REVISIÓN JURÍDICA",
         "Este contenido corresponde a una plantilla parametrizable sujeta a revisión jurídica de la empresa. "
         "La generación automática no constituye concepto legal ni garantiza adecuación a todos los casos particulares."),
    ])

    partes = _tabla_datos([
        ("Empleador", empresa["nombre"]), ("NIT", empresa["nit"]),
        ("Representante", empresa["representante"]), ("Domicilio", empresa["ciudad"]),
        ("Trabajador", empleado["nombre"]), ("Identificación", f"{empleado['tipo_documento']} {empleado['documento']}"),
        ("Cargo", empleado["cargo"]), ("Fecha de inicio", _fecha(config.get("fecha_inicio_contrato"))),
    ], estilos, paleta, 15.7*cm, columnas=2)
    elementos = [partes, Spacer(1, 7), _parrafo(
        "Entre las partes identificadas se celebra el presente contrato individual de trabajo, regido por la normativa laboral colombiana y las cláusulas siguientes:",
        estilos)]
    for idx, (nombre_clause, texto_clause) in enumerate(clauses):
        ordinal = ORDINALES[idx] if idx < len(ORDINALES) else f"CLÁUSULA {idx+1}"
        elementos.append(_parrafo(f"<b>{ordinal} — {_txt(nombre_clause)}:</b> {texto_clause}", estilos))
    elementos.extend([
        CondPageBreak(5.4*cm),
        _parrafo(f"Se firma en <b>{_txt(empresa['ciudad'])}</b>, el <b>{_fecha(config.get('fecha_celebracion') or date.today())}</b>.", estilos),
        Spacer(1, 10),
        _firma(empresa, empleado, estilos, paleta, incluir_empleado=True),
    ])
    return _build(ruta, "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO",
                  "contrato_indefinido", empleado_raw, empresa_raw, elementos,
                  "amplio", disenio, usar_marca_agua,
                  impresion_economica=bool(config.get("impresion_economica")),
                  usuario=config.get("usuario_generador", "Usuario autenticado"),
                  numero_documento=config.get("numero_documento"))


def generar_dotacion_premium(empleado_raw: dict, empresa_raw: dict, ruta: str,
                              config: dict, disenio: int = 1,
                              usar_marca_agua: bool = False):
    hallazgos = validar_documento("dotacion", empleado_raw, empresa_raw, config)
    if hay_errores(hallazgos):
        raise ValueError("; ".join(h.mensaje for h in hallazgos if h.nivel == Nivel.ERROR))
    empleado, empresa = _empleado_normalizado(empleado_raw), _empresa_normalizada(empresa_raw)
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    estilos = crear_estilos(paleta, perfil="compacto")
    tipo = config.get("tipo_entrega", "otro")
    etiquetas = {
        "dotacion_legal": "Dotación legal",
        "entrega_voluntaria": "Entrega voluntaria",
        "uniforme_corporativo": "Uniforme corporativo",
        "herramienta_trabajo": "Herramienta de trabajo",
        "epp": "Elemento de protección personal",
        "otro": "Otra entrega",
    }
    intro = (
        f"<b>{_txt(empresa['nombre'])}</b> registra la entrega efectiva de los elementos descritos a "
        f"<b>{_txt(empleado['nombre'])}</b>, identificación <b>{_txt(empleado['documento'])}</b>, "
        f"el <b>{_fecha(config.get('fecha_entrega'))}</b> en <b>{_txt(config.get('lugar_entrega') or empresa['ciudad'])}</b>. "
        f"Clasificación: <b>{_txt(etiquetas.get(tipo, tipo))}</b>."
    )
    if tipo == "dotacion_legal" and config.get("cumple_requisitos_dotacion"):
        intro += " La empresa deja constancia de que la entrega fue clasificada como dotación legal conforme a los parámetros confirmados por el usuario."
    elif tipo == "dotacion_legal":
        intro += " La clasificación requiere revisión antes de aprobar el acta, pues no se confirmaron todos los parámetros configurados."

    cell = ParagraphStyle("CeldaDotacion", parent=estilos["cuerpo_izq"], fontSize=7.2, leading=8.3, spaceAfter=0)
    header_cell = ParagraphStyle("CabeceraDotacion", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    header = ["#", "Tipo", "Descripción", "Talla / color", "Marca / referencia", "Cant.", "Estado", "Observaciones"]
    filas = [[Paragraph(h, header_cell) for h in header]]
    for i, item in enumerate(config.get("items") or [], 1):
        talla_color = " / ".join(x for x in [_txt(item.get("talla")), _txt(item.get("color"))] if x) or "—"
        filas.append([
            Paragraph(str(i), cell), Paragraph(_txt(item.get("tipo") or etiquetas.get(tipo, tipo)), cell),
            Paragraph(_txt(item.get("descripcion")), cell), Paragraph(talla_color, cell),
            Paragraph(_txt(item.get("marca") or item.get("referencia")) or "—", cell),
            Paragraph(_txt(item.get("cantidad", 1)), cell), Paragraph(_txt(item.get("estado", "Nuevo")), cell),
            Paragraph(_txt(item.get("observaciones")) or "—", cell),
        ])
    widths = [0.55*cm, 1.65*cm, 4.3*cm, 1.75*cm, 2.25*cm, 0.8*cm, 1.35*cm, 3.25*cm]
    def _crear_tabla_dotacion(filas_tabla):
        tabla_local = Table(filas_tabla, colWidths=widths, repeatRows=1, splitByRow=1, hAlign="LEFT")
        tabla_local.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), paleta["primario"]),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), .35, paleta["borde"]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ALIGN", (0,0), (0,-1), "CENTER"),
            ("ALIGN", (5,0), (6,-1), "CENTER"),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        return tabla_local

    if len(filas) - 1 > 10:
        tablas_dotacion = [
            _crear_tabla_dotacion([filas[0], *filas[1:11]]),
            PageBreak(),
            _crear_tabla_dotacion([filas[0], *filas[11:]]),
        ]
    else:
        tablas_dotacion = [_crear_tabla_dotacion(filas)]
    devolutivo = tipo in {"herramienta_trabajo", "epp"} and config.get("elementos_devolutivos", False)
    compromiso = (
        "La persona trabajadora manifiesta haber recibido los elementos descritos y se compromete a destinarlos al desarrollo "
        "de sus funciones, conservarlos adecuadamente y utilizarlos conforme a las políticas internas de la empresa."
    )
    if devolutivo:
        compromiso += " Los elementos identificados como devolutivos deberán reintegrarse conforme al inventario, su vida útil y las políticas aplicables."
    elementos = [
        _parrafo(intro, estilos, compacto=True),
        _tabla_datos([
            ("Periodo de entrega", config.get("periodo_entrega") or "No especificado"),
            ("Responsable que entrega", config.get("responsable_entrega") or empresa["representante"] or "Pendiente"),
            ("Cargo del trabajador", empleado["cargo"]),
            ("Centro de trabajo", empleado["sede"] or empresa["ciudad"]),
        ], estilos, paleta, 15.9*cm, columnas=2, compacto=True),
        Spacer(1, 6), *tablas_dotacion, Spacer(1, 6),
        _parrafo(compromiso, estilos, compacto=True),
    ]
    if config.get("observaciones"):
        elementos.append(_parrafo(f"<b>Observaciones generales:</b> {_txt(config['observaciones'])}", estilos, compacto=True))
    elementos.extend([CondPageBreak(4.8*cm), Spacer(1, 5), _firma(empresa, empleado, estilos, paleta, incluir_empleado=True)])
    return _build(ruta, "ACTA DE ENTREGA DE DOTACIÓN", "dotacion", empleado_raw, empresa_raw,
                  elementos, "compacto", disenio, usar_marca_agua,
                  impresion_economica=bool(config.get("impresion_economica")),
                  usuario=config.get("usuario_generador", "Usuario autenticado"),
                  numero_documento=config.get("numero_documento"))


def generar_liquidacion_premium(resultado: dict, empresa_raw: dict, ruta: str,
                                  disenio: int = 1, usar_marca_agua: bool = False,
                                  config: dict | None = None):
    config = config or {}
    empleado_raw = {
        "Nombre": resultado.get("Nombre", ""), "Documento": resultado.get("Documento", ""),
        "Cargo": resultado.get("Cargo", ""), "Tipo contrato": resultado.get("Tipo contrato", ""),
        "Salario": resultado.get("Salario base", 0), "Fecha ingreso": resultado.get("Fecha ingreso", ""),
        "Fecha retiro": resultado.get("Fecha corte", ""), "Cuenta bancaria": resultado.get("Cuenta bancaria", ""),
    }
    val_config = {
        "fecha_corte": resultado.get("Fecha corte"),
        "motivo_retiro": resultado.get("Motivo retiro"),
        "pagos_previos_confirmados": config.get("pagos_previos_confirmados", resultado.get("Pagos previos confirmados", False)),
        "novedades_confirmadas": config.get("novedades_confirmadas", resultado.get("Novedades confirmadas", False)),
    }
    hallazgos = validar_documento("liquidacion", empleado_raw, empresa_raw, val_config)
    if hay_errores(hallazgos):
        raise ValueError("; ".join(h.mensaje for h in hallazgos if h.nivel == Nivel.ERROR))
    empleado, empresa = _empleado_normalizado(empleado_raw), _empresa_normalizada(empresa_raw)
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    estilos = crear_estilos(paleta, perfil="compacto")
    base_prestacional = resultado.get("Base prestacional (salario + auxilio)", resultado.get("Salario base", 0))
    base_vacaciones = resultado.get("Base vacaciones", resultado.get("Salario base", 0))
    dias_total = resultado.get("Dias totales (base 360)", 0)
    dias_prima = resultado.get("Dias semestre actual (prima)", 0)
    conceptos = [
        ("Salario pendiente", resultado.get("Periodo salario inicio", "—"), resultado.get("Fecha corte", "—"), resultado.get("Dias salario pendiente", 0), resultado.get("Salario base", 0), "salario / 30 × días", resultado.get("Salario pendiente (estimado)", 0)),
        ("Cesantías", resultado.get("Fecha ingreso", "—"), resultado.get("Fecha corte", "—"), dias_total, base_prestacional, "base × días / 360", resultado.get("Cesantias (Art. 249 CST)", 0)),
        ("Intereses de cesantías", resultado.get("Fecha ingreso", "—"), resultado.get("Fecha corte", "—"), dias_total, resultado.get("Cesantias (Art. 249 CST)", 0), "cesantías × 12% × días / 360", resultado.get("Intereses cesantias 12% (Ley 52/75)", 0)),
        ("Prima de servicios", resultado.get("Inicio periodo prima", "—"), resultado.get("Fecha corte", "—"), dias_prima, base_prestacional, "base × días / 360", resultado.get("Prima semestral (Art. 306 CST)", 0)),
        ("Vacaciones", resultado.get("Fecha ingreso", "—"), resultado.get("Fecha corte", "—"), dias_total, base_vacaciones, "salario × días / 720", resultado.get("Vacaciones (Art. 186 CST)", 0)),
    ]
    if float(resultado.get("Indemnizacion (Art. 64 CST)", 0) or 0) > 0:
        conceptos.append(("Indemnización", "—", resultado.get("Fecha corte", "—"), resultado.get("Indemnizacion dias", 0), resultado.get("Salario base", 0), resultado.get("Indemnizacion detalle", "Art. 64 CST"), resultado.get("Indemnizacion (Art. 64 CST)", 0)))
    for extra in resultado.get("Otros conceptos", []) or []:
        conceptos.append((extra.get("concepto", "Otro"), extra.get("periodo_inicial", "—"), extra.get("periodo_final", "—"), extra.get("dias", "—"), extra.get("base", 0), extra.get("formula", "Registrado"), extra.get("valor", 0)))

    cell = ParagraphStyle("CeldaLiq", parent=estilos["cuerpo_izq"], fontSize=7.2, leading=8.4, spaceAfter=0)
    header_cell = ParagraphStyle("CabeceraLiq", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    headers = ["Concepto", "Periodo inicial", "Periodo final", "Días", "Base", "Fórmula", "Devengado"]
    filas = [[Paragraph(h, header_cell) for h in headers]]
    for c in conceptos:
        filas.append([
            Paragraph(_txt(c[0]), cell), Paragraph(_txt(c[1]), cell), Paragraph(_txt(c[2]), cell),
            Paragraph(_txt(c[3]), cell), Paragraph(formato_moneda(c[4]), cell),
            Paragraph(_txt(c[5]), cell), Paragraph(formato_moneda(c[6]), cell),
        ])
    widths = [3.0*cm, 1.9*cm, 1.9*cm, 0.8*cm, 2.25*cm, 3.9*cm, 2.35*cm]
    tabla = Table(filas, colWidths=widths, repeatRows=1, splitByRow=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), paleta["primario"]), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), .35, paleta["borde"]), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (3,1), (4,-1), "RIGHT"), ("ALIGN", (6,1), (6,-1), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    bruto = float(resultado.get("TOTAL DEVENGADO", resultado.get("TOTAL LIQUIDACION ESTIMADA", 0)) or 0)
    deducciones = float(resultado.get("TOTAL DEDUCCIONES AUTORIZADAS", resultado.get("Deducciones autorizadas", 0)) or 0)
    neto = float(resultado.get("NETO A PAGAR", bruto - deducciones) or 0)
    resumen = Table([
        ["TOTAL DEVENGADO", formato_moneda(bruto)],
        ["DEDUCCIONES AUTORIZADAS", formato_moneda(deducciones)],
        ["NETO A PAGAR", formato_moneda(neto)],
    ], colWidths=[10.8*cm, 5.3*cm], hAlign="RIGHT")
    resumen.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,0), (1,-1), "RIGHT"), ("GRID", (0,0), (-1,-1), .45, paleta["borde"]),
        ("BACKGROUND", (0,-1), (-1,-1), paleta["secundario"]), ("TEXTCOLOR", (0,-1), (-1,-1), colors.white),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))
    advertencias = [h.mensaje for h in hallazgos if h.nivel == Nivel.ADVERTENCIA]
    advertencias.extend(resultado.get("Advertencias", []) or [])
    elementos = [
        _seccion("Datos generales", estilos, paleta),
        _tabla_datos([
            ("Trabajador", empleado["nombre"]), ("Identificación", empleado["documento"]),
            ("Fecha de ingreso", _fecha(empleado["fecha_ingreso"])), ("Fecha de retiro", _fecha(empleado["fecha_retiro"])),
            ("Causa de retiro", resultado.get("Motivo retiro", "No confirmada")), ("Tipo de contrato", empleado["tipo_contrato"]),
            ("Total de días", dias_total), ("Cuenta / forma de pago", resultado.get("Cuenta bancaria") or config.get("forma_pago") or "No registrada"),
        ], estilos, paleta, 16.1*cm, columnas=2, compacto=True),
        _seccion("Bases utilizadas", estilos, paleta),
        _tabla_datos([
            ("Salario mensual", formato_moneda(resultado.get("Salario base", 0))),
            ("Auxilio de transporte", formato_moneda(resultado.get("Auxilio transporte valor", 0))),
            ("Base cesantías y prima", formato_moneda(base_prestacional)),
            ("Base vacaciones", formato_moneda(base_vacaciones)),
            ("Base indemnización", formato_moneda(resultado.get("Salario base", 0))),
            ("Método de días", "Año comercial 360; vacaciones divisor 720"),
        ], estilos, paleta, 16.1*cm, columnas=2, compacto=True),
        _seccion("Detalle por concepto", estilos, paleta), tabla, Spacer(1, 6), resumen,
        _seccion("Resumen de validación", estilos, paleta),
        Paragraph(
            "Cálculo generado con base en los datos y novedades registradas. Verifique las excepciones antes de aprobar. "
            + ("<b>Advertencias:</b> " + " | ".join(_txt(x) for x in advertencias) + ". " if advertencias else "")
            + "La recepción del documento y de los valores registrados no implica renuncia a derechos ciertos e indiscutibles ni impide ajustes por información omitida o corregida.",
            ParagraphStyle("ValidacionLiquidacion", parent=estilos["nota"], fontSize=8.0, leading=9.6,
                           textColor=paleta["texto"], spaceBefore=0, spaceAfter=2),
        ),
        _firma(empresa, empleado, estilos, paleta, incluir_empleado=True),
    ]
    return _build(ruta, "LIQUIDACIÓN DE PRESTACIONES SOCIALES", "liquidacion",
                  empleado_raw, empresa_raw, elementos, "compacto", disenio,
                  usar_marca_agua, impresion_economica=bool(config.get("impresion_economica")),
                  usuario=config.get("usuario_generador", "Usuario autenticado"),
                  numero_documento=config.get("numero_documento"))
