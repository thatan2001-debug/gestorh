"""
Sistema visual corporativo centralizado (Etapa Rediseño A).

Este módulo es la ÚNICA fuente de verdad para:
- Colores corporativos (paletas)
- Tipografía (familias, tamaños, pesos)
- Márgenes de página
- Espaciados verticales
- Estilos de tablas
- Estilos de firmas
- Componentes reutilizables

Todos los generadores de documentos (contratos, cartas, liquidaciones, actas)
deben usar estas constantes y componentes en vez de definir estilos duplicados.

Objetivos de diseño:
- Aspecto profesional y corporativo consistente
- Aprovechar el espacio de la hoja sin ser apretado
- Facilitar mantenimiento (un cambio de color aquí afecta todo)
- Adaptativo: soporte para nombres largos, logos verticales/horizontales
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle,
    KeepTogether, Image, HRFlowable,
)
from datetime import datetime
from pathlib import Path
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

from reportlab.lib.pagesizes import A4  # 595 x 842 pts — estándar corporativo internacional

PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE

# ─── Márgenes por perfil (compatibilidad con código existente) ───────────
# COMPACTO: aprovecha máximo espacio, para documentos que necesitan una hoja
MARGEN_COMPACTO_SUP = 1.8 * cm
MARGEN_COMPACTO_INF = 2.0 * cm
MARGEN_COMPACTO_IZQ = 2.2 * cm
MARGEN_COMPACTO_DER = 2.2 * cm

# NORMAL: balance profesional
MARGEN_NORMAL_SUP = 2.2 * cm
MARGEN_NORMAL_INF = 2.5 * cm
MARGEN_NORMAL_IZQ = 2.8 * cm
MARGEN_NORMAL_DER = 2.5 * cm

# AMPLIO: para contratos y documentos legales
MARGEN_AMPLIO_SUP = 2.5 * cm
MARGEN_AMPLIO_INF = 3.0 * cm
MARGEN_AMPLIO_IZQ = 3.2 * cm
MARGEN_AMPLIO_DER = 2.8 * cm

# ─── Márgenes por TIPO de documento (rediseño A4) ────────────────────────
# Valores del brief de diseño corporativo
MARGENES_POR_TIPO = {
    # Certificado: 23/22/25/25 mm — sobrio, cercano a carta empresarial
    "certificado": (2.3 * cm, 2.2 * cm, 2.5 * cm, 2.5 * cm),
    # Contrato: 22/22/28/23 mm — margen izquierdo amplio para perforación/archivo
    "contrato_indefinido": (2.2 * cm, 2.2 * cm, 2.8 * cm, 2.3 * cm),
    "contrato": (2.2 * cm, 2.2 * cm, 2.8 * cm, 2.3 * cm),
    # Liquidación: 18/20/17/17 mm — más espacio horizontal para tablas
    "liquidacion": (1.8 * cm, 2.0 * cm, 1.7 * cm, 1.7 * cm),
    # Actas: 20/20/22/22 mm — equilibrado
    "dotacion": (2.0 * cm, 2.0 * cm, 2.2 * cm, 2.2 * cm),
    "acta": (2.0 * cm, 2.0 * cm, 2.2 * cm, 2.2 * cm),
}


def ancho_util(perfil: str = "normal") -> float:
    """Retorna el ancho útil del texto según el perfil de márgenes."""
    if perfil == "compacto":
        return PAGE_WIDTH - MARGEN_COMPACTO_IZQ - MARGEN_COMPACTO_DER
    if perfil == "amplio":
        return PAGE_WIDTH - MARGEN_AMPLIO_IZQ - MARGEN_AMPLIO_DER
    return PAGE_WIDTH - MARGEN_NORMAL_IZQ - MARGEN_NORMAL_DER


def alto_util(perfil: str = "normal") -> float:
    """Retorna el alto útil disponible según el perfil de márgenes."""
    if perfil == "compacto":
        return PAGE_HEIGHT - MARGEN_COMPACTO_SUP - MARGEN_COMPACTO_INF
    if perfil == "amplio":
        return PAGE_HEIGHT - MARGEN_AMPLIO_SUP - MARGEN_AMPLIO_INF
    return PAGE_HEIGHT - MARGEN_NORMAL_SUP - MARGEN_NORMAL_INF


# ══════════════════════════════════════════════════════════════════════════════
# 2. TIPOGRAFÍA
# ══════════════════════════════════════════════════════════════════════════════

# ReportLab tiene Helvetica por defecto (equivale a Arial). Es la elección
# más segura por compatibilidad. No requiere fuentes externas.
FUENTE_REGULAR = "Helvetica"
FUENTE_NEGRITA = "Helvetica-Bold"
FUENTE_CURSIVA = "Helvetica-Oblique"
FUENTE_NEGRITA_CURSIVA = "Helvetica-BoldOblique"

# ─── Tamaños ───────────────────────────────────────────────────────────
# En puntos. Escala visualmente consistente.
TAM_MICRO       = 7.5   # pie de página, notas al pie
TAM_PEQUEÑO     = 8.5   # notas, disclaimers
TAM_CUERPO_MIN  = 9.5   # cuerpo compacto cuando el espacio aprieta
TAM_CUERPO      = 10.5  # cuerpo estándar
TAM_CUERPO_MAX  = 11.0  # cuerpo cómodo
TAM_SUBTITULO   = 12    # subtítulos y encabezados de sección
TAM_TITULO      = 14    # título de documento
TAM_TITULO_XL   = 16    # títulos destacados

# ─── Interlineado ──────────────────────────────────────────────────────
# 1.15-1.3 es lo profesional. 1.5 se ve espaciado, 1.0 apretado.
INTERLINEADO_COMPACTO = 1.15
INTERLINEADO_NORMAL   = 1.25
INTERLINEADO_AMPLIO   = 1.4


# ══════════════════════════════════════════════════════════════════════════════
# 3. COLORES CORPORATIVOS (5 paletas del sistema)
# ══════════════════════════════════════════════════════════════════════════════

PALETAS = {
    1: {
        "nombre":      "Clásico Corporativo",
        "primario":    colors.HexColor("#1B3F6E"),  # azul oscuro
        "secundario":  colors.HexColor("#2D6BE4"),  # azul brillante
        "acento":      colors.HexColor("#E8F0FD"),  # azul muy claro (fondos)
        "texto":       colors.HexColor("#1F2937"),  # negro suave
        "texto_suave": colors.HexColor("#6B7280"),  # gris medio
        "borde":       colors.HexColor("#D1D5DB"),  # gris borde
        "borde_suave": colors.HexColor("#E5E7EB"),  # gris muy claro
        "fondo_tabla": colors.HexColor("#F9FAFB"),  # gris fondo alterno
    },
    2: {
        "nombre":      "Ejecutivo Oscuro",
        "primario":    colors.HexColor("#1F2937"),
        "secundario":  colors.HexColor("#B45309"),
        "acento":      colors.HexColor("#FEF3C7"),
        "texto":       colors.HexColor("#111827"),
        "texto_suave": colors.HexColor("#6B7280"),
        "borde":       colors.HexColor("#D1D5DB"),
        "borde_suave": colors.HexColor("#E5E7EB"),
        "fondo_tabla": colors.HexColor("#FEF7ED"),
    },
    3: {
        "nombre":      "Verde Institucional",
        "primario":    colors.HexColor("#064E3B"),
        "secundario":  colors.HexColor("#059669"),
        "acento":      colors.HexColor("#ECFDF5"),
        "texto":       colors.HexColor("#1F2937"),
        "texto_suave": colors.HexColor("#6B7280"),
        "borde":       colors.HexColor("#D1D5DB"),
        "borde_suave": colors.HexColor("#D1FAE5"),
        "fondo_tabla": colors.HexColor("#F0FDF4"),
    },
    4: {
        "nombre":      "Moderno Minimalista",
        "primario":    colors.HexColor("#111827"),
        "secundario":  colors.HexColor("#DC2626"),
        "acento":      colors.HexColor("#FEF2F2"),
        "texto":       colors.HexColor("#1F2937"),
        "texto_suave": colors.HexColor("#6B7280"),
        "borde":       colors.HexColor("#D1D5DB"),
        "borde_suave": colors.HexColor("#E5E7EB"),
        "fondo_tabla": colors.HexColor("#F9FAFB"),
    },
    5: {
        "nombre":      "Profesional Violeta",
        "primario":    colors.HexColor("#4C1D95"),
        "secundario":  colors.HexColor("#7C3AED"),
        "acento":      colors.HexColor("#F5F3FF"),
        "texto":       colors.HexColor("#1F2937"),
        "texto_suave": colors.HexColor("#6B7280"),
        "borde":       colors.HexColor("#D1D5DB"),
        "borde_suave": colors.HexColor("#EDE9FE"),
        "fondo_tabla": colors.HexColor("#FAF5FF"),
    },
}


def obtener_paleta(numero: int = 1) -> dict:
    """Retorna la paleta indicada, con fallback a la 1 si no existe."""
    return PALETAS.get(int(numero), PALETAS[1])


# ══════════════════════════════════════════════════════════════════════════════
# 4. LOGO — cálculo de dimensiones adaptativo
# ══════════════════════════════════════════════════════════════════════════════

# Dimensiones del contenedor del logo. La imagen respeta proporción dentro.
LOGO_MAX_ANCHO = 3.5 * cm
LOGO_MAX_ALTO  = 2.5 * cm

# En modo compacto (acta 1 hoja), el logo se reduce
LOGO_COMPACTO_MAX_ANCHO = 2.8 * cm
LOGO_COMPACTO_MAX_ALTO  = 2.0 * cm


def calcular_dimensiones_logo(logo_path: str,
                                max_ancho: float = LOGO_MAX_ANCHO,
                                max_alto: float = LOGO_MAX_ALTO) -> tuple:
    """
    Calcula el ancho y alto óptimos del logo respetando su proporción.
    Soporta logos horizontales, cuadrados y verticales sin deformarlos.
    Retorna: (ancho, alto) en puntos.
    """
    if not logo_path or not Path(logo_path).exists():
        return max_ancho, max_alto

    try:
        from PIL import Image as PILImage
        img = PILImage.open(logo_path)
        ancho_orig, alto_orig = img.size
        if ancho_orig <= 0 or alto_orig <= 0:
            return max_ancho, max_alto

        # Escalar hasta el más restrictivo (ancho o alto)
        ratio_ancho = max_ancho / ancho_orig
        ratio_alto = max_alto / alto_orig
        ratio = min(ratio_ancho, ratio_alto)

        return ancho_orig * ratio, alto_orig * ratio
    except Exception:
        return max_ancho, max_alto


# ══════════════════════════════════════════════════════════════════════════════
# 5. ESTILOS DE PÁRRAFO (fábrica según perfil)
# ══════════════════════════════════════════════════════════════════════════════

def crear_estilos(paleta: dict, perfil: str = "normal") -> dict:
    """
    Fabrica los estilos de Paragraph para el perfil dado.

    perfil: "compacto" | "normal" | "amplio"
    Los estilos compactos usan tamaños menores y menos espacio antes/después.
    """
    if perfil == "compacto":
        tam_cuerpo = TAM_CUERPO_MIN
        tam_titulo = TAM_TITULO
        space_before = 4
        space_after = 4
        leading = tam_cuerpo * INTERLINEADO_COMPACTO
    elif perfil == "amplio":
        tam_cuerpo = TAM_CUERPO_MAX
        tam_titulo = TAM_TITULO_XL
        space_before = 8
        space_after = 8
        leading = tam_cuerpo * INTERLINEADO_AMPLIO
    else:  # normal
        tam_cuerpo = TAM_CUERPO
        tam_titulo = TAM_TITULO
        space_before = 6
        space_after = 6
        leading = tam_cuerpo * INTERLINEADO_NORMAL

    estilos = {
        # Cuerpo justificado (default)
        "cuerpo": ParagraphStyle(
            name="Cuerpo",
            fontName=FUENTE_REGULAR,
            fontSize=tam_cuerpo,
            leading=leading,
            textColor=paleta["texto"],
            alignment=TA_JUSTIFY,
            spaceBefore=space_before,
            spaceAfter=space_after,
        ),
        # Cuerpo alineado izquierda (para direcciones, datos)
        "cuerpo_izq": ParagraphStyle(
            name="CuerpoIzq",
            fontName=FUENTE_REGULAR,
            fontSize=tam_cuerpo,
            leading=leading,
            textColor=paleta["texto"],
            alignment=TA_LEFT,
            spaceBefore=space_before,
            spaceAfter=space_after,
        ),
        # Cuerpo centrado (para títulos secundarios, subtítulos)
        "cuerpo_centro": ParagraphStyle(
            name="CuerpoCentro",
            fontName=FUENTE_REGULAR,
            fontSize=tam_cuerpo,
            leading=leading,
            textColor=paleta["texto"],
            alignment=TA_CENTER,
            spaceBefore=space_before,
            spaceAfter=space_after,
        ),
        # Título principal del documento
        "titulo": ParagraphStyle(
            name="Titulo",
            fontName=FUENTE_NEGRITA,
            fontSize=tam_titulo,
            leading=tam_titulo * 1.2,
            textColor=paleta["primario"],
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=10,
        ),
        # Subtítulo
        "subtitulo": ParagraphStyle(
            name="Subtitulo",
            fontName=FUENTE_NEGRITA,
            fontSize=TAM_SUBTITULO,
            leading=TAM_SUBTITULO * 1.3,
            textColor=paleta["primario"],
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=6,
        ),
        # Firma - nombre
        "firma_nombre": ParagraphStyle(
            name="FirmaNombre",
            fontName=FUENTE_NEGRITA,
            fontSize=tam_cuerpo,
            leading=tam_cuerpo * 1.1,
            textColor=paleta["texto"],
            alignment=TA_CENTER,
        ),
        # Firma - cargo
        "firma_cargo": ParagraphStyle(
            name="FirmaCargo",
            fontName=FUENTE_REGULAR,
            fontSize=tam_cuerpo - 1,
            leading=(tam_cuerpo - 1) * 1.15,
            textColor=paleta["texto_suave"],
            alignment=TA_CENTER,
        ),
        # Nota / disclaimer
        "nota": ParagraphStyle(
            name="Nota",
            fontName=FUENTE_CURSIVA,
            fontSize=TAM_PEQUEÑO,
            leading=TAM_PEQUEÑO * 1.25,
            textColor=paleta["texto_suave"],
            alignment=TA_LEFT,
            spaceBefore=4,
            spaceAfter=4,
        ),
        # Etiqueta (para "Nombre:", "Documento:", etc.)
        "etiqueta": ParagraphStyle(
            name="Etiqueta",
            fontName=FUENTE_NEGRITA,
            fontSize=tam_cuerpo,
            leading=tam_cuerpo * 1.15,
            textColor=paleta["texto"],
            alignment=TA_LEFT,
        ),
    }

    # Guardar la paleta y perfil como metadatos accesibles
    estilos["_paleta"] = paleta
    estilos["_perfil"] = perfil
    estilos["_tam_cuerpo"] = tam_cuerpo

    return estilos


# ══════════════════════════════════════════════════════════════════════════════
# 6. COMPONENTE: ENCABEZADO CORPORATIVO COMPACTO
# ══════════════════════════════════════════════════════════════════════════════

def crear_encabezado_corporativo(datos_empresa: dict, paleta: dict,
                                    perfil: str = "normal",
                                    ancho_total: Optional[float] = None) -> list:
    """
    Crea el encabezado corporativo compacto con:
    - Logo a la izquierda (o derecha si logo_derecha)
    - Nombre + NIT en el mismo bloque, sin verse "flotando"
    - Alta legibilidad, formato profesional
    - Etiqueta de versión sutil arriba a la derecha (para verificación)

    Estructura elegida (Alternativa A del prompt):
    - Logo IZQUIERDA (proporción respetada)
    - Nombre destacado + NIT + datos de contacto opcionales A LA DERECHA
    - Separador horizontal fino con color primario

    Retorna: lista de elementos Platypus.
    """
    if ancho_total is None:
        ancho_total = ancho_util(perfil)

    elementos = []

    nombre = datos_empresa.get("nombre", "")
    nit = datos_empresa.get("nit", "")
    ciudad = datos_empresa.get("ciudad", "")
    tel = datos_empresa.get("telefono_empresa") or datos_empresa.get("telefono", "")
    correo = datos_empresa.get("correo_empresa", "")
    logo_path = datos_empresa.get("logo_path", "")
    tiene_logo = bool(logo_path and Path(logo_path).exists())

    # ── Modo compacto tiene logo más pequeño ──────────────────────
    if perfil == "compacto":
        logo_ancho_max = LOGO_COMPACTO_MAX_ANCHO
        logo_alto_max = LOGO_COMPACTO_MAX_ALTO
    else:
        logo_ancho_max = LOGO_MAX_ANCHO
        logo_alto_max = LOGO_MAX_ALTO

    # ── Datos de la empresa — AHORA a la IZQUIERDA (alineados a la izquierda) ──
    tam_nombre = TAM_SUBTITULO if perfil == "compacto" else TAM_TITULO
    tam_datos = TAM_PEQUEÑO if perfil == "compacto" else TAM_CUERPO_MIN

    # Estilo del nombre (grande, negrita, primario) - AHORA a la izquierda
    estilo_nombre = ParagraphStyle(
        name="EmpresaNombre",
        fontName=FUENTE_NEGRITA,
        fontSize=tam_nombre,
        leading=tam_nombre * 1.15,
        textColor=paleta["primario"],
        alignment=TA_LEFT,
    )

    # Estilo de los datos secundarios (pequeño, gris) - AHORA a la izquierda
    estilo_datos = ParagraphStyle(
        name="EmpresaDatos",
        fontName=FUENTE_REGULAR,
        fontSize=tam_datos,
        leading=tam_datos * 1.3,
        textColor=paleta["texto_suave"],
        alignment=TA_LEFT,
    )

    # Construir el bloque de datos con solo lo que existe
    datos_html = [f'<b>{nombre}</b>']
    subdatos = []
    if nit:
        subdatos.append(f"NIT {nit}")
    if ciudad:
        subdatos.append(ciudad)
    if tel:
        subdatos.append(f"Tel. {tel}")
    if correo:
        subdatos.append(correo)

    bloque_datos = [
        Paragraph(nombre, estilo_nombre),
        Paragraph(" · ".join(subdatos), estilo_datos) if subdatos else None,
    ]
    bloque_datos = [b for b in bloque_datos if b is not None]

    # ── Logo AHORA a la DERECHA ─────────────────────────────────
    if tiene_logo:
        try:
            w, h = calcular_dimensiones_logo(logo_path, logo_ancho_max, logo_alto_max)
            logo_img = Image(logo_path, width=w, height=h)
            logo_img.hAlign = "RIGHT"

            # Tabla de 2 columnas: DATOS (izq) | LOGO (der)
            ancho_col_logo = logo_ancho_max + 0.3 * cm
            ancho_col_datos = ancho_total - ancho_col_logo

            tabla = Table(
                [[bloque_datos, logo_img]],  # ← invertido: datos primero, logo después
                colWidths=[ancho_col_datos, ancho_col_logo],
            )
            tabla.setStyle(TableStyle([
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN",        (0, 0), (0, 0),   "LEFT"),   # datos alineados a la izq
                ("ALIGN",        (1, 0), (1, 0),   "RIGHT"),  # logo alineado a la der
                ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING",   (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
            ]))
            elementos.append(tabla)
        except Exception:
            # Fallback: sin logo, solo datos
            for b in bloque_datos:
                elementos.append(b)
    else:
        # Sin logo — datos alineados a la izquierda
        estilo_nombre_sin_logo = ParagraphStyle(
            name="EmpresaNombreSinLogo",
            parent=estilo_nombre,
            alignment=TA_LEFT,
        )
        estilo_datos_sin_logo = ParagraphStyle(
            name="EmpresaDatosSinLogo",
            parent=estilo_datos,
            alignment=TA_LEFT,
        )
        elementos.append(Paragraph(nombre, estilo_nombre_sin_logo))
        if subdatos:
            elementos.append(Paragraph(" · ".join(subdatos), estilo_datos_sin_logo))

    # ── Separador horizontal ──────────────────────────────────────
    espaciador_sup = 6 if perfil == "compacto" else 8
    espaciador_inf = 8 if perfil == "compacto" else 12
    elementos.append(Spacer(1, espaciador_sup))
    elementos.append(HRFlowable(
        width="100%", thickness=1.2,
        color=paleta["primario"], spaceBefore=0, spaceAfter=0,
    ))
    elementos.append(Spacer(1, espaciador_inf))

    return elementos


# ══════════════════════════════════════════════════════════════════════════════
# 7. COMPONENTE: TÍTULO DEL DOCUMENTO
# ══════════════════════════════════════════════════════════════════════════════

def crear_titulo_documento(titulo: str, estilos: dict) -> Paragraph:
    """
    Crea el título del documento centrado, en color primario.
    """
    return Paragraph(titulo.upper(), estilos["titulo"])


# ══════════════════════════════════════════════════════════════════════════════
# 8. COMPONENTE: BLOQUE DE EMPLEADO
# ══════════════════════════════════════════════════════════════════════════════

def crear_bloque_empleado(empleado: dict, paleta: dict, perfil: str = "normal",
                            incluir_cargo: bool = True) -> Paragraph:
    """
    Bloque destinatario compacto — 2 líneas.
    La CC ya no se incluye aquí (aparece en pie de firma abajo).

    Formato actual:
    Línea 1: Señor(a): NOMBRE COMPLETO (negrita)
    Línea 2: Cargo: CARGO (si incluir_cargo)
    """
    nombre = empleado.get("nombre", "").upper()
    cargo = empleado.get("cargo", "")

    tam = TAM_CUERPO_MIN if perfil == "compacto" else TAM_CUERPO
    leading = tam * 1.3

    estilo = ParagraphStyle(
        name="BloqueEmpleado",
        fontName=FUENTE_REGULAR,
        fontSize=tam,
        leading=leading,
        textColor=paleta["texto"],
        alignment=TA_LEFT,
    )

    lineas = [f"<b>Señor(a):</b> <b>{nombre}</b>"]
    if incluir_cargo and cargo:
        lineas.append(f"<b>Cargo:</b> {cargo}")

    return Paragraph("<br/>".join(lineas), estilo)


# ══════════════════════════════════════════════════════════════════════════════
# 9. COMPONENTE: TABLA CORPORATIVA
# ══════════════════════════════════════════════════════════════════════════════

def crear_tabla_corporativa(filas: list, col_widths: Optional[list] = None,
                              paleta: Optional[dict] = None,
                              perfil: str = "normal",
                              alinear_valores_derecha: bool = False) -> Table:
    """
    Tabla corporativa con estilo consistente:
    - Encabezado con fondo primario
    - Bordes suaves
    - Filas alternas ligeramente coloreadas (perfil normal/amplio)
    - Padding reducido en perfil compacto

    Args:
        filas: primera fila es el encabezado
        col_widths: anchos opcionales
        alinear_valores_derecha: si True, las columnas numéricas se alinean a la derecha
    """
    if paleta is None:
        paleta = PALETAS[1]

    tabla = Table(filas, colWidths=col_widths) if col_widths else Table(filas)

    # Padding según perfil
    padding = 4 if perfil == "compacto" else 6

    estilos_tabla = [
        # Encabezado
        ("BACKGROUND",    (0, 0), (-1, 0), paleta["primario"]),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), FUENTE_NEGRITA),
        ("FONTSIZE",      (0, 0), (-1, 0),
            TAM_PEQUEÑO if perfil == "compacto" else TAM_CUERPO_MIN),

        # Alineación general
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),

        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LEFTPADDING",   (0, 0), (-1, -1), padding + 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), padding + 2),

        # Bordes
        ("GRID",          (0, 0), (-1, -1), 0.4, paleta["borde"]),

        # Tamaño del texto en el cuerpo
        ("FONTSIZE",      (0, 1), (-1, -1),
            TAM_PEQUEÑO if perfil == "compacto" else TAM_CUERPO_MIN),
    ]

    # Filas alternadas ligeramente coloreadas (solo si no es compacto)
    if perfil != "compacto":
        for i in range(2, len(filas), 2):
            estilos_tabla.append(
                ("BACKGROUND", (0, i), (-1, i), paleta["fondo_tabla"])
            )

    tabla.setStyle(TableStyle(estilos_tabla))
    return tabla


# ══════════════════════════════════════════════════════════════════════════════
# 10. COMPONENTE: FIRMAS DOBLES
# ══════════════════════════════════════════════════════════════════════════════

def crear_firmas_dobles(representante: str, cargo_representante: str,
                          empresa: str, nombre_empleado: str, cedula: str,
                          estilos: dict, perfil: str = "normal") -> KeepTogether:
    """
    Crea el bloque de firmas dobles (empresa | empleado) envuelto en
    KeepTogether para evitar que se separe del texto anterior.

    Cada firma tiene:
    - Espacio para escribir (Spacer)
    - Línea horizontal
    - Nombre en negrita
    - Cargo/detalle en gris
    """
    paleta = estilos["_paleta"]
    ancho = ancho_util(perfil)

    # Espacio antes de la línea (para la firma manuscrita)
    espacio_firma = 30 if perfil == "compacto" else 45

    # Línea horizontal
    linea_horizontal = HRFlowable(
        width="80%", thickness=0.7,
        color=paleta["texto"], spaceBefore=0, spaceAfter=2,
        hAlign="CENTER",
    )

    # Columna izquierda: representante empresa
    col_empresa = [
        Spacer(1, espacio_firma),
        linea_horizontal,
        Paragraph(representante.upper(), estilos["firma_nombre"]),
        Paragraph(cargo_representante, estilos["firma_cargo"]),
        Paragraph(f"<i>{empresa}</i>", estilos["firma_cargo"]),
    ]

    # Columna derecha: empleado
    col_empleado = [
        Spacer(1, espacio_firma),
        HRFlowable(width="80%", thickness=0.7,
            color=paleta["texto"], spaceBefore=0, spaceAfter=2,
            hAlign="CENTER"),
        Paragraph(nombre_empleado.upper(), estilos["firma_nombre"]),
        Paragraph(f"C.C. {cedula}", estilos["firma_cargo"]),
        Paragraph("EL TRABAJADOR", estilos["firma_cargo"]),
    ]

    tabla_firmas = Table(
        [[col_empresa, col_empleado]],
        colWidths=[ancho / 2, ancho / 2],
    )
    tabla_firmas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # KeepTogether asegura que si no cabe, se pase entera a la siguiente página
    return KeepTogether(tabla_firmas)


# ══════════════════════════════════════════════════════════════════════════════
# 11. COMPONENTE: PIE DE PÁGINA CON NUMERACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def crear_funcion_pie(paleta: dict, logo_path: Optional[str] = None,
                        usar_marca_agua: bool = False,
                        membrete_oficial_path: Optional[str] = None,
                        mostrar_pagina: bool = True) -> callable:
    """
    Crea una función que dibuja el pie de página en cada hoja.
    Uso: doc.build(el, onFirstPage=fn, onLaterPages=fn)

    Args:
        mostrar_pagina: si True, muestra "Página X de Y"
    """
    def _pie(canvas_obj, doc):
        # ── Membrete oficial como fondo completo (modo especial) ───
        if membrete_oficial_path:
            try:
                from PIL import Image as PILImage
                img = PILImage.open(membrete_oficial_path)
                ancho_img, alto_img = img.size
                ancho_pag, alto_pag = PAGE_SIZE
                ratio_img = ancho_img / alto_img
                ratio_pag = ancho_pag / alto_pag
                if ratio_img > ratio_pag:
                    w = ancho_pag
                    h = ancho_pag / ratio_img
                    x, y = 0, (alto_pag - h) / 2
                else:
                    h = alto_pag
                    w = alto_pag * ratio_img
                    y, x = 0, (ancho_pag - w) / 2
                canvas_obj.drawImage(membrete_oficial_path, x, y,
                    width=w, height=h, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
            return  # En modo membrete oficial no dibujar más

        # ── Marca de agua sutil (5% opacidad) ──────────────────────
        if usar_marca_agua and logo_path and Path(logo_path).exists():
            canvas_obj.saveState()
            try:
                canvas_obj.setFillAlpha(0.05)  # 5% — muy sutil
                canvas_obj.setStrokeAlpha(0.05)
                # Centrar
                marca_w = 12 * cm
                marca_h = 12 * cm
                x = (PAGE_WIDTH - marca_w) / 2
                y = (PAGE_HEIGHT - marca_h) / 2
                canvas_obj.drawImage(
                    logo_path, x, y, width=marca_w, height=marca_h,
                    preserveAspectRatio=True, mask="auto",
                )
            except Exception:
                pass
            canvas_obj.restoreState()

        # ── Línea separadora del pie ───────────────────────────────
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(paleta["borde_suave"])
        canvas_obj.setLineWidth(0.4)
        canvas_obj.line(2 * cm, 1.4 * cm, PAGE_WIDTH - 2 * cm, 1.4 * cm)

        # ── Texto del pie ──────────────────────────────────────────
        canvas_obj.setFont(FUENTE_REGULAR, TAM_MICRO)
        canvas_obj.setFillColor(paleta["texto_suave"])

        # Izquierda: fecha de generación + marca GestorRH
        fecha = datetime.today().strftime("%d/%m/%Y %H:%M")
        canvas_obj.drawString(
            2 * cm, 1.0 * cm,
            f"Generado el {fecha} — Gestor RH IA"
        )

        # Derecha: número de página
        if mostrar_pagina:
            num_pagina = canvas_obj.getPageNumber()
            # PageNumber solo tiene la actual — el "X de Y" requiere segundo pass
            canvas_obj.drawRightString(
                PAGE_WIDTH - 2 * cm, 1.0 * cm,
                f"Página {num_pagina}"
            )

        canvas_obj.restoreState()

    return _pie


# ══════════════════════════════════════════════════════════════════════════════
# 12. UTILIDADES DE FORMATO
# ══════════════════════════════════════════════════════════════════════════════

def formato_moneda(valor) -> str:
    """
    Formato colombiano: $ 2.990.000
    """
    try:
        num = float(valor or 0)
    except (ValueError, TypeError):
        return "$ 0"
    entero = int(num)
    s = f"{entero:,}".replace(",", ".")
    return f"$ {s}"


def formato_fecha_larga(fecha_str: str) -> str:
    """Convierte fecha a formato '15 de agosto de 2026'."""
    if not fecha_str:
        return ""
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(str(fecha_str)[:10], fmt)
            return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"
        except ValueError:
            continue
    return str(fecha_str)


def fecha_hoy_larga() -> str:
    """Retorna la fecha de hoy en formato largo."""
    hoy = datetime.today()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
