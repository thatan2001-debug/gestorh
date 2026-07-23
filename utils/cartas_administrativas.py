"""
Cartas administrativas de RRHH.

Documentos incluidos:
- Comunicación de cambio de horario
- Comunicación de cambio de cargo
- Comunicación de cambio salarial (aumento)
- Comunicación de cambio de sede
- Comunicación de ascenso
- Carta de reconocimiento/felicitación
- Permiso remunerado
- Constancia de retiro
- Acta de entrega de dotación
- Autorización de descuento

Todos usan el mismo motor de PDF (utils/plantillas_disenio.py) y la
infraestructura visual (paletas, membrete, firmantes).

IMPORTANTE — Alcance legal:
Estas plantillas son ADMINISTRATIVAS de bajo riesgo legal. Las cartas
disciplinarias (llamados de atención, citación a descargos, despido con
justa causa) NO están aquí porque requieren asesoría jurídica específica
y debido proceso documentado.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from utils.plantillas_disenio import (
    PALETAS, _estilos_para, _encabezado, _firmas_dobles, _pie,
    MARGEN_SUP_NORMAL, MARGEN_SUP_MEMBRETE, MARGEN_INF,
    MARGEN_IZQ, MARGEN_DER,
)
from utils.fecha_utils import fmt_fecha, fecha_hoy_larga


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN BASE PARA CARTAS ADMINISTRATIVAS
# ══════════════════════════════════════════════════════════════════════════════

def _generar_carta_base(empleado, datos_empresa, ruta_salida, config,
                          titulo: str, contenido_fn, referencia: str = "",
                          disenio=1, usar_marca_agua=False,
                          membrete_path=None, usar_logo_enc=True,
                          incluir_firma_empleado=True):
    """
    Motor unificado para cartas administrativas.

    Args:
        titulo: título de la carta (ej: "COMUNICACIÓN DE CAMBIO DE HORARIO")
        contenido_fn: función que agrega los párrafos del cuerpo al elemento
        referencia: texto que aparece como "REF:" (opcional)
        incluir_firma_empleado: si False, solo firma la empresa
    """
    paleta = PALETAS.get(int(disenio), PALETAS[1])
    estilos = _estilos_para(paleta)

    # Inyectar los colores de la paleta a los estilos para uso en contenido_fn
    estilos["_paleta"] = paleta

    logo = datos_empresa.get("logo_path", "")
    membrete = membrete_path or datos_empresa.get("membrete_path", "")
    representante = datos_empresa.get("representante", "")
    firmante_nombre = datos_empresa.get("firmante_cert_nombre", representante) or representante
    firmante_cargo = datos_empresa.get("firmante_cert_cargo", "Representante Legal") or "Representante Legal"

    margen_sup = MARGEN_SUP_MEMBRETE if membrete else MARGEN_SUP_NORMAL
    doc = SimpleDocTemplate(
        ruta_salida, pagesize=letter,
        leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER,
        topMargin=margen_sup, bottomMargin=MARGEN_INF,
    )

    el = []
    _encabezado(el, datos_empresa, estilos, paleta, disenio,
                 logo_derecha=usar_logo_enc, membrete_path=membrete)

    # Referencia (número consecutivo o similar)
    if referencia:
        el.append(Paragraph(f"<b>Ref:</b> {referencia}", estilos["nota"]))
        el.append(Spacer(1, 6))

    # Ciudad y fecha
    ciudad = datos_empresa.get("ciudad", "Colombia")
    fecha_larga = fecha_hoy_larga()
    el.append(Paragraph(
        f"{ciudad}, {fecha_larga}",
        estilos["cuerpo"]))
    el.append(Spacer(1, 20))

    # Título
    el.append(Paragraph(titulo, estilos["titulo"]))
    el.append(Spacer(1, 16))

    # Destinatario
    nombre_emp = empleado.get("nombre", "")
    doc_emp = empleado.get("documento", "")
    cargo_emp = empleado.get("cargo", "")

    el.append(Paragraph(
        f"<b>Señor(a):</b><br/>"
        f"<b>{nombre_emp.upper()}</b><br/>"
        f"C.C. No. {doc_emp}<br/>"
        f"{cargo_emp}<br/>"
        f"Ciudad",
        estilos["cuerpo"]))
    el.append(Spacer(1, 20))

    # Cuerpo dinámico (aportado por la función específica)
    contenido_fn(el, empleado, datos_empresa, config, estilos)

    el.append(Spacer(1, 30))

    # Cordialmente / firmas
    el.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    el.append(Spacer(1, 40))

    if incluir_firma_empleado:
        _firmas_dobles(el,
            representante=firmante_nombre,
            empresa=datos_empresa.get("nombre", ""),
            nombre_empleado=nombre_emp,
            cedula=doc_emp,
            paleta=paleta,
            estilos=estilos,
            cargo_firmante=firmante_cargo,
        )
    else:
        # Solo firma la empresa
        el.append(Paragraph(f"<b>{firmante_nombre}</b>", estilos["firma_nombre"]))
        el.append(Paragraph(firmante_cargo, estilos["firma_cargo"]))
        el.append(Paragraph(datos_empresa.get("nombre", ""), estilos["firma_cargo"]))

    _fn = lambda c, d: _pie(c, d, paleta, logo, usar_marca_agua)
    doc.build(el, onFirstPage=_fn, onLaterPages=_fn)


# ══════════════════════════════════════════════════════════════════════════════
# CAMBIO DE HORARIO
# ══════════════════════════════════════════════════════════════════════════════

def generar_cambio_horario(empleado, datos_empresa, ruta_salida, config,
                             disenio=1, usar_marca_agua=False,
                             membrete_path=None, usar_logo_enc=True):
    """
    Comunica al empleado un cambio en su horario de trabajo.

    config debe contener:
    - horario_actual: str (ej: "Lunes a viernes 8am-5pm")
    - horario_nuevo:  str (ej: "Lunes a viernes 7am-4pm")
    - fecha_vigencia: str (dd/mm/yyyy)
    - justificacion:  str (opcional)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        horario_actual = config.get("horario_actual", empleado.get("horario", "el actual"))
        horario_nuevo = config.get("horario_nuevo", "")
        fecha_vig = fmt_fecha(config.get("fecha_vigencia", ""))
        justif = config.get("justificacion", "").strip()

        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"Por medio de la presente, <b>{empresa}</b> le comunica que a partir "
            f"del <b>{fecha_vig}</b>, se modificará su horario de trabajo.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        # Tabla de cambio
        tabla_datos = [
            ["Situación", "Horario"],
            ["Horario actual", horario_actual or "—"],
            ["Nuevo horario", horario_nuevo],
        ]
        t = Table(tabla_datos, colWidths=[5*cm, 10*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        if justif:
            el.append(Paragraph(
                f"<b>Justificación:</b> {justif}",
                estilos["cuerpo"]))
            el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Este cambio busca garantizar la buena marcha de las operaciones "
            "de la empresa. Las demás condiciones de su contrato de trabajo "
            "se mantienen inalteradas.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Con su firma en el presente documento, usted manifiesta haber "
            "sido informado(a) y aceptar las nuevas condiciones de horario.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="COMUNICACIÓN DE CAMBIO DE HORARIO",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CAMBIO DE CARGO
# ══════════════════════════════════════════════════════════════════════════════

def generar_cambio_cargo(empleado, datos_empresa, ruta_salida, config,
                           disenio=1, usar_marca_agua=False,
                           membrete_path=None, usar_logo_enc=True):
    """
    config:
    - cargo_actual:   str (o toma del empleado)
    - cargo_nuevo:    str
    - fecha_vigencia: str
    - salario_nuevo:  float (opcional, si viene con cambio salarial)
    - funciones_nuevas: str (opcional, texto descriptivo)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        cargo_actual = config.get("cargo_actual", empleado.get("cargo", ""))
        cargo_nuevo = config.get("cargo_nuevo", "")
        fecha_vig = fmt_fecha(config.get("fecha_vigencia", ""))
        salario_nuevo = config.get("salario_nuevo", 0)
        funciones = config.get("funciones_nuevas", "").strip()

        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"Por medio de la presente, <b>{empresa}</b> le comunica que a partir "
            f"del <b>{fecha_vig}</b>, usted asumirá un nuevo cargo dentro de la organización.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        # Tabla de cambio
        filas = [
            ["Situación", "Detalle"],
            ["Cargo actual", cargo_actual or "—"],
            ["Nuevo cargo", cargo_nuevo],
        ]
        if salario_nuevo and float(salario_nuevo) > 0:
            filas.append(["Nuevo salario",
                            f"${float(salario_nuevo):,.0f} COP".replace(",", ".")])

        t = Table(filas, colWidths=[5*cm, 10*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        if funciones:
            el.append(Paragraph(
                f"<b>Funciones principales del nuevo cargo:</b><br/>{funciones}",
                estilos["cuerpo"]))
            el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Este cambio se realiza teniendo en cuenta las necesidades operativas "
            "de la empresa y sus capacidades profesionales. Las demás condiciones "
            "del contrato de trabajo permanecen vigentes salvo las expresamente "
            "modificadas por este documento.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Con su firma en el presente documento, usted manifiesta aceptar "
            "las nuevas condiciones laborales aquí establecidas.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="COMUNICACIÓN DE CAMBIO DE CARGO",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CAMBIO SALARIAL (AUMENTO)
# ══════════════════════════════════════════════════════════════════════════════

def generar_cambio_salarial(empleado, datos_empresa, ruta_salida, config,
                              disenio=1, usar_marca_agua=False,
                              membrete_path=None, usar_logo_enc=True):
    """
    config:
    - salario_actual: float
    - salario_nuevo:  float
    - fecha_vigencia: str
    - motivo:         str (opcional: "reconocimiento a su desempeño", "ajuste legal", etc.)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        salario_actual = float(config.get("salario_actual", empleado.get("salario", 0)) or 0)
        salario_nuevo = float(config.get("salario_nuevo", 0) or 0)
        fecha_vig = fmt_fecha(config.get("fecha_vigencia", ""))
        motivo = config.get("motivo", "").strip()

        diferencia = salario_nuevo - salario_actual
        porcentaje = (diferencia / salario_actual * 100) if salario_actual > 0 else 0

        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"Por medio de la presente, <b>{empresa}</b> le comunica que a partir "
            f"del <b>{fecha_vig}</b> se realizará un ajuste en su remuneración salarial.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        # Tabla
        filas = [
            ["Concepto", "Valor"],
            ["Salario actual",
              f"${salario_actual:,.0f} COP".replace(",", ".")],
            ["Nuevo salario",
              f"${salario_nuevo:,.0f} COP".replace(",", ".")],
            ["Incremento",
              f"${diferencia:,.0f} COP ({porcentaje:.1f}%)".replace(",", ".")],
        ]
        t = Table(filas, colWidths=[5*cm, 10*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        if motivo:
            el.append(Paragraph(
                f"<b>Motivo del ajuste:</b> {motivo}",
                estilos["cuerpo"]))
            el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Las demás condiciones establecidas en su contrato individual de "
            "trabajo permanecen sin modificaciones. Este ajuste será aplicado "
            "en el pago de la próxima nómina.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Con su firma en el presente documento, usted manifiesta haber "
            "sido informado(a) y aceptar el nuevo salario.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="COMUNICACIÓN DE CAMBIO SALARIAL",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CAMBIO DE SEDE
# ══════════════════════════════════════════════════════════════════════════════

def generar_cambio_sede(empleado, datos_empresa, ruta_salida, config,
                          disenio=1, usar_marca_agua=False,
                          membrete_path=None, usar_logo_enc=True):
    """
    config:
    - sede_actual:    str
    - sede_nueva:     str
    - direccion_nueva: str (opcional)
    - fecha_vigencia: str
    - motivo:         str (opcional)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        sede_actual = config.get("sede_actual", empleado.get("sede", "la actual"))
        sede_nueva = config.get("sede_nueva", "")
        direccion_nueva = config.get("direccion_nueva", "").strip()
        fecha_vig = fmt_fecha(config.get("fecha_vigencia", ""))
        motivo = config.get("motivo", "").strip()

        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"Por medio de la presente, <b>{empresa}</b> le comunica que a partir "
            f"del <b>{fecha_vig}</b> su lugar habitual de trabajo será modificado.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        filas = [
            ["Situación", "Sede"],
            ["Sede actual", sede_actual or "—"],
            ["Nueva sede", sede_nueva],
        ]
        if direccion_nueva:
            filas.append(["Dirección de la nueva sede", direccion_nueva])

        t = Table(filas, colWidths=[6*cm, 9*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        if motivo:
            el.append(Paragraph(
                f"<b>Motivo del traslado:</b> {motivo}",
                estilos["cuerpo"]))
            el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Las demás condiciones de su contrato de trabajo se mantienen "
            "inalteradas. Le agradecemos su comprensión y colaboración con "
            "esta decisión que busca mejorar la operación de la empresa.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Con su firma en el presente documento, usted manifiesta haber "
            "sido informado(a) de este cambio.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="COMUNICACIÓN DE CAMBIO DE SEDE",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ASCENSO
# ══════════════════════════════════════════════════════════════════════════════

def generar_ascenso(empleado, datos_empresa, ruta_salida, config,
                      disenio=1, usar_marca_agua=False,
                      membrete_path=None, usar_logo_enc=True):
    """
    config:
    - cargo_actual:    str
    - cargo_nuevo:     str
    - salario_actual:  float
    - salario_nuevo:   float (opcional)
    - fecha_vigencia:  str
    - mensaje_personal: str (opcional, felicitación)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        cargo_actual = config.get("cargo_actual", empleado.get("cargo", ""))
        cargo_nuevo = config.get("cargo_nuevo", "")
        salario_actual = float(config.get("salario_actual", empleado.get("salario", 0)) or 0)
        salario_nuevo = float(config.get("salario_nuevo", 0) or 0)
        fecha_vig = fmt_fecha(config.get("fecha_vigencia", ""))
        mensaje = config.get("mensaje_personal", "").strip()

        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"Es un gusto para <b>{empresa}</b> comunicarle que ha sido "
            f"promovido(a) dentro de la organización, en reconocimiento a "
            f"su dedicación, compromiso y desempeño demostrado durante su "
            f"trayectoria con nosotros.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            f"A partir del <b>{fecha_vig}</b> sus nuevas condiciones "
            f"laborales serán las siguientes:",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        filas = [
            ["Concepto", "Anterior", "Nuevo"],
            ["Cargo", cargo_actual or "—", cargo_nuevo],
        ]
        if salario_nuevo > 0:
            filas.append(["Salario",
                            f"${salario_actual:,.0f}".replace(",", "."),
                            f"${salario_nuevo:,.0f}".replace(",", ".")])

        t = Table(filas, colWidths=[4*cm, 5.5*cm, 5.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 16))

        if mensaje:
            el.append(Paragraph(mensaje, estilos["cuerpo"]))
            el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Confiamos en que asumirá este nuevo reto con el profesionalismo "
            "que le caracteriza. Le deseamos muchos éxitos en esta nueva etapa "
            "profesional dentro de nuestra organización.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Con su firma en el presente documento, usted manifiesta aceptar "
            "las nuevas condiciones laborales.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="COMUNICACIÓN DE ASCENSO",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )


# ══════════════════════════════════════════════════════════════════════════════
# RECONOCIMIENTO / FELICITACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def generar_reconocimiento(empleado, datos_empresa, ruta_salida, config,
                             disenio=1, usar_marca_agua=False,
                             membrete_path=None, usar_logo_enc=True):
    """
    config:
    - motivo:         str ("cumplimiento de metas", "5 años de servicio", etc.)
    - detalle:        str (descripción detallada del logro)
    - fecha_logro:    str (opcional)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        motivo = config.get("motivo", "su excelente desempeño")
        detalle = config.get("detalle", "").strip()

        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"<b>{empresa}</b> desea expresarle su más sincero reconocimiento "
            f"por <b>{motivo}</b>.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        if detalle:
            el.append(Paragraph(detalle, estilos["cuerpo"]))
            el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Su dedicación, compromiso y la calidad de su trabajo constituyen "
            "un valioso aporte para la organización y un ejemplo positivo para "
            "todo el equipo humano.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Le agradecemos su esfuerzo y le animamos a continuar aportando "
            "su valioso talento a nuestra empresa.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Reciba un cordial saludo y nuestros mejores deseos.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="CARTA DE RECONOCIMIENTO",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
        incluir_firma_empleado=False,  # No requiere firma del empleado
    )


# ══════════════════════════════════════════════════════════════════════════════
# PERMISO REMUNERADO
# ══════════════════════════════════════════════════════════════════════════════

def generar_permiso(empleado, datos_empresa, ruta_salida, config,
                      disenio=1, usar_marca_agua=False,
                      membrete_path=None, usar_logo_enc=True):
    """
    config:
    - fecha_inicio:  str (dd/mm/yyyy)
    - fecha_fin:     str
    - motivo:        str ("cita médica", "diligencia personal", etc.)
    - remunerado:    bool (True por defecto)
    - dias:          int (calculado o aportado)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        fecha_ini = fmt_fecha(config.get("fecha_inicio", ""))
        fecha_fin = fmt_fecha(config.get("fecha_fin", ""))
        motivo = config.get("motivo", "").strip()
        remunerado = config.get("remunerado", True)
        dias = config.get("dias", 1)

        tipo_permiso = "REMUNERADO" if remunerado else "NO REMUNERADO"
        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"Por medio de la presente, <b>{empresa}</b> autoriza al trabajador "
            f"mencionado un permiso <b>{tipo_permiso}</b> conforme al siguiente "
            f"detalle:",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        filas = [
            ["Concepto", "Detalle"],
            ["Fecha de inicio", fecha_ini],
            ["Fecha de terminación", fecha_fin],
            ["Días autorizados", str(dias)],
            ["Motivo", motivo or "No especificado"],
            ["Tipo", "Con remuneración" if remunerado else "Sin remuneración"],
        ]
        t = Table(filas, colWidths=[5*cm, 10*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "El trabajador deberá reintegrarse a sus labores en la fecha "
            "señalada. Se recuerda que este permiso ha sido concedido con "
            "base en la confianza y responsabilidad del trabajador.",
            estilos["cuerpo"]))

        if not remunerado:
            el.append(Spacer(1, 12))
            el.append(Paragraph(
                "Los días no laborados durante este permiso no generarán "
                "remuneración salarial ni aportes a seguridad social.",
                estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo=f"AUTORIZACIÓN DE PERMISO LABORAL",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANCIA DE RETIRO
# ══════════════════════════════════════════════════════════════════════════════

def generar_constancia_retiro(empleado, datos_empresa, ruta_salida, config,
                                disenio=1, usar_marca_agua=False,
                                membrete_path=None, usar_logo_enc=True):
    """
    Constancia formal del retiro del empleado (sin datos salariales,
    útil para presentar en otras empresas).

    config:
    - motivo_retiro: str (opcional: "renuncia voluntaria", "terminación de contrato", etc.)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        fecha_ingreso = fmt_fecha(empleado.get("fecha_ingreso", ""))
        fecha_retiro = fmt_fecha(empleado.get("fecha_retiro", ""))
        cargo = empleado.get("cargo", "")
        motivo = config.get("motivo_retiro", "").strip()

        empresa = datos_empresa.get("nombre", "la empresa")
        nit = datos_empresa.get("nit", "")

        el.append(Paragraph(
            f"<b>{empresa}</b>{f' identificada con NIT {nit},' if nit else ','} "
            f"hace constar que:",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        nombre_emp = empleado.get("nombre", "")
        doc_emp = empleado.get("documento", "")

        el.append(Paragraph(
            f"El(la) señor(a) <b>{nombre_emp}</b>, identificado(a) con cédula "
            f"de ciudadanía No. <b>{doc_emp}</b>, prestó sus servicios a esta "
            f"empresa desempeñando el cargo de <b>{cargo}</b>.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        filas = [
            ["Concepto", "Detalle"],
            ["Fecha de ingreso", fecha_ingreso or "—"],
            ["Fecha de retiro", fecha_retiro or "—"],
            ["Cargo desempeñado", cargo],
        ]
        if motivo:
            filas.append(["Motivo del retiro", motivo])

        t = Table(filas, colWidths=[5*cm, 10*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "El presente documento se expide a solicitud del(la) interesado(a) "
            "para los fines que estime convenientes.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="CONSTANCIA DE RETIRO",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
        incluir_firma_empleado=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ACTA DE ENTREGA DE DOTACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def generar_entrega_dotacion(empleado, datos_empresa, ruta_salida, config,
                                disenio=1, usar_marca_agua=False,
                                membrete_path=None, usar_logo_enc=True):
    """
    config:
    - items: list de dicts [{"descripcion": str, "cantidad": int, "estado": str}]
    - fecha_entrega: str
    - observaciones: str (opcional)
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        items = config.get("items", [])
        fecha_entrega = fmt_fecha(config.get("fecha_entrega", ""))
        observaciones = config.get("observaciones", "").strip()

        empresa = datos_empresa.get("nombre", "la empresa")

        el.append(Paragraph(
            f"<b>{empresa}</b> hace constar que en la fecha <b>{fecha_entrega}</b>, "
            f"hace entrega al(la) trabajador(a) de los siguientes elementos de "
            f"dotación de trabajo, en cumplimiento del Art. 230 del Código "
            f"Sustantivo del Trabajo:",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        # Tabla de items
        filas = [["#", "Descripción", "Cantidad", "Estado"]]
        for i, item in enumerate(items, 1):
            filas.append([
                str(i),
                item.get("descripcion", ""),
                str(item.get("cantidad", 1)),
                item.get("estado", "Nuevo"),
            ])
        if not items:
            filas.append(["1", "(sin elementos registrados)", "-", "-"])

        t = Table(filas, colWidths=[1*cm, 8*cm, 2.5*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (3, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        if observaciones:
            el.append(Paragraph(
                f"<b>Observaciones:</b> {observaciones}",
                estilos["cuerpo"]))
            el.append(Spacer(1, 12))

        el.append(Paragraph(
            "El(la) trabajador(a) se compromete a hacer buen uso de los "
            "elementos entregados, mantenerlos en buen estado y devolverlos "
            "en caso de terminación del contrato de trabajo o cuando la "
            "empresa así lo requiera.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Con su firma en el presente documento, el(la) trabajador(a) "
            "manifiesta haber recibido a satisfacción los elementos "
            "detallados.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="ACTA DE ENTREGA DE DOTACIÓN",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )


# ══════════════════════════════════════════════════════════════════════════════
# AUTORIZACIÓN DE DESCUENTO
# ══════════════════════════════════════════════════════════════════════════════

def generar_autorizacion_descuento(empleado, datos_empresa, ruta_salida, config,
                                       disenio=1, usar_marca_agua=False,
                                       membrete_path=None, usar_logo_enc=True):
    """
    Autorización expresa del trabajador para descuento salarial (Art. 149 CST).

    config:
    - concepto:       str ("préstamo", "libranza", "elemento perdido", etc.)
    - valor_total:    float
    - valor_cuota:    float
    - num_cuotas:     int
    - fecha_inicio:   str
    """
    def contenido(el, empleado, datos_empresa, config, estilos):
        concepto = config.get("concepto", "").strip()
        valor_total = float(config.get("valor_total", 0) or 0)
        valor_cuota = float(config.get("valor_cuota", 0) or 0)
        num_cuotas = int(config.get("num_cuotas", 1))
        fecha_ini = fmt_fecha(config.get("fecha_inicio", ""))

        empresa = datos_empresa.get("nombre", "la empresa")
        nombre_emp = empleado.get("nombre", "")
        doc_emp = empleado.get("documento", "")

        el.append(Paragraph(
            f"Yo, <b>{nombre_emp}</b>, identificado(a) con cédula de "
            f"ciudadanía No. <b>{doc_emp}</b>, en mi calidad de trabajador(a) "
            f"de <b>{empresa}</b>, actuando de manera libre, voluntaria y "
            f"consciente, en cumplimiento del Artículo 149 del Código "
            f"Sustantivo del Trabajo, <b>AUTORIZO EXPRESAMENTE</b> a la "
            f"empresa para descontar de mi salario los siguientes valores:",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        filas = [
            ["Concepto", "Detalle"],
            ["Concepto del descuento", concepto or "No especificado"],
            ["Valor total", f"${valor_total:,.0f} COP".replace(",", ".")],
            ["Número de cuotas", str(num_cuotas)],
            ["Valor por cuota", f"${valor_cuota:,.0f} COP".replace(",", ".")],
            ["Fecha inicio descuento", fecha_ini or "—"],
        ]
        t = Table(filas, colWidths=[5*cm, 10*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), estilos["_paleta"]["primario"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, estilos["_paleta"]["borde"]),
        ]))
        el.append(t)
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "Esta autorización se otorga por escrito, de manera específica "
            "para el concepto arriba mencionado, y podrá ser revocada por "
            "escrito en cualquier momento, sin perjuicio del saldo pendiente "
            "por pagar a la fecha de la revocatoria.",
            estilos["cuerpo"]))
        el.append(Spacer(1, 12))

        el.append(Paragraph(
            "En constancia de lo anterior, firmo el presente documento en la "
            "fecha señalada.",
            estilos["cuerpo"]))

    _generar_carta_base(
        empleado, datos_empresa, ruta_salida, config,
        titulo="AUTORIZACIÓN DE DESCUENTO SALARIAL",
        contenido_fn=contenido,
        disenio=disenio, usar_marca_agua=usar_marca_agua,
        membrete_path=membrete_path, usar_logo_enc=usar_logo_enc,
    )
