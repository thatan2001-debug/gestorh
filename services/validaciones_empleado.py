"""
Validaciones para datos de empleados.

Cada función retorna (ok: bool, mensaje: str).
Diseñadas para usarse en formularios de Streamlit y en importación Excel.

Uso:
    from services.validaciones_empleado import validar_empleado

    ok, errores = validar_empleado(datos_dict)
    if not ok:
        for campo, mensaje in errores.items():
            st.error(f"{campo}: {mensaje}")
"""

import re
from datetime import datetime, date
from typing import Optional, Dict, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# VALIDADORES INDIVIDUALES
# ══════════════════════════════════════════════════════════════════════════════

def validar_documento(documento: str, tipo_doc: str = "CC") -> Tuple[bool, str]:
    """
    Valida un número de documento colombiano según su tipo.

    Tipos:
    - CC (Cédula de Ciudadanía): 6-10 dígitos
    - CE (Cédula de Extranjería): 6-8 dígitos
    - TI (Tarjeta de Identidad): 10-11 dígitos
    - PP (Pasaporte): alfanumérico, 6-12 caracteres
    - NIT: 9-10 dígitos (con o sin dígito de verificación)
    """
    if not documento or not str(documento).strip():
        return False, "El documento es obligatorio"

    doc = str(documento).strip().replace(".", "").replace("-", "").replace(" ", "")

    if tipo_doc in ("CC", "CE"):
        if not doc.isdigit():
            return False, f"El {tipo_doc} debe contener solo números"
        if len(doc) < 5 or len(doc) > 11:
            return False, f"El {tipo_doc} debe tener entre 5 y 11 dígitos"
    elif tipo_doc == "TI":
        if not doc.isdigit():
            return False, "La TI debe contener solo números"
        if len(doc) < 10 or len(doc) > 11:
            return False, "La TI debe tener 10 u 11 dígitos"
    elif tipo_doc == "PP":
        if len(doc) < 6 or len(doc) > 15:
            return False, "El pasaporte debe tener entre 6 y 15 caracteres"
    elif tipo_doc == "NIT":
        if not doc.isdigit():
            return False, "El NIT debe contener solo números"
        if len(doc) < 9 or len(doc) > 10:
            return False, "El NIT debe tener 9 o 10 dígitos"

    return True, ""


def validar_nombre(nombre: str) -> Tuple[bool, str]:
    """Valida un nombre completo."""
    if not nombre or not str(nombre).strip():
        return False, "El nombre es obligatorio"
    if len(str(nombre).strip()) < 3:
        return False, "El nombre debe tener al menos 3 caracteres"
    if len(str(nombre).strip()) > 200:
        return False, "El nombre es demasiado largo (máximo 200 caracteres)"
    return True, ""


def validar_correo(correo: str, obligatorio: bool = False) -> Tuple[bool, str]:
    """Valida formato de correo electrónico."""
    correo = str(correo or "").strip()

    if not correo:
        if obligatorio:
            return False, "El correo es obligatorio"
        return True, ""  # vacío está bien si no es obligatorio

    # Regex simple pero efectiva
    patron = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(patron, correo):
        return False, "Formato de correo inválido"

    return True, ""


def validar_telefono(telefono: str, obligatorio: bool = False) -> Tuple[bool, str]:
    """Valida teléfono (celular o fijo colombiano)."""
    tel = str(telefono or "").strip().replace(" ", "").replace("-", "").replace("+", "")

    if not tel:
        if obligatorio:
            return False, "El teléfono es obligatorio"
        return True, ""

    if not tel.isdigit():
        return False, "El teléfono debe contener solo números"

    # Colombia: 7 dígitos (fijo local), 10 dígitos (celular con indicativo)
    if len(tel) < 7 or len(tel) > 13:
        return False, "El teléfono debe tener entre 7 y 13 dígitos"

    return True, ""


def validar_salario(salario) -> Tuple[bool, str]:
    """Valida que el salario sea numérico y positivo."""
    if salario is None or salario == "":
        return False, "El salario es obligatorio"

    try:
        s = float(salario)
    except (ValueError, TypeError):
        return False, "El salario debe ser un número"

    if s < 0:
        return False, "El salario no puede ser negativo"

    if s == 0:
        return False, "El salario debe ser mayor a 0"

    # Salario mínimo Colombia 2026 aprox. — advertencia si es menor
    SMMLV_2026 = 1_423_500  # actualizar cada año
    if s < SMMLV_2026 * 0.9:  # 10% de tolerancia (jornada parcial, etc.)
        return True, f"⚠️ El salario es menor al SMMLV 2026 (${SMMLV_2026:,.0f}). ¿Es jornada parcial?"

    return True, ""


def validar_fecha(fecha_str: str, campo: str = "fecha",
                    obligatoria: bool = True) -> Tuple[bool, str]:
    """Valida que sea una fecha en formato dd/mm/yyyy o yyyy-mm-dd."""
    fecha_str = str(fecha_str or "").strip()

    if not fecha_str:
        if obligatoria:
            return False, f"La {campo} es obligatoria"
        return True, ""

    # Intentar parsear en varios formatos
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            datetime.strptime(fecha_str[:10], fmt)
            return True, ""
        except ValueError:
            continue

    return False, f"Formato de {campo} inválido (use dd/mm/yyyy)"


def validar_fechas_coherentes(fecha_ingreso: str, fecha_retiro: str) -> Tuple[bool, str]:
    """La fecha de retiro debe ser posterior a la de ingreso."""
    if not fecha_retiro or not str(fecha_retiro).strip():
        return True, ""  # sin retiro está bien

    def _parsear(s):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(str(s)[:10], fmt)
            except ValueError:
                continue
        return None

    fi = _parsear(fecha_ingreso)
    fr = _parsear(fecha_retiro)

    if not fi:
        return False, "Fecha de ingreso inválida"
    if not fr:
        return False, "Fecha de retiro inválida"

    if fr < fi:
        return False, "La fecha de retiro no puede ser anterior a la fecha de ingreso"

    return True, ""


def validar_tipo_contrato(tipo: str) -> Tuple[bool, str]:
    """Valida que el tipo de contrato sea uno permitido."""
    permitidos = {
        "indefinido", "fijo", "obra", "prestacion",
        "aprendizaje", "temporal",
    }
    t = str(tipo or "").strip().lower().replace(" ", "_")
    # Aceptar variantes
    t = t.replace("término_", "").replace("de_", "").replace("por_", "")

    if not tipo or not str(tipo).strip():
        return False, "El tipo de contrato es obligatorio"

    if t not in permitidos and "indefinido" not in t and "fijo" not in t \
        and "obra" not in t and "prestacion" not in t and "aprend" not in t:
        return False, f"Tipo de contrato desconocido: {tipo}"

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# VALIDADOR INTEGRAL
# ══════════════════════════════════════════════════════════════════════════════

def validar_empleado(datos: Dict) -> Tuple[bool, Dict[str, str]]:
    """
    Valida un empleado completo. Retorna (ok, errores).

    errores es un dict {campo: mensaje} — solo contiene los campos con problema.
    ok es True solo si el dict está vacío (o solo tiene warnings ⚠️).
    """
    errores = {}
    warnings = {}

    # ── Documento ──
    tipo_doc = datos.get("tipo_documento", "CC")
    ok, msg = validar_documento(datos.get("documento", ""), tipo_doc)
    if not ok:
        errores["documento"] = msg

    # ── Nombre ──
    ok, msg = validar_nombre(datos.get("nombre", ""))
    if not ok:
        errores["nombre"] = msg

    # ── Correo ──
    ok, msg = validar_correo(datos.get("correo", ""), obligatorio=False)
    if not ok:
        errores["correo"] = msg

    # ── Correo personal (opcional) ──
    ok, msg = validar_correo(datos.get("correo_personal", ""), obligatorio=False)
    if not ok:
        errores["correo_personal"] = msg

    # ── Teléfono ──
    ok, msg = validar_telefono(datos.get("telefono", ""), obligatorio=False)
    if not ok:
        errores["telefono"] = msg

    # ── Salario ──
    ok, msg = validar_salario(datos.get("salario"))
    if not ok:
        errores["salario"] = msg
    elif msg.startswith("⚠️"):
        warnings["salario"] = msg

    # ── Cargo ──
    cargo = str(datos.get("cargo", "") or "").strip()
    if not cargo:
        errores["cargo"] = "El cargo es obligatorio"

    # ── Fechas ──
    ok, msg = validar_fecha(datos.get("fecha_ingreso", ""),
                             campo="fecha de ingreso", obligatoria=True)
    if not ok:
        errores["fecha_ingreso"] = msg

    ok, msg = validar_fecha(datos.get("fecha_retiro", ""),
                             campo="fecha de retiro", obligatoria=False)
    if not ok:
        errores["fecha_retiro"] = msg

    # Coherencia entre fechas
    if "fecha_ingreso" not in errores and "fecha_retiro" not in errores:
        ok, msg = validar_fechas_coherentes(
            datos.get("fecha_ingreso", ""),
            datos.get("fecha_retiro", "")
        )
        if not ok:
            errores["fecha_retiro"] = msg

    # ── Tipo de contrato ──
    ok, msg = validar_tipo_contrato(datos.get("tipo_contrato", "Indefinido"))
    if not ok:
        errores["tipo_contrato"] = msg

    # ── Contacto de emergencia (si nombre está, teléfono debe estar) ──
    em_nombre = str(datos.get("emergencia_nombre", "") or "").strip()
    em_telefono = str(datos.get("emergencia_telefono", "") or "").strip()
    if em_nombre and not em_telefono:
        errores["emergencia_telefono"] = "Si hay contacto de emergencia, el teléfono es obligatorio"
    if em_telefono:
        ok, msg = validar_telefono(em_telefono, obligatorio=False)
        if not ok:
            errores["emergencia_telefono"] = msg

    # Los warnings no impiden guardar, pero se retornan
    for campo, warn in warnings.items():
        if campo not in errores:
            errores[campo + "_warning"] = warn

    solo_warnings = all(k.endswith("_warning") for k in errores.keys())
    ok_total = len(errores) == 0 or solo_warnings

    return ok_total, errores


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES ÚTILES PARA FORMULARIOS
# ══════════════════════════════════════════════════════════════════════════════

TIPOS_DOCUMENTO = {
    "CC": "Cédula de Ciudadanía",
    "CE": "Cédula de Extranjería",
    "TI": "Tarjeta de Identidad",
    "PP": "Pasaporte",
    "NIT": "NIT",
}

ESTADOS_CIVILES = ["Soltero(a)", "Casado(a)", "Unión libre", "Divorciado(a)", "Viudo(a)"]

GENEROS = ["Femenino", "Masculino", "No binario", "Prefiero no decir"]

MODALIDADES = ["presencial", "remoto", "hibrido"]

JORNADAS = ["completa", "media", "por_horas"]

TIPOS_CONTRATO = [
    "Indefinido",
    "Término fijo",
    "Obra o labor",
    "Prestación de servicios",
    "Aprendizaje",
    "Temporal",
]

# EPS más comunes en Colombia (para autocompletar)
EPS_COMUNES = [
    "Sura", "Sanitas", "Compensar", "Nueva EPS", "Salud Total",
    "Famisanar", "Coosalud", "Mutual Ser", "Aliansalud", "Cajacopi",
    "Servicio Occidental de Salud (SOS)", "Ecoopsos", "Emssanar",
    "Otro",
]

# Fondos de pensiones
FONDOS_PENSION = [
    "Colpensiones", "Porvenir", "Protección", "Colfondos", "Skandia", "Otro",
]

# Fondos de cesantías
FONDOS_CESANTIAS = [
    "Porvenir", "Protección", "Colfondos", "Fondo Nacional del Ahorro", "Skandia", "Otro",
]

# ARL más comunes
ARL_COMUNES = [
    "Sura", "Positiva", "Colmena", "Bolívar", "AXA Colpatria",
    "La Equidad", "Mapfre", "Liberty", "Otro",
]

# Cajas de compensación
CAJAS_COMPENSACION = [
    "Compensar", "Cafam", "Colsubsidio", "Comfenalco Valle", "Comfama",
    "Comfandi", "Cajasan", "Comfaboy", "Otro",
]
