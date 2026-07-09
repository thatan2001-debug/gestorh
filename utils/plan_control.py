"""
Control de planes y límites — RH Fácil.
Planes ajustados al modelo de negocio real para PYMES colombianas.
"""

import os

WHATSAPP_NUMERO = os.getenv("WHATSAPP_NUMERO", "573001234567")

# ── Definición de planes ────────────────────────────────────────────────────
PLANES = {
    "gratuito": {
        "nombre":          "Gratuito",
        "precio":          0,
        "precio_fmt":      "Gratis",
        "descripcion":     "Para conocer la herramienta",
        "limite_empleados": 5,
        "limite_docs_mes":  5,
        "limite_total":     5,
        "dias_prueba":      None,
        "tiene_limite":    True,
        "multiempresa":    False,
        "marca_agua_rh":   True,     # Documentos con "Generado con RH Fácil"
        "features": [
            "1 empresa",
            "Hasta 5 empleados",
            "Hasta 5 documentos en total",
            "Certificado laboral con/sin salario",
            "Carta de vacaciones",
            "Descarga en PDF",
            'Marca "Generado con RH Fácil"',
        ],
        "documentos_habilitados": [
            "certificado_con_salario",
            "certificado_sin_salario",
            "carta_vacaciones",
        ],
        "color_badge": "#6B7280",
        "badge": "Gratis",
    },

    "basico": {
        "nombre":          "Básico",
        "precio":          39900,
        "precio_fmt":      "$39.900",
        "descripcion":     "Para PYMES con equipo pequeño",
        "limite_empleados": 30,
        "limite_docs_mes":  100,
        "limite_total":    None,
        "dias_prueba":     None,
        "tiene_limite":    True,
        "multiempresa":    False,
        "marca_agua_rh":   False,
        "features": [
            "1 empresa",
            "Hasta 30 empleados",
            "100 documentos por mes",
            "Todo lo del plan Gratuito",
            "Paz y salvo laboral",
            "Autorizaciones de descuento",
            "Autorización tratamiento de datos",
            "Carta de ingresos",
            "Actas de entrega",
            "Permisos y licencias",
            "Descarga PDF sin marca de agua",
            "Soporte por WhatsApp",
        ],
        "documentos_habilitados": [
            "certificado_con_salario", "certificado_sin_salario",
            "carta_vacaciones", "solicitud_vacaciones",
            "paz_salvo", "autorizacion_descuento", "autorizacion_datos",
            "carta_ingresos", "acta_entrega_cargo", "acta_entrega_equipos",
            "entrega_dotacion", "permiso_remunerado", "permiso_no_remunerado",
            "licencia_no_remunerada",
        ],
        "color_badge": "#2D6BE4",
        "badge": "⭐ Popular",
    },

    "pro": {
        "nombre":          "Pro",
        "precio":          89900,
        "precio_fmt":      "$89.900",
        "descripcion":     "Para empresas en crecimiento",
        "limite_empleados": 100,
        "limite_docs_mes":  500,
        "limite_total":    None,
        "dias_prueba":     None,
        "tiene_limite":    False,  # "ilimitados razonables"
        "multiempresa":    False,
        "marca_agua_rh":   False,
        "features": [
            "1 empresa",
            "Hasta 100 empleados",
            "Documentos ilimitados",
            "Todo lo del plan Básico",
            "Contratos laborales (fijo, indefinido, obra)",
            "Contrato prestación de servicios",
            "Carta de terminación de contrato",
            "Carta de no renovación",
            "Liquidación de prestaciones",
            "Llamados de atención y descargos",
            "Cambio de salario / cambio de cargo",
            "Logo de empresa en documentos",
            "Historial por empleado",
            "Envío por correo electrónico",
            "Soporte prioritario",
        ],
        "documentos_habilitados": "todos",  # todos los implementados
        "color_badge": "#1B3F6E",
        "badge": "Pro",
    },

    "empresarial": {
        "nombre":          "Empresarial",
        "precio":          199900,
        "precio_fmt":      "$199.900",
        "descripcion":     "Para contadores y outsourcing de RH",
        "limite_empleados": None,   # sin límite
        "limite_docs_mes":  None,
        "limite_total":    None,
        "dias_prueba":     None,
        "tiene_limite":    False,
        "multiempresa":    True,
        "marca_agua_rh":   False,
        "features": [
            "Multiempresa (clientes ilimitados)",
            "Empleados ilimitados",
            "Documentos ilimitados",
            "Todo lo del plan Pro",
            "Historial completo por empresa",
            "Plantillas personalizadas",
            "Exportación de datos",
            "Reportes y estadísticas",
            "Capacitación incluida",
            "Gerente de cuenta dedicado",
            "Soporte prioritario 24/7",
        ],
        "documentos_habilitados": "todos",
        "color_badge": "#059669",
        "badge": "Empresarial",
    },
}

PLAN_ORDEN = ["gratuito", "basico", "pro", "empresarial"]


def plan_permite_documento(plan: str, tipo_documento: str) -> bool:
    """Verifica si el plan habilita un tipo de documento específico."""
    info = PLANES.get(plan, PLANES["gratuito"])
    habilitados = info.get("documentos_habilitados", [])
    if habilitados == "todos":
        return True
    return tipo_documento in habilitados


def plan_permite_empleado(plan: str, num_empleados_actuales: int) -> bool:
    """Verifica si el plan permite agregar más empleados."""
    info = PLANES.get(plan, PLANES["gratuito"])
    limite = info.get("limite_empleados")
    if limite is None:
        return True
    return num_empleados_actuales < limite


def plan_permite_doc_mes(plan: str, docs_este_mes: int) -> tuple[bool, int | None]:
    """Verifica si el plan permite generar más documentos este mes."""
    info = PLANES.get(plan, PLANES["gratuito"])
    limite = info.get("limite_docs_mes")
    if limite is None:
        return True, None
    return docs_este_mes < limite, limite - docs_este_mes


def docs_restantes_totales(plan: str, docs_usados: int) -> int | None:
    """Retorna documentos restantes totales o None si no tiene límite."""
    info = PLANES.get(plan, PLANES["gratuito"])
    limite = info.get("limite_total")
    if limite is None:
        return None
    return max(0, limite - docs_usados)


def obtener_limite_plan(plan: str) -> dict:
    """Retorna límites del plan en formato compatible con el resto del código."""
    info = PLANES.get(plan, PLANES["gratuito"])
    return {
        "max_docs":       info.get("limite_total") or info.get("limite_docs_mes") or 9999,
        "tiene_limite":   info.get("tiene_limite", True),
        "max_empleados":  info.get("limite_empleados"),
        "multiempresa":   info.get("multiempresa", False),
        "marca_agua_rh":  info.get("marca_agua_rh", False),
    }


def link_whatsapp(mensaje: str = "") -> str:
    """Genera link de WhatsApp con mensaje pre-escrito."""
    import urllib.parse
    if not mensaje:
        mensaje = "Hola, quiero suscribirme a RH Fácil. ¿Me pueden dar información sobre los planes disponibles?"
    return f"https://wa.me/{WHATSAPP_NUMERO}?text={urllib.parse.quote(mensaje)}"


def link_whatsapp_plan(plan: str) -> str:
    """Link de WhatsApp para activar un plan específico."""
    info = PLANES.get(plan, {})
    precio = info.get("precio_fmt", "")
    nombre = info.get("nombre", plan)
    msg = (
        f"Hola, quiero activar el plan {nombre} de RH Fácil "
        f"({precio}/mes). ¿Cómo procedo?"
    )
    return link_whatsapp(msg)


# ── Textos comerciales seguros ────────────────────────────────────────────────
MENSAJE_PRINCIPAL = (
    "RH Fácil te ayuda a generar documentos laborales profesionales "
    "para tu empresa en minutos, usando los datos de tus empleados, "
    "el logo de tu empresa y plantillas organizadas, listas para revisar, "
    "firmar, descargar o enviar."
)

DISCLAIMER_DOCUMENTOS = (
    "⚖️ Aviso: Los documentos generados por RH Fácil son de referencia. "
    "No constituyen asesoría legal, laboral, contable ni tributaria. "
    "Valide siempre con su contador o abogado antes de firmar o usar para pagos reales."
)

DISCLAIMER_LIQUIDACIONES = (
    "⚠️ Estimación de referencia: Esta liquidación se calcula con las fórmulas "
    "generales del CST. No incluye: salario integral, mora en cesantías, "
    "embargos, incapacidades, horas extras ni casos especiales. "
    "Valide con su contador antes de realizar el pago."
)

FRASES_EVITAR = [
    "Cumple automáticamente la ley",
    "100% legal",
    "Reemplaza a tu abogado",
    "Liquidaciones exactas garantizadas",
]

FRASES_CORRECTAS = [
    "Documentos de referencia listos para revisión",
    "Basado en parámetros laborales configurables",
    "No reemplaza asesoría legal, laboral ni contable",
    "Valida siempre los casos especiales con tu contador o abogado",
]
