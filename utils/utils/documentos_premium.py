"""Motor documental corporativo para los documentos críticos de Gestor RH IA.

Conserva las firmas públicas existentes y separa el documento formal de las
validaciones técnicas que pertenecen a la interfaz y a la auditoría interna.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
    Image, PageBreak,
)

from utils.documento_control import crear_control_documental, canvas_factory
from utils.etiquetas_documentales import etiqueta_formal
from utils.estilos_corporativos import (
    PALETAS, crear_estilos, crear_encabezado_corporativo,
    MARGEN_COMPACTO_SUP, MARGEN_COMPACTO_INF, MARGEN_COMPACTO_IZQ, MARGEN_COMPACTO_DER,
    MARGEN_NORMAL_SUP, MARGEN_NORMAL_INF, MARGEN_NORMAL_IZQ, MARGEN_NORMAL_DER,
    MARGEN_AMPLIO_SUP, MARGEN_AMPLIO_INF, MARGEN_AMPLIO_IZQ, MARGEN_AMPLIO_DER,
    formato_moneda, formato_fecha_larga,
)
from utils.numero_letras import numero_a_letras
from utils.validaciones_documentales import validar_documento, hay_errores, Nivel

ORDINALES = [
    "PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA",
    "OCTAVA", "NOVENA", "DÉCIMA", "DÉCIMA PRIMERA", "DÉCIMA SEGUNDA",
    "DÉCIMA TERCERA", "DÉCIMA CUARTA", "DÉCIMA QUINTA", "DÉCIMA SEXTA",
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


def _fecha_corta(value) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    texto = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return texto


def _fecha_obj(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    texto = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


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
    telefono = _get(empresa, "telefono", "telefono_empresa")
    return {
        **empresa,
        "nombre": _get(empresa, "nombre", "razon_social"),
        "nit": _get(empresa, "nit"),
        "ciudad": _get(empresa, "ciudad", default="Colombia"),
        "direccion": _get(empresa, "direccion"),
        "telefono": telefono,
        "telefono_empresa": telefono,
        "correo_empresa": _get(empresa, "correo_empresa", "correo"),
        "representante": _get(empresa, "representante", "firmante_cert_nombre"),
        "cargo_firmante": _get(empresa, "_cargo_firmante", "firmante_cert_cargo", default="Representante Legal"),
        "logo_path": _get(empresa, "logo_path"),
    }


def _margenes(perfil: str, tipo_documento: str = None):
    """Márgenes por perfil O por tipo de documento (prioridad al tipo).

    Márgenes A4 corporativos por tipo (del brief de diseño):
      certificado:  23/22/25/25 mm
      contrato:     22/22/28/23 mm  (izq amplio para perforación)
      liquidacion:  18/20/17/17 mm  (más espacio horizontal para tablas)
      dotacion:     20/20/22/22 mm
    """
    from utils.estilos_corporativos import MARGENES_POR_TIPO
    if tipo_documento and tipo_documento in MARGENES_POR_TIPO:
        return MARGENES_POR_TIPO[tipo_documento]
    if perfil == "compacto":
        return MARGEN_COMPACTO_SUP, MARGEN_COMPACTO_INF, MARGEN_COMPACTO_IZQ, MARGEN_COMPACTO_DER
    if perfil == "amplio":
        return MARGEN_AMPLIO_SUP, MARGEN_AMPLIO_INF, MARGEN_AMPLIO_IZQ, MARGEN_AMPLIO_DER
    return MARGEN_NORMAL_SUP, MARGEN_NORMAL_INF, MARGEN_NORMAL_IZQ, MARGEN_NORMAL_DER


def _crear_doc(ruta: str, titulo: str, perfil: str, tipo_documento: str = None):
    sup, inf, izq, der = _margenes(perfil, tipo_documento)
    return SimpleDocTemplate(
        ruta, pagesize=A4, topMargin=sup, bottomMargin=max(inf, 1.7 * cm),
        leftMargin=izq, rightMargin=der, title=titulo, author="Gestor RH IA",
        subject="Documento laboral generado por Gestor RH IA", allowSplitting=True,
    )


def _control_linea(control, paleta: dict, estilos: dict, ancho: float) -> Table:
    estilo = ParagraphStyle(
        "ControlLinea", parent=estilos["nota"], fontSize=7.4, leading=8.8,
        textColor=paleta["texto_suave"], spaceAfter=0,
    )
    fecha = control.generado_en.strftime("%d/%m/%Y")
    texto = (
        f"{_txt(control.codigo)} · {_txt(control.numero)} · Versión {_txt(control.version_plantilla)} · "
        f"{_txt(fecha)} · Estado: <b>{_txt(control.estado)}</b>"
    )
    tabla = Table([[Paragraph(texto, estilo)]], colWidths=[ancho])
    tabla.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), .55, paleta["borde"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _titulo(texto: str, estilos: dict, paleta: dict) -> Paragraph:
    style = ParagraphStyle(
        "TituloPremium", parent=estilos["titulo"], fontSize=15.5, leading=18,
        alignment=1, textColor=paleta["primario"], spaceBefore=6, spaceAfter=7,
    )
    return Paragraph(_txt(texto), style)


def _seccion(texto: str, estilos: dict, paleta: dict, compacto: bool = False) -> Paragraph:
    style = ParagraphStyle(
        "SeccionPremiumCompacta" if compacto else "SeccionPremium",
        parent=estilos["subtitulo"], fontSize=9.3 if compacto else 10.5,
        leading=10.8 if compacto else 12.5, textColor=paleta["primario"],
        spaceBefore=5 if compacto else 8, spaceAfter=3, keepWithNext=True,
    )
    return Paragraph(_txt(texto).upper(), style)


def _parrafo(texto: str, estilos: dict, compacto: bool = False, justificar: bool = False) -> Paragraph:
    base = estilos["cuerpo"] if justificar else estilos["cuerpo_izq"]
    style = ParagraphStyle(
        "ParrafoPremiumCompacto" if compacto else "ParrafoPremium", parent=base,
        fontSize=8.7 if compacto else 9.8, leading=10.7 if compacto else 12.4,
        spaceAfter=4 if compacto else 6, alignment=4 if justificar else 0,
        splitLongWords=True, allowWidows=0, allowOrphans=0,
    )
    return Paragraph(texto, style)


def _tabla_datos(pares: Iterable[tuple[str, object]], estilos: dict, paleta: dict,
                  ancho: float, columnas: int = 2, compacto: bool = False) -> Table:
    pares = [(e, v) for e, v in pares if v not in (None, "")]
    valor = ParagraphStyle(
        "DatoValorCompacto" if compacto else "DatoValor", parent=estilos["cuerpo_izq"],
        fontSize=8.1 if compacto else 8.9, leading=9.4 if compacto else 10.5,
        textColor=paleta["texto"], spaceAfter=0,
    )
    filas = []
    if columnas == 2:
        for i in range(0, len(pares), 2):
            fila = [Paragraph(f"<b>{_txt(e)}</b><br/>{_txt(v)}", valor) for e, v in pares[i:i + 2]]
            while len(fila) < 2:
                fila.append(Paragraph("", valor))
            filas.append(fila)
        widths = [ancho / 2] * 2
    else:
        filas = [[Paragraph(f"<b>{_txt(e)}</b>", valor), Paragraph(_txt(v), valor)] for e, v in pares]
        widths = [ancho * .31, ancho * .69]
    tabla = Table(filas or [[Paragraph("", valor)]], colWidths=widths, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), paleta["fondo_tabla"]),
        ("BOX", (0, 0), (-1, -1), .35, paleta["borde_suave"]),
        ("INNERGRID", (0, 0), (-1, -1), .25, paleta["borde_suave"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return tabla


def _separar_nombre_cargo(texto: str, cargo_default: str = "Responsable") -> tuple[str, str]:
    texto = str(texto or "").strip()
    for sep in (" — ", " - ", "|", "\n"):
        if sep in texto:
            nombre, cargo = texto.split(sep, 1)
            return nombre.strip(), cargo.strip()
    return texto, cargo_default


def _bloque_firma(nombre: str, cargo: str, estilos: dict, paleta: dict,
                  firma_path: str | None = None, extra: str = "", compacto: bool = False) -> list:
    nombre_style = ParagraphStyle(
        "FirmaNombreCompacta" if compacto else "FirmaNombre", parent=estilos["firma_nombre"],
        fontSize=8.2 if compacto else 9.0, leading=9.2 if compacto else 10.4,
    )
    cargo_style = ParagraphStyle(
        "FirmaCargoCompacta" if compacto else "FirmaCargo", parent=estilos["firma_cargo"],
        fontSize=7.2 if compacto else 8.0, leading=8.1 if compacto else 9.2,
    )
    elementos = []
    if firma_path and Path(str(firma_path)).exists():
        try:
            img = Image(str(firma_path), width=3.0 * cm, height=0.8 * cm, kind="proportional")
            img.hAlign = "LEFT"
            elementos.append(img)
        except Exception:
            elementos.append(Spacer(1, 0.35 * cm))
    else:
        elementos.append(Spacer(1, 0.45 * cm if compacto else 0.7 * cm))
    elementos.extend([
        Table([[""]], colWidths=[6.4 * cm], rowHeights=[1],
              style=TableStyle([("LINEABOVE", (0, 0), (-1, -1), .65, paleta["primario"])])),
        Paragraph(f"<b>{_txt(nombre)}</b>", nombre_style),
        Paragraph(_txt(cargo), cargo_style),
    ])
    if extra:
        elementos.append(Paragraph(_txt(extra), cargo_style))
    return elementos


def _firmas(empresa: dict, empleado: dict | None, estilos: dict, paleta: dict,
            incluir_empleado: bool, izquierdo_nombre: str | None = None,
            izquierdo_cargo: str | None = None, compacto: bool = False) -> KeepTogether:
    nombre_izq = izquierdo_nombre or empresa.get("representante", "")
    cargo_izq = izquierdo_cargo or empresa.get("cargo_firmante", "Representante Legal")
    firma_path = _get(empresa, "firma_path", "firma_digitalizada_path")
    izquierda = _bloque_firma(
        nombre_izq, cargo_izq, estilos, paleta, firma_path=firma_path,
        extra="" if compacto else empresa.get("nombre", ""), compacto=compacto,
    )
    if incluir_empleado and empleado:
        derecha = _bloque_firma(
            empleado.get("nombre", ""), "Firma de la persona trabajadora", estilos, paleta,
            extra=f"{empleado.get('tipo_documento', 'C.C.')} {empleado.get('documento', '')}",
            compacto=compacto,
        )
        tabla = Table([[izquierda, derecha]], colWidths=[7.5 * cm, 7.5 * cm])
    else:
        tabla = Table([[izquierda]], colWidths=[8.0 * cm], hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether([tabla])


def _build(ruta: str, titulo: str, tipo: str, empleado_raw: dict, empresa_raw: dict,
           elementos: list, perfil: str, disenio: int, usar_marca_agua: bool,
           impresion_economica: bool = False, usuario: str = "Usuario autenticado",
           numero_documento: str | None = None, estado_documento: str = "Emitido"):
    empresa = _empresa_normalizada(empresa_raw)
    empleado = _empleado_normalizado(empleado_raw)
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    estado = "Borrador" if usar_marca_agua else (estado_documento or "Emitido")
    control = crear_control_documental(
        tipo, empleado["documento"], empresa["nit"], usuario=usuario,
        numero=numero_documento, estado=estado,
    )
    doc = _crear_doc(ruta, titulo, perfil, tipo_documento=tipo)
    estilos = crear_estilos(paleta, perfil="compacto" if perfil == "compacto" else "normal")
    cabecera = crear_encabezado_corporativo(
        empresa, paleta, perfil="compacto" if perfil == "compacto" else "normal",
        ancho_total=doc.width,
    )
    story = [*cabecera, _titulo(titulo, estilos, paleta), Spacer(1, 8), *elementos]
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    doc.build(
        story,
        canvasmaker=canvas_factory(
            control, paleta, usar_marca_agua=usar_marca_agua,
            impresion_economica=impresion_economica, titulo=titulo,
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
    activo = not bool(str(empleado["fecha_retiro"] or "").strip())
    nombre = _txt(empleado["nombre"])
    identificacion = f"{_txt(empleado['tipo_documento'])} No. {_txt(empleado['documento'])}"

    # ─── Estructura CARTA EMPRESARIAL (estilo modelo del cliente) ────────────
    # 1. Fecha alineada a la izquierda
    # 2. Palabra "CERTIFICA" centrada como separador
    # 3. Cuerpo en prosa justificada (empieza con "Que...")
    # 4. Línea de solicitud/expedición
    # 5. "Cordialmente,"
    # 6. Firma con nombre en negrita mayúsculas + cargo

    fecha_emision = config.get("fecha_emision") or date.today()
    ciudad = _txt(empresa['ciudad'])
    proposito = _txt(config.get("proposito") or "los fines que la persona interesada estime pertinentes")

    # Encabezado de fecha
    encabezado_fecha = f"{ciudad}, {_fecha(fecha_emision)}"

    # Cuerpo en prosa (comienza con "Que...")
    if activo:
        cuerpo = (
            f"Que <b>{nombre}</b>, identificado(a) con <b>{identificacion}</b>, "
            f"se encuentra vinculado(a) a esta empresa desde el <b>{_fecha(empleado['fecha_ingreso'])}</b>, "
            f"mediante contrato <b>{_txt(empleado['tipo_contrato']).lower()}</b>, "
            f"desempeñando el cargo de <b>{_txt(empleado['cargo'])}</b>."
        )
        if incluir_salario:
            cuerpo += (
                f" Actualmente devenga un salario mensual de "
                f"<b>{formato_moneda(empleado['salario'])}</b>."
            )
    else:
        cuerpo = (
            f"Que <b>{nombre}</b>, identificado(a) con <b>{identificacion}</b>, "
            f"laboró en esta empresa desde el <b>{_fecha(empleado['fecha_ingreso'])}</b> "
            f"hasta el <b>{_fecha(empleado['fecha_retiro'])}</b>, "
            f"mediante contrato <b>{_txt(empleado['tipo_contrato']).lower()}</b>, "
            f"desempeñando el cargo de <b>{_txt(empleado['cargo'])}</b>."
        )
        if incluir_salario:
            cuerpo += (
                f" Al momento de su retiro devengaba un salario mensual de "
                f"<b>{formato_moneda(empleado['salario'])}</b>."
            )

    # Funciones opcionales integradas
    funciones = config.get("funciones") or []
    if isinstance(funciones, str):
        funciones = [x.strip(" -•\t") for x in funciones.replace(";", "\n").splitlines() if x.strip()]
    if config.get("incluir_funciones") and funciones:
        lista_funciones = ", ".join(_txt(f).lower() for f in funciones)
        cuerpo += f" Entre sus funciones principales se encontraban: {lista_funciones}."

    # Línea de expedición como cierre
    linea_expedicion = (
        f"La presente certificación se expide en <b>{ciudad}</b>, "
        f"el <b>{_fecha(fecha_emision)}</b>, para {proposito}."
    )

    # ─── Estilos específicos del certificado ────────────────────────────────
    estilo_fecha = ParagraphStyle(
        "FechaCert", parent=estilos["cuerpo"], fontSize=10.5, leading=13,
        alignment=TA_LEFT, spaceAfter=18,
    )
    estilo_certifica = ParagraphStyle(
        "CertificaTitulo", parent=estilos["cuerpo"], fontSize=13, leading=16,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
        textColor=paleta["primario"], spaceBefore=14, spaceAfter=18,
    )
    estilo_cuerpo_carta = ParagraphStyle(
        "CuerpoCarta", parent=estilos["cuerpo"], fontSize=10.5, leading=15,
        alignment=TA_JUSTIFY, spaceAfter=16, firstLineIndent=0,
    )
    estilo_despedida = ParagraphStyle(
        "Despedida", parent=estilos["cuerpo"], fontSize=10.5, leading=14,
        alignment=TA_LEFT, spaceBefore=18, spaceAfter=6,
    )

    dirigido = str(config.get("dirigido_a") or "").strip()
    elementos: list = []

    if dirigido:
        elementos.append(Paragraph(f"<b>{_txt(dirigido)}</b>", estilo_fecha))
    # (fecha superior eliminada por decisión del cliente — la fecha ya aparece
    #  en la línea "La presente certificación se expide en... el <fecha>")

    # Palabra "CERTIFICA" centrada
    elementos.append(Paragraph("<b>CERTIFICA</b>", estilo_certifica))

    # 2 espacios verticales adicionales después de CERTIFICA
    elementos.append(Spacer(1, 22))

    # Cuerpo en prosa
    elementos.append(Paragraph(cuerpo, estilo_cuerpo_carta))

    # Línea de expedición
    elementos.append(Paragraph(linea_expedicion, estilo_cuerpo_carta))

    # Despedida "Cordialmente,"
    elementos.append(Paragraph("Cordialmente,", estilo_despedida))

    # Espacio para firma (mínimo 25 mm como pide el brief)
    elementos.append(Spacer(1, 2.6 * cm))

    # Firma alineada a la izquierda (estilo carta empresarial)
    elementos.append(_firmas(empresa, None, estilos, paleta, incluir_empleado=False, compacto=True))

    # Verificación discreta
    elementos.append(Spacer(1, 10))
    correo = _txt(empresa.get('correo_empresa') or 'corporativo de la empresa')
    estilo_verificacion = ParagraphStyle(
        "VerifCert", parent=estilos["cuerpo"], fontSize=8.5, leading=11,
        alignment=TA_LEFT, textColor=paleta["texto_suave"],
    )
    elementos.append(Paragraph(
        f"Para verificar la autenticidad de esta certificación, "
        f"comuníquese al correo <b>{correo}</b>.",
        estilo_verificacion,
    ))

    return _build(
        ruta, "CERTIFICACIÓN LABORAL", "certificado", empleado_raw, empresa_raw,
        elementos, "compacto", disenio, usar_marca_agua,
        impresion_economica=bool(config.get("impresion_economica")),
        usuario=config.get("usuario_generador", "Usuario autenticado"),
        numero_documento=config.get("numero_documento"),
        estado_documento=config.get("estado_documento", "Emitido"),
    )


def _texto_pago(config: dict) -> str:
    periodicidad = str(config.get("periodicidad_pago") or "mensual").strip().lower()
    forma = str(config.get("forma_pago") or "transferencia bancaria").strip().lower()
    dias = str(config.get("dia_pago") or "").strip()
    if periodicidad == "quincenal" and ("15" in dias or not dias):
        return f"El salario será pagado quincenalmente mediante {forma}, el día quince (15) y el último día hábil de cada mes."
    if dias:
        return f"El salario será pagado con periodicidad {periodicidad}, mediante {forma}, en la fecha habitual: {dias}."
    return f"El salario será pagado con periodicidad {periodicidad}, mediante {forma}, conforme al calendario de nómina comunicado por el EMPLEADOR."


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
        funciones = ["Cumplir las responsabilidades definidas en el perfil de cargo vigente y las instrucciones compatibles con la naturaleza del puesto."]
    funciones_html = "".join(f"<br/>• {_txt(f)}" for f in funciones)
    horario = _txt(config.get("horario") or "horario comunicado por el empleador")
    descanso = _txt(config.get("dia_descanso") or "día de descanso definido en la programación")
    modalidad = _txt(config.get("modalidad_laboral") or "presencial")
    lugar = _txt(config.get("lugar_trabajo") or empresa["ciudad"])
    pago = _texto_pago(config)
    otros_pagos = str(config.get("otros_pagos") or "").strip()
    salario_texto = f"El salario mensual convenido es <b>{formato_moneda(empleado['salario'])} COP</b>. {pago}"
    if otros_pagos:
        salario_texto += f" Adicionalmente, se reconoce: <b>{_txt(otros_pagos)}</b>."

    clauses: list[tuple[str, str]] = [
        ("OBJETO, CARGO Y FUNCIONES",
         f"El TRABAJADOR prestará personalmente sus servicios en el cargo de <b>{_txt(empleado['cargo'])}</b>. "
         f"Sus funciones principales son:{funciones_html}<br/>El perfil de cargo vigente forma parte integral del contrato."),
        ("DURACIÓN E INICIO",
         f"El contrato es a término indefinido y comienza el <b>{_fecha(config.get('fecha_inicio_contrato'))}</b>."),
    ]
    if config.get("periodo_prueba", False):
        clauses.append(("PERÍODO DE PRUEBA",
            f"Las partes pactan por escrito un período de prueba de <b>{_txt(config.get('duracion_periodo_prueba', 'dos (2) meses'))}</b>, "
            "dentro de los límites y condiciones legalmente aplicables."))
    clauses.extend([
        ("LUGAR Y MODALIDAD DE TRABAJO",
         f"El servicio se prestará principalmente en <b>{lugar}</b>, bajo modalidad <b>{modalidad}</b>. "
         "Los cambios permanentes se comunicarán y documentarán cuando corresponda."),
        ("JORNADA Y DESCANSO",
         f"La jornada será <b>{_txt(config.get('jornada') or 'diurna')}</b>, con horario <b>{horario}</b>, "
         f"una distribución de <b>{_txt(config.get('distribucion_semanal') or 'la jornada semanal vigente')}</b> y "
         f"descanso en <b>{descanso}</b>, sin exceder la jornada máxima legal."),
        ("SALARIO Y FORMA DE PAGO", salario_texto),
        ("HERRAMIENTAS Y ELEMENTOS",
         "El EMPLEADOR suministrará las herramientas y elementos necesarios para el desarrollo de las funciones, "
         "los cuales se documentarán en actas o inventarios independientes cuando corresponda."),
        ("OBLIGACIONES Y SEGURIDAD Y SALUD",
         "Las partes cumplirán las obligaciones legales, el Sistema de Gestión de Seguridad y Salud en el Trabajo, "
         "el reglamento interno y las políticas aplicables."),
        ("CONFIDENCIALIDAD Y PROPIEDAD INTELECTUAL",
         "El TRABAJADOR protegerá la información reservada a la que tenga acceso. Las reglas de propiedad intelectual "
         "se aplicarán según la naturaleza de las funciones y los anexos expresamente pactados."),
        ("TRATAMIENTO DE DATOS PERSONALES",
         f"El responsable del tratamiento es <b>{_txt(empresa['nombre'])}</b>. Los datos serán tratados para gestionar la relación laboral, "
         f"nómina, seguridad social, bienestar, seguridad y cumplimiento legal. El canal de atención es "
         f"<b>{_txt(empresa.get('correo_empresa') or 'el definido en la política corporativa')}</b>."),
        ("TERMINACIÓN",
         "El contrato podrá terminar por las causas y mediante los procedimientos previstos en la ley. La causa, la fecha efectiva "
         "y los valores correspondientes deberán quedar documentados."),
        ("NOTIFICACIONES",
         f"Las comunicaciones se remitirán a los datos registrados por las partes. El canal corporativo es "
         f"<b>{_txt(empresa.get('correo_empresa') or 'el informado por el EMPLEADOR')}</b>."),
        ("ANEXOS Y ENTREGA DE EJEMPLARES",
         f"Hacen parte del contrato los anexos expresamente relacionados, entre ellos: "
         f"<b>{_txt(config.get('anexos') or 'perfil de cargo y políticas aceptadas')}</b>. Cada parte recibe un ejemplar o acceso verificable."),
    ])

    partes = _tabla_datos([
        ("Empleador", empresa["nombre"]), ("NIT", empresa["nit"]),
        ("Representante", empresa["representante"]), ("Domicilio", empresa["ciudad"]),
        ("Trabajador", empleado["nombre"]), ("Identificación", f"{empleado['tipo_documento']} {empleado['documento']}"),
        ("Cargo", empleado["cargo"]), ("Fecha de inicio", _fecha(config.get("fecha_inicio_contrato"))),
    ], estilos, paleta, 15.7 * cm, columnas=2)
    elementos: list = [partes, Spacer(1, 6), _parrafo(
        "Entre las partes identificadas se celebra el presente contrato individual de trabajo, regido por la normativa laboral colombiana y las cláusulas siguientes:",
        estilos, justificar=True,
    )]
    corte_pagina = 5 if len(clauses) >= 11 else 7
    for idx, (nombre_clause, texto_clause) in enumerate(clauses):
        ordinal = ORDINALES[idx] if idx < len(ORDINALES) else f"CLÁUSULA {idx + 1}"
        elementos.append(_parrafo(f"<b>{ordinal} - {_txt(nombre_clause)}:</b> {texto_clause}", estilos, justificar=True))
        if idx + 1 == corte_pagina:
            elementos.append(PageBreak())
    elementos.extend([
        _parrafo(
            f"Se firma en <b>{_txt(empresa['ciudad'])}</b>, el <b>{_fecha(config.get('fecha_celebracion') or date.today())}</b>.",
            estilos,
        ),
        Spacer(1, 12),
        _firmas(empresa, empleado, estilos, paleta, incluir_empleado=True),
    ])
    return _build(
        ruta, "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO",
        "contrato_indefinido", empleado_raw, empresa_raw, elementos,
        "amplio", disenio, usar_marca_agua,
        impresion_economica=bool(config.get("impresion_economica")),
        usuario=config.get("usuario_generador", "Usuario autenticado"),
        numero_documento=config.get("numero_documento"),
        estado_documento=config.get("estado_documento", "Aprobado"),
    )


def generar_dotacion_premium(empleado_raw: dict, empresa_raw: dict, ruta: str,
                              config: dict, disenio: int = 1,
                              usar_marca_agua: bool = False):
    hallazgos = validar_documento("dotacion", empleado_raw, empresa_raw, config)
    if hay_errores(hallazgos):
        raise ValueError("; ".join(h.mensaje for h in hallazgos if h.nivel == Nivel.ERROR))
    empleado, empresa = _empleado_normalizado(empleado_raw), _empresa_normalizada(empresa_raw)
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    estilos = crear_estilos(paleta, perfil="compacto")
    fecha_entrega = config.get("fecha_entrega")
    lugar = config.get("lugar_entrega") or empresa["ciudad"]

    responsable_nombre, responsable_cargo = _separar_nombre_cargo(
        config.get("responsable_entrega") or empresa["representante"], "Responsable de la entrega"
    )

    # ─── Destinatario (SIN "CC. No. XXXX" al lado — solo nombre y cargo) ─────
    estilo_destinatario = ParagraphStyle(
        "DestinatarioActa", parent=estilos["cuerpo"], fontSize=10.5, leading=14,
        alignment=TA_LEFT, spaceAfter=14,
    )
    destinatario_lineas = [
        f"<b>Señor(a):</b> <b>{_txt(empleado['nombre']).upper()}</b>",
    ]
    if empleado.get("cargo"):
        destinatario_lineas.append(f"<b>Cargo:</b> {_txt(empleado['cargo']).upper()}")
    destinatario_html = "<br/>".join(destinatario_lineas)

    # ─── Intro con contexto y fundamento legal solo si aplica ────────────────
    tipo_entrega = str(config.get("tipo_entrega") or "").lower()
    if tipo_entrega == "dotacion_legal" and config.get("cumple_requisitos_dotacion"):
        fundamento = ", en cumplimiento del Art. 230 del Código Sustantivo del Trabajo"
    else:
        fundamento = ""

    intro = (
        f"<b>{_txt(empresa['nombre'])}</b> hace constar que en la fecha "
        f"<b>{_fecha(fecha_entrega)}</b>, hace entrega al(la) trabajador(a) de los "
        f"siguientes elementos de dotación para el desarrollo de sus funciones{fundamento}:"
    )
    estilo_intro = ParagraphStyle(
        "IntroActa", parent=estilos["cuerpo"], fontSize=10.5, leading=14,
        alignment=TA_JUSTIFY, spaceAfter=14,
    )

    # ─── Tabla con columna # (numeración) como en el modelo del cliente ──────
    cell = ParagraphStyle("CeldaDotacion", parent=estilos["cuerpo_izq"],
                            fontSize=9.5, leading=11, spaceAfter=0, alignment=TA_LEFT)
    cell_center = ParagraphStyle("CeldaDotacionCentro", parent=cell, alignment=TA_CENTER)
    header_cell = ParagraphStyle("CabeceraDotacion", parent=cell_center,
                                    textColor=colors.white, fontName="Helvetica-Bold",
                                    fontSize=10)

    items = config.get("items") or []

    # Detectar si alguna fila tiene talla registrada. Si ninguna la tiene,
    # ocultamos la columna para no mostrar espacios vacíos.
    mostrar_talla = any(str(x.get("talla") or "").strip() for x in items)

    if mostrar_talla:
        headers = ["#", "Descripción", "Talla", "Cantidad", "Estado"]
    else:
        headers = ["#", "Descripción", "Cantidad", "Estado"]

    filas = [[Paragraph(h, header_cell) for h in headers]]
    for idx, item in enumerate(items, start=1):
        fila = [Paragraph(str(idx), cell_center),
                 Paragraph(_txt(item.get("descripcion")), cell)]
        if mostrar_talla:
            fila.append(Paragraph(_txt(item.get("talla")), cell_center))
        fila.append(Paragraph(_txt(item.get("cantidad")), cell_center))
        fila.append(Paragraph(_txt(item.get("estado") or "Nuevo"), cell_center))
        filas.append(fila)

    # Anchos: A4 con márgenes 22/22 mm → ancho útil ~166 mm = 16.6 cm
    if mostrar_talla:
        col_widths = [1.2 * cm, 8.4 * cm, 1.8 * cm, 2.2 * cm, 3.0 * cm]
    else:
        col_widths = [1.2 * cm, 10.2 * cm, 2.2 * cm, 3.0 * cm]

    tabla = Table(filas, colWidths=col_widths,
                    repeatRows=1, splitByRow=1, hAlign="CENTER")
    tabla.setStyle(TableStyle([
        # Encabezado con fondo azul corporativo (estilo modelo)
        ("BACKGROUND", (0, 0), (-1, 0), paleta["primario"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        # Bordes finos
        ("GRID", (0, 0), (-1, -1), 0.5, paleta["borde"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Padding cómodo (evitar textos apretados)
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    # ─── Declaración de recibido ────────────────────────────────────────────
    if tipo_entrega in ("dotacion_legal", "uniforme", "epp"):
        declaracion_texto = (
            "El(la) trabajador(a) se compromete a hacer buen uso de los elementos entregados, "
            "mantenerlos en buen estado y devolverlos en caso de terminación del contrato de trabajo o "
            "cuando la empresa así lo requiera. Con su firma manifiesta haber recibido a satisfacción "
            "los elementos detallados."
        )
    else:
        declaracion_texto = (
            "El(la) trabajador(a) manifiesta haber recibido los elementos relacionados, se compromete "
            "a destinarlos al desarrollo de sus funciones y a utilizarlos conforme a las políticas "
            "internas de la empresa."
        )
    estilo_declaracion = ParagraphStyle(
        "DeclaracionActa", parent=estilos["cuerpo"], fontSize=10.5, leading=14,
        alignment=TA_JUSTIFY, spaceBefore=14, spaceAfter=8,
    )

    # ─── Ensamblaje con distribución equilibrada ────────────────────────────
    elementos = [
        Paragraph(destinatario_html, estilo_destinatario),
        Paragraph(intro, estilo_intro),
        tabla,
        Paragraph(declaracion_texto, estilo_declaracion),
    ]

    if config.get("mostrar_observaciones_generales") and config.get("observaciones"):
        estilo_obs = ParagraphStyle(
            "ObsActa", parent=estilos["cuerpo"], fontSize=10, leading=13,
            alignment=TA_JUSTIFY, spaceAfter=8,
        )
        elementos.append(Paragraph(f"<b>Observaciones:</b> {_txt(config['observaciones'])}", estilo_obs))

    # Espacio antes de firmas — mínimo 25 mm para firma manuscrita como pide el brief
    elementos.append(Spacer(1, 2.6 * cm))

    elementos.append(_firmas(
        empresa, empleado, estilos, paleta, incluir_empleado=True,
        izquierdo_nombre=responsable_nombre, izquierdo_cargo=responsable_cargo,
        compacto=True,
    ))

    return _build(
        ruta, "ACTA DE ENTREGA DE DOTACIÓN", "dotacion", empleado_raw, empresa_raw,
        elementos, "compacto", disenio, usar_marca_agua,
        impresion_economica=bool(config.get("impresion_economica")),
        usuario=config.get("usuario_generador", "Usuario autenticado"),
        numero_documento=config.get("numero_documento"),
        estado_documento=config.get("estado_documento", "Aprobado"),
    )


def _periodo_salario(resultado: dict) -> str:
    dias = int(resultado.get("Dias salario pendiente", 0) or 0)
    if dias <= 0:
        return ""
    inicio = resultado.get("Periodo salario inicio")
    fin = resultado.get("Periodo salario fin") or resultado.get("Fecha corte")
    if not inicio:
        corte = _fecha_obj(fin)
        if corte:
            inicio = corte - timedelta(days=dias - 1)
    return f"{_fecha_corta(inicio)} al {_fecha_corta(fin)}"


def _tabla_conceptos(conceptos: list[dict], estilos: dict, paleta: dict) -> Table:
    cell = ParagraphStyle("CeldaLiqFinal", parent=estilos["cuerpo_izq"], fontSize=6.9, leading=8.0, spaceAfter=0)
    head = ParagraphStyle("CabeceraLiqFinal", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    headers = ["Concepto", "Periodo", "Días", "Base", "Devengado", "Deducción", "Neto"]
    filas = [[Paragraph(h, head) for h in headers]]
    for c in conceptos:
        dev = float(c.get("devengado", 0) or 0)
        ded = float(c.get("deduccion", 0) or 0)
        net = float(c.get("neto", dev - ded) or 0)
        filas.append([
            Paragraph(_txt(c.get("concepto")), cell), Paragraph(_txt(c.get("periodo")), cell),
            Paragraph(_txt(c.get("dias")), cell), Paragraph(formato_moneda(c.get("base", 0)), cell),
            Paragraph(formato_moneda(dev) if dev else "", cell),
            Paragraph(formato_moneda(ded) if ded else "", cell),
            Paragraph(formato_moneda(net), cell),
        ])
    tabla = Table(filas, colWidths=[3.15 * cm, 3.05 * cm, .75 * cm, 2.2 * cm, 2.15 * cm, 2.05 * cm, 2.15 * cm], repeatRows=1, splitByRow=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), paleta["primario"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .3, paleta["borde"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabla


def _tabla_deducciones(items: list[dict], estilos: dict, paleta: dict) -> Table:
    cell = ParagraphStyle("CeldaDeduccion", parent=estilos["cuerpo_izq"], fontSize=7.2, leading=8.2, spaceAfter=0)
    head = ParagraphStyle("CabeceraDeduccion", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    filas = [[Paragraph(x, head) for x in ["Concepto", "Base", "Tarifa", "Valor"]]]
    for item in items:
        tarifa = item.get("tarifa")
        tarifa_txt = f"{float(tarifa) * 100:g}%" if isinstance(tarifa, (int, float)) else str(tarifa or "")
        filas.append([
            Paragraph(_txt(item.get("concepto")), cell),
            Paragraph(formato_moneda(item.get("base", 0)), cell),
            Paragraph(_txt(tarifa_txt), cell),
            Paragraph(formato_moneda(item.get("valor", 0)), cell),
        ])
    tabla = Table(filas, colWidths=[7.4 * cm, 3.1 * cm, 2.2 * cm, 3.2 * cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), paleta["primario"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .3, paleta["borde"]),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabla


def generar_liquidacion_premium(resultado: dict, empresa_raw: dict, ruta: str,
                                  disenio: int = 1, usar_marca_agua: bool = False,
                                  config: dict | None = None):
    config = config or {}
    empleado_raw = {
        "Nombre": resultado.get("Nombre", ""), "Documento": resultado.get("Documento", ""),
        "Tipo documento": resultado.get("Tipo documento", "C.C."), "Cargo": resultado.get("Cargo", ""),
        "Tipo contrato": resultado.get("Tipo contrato", ""), "Salario": resultado.get("Salario base", 0),
        "Fecha ingreso": resultado.get("Fecha ingreso", ""), "Fecha retiro": resultado.get("Fecha corte", ""),
        "Cuenta bancaria": resultado.get("Cuenta bancaria", ""),
    }
    val_config = {
        "fecha_corte": resultado.get("Fecha corte"), "motivo_retiro": resultado.get("Motivo retiro"),
        "pagos_previos_confirmados": config.get("pagos_previos_confirmados", resultado.get("Pagos previos confirmados", False)),
        "novedades_confirmadas": config.get("novedades_confirmadas", resultado.get("Novedades confirmadas", False)),
        "dias_salario_pendiente": resultado.get("Dias salario pendiente", 0),
        "estado_aportes_periodo_final": resultado.get("Estado aportes periodo final"),
        "aporte_salud_ya_descontado": resultado.get("Aporte salud ya descontado", 0),
        "aporte_pension_ya_descontado": resultado.get("Aporte pension ya descontado", 0),
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
    fecha_ingreso = _fecha_corta(resultado.get("Fecha ingreso"))
    fecha_corte = _fecha_corta(resultado.get("Fecha corte"))
    conceptos: list[dict] = []

    def agregar(concepto, periodo, dias, base, valor):
        valor = float(valor or 0)
        if valor > 0:
            conceptos.append({"concepto": concepto, "periodo": periodo, "dias": dias, "base": base, "devengado": valor, "neto": valor})

    agregar("Salario pendiente", _periodo_salario(resultado), resultado.get("Dias salario pendiente", 0),
            resultado.get("Salario base", 0), resultado.get("Salario pendiente (estimado)", 0))
    agregar("Cesantías", f"{fecha_ingreso} al {fecha_corte}", dias_total, base_prestacional,
            resultado.get("Cesantias (Art. 249 CST)", 0))
    agregar("Intereses de cesantías", f"{fecha_ingreso} al {fecha_corte}", resultado.get("Dias intereses cesantias", dias_total),
            base_prestacional, resultado.get("Intereses cesantias 12% (Ley 52/75)", 0))
    agregar("Prima de servicios", f"{_fecha_corta(resultado.get('Inicio periodo prima') or fecha_ingreso)} al {fecha_corte}",
            dias_prima, base_prestacional, resultado.get("Prima semestral (Art. 306 CST)", 0))
    agregar("Vacaciones", f"{fecha_ingreso} al {fecha_corte}", dias_total, base_vacaciones,
            resultado.get("Vacaciones (Art. 186 CST)", 0))
    agregar("Indemnización", fecha_corte, resultado.get("Indemnizacion dias", 0), resultado.get("Salario base", 0),
            resultado.get("Indemnizacion (Art. 64 CST)", 0))
    for extra in resultado.get("Otros conceptos", []) or []:
        agregar(etiqueta_formal(extra.get("concepto"), "Otro concepto"),
                f"{_fecha_corta(extra.get('periodo_inicial'))} al {_fecha_corta(extra.get('periodo_final'))}",
                extra.get("dias", ""), extra.get("base", 0), extra.get("valor", 0))

    # ─── Recargos adicionales (adicionados manualmente por el usuario) ───────
    # Se agregan como conceptos devengados normales dentro del detalle.
    # Formato esperado: [{"concepto": "Recargo nocturno", "periodo": "...", "dias": N, "base": X, "valor": Y}, ...]
    for recargo in resultado.get("Recargos adicionales", []) or []:
        agregar(
            etiqueta_formal(recargo.get("concepto"), "Recargo"),
            recargo.get("periodo", ""),
            recargo.get("dias", ""),
            recargo.get("base", 0),
            recargo.get("valor", 0),
        )

    # ─── Cálculo automático de aportes de salud y pensión pendientes ─────────
    # Cuando hay salario pendiente en la liquidación, se determina si los
    # aportes de nómina ya fueron descontados o hay que descontarlos aquí.
    #
    # BASE DE APORTE:
    # Los aportes de salud/pensión se causan sobre el salario mensual completo
    # (no sobre los días pendientes). Ejemplo con salario $2.000.000:
    #   - Base quincenal: $1.000.000  (aporte 4% = $40.000)
    #   - Base mensual: $2.000.000    (aporte 4% = $80.000)
    #
    # ESTADOS:
    #   descontados_completamente   → NO descontar nada
    #   descontados_segunda_quincena → NO descontar (todo cubierto)
    #   descontados_primera_quincena → Descontar SOLO 2da quincena (base = salario/2)
    #   descontados_fin_de_mes      → Descontar TODO el mes (base = salario mensual)
    #   no_descontados               → Descontar TODO el mes (base = salario mensual)
    #   descontados_parcialmente     → Descontar diferencia según valores registrados
    #   revision_manual              → No calcular, dejar tal cual
    ded_ley_calculadas = list(resultado.get("Deducciones de ley") or [])
    tiene_deducciones_previas = any(
        x for x in ded_ley_calculadas
        if float(x.get("valor", 0) or 0) > 0
    )
    dias_pendientes = int(resultado.get("Dias salario pendiente", 0) or 0)
    salario_base_mensual = float(resultado.get("Salario base", 0) or 0)
    estado_aportes = str(resultado.get("Estado aportes periodo final") or "").strip().lower()

    if dias_pendientes > 0 and salario_base_mensual > 0 and not tiene_deducciones_previas:
        base_aporte_mensual = salario_base_mensual         # $2.000.000
        base_aporte_quincenal = salario_base_mensual / 2   # $1.000.000

        base_aporte = 0.0  # base efectiva sobre la que se calculará
        etiqueta_periodo = ""

        if estado_aportes in ("descontados_fin_de_mes", "no_descontados"):
            # Descontar sobre el mes completo
            base_aporte = base_aporte_mensual
            etiqueta_periodo = ""  # sin sufijo, es el aporte estándar mensual
        elif estado_aportes == "descontados_primera_quincena":
            # Solo falta la segunda quincena
            base_aporte = base_aporte_quincenal
            etiqueta_periodo = " (2da quincena)"
        elif estado_aportes == "descontados_parcialmente":
            # Aporte esperado del mes completo menos lo que ya se descontó
            aporte_completo_salud = round(base_aporte_mensual * 0.04, 0)
            aporte_completo_pension = round(base_aporte_mensual * 0.04, 0)
            salud_ya = float(resultado.get("Aporte salud ya descontado", 0) or 0)
            pension_ya = float(resultado.get("Aporte pension ya descontado", 0) or 0)
            salud_pendiente = max(0, aporte_completo_salud - salud_ya)
            pension_pendiente = max(0, aporte_completo_pension - pension_ya)
            if salud_pendiente > 0:
                ded_ley_calculadas.append({
                    "concepto": "Salud trabajador (pendiente)",
                    "base": base_aporte_mensual, "tarifa": "4%",
                    "valor": salud_pendiente,
                })
            if pension_pendiente > 0:
                ded_ley_calculadas.append({
                    "concepto": "Pensión trabajador (pendiente)",
                    "base": base_aporte_mensual, "tarifa": "4%",
                    "valor": pension_pendiente,
                })
            base_aporte = 0.0  # ya se procesó arriba
        # Estados "descontados_completamente", "descontados_segunda_quincena",
        # "revision_manual" y desconocidos → base_aporte = 0 (no descontar)

        if base_aporte > 0:
            valor_salud = round(base_aporte * 0.04, 0)
            valor_pension = round(base_aporte * 0.04, 0)
            if valor_salud > 0:
                ded_ley_calculadas.append({
                    "concepto": f"Salud trabajador{etiqueta_periodo}",
                    "base": base_aporte, "tarifa": "4%",
                    "valor": valor_salud,
                })
            if valor_pension > 0:
                ded_ley_calculadas.append({
                    "concepto": f"Pensión trabajador{etiqueta_periodo}",
                    "base": base_aporte, "tarifa": "4%",
                    "valor": valor_pension,
                })

    ded_ley = [x for x in ded_ley_calculadas if float(x.get("valor", 0) or 0) > 0]
    ded_aut = [x for x in (resultado.get("Deducciones autorizadas detalle") or []) if float(x.get("valor", 0) or 0) > 0]
    if not ded_aut and float(resultado.get("TOTAL DEDUCCIONES AUTORIZADAS", 0) or 0) > 0:
        ded_aut = [{"concepto": "Descuentos autorizados registrados", "base": resultado.get("TOTAL DEDUCCIONES AUTORIZADAS"), "tarifa": "", "valor": resultado.get("TOTAL DEDUCCIONES AUTORIZADAS")}]
    bruto = float(resultado.get("TOTAL DEVENGADO", 0) or 0)
    # Siempre recalcular total_ley desde las deducciones actuales, para incluir
    # los aportes calculados automáticamente arriba (salud/pensión pendientes)
    total_ley = sum(float(x.get("valor", 0) or 0) for x in ded_ley)
    total_aut = float(resultado.get("TOTAL DEDUCCIONES AUTORIZADAS", sum(float(x.get("valor", 0) or 0) for x in ded_aut)) or 0)
    # El neto se recalcula automáticamente si los totales cambiaron
    neto_original = float(resultado.get("NETO A PAGAR", 0) or 0)
    total_deducciones = total_ley + total_aut
    total_ley_original = float(resultado.get("TOTAL DEDUCCIONES DE LEY", 0) or 0)
    if abs(total_ley - total_ley_original) > 1:  # cambió el total de deducciones
        neto = bruto - total_deducciones
    else:
        neto = neto_original if neto_original > 0 else (bruto - total_deducciones)

    resumen = Table([
        ["TOTAL BRUTO", formato_moneda(bruto)],
        ["TOTAL DEDUCCIONES", formato_moneda(total_ley + total_aut)],
        ["NETO A PAGAR", formato_moneda(neto)],
    ], colWidths=[10.7 * cm, 5.2 * cm], hAlign="RIGHT")
    resumen.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), .4, paleta["borde"]),
        ("BACKGROUND", (0, -1), (-1, -1), paleta["secundario"]), ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    bases = [
        ("Salario mensual", formato_moneda(resultado.get("Salario base", 0))),
        ("Base cesantías y prima", formato_moneda(base_prestacional)),
        ("Base vacaciones", formato_moneda(base_vacaciones)),
    ]
    if float(resultado.get("Auxilio transporte valor", 0) or 0) > 0:
        bases.append(("Auxilio de transporte", formato_moneda(resultado.get("Auxilio transporte valor", 0))))
    elementos: list = [
        _tabla_datos([
            ("Trabajador", empleado["nombre"]), ("Identificación", empleado["documento"]),
            ("Fecha de ingreso", _fecha(empleado["fecha_ingreso"])), ("Fecha de retiro", _fecha(empleado["fecha_retiro"])),
            ("Causa de retiro", etiqueta_formal(resultado.get("Motivo retiro"))), ("Tipo de contrato", empleado["tipo_contrato"]),
        ], estilos, paleta, 15.9 * cm, columnas=2, compacto=True),
        _seccion("Bases principales", estilos, paleta, compacto=True),
        _tabla_datos(bases, estilos, paleta, 15.9 * cm, columnas=2, compacto=True),
        _seccion("Detalle de conceptos", estilos, paleta, compacto=True),
        _tabla_conceptos(conceptos, estilos, paleta),
    ]
    if ded_ley:
        elementos.extend([_seccion("Deducciones de ley", estilos, paleta, compacto=True), _tabla_deducciones(ded_ley, estilos, paleta)])
    if ded_aut:
        elementos.extend([_seccion("Deducciones autorizadas", estilos, paleta, compacto=True), _tabla_deducciones(ded_aut, estilos, paleta)])
    elementos.extend([
        Spacer(1, 5), resumen,
        _parrafo(f"<b>Valor en letras:</b> {_txt(numero_a_letras(neto))}.", estilos, compacto=True),
        _parrafo(
            "Liquidación generada con base en los datos y novedades registrados por la empresa. Los ajustes derivados de "
            "información adicional deberán documentarse mediante una nueva versión.",
            estilos, compacto=True, justificar=True,
        ),
        Spacer(1, 5),
        _firmas(empresa, empleado, estilos, paleta, incluir_empleado=True, compacto=True),
    ])
    return _build(
        ruta, "LIQUIDACIÓN DE PRESTACIONES SOCIALES", "liquidacion",
        empleado_raw, empresa_raw, elementos, "compacto", disenio, usar_marca_agua,
        impresion_economica=bool(config.get("impresion_economica")),
        usuario=config.get("usuario_generador", "Usuario autenticado"),
        numero_documento=config.get("numero_documento"),
        estado_documento=config.get("estado_documento", "Aprobado"),
    )
