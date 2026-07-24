"""
Catálogo de documentos disponibles en Gestor RH IA.
Define qué documentos existen, qué campos requieren, qué plan los habilita
y qué plantilla PDF los genera.

Para agregar un nuevo documento:
1. Agregar entrada en CATALOGO con todos sus metadatos
2. Crear la función generadora en utils/plantillas_disenio.py
3. Agregar el tipo en utils/historial.py → NOMBRES_DOCUMENTO

Esta arquitectura permite agregar documentos sin tocar app.py.
"""

# ── Plan mínimo requerido por documento ────────────────────────────────────────
PLAN_ORDEN = ["gratuito", "basico", "pro", "empresarial"]

# ─── MODO BETA (validación pre-lanzamiento) ────────────────────────────────
# Por defecto está ACTIVO para permitir pruebas completas de la plataforma.
# Cuando se quiera desactivar (para producción real con clientes), poner
# MODO_BETA_SIN_LIMITES=0 en el entorno.
import os as _os
_MODO_BETA = _os.getenv("MODO_BETA_SIN_LIMITES", "1").lower() in ("1", "true", "yes", "on")


def plan_permite(plan_usuario: str, plan_requerido: str) -> bool:
    """Retorna True si el plan del usuario habilita el documento."""
    if _MODO_BETA:
        return True  # ← BETA: todos los planes permiten todo
    try:
        return PLAN_ORDEN.index(plan_usuario) >= PLAN_ORDEN.index(plan_requerido)
    except ValueError:
        return False


def modo_beta_activo() -> bool:
    """True si el modo beta está activo (todos los documentos desbloqueados)."""
    return _MODO_BETA


# ── Catálogo completo ─────────────────────────────────────────────────────────
# Cada documento tiene:
#   id:             identificador interno único
#   nombre:         nombre legible para mostrar al usuario
#   categoria:      agrupación visual
#   icono:          emoji para la UI
#   plan_minimo:    plan requerido para generarlo
#   implementado:   True si ya está disponible, False = "próximamente"
#   descripcion:    texto de ayuda
#   campos_req:     campos del formulario obligatorios (además de empleado)
#   campos_opt:     campos opcionales del formulario
#   genera_pdf:     función en plantillas_disenio que lo genera
#   disclaimer:     texto legal específico del documento

CATALOGO = {

    # ══════════════════════════════════════════════════════════════
    # CERTIFICADOS
    # ══════════════════════════════════════════════════════════════

    "certificado_con_salario": {
        "nombre":       "Certificado Laboral con Salario",
        "categoria":    "Certificados",
        "icono":        "📋",
        "plan_minimo":  "gratuito",
        "implementado": True,
        "descripcion":  "Certifica nombre, cargo, salario, fecha de ingreso y tipo de contrato.",
        "campos_req":   [],
        "campos_opt":   ["ingreso_variable", "observaciones"],
        "genera_pdf":   "generar_certificado",
        "subtipo":      "con_salario",
        "disclaimer":   "Documento de referencia. Verifique los datos antes de su uso oficial.",
    },

    "certificado_sin_salario": {
        "nombre":       "Certificado Laboral sin Salario",
        "categoria":    "Certificados",
        "icono":        "📋",
        "plan_minimo":  "gratuito",
        "implementado": True,
        "descripcion":  "Certifica cargo y fecha de ingreso sin incluir el valor del salario.",
        "campos_req":   [],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_certificado_sin_salario",
        "subtipo":      "sin_salario",
        "disclaimer":   "Documento de referencia. Verifique los datos antes de su uso oficial.",
    },

    "certificacion_funciones": {
        "nombre":       "Certificación de Funciones",
        "categoria":    "Certificados",
        "icono":        "📋",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Detalla las funciones y responsabilidades del cargo.",
        "campos_req":   ["descripcion_funciones"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Documento de referencia. Valide con su contador o abogado.",
    },

    "carta_ingresos": {
        "nombre":       "Carta de Ingresos",
        "categoria":    "Certificados",
        "icono":        "💵",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Certifica los ingresos totales del empleado para trámites bancarios o de vivienda.",
        "campos_req":   [],
        "campos_opt":   ["proposito", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Estimación de ingresos de referencia. No constituye garantía bancaria.",
    },

    # ══════════════════════════════════════════════════════════════
    # VACACIONES
    # ══════════════════════════════════════════════════════════════

    "carta_vacaciones": {
        "nombre":       "Carta de Vacaciones",
        "categoria":    "Vacaciones",
        "icono":        "🏖️",
        "plan_minimo":  "gratuito",
        "implementado": True,
        "descripcion":  "Informa al empleado el período de vacaciones aprobado.",
        "campos_req":   ["fecha_inicio_vac", "fecha_fin_vac"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_vacaciones",
        "disclaimer":   "Documento de referencia. Art. 186 CST.",
    },

    "solicitud_vacaciones": {
        "nombre":       "Solicitud de Vacaciones",
        "categoria":    "Vacaciones",
        "icono":        "📝",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Formato de solicitud de vacaciones firmado por el empleado.",
        "campos_req":   ["fecha_inicio_vac", "fecha_fin_vac"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Documento de referencia. Art. 186 CST.",
    },

    # ══════════════════════════════════════════════════════════════
    # CONTRATOS
    # ══════════════════════════════════════════════════════════════

    "contrato_indefinido": {
        "nombre":       "Contrato a Término Indefinido",
        "categoria":    "Contratos",
        "icono":        "📄",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Contrato laboral sin fecha de terminación fija. Art. 45 CST.",
        "campos_req":   ["fecha_inicio_contrato", "lugar_trabajo", "jornada"],
        "campos_opt":   ["periodo_prueba", "funciones", "observaciones"],
        "genera_pdf":   None,
        "disclaimer":   "Borrador de referencia. Debe ser revisado por abogado laboral antes de firmar.",
    },

    "contrato_fijo": {
        "nombre":       "Contrato a Término Fijo",
        "categoria":    "Contratos",
        "icono":        "📄",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Contrato con fecha de terminación definida. Mínimo 1 mes, máximo 3 años. Art. 46 CST.",
        "campos_req":   ["fecha_inicio_contrato", "fecha_fin_contrato", "lugar_trabajo"],
        "campos_opt":   ["periodo_prueba", "funciones", "observaciones"],
        "genera_pdf":   None,
        "disclaimer":   "Borrador de referencia. Debe ser revisado por abogado laboral antes de firmar.",
    },

    "contrato_obra": {
        "nombre":       "Contrato por Obra o Labor",
        "categoria":    "Contratos",
        "icono":        "📄",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Contrato para una obra o labor específica. Art. 45 CST.",
        "campos_req":   ["fecha_inicio_contrato", "descripcion_obra"],
        "campos_opt":   ["lugar_trabajo", "observaciones"],
        "genera_pdf":   None,
        "disclaimer":   "Borrador de referencia. Debe ser revisado por abogado laboral antes de firmar.",
    },

    "contrato_prestacion": {
        "nombre":       "Contrato de Prestación de Servicios",
        "categoria":    "Contratos",
        "icono":        "📄",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Para contratistas independientes. No genera relación laboral.",
        "campos_req":   ["fecha_inicio_contrato", "fecha_fin_contrato", "objeto_contrato", "honorarios"],
        "campos_opt":   ["forma_pago", "obligaciones", "observaciones"],
        "genera_pdf":   None,
        "disclaimer":   "Este contrato NO genera relación laboral. Revise con contador o abogado.",
    },

    # ══════════════════════════════════════════════════════════════
    # TERMINACIÓN
    # ══════════════════════════════════════════════════════════════

    "carta_terminacion": {
        "nombre":       "Carta de Terminación de Contrato",
        "categoria":    "Terminación",
        "icono":        "📮",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Notificación formal de terminación del contrato con o sin justa causa.",
        "campos_req":   ["fecha_retiro", "motivo_retiro"],
        "campos_opt":   ["causal_justa_causa", "preaviso", "observaciones"],
        "genera_pdf":   None,
        "disclaimer":   "Borrador de referencia. Valide causales con abogado laboral antes de enviar.",
    },

    "carta_no_renovacion": {
        "nombre":       "Carta de No Renovación",
        "categoria":    "Terminación",
        "icono":        "📮",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Aviso de no renovación para contratos a término fijo. Art. 46 CST (30 días de antelación).",
        "campos_req":   ["fecha_vencimiento_contrato"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   None,
        "disclaimer":   "Debe enviarse con mínimo 30 días de antelación. Art. 46 CST.",
    },

    "carta_aceptacion_renuncia": {
        "nombre":       "Carta de Aceptación de Renuncia",
        "categoria":    "Terminación",
        "icono":        "📮",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Acepta formalmente la renuncia voluntaria del empleado.",
        "campos_req":   ["fecha_retiro"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   None,
        "disclaimer":   "Documento de referencia. Verifique con abogado laboral.",
    },

    # ══════════════════════════════════════════════════════════════
    # LIQUIDACIÓN
    # ══════════════════════════════════════════════════════════════

    "liquidacion_prestaciones": {
        "nombre":       "Liquidación de Prestaciones Sociales",
        "categoria":    "Liquidación",
        "icono":        "💰",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Calcula cesantías, intereses, prima, vacaciones y salario pendiente.",
        "campos_req":   ["fecha_corte", "motivo_retiro"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_liquidacion",
        "disclaimer":   "ESTIMACIÓN de referencia. No incluye embargos, mora ni casos especiales. Valide con contador.",
    },

    # ══════════════════════════════════════════════════════════════
    # PAZ Y SALVO / AUTORIZACIONES
    # ══════════════════════════════════════════════════════════════

    "paz_salvo": {
        "nombre":       "Paz y Salvo Laboral",
        "categoria":    "Autorizaciones",
        "icono":        "✅",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Certifica que el empleado no tiene pendientes con la empresa.",
        "campos_req":   ["fecha_retiro"],
        "campos_opt":   ["conceptos_pendientes", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Verifique todos los conceptos antes de firmar el paz y salvo.",
    },

    "autorizacion_descuento": {
        "nombre":       "Autorización de Descuento",
        "categoria":    "Autorizaciones",
        "icono":        "📝",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Autorización firmada del empleado para descuentos en nómina.",
        "campos_req":   ["concepto_descuento", "valor_descuento", "cuotas"],
        "campos_opt":   ["fecha_inicio_descuento", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Los descuentos no pueden superar el 50% del salario. Art. 149 CST.",
    },

    "autorizacion_datos": {
        "nombre":       "Autorización Tratamiento de Datos Personales",
        "categoria":    "Autorizaciones",
        "icono":        "🔒",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Cumplimiento de la Ley 1581 de 2012 de protección de datos.",
        "campos_req":   [],
        "campos_opt":   ["finalidad_datos", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Ley 1581/2012. El empleado tiene derecho a conocer, actualizar y rectificar sus datos.",
    },

    # ══════════════════════════════════════════════════════════════
    # ACTAS
    # ══════════════════════════════════════════════════════════════

    "acta_entrega_cargo": {
        "nombre":       "Acta de Entrega de Cargo",
        "categoria":    "Actas",
        "icono":        "📋",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Formaliza la entrega del cargo al terminar la relación laboral o en cambio de funciones.",
        "campos_req":   ["fecha_entrega"],
        "campos_opt":   ["pendientes", "documentos_entregados", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Documento de referencia. Verifique todos los pendientes antes de firmar.",
    },

    "acta_entrega_equipos": {
        "nombre":       "Acta de Entrega de Equipos",
        "categoria":    "Actas",
        "icono":        "💻",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Registro de equipos y elementos entregados al empleado.",
        "campos_req":   ["fecha_entrega"],
        "campos_opt":   ["lista_equipos", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Documento de referencia. Verifique los elementos antes de firmar.",
    },

    "entrega_dotacion": {
        "nombre":       "Acta de Entrega de Dotación",
        "categoria":    "Actas",
        "icono":        "👕",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Registro de dotación entregada. Art. 230 CST (3 veces al año).",
        "campos_req":   ["fecha_entrega", "periodo_dotacion"],
        "campos_opt":   ["lista_dotacion", "talla", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Art. 230 CST: Dotación para empleados con salario hasta 2 SMMLV.",
    },

    # ══════════════════════════════════════════════════════════════
    # NOVEDADES / CAMBIOS
    # ══════════════════════════════════════════════════════════════

    "cambio_salario": {
        "nombre":       "Comunicación de Cambio de Salario",
        "categoria":    "Novedades",
        "icono":        "💰",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Notifica al empleado un cambio en su salario.",
        "campos_req":   ["nuevo_salario", "fecha_vigencia"],
        "campos_opt":   ["motivo", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Otrosí al contrato recomendado para cambios permanentes.",
    },

    "cambio_cargo": {
        "nombre":       "Comunicación de Cambio de Cargo",
        "categoria":    "Novedades",
        "icono":        "🔄",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Notifica al empleado un cambio de cargo o funciones.",
        "campos_req":   ["nuevo_cargo", "fecha_vigencia"],
        "campos_opt":   ["nuevo_salario", "nuevas_funciones", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Art. 23 CST: El cargo es elemento esencial del contrato.",
    },

    "otrosi": {
        "nombre":       "Otrosí al Contrato",
        "categoria":    "Novedades",
        "icono":        "✍️",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Modifica el contrato original por cambio de cargo, salario o lugar de trabajo. Se genera desde la pantalla de Empleados.",
        "campos_req":   ["tipo_cambio", "fecha_vigencia"],
        "campos_opt":   ["motivo"],
        "genera_pdf":   "generar_otrosi",
        "disclaimer":   "Art. 43 CST — Modificación por mutuo acuerdo. Actualiza los datos del empleado en la base de datos.",
    },

    # ══════════════════════════════════════════════════════════════
    # DISCIPLINARIO
    # ══════════════════════════════════════════════════════════════

    "llamado_atencion": {
        "nombre":       "Llamado de Atención",
        "categoria":    "Disciplinario",
        "icono":        "⚠️",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Llamado de atención escrito por incumplimiento de obligaciones.",
        "campos_req":   ["fecha_hecho", "descripcion_hecho"],
        "campos_opt":   ["norma_incumplida", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Siga el proceso disciplinario del reglamento interno. Consulte abogado laboral.",
    },

    "citacion_descargos": {
        "nombre":       "Citación a Descargos",
        "categoria":    "Disciplinario",
        "icono":        "⚖️",
        "plan_minimo":  "pro",
        "implementado": True,
        "descripcion":  "Citación formal al empleado para presentar descargos por falta disciplinaria.",
        "campos_req":   ["fecha_citacion", "hora_citacion", "causal"],
        "campos_opt":   ["lugar_citacion", "observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Proceso obligatorio antes de sancionar. Art. 115 CST.",
    },

    # ══════════════════════════════════════════════════════════════
    # PERMISOS Y LICENCIAS
    # ══════════════════════════════════════════════════════════════

    "permiso_remunerado": {
        "nombre":       "Permiso Remunerado",
        "categoria":    "Permisos",
        "icono":        "📅",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Autorización de permiso con pago de salario.",
        "campos_req":   ["fecha_inicio_permiso", "fecha_fin_permiso", "motivo"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Documento de referencia. Verifique política interna de permisos.",
    },

    "permiso_no_remunerado": {
        "nombre":       "Permiso No Remunerado",
        "categoria":    "Permisos",
        "icono":        "📅",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Autorización de permiso sin pago de salario.",
        "campos_req":   ["fecha_inicio_permiso", "fecha_fin_permiso", "motivo"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Descuento proporcional de salario por los días no laborados.",
    },

    "licencia_no_remunerada": {
        "nombre":       "Licencia No Remunerada",
        "categoria":    "Permisos",
        "icono":        "📅",
        "plan_minimo":  "basico",
        "implementado": True,
        "descripcion":  "Licencia temporal sin pago de salario ni prestaciones.",
        "campos_req":   ["fecha_inicio_licencia", "fecha_fin_licencia", "motivo"],
        "campos_opt":   ["observaciones"],
        "genera_pdf":   "generar_universal",
        "disclaimer":   "Durante la licencia no remunerada se suspende el contrato. Art. 51 CST.",
    },
}


def obtener_por_categoria() -> dict:
    """Agrupa el catálogo por categoría para mostrar en la UI."""
    resultado = {}
    for doc_id, doc in CATALOGO.items():
        cat = doc["categoria"]
        if cat not in resultado:
            resultado[cat] = []
        resultado[cat].append({**doc, "id": doc_id})
    return resultado


def obtener_disponibles(plan_usuario: str) -> list:
    """Retorna solo los documentos que el plan del usuario puede generar."""
    return [
        {**doc, "id": doc_id}
        for doc_id, doc in CATALOGO.items()
        if plan_permite(plan_usuario, doc["plan_minimo"])
    ]


def obtener_implementados(plan_usuario: str = None) -> list:
    """Retorna solo los documentos ya implementados."""
    return [
        {**doc, "id": doc_id}
        for doc_id, doc in CATALOGO.items()
        if doc["implementado"] and (
            plan_usuario is None or plan_permite(plan_usuario, doc["plan_minimo"])
        )
    ]


def obtener_por_id(doc_id: str) -> dict | None:
    return CATALOGO.get(doc_id)


# ── Resumen de categorías para la UI ─────────────────────────────────────────
CATEGORIAS_ORDEN = [
    "Certificados", "Vacaciones", "Contratos", "Terminación",
    "Liquidación", "Autorizaciones", "Actas", "Novedades",
    "Disciplinario", "Permisos",
]

TOTAL_DOCUMENTOS    = len(CATALOGO)
IMPLEMENTADOS       = sum(1 for d in CATALOGO.values() if d["implementado"])
PROXXIMAMENTE       = TOTAL_DOCUMENTOS - IMPLEMENTADOS
