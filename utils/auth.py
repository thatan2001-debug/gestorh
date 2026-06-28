"""
Sistema de autenticación RH Fácil.
- Login persistente con st.session_state
- Registro de nuevos usuarios (plan gratuito, pendiente activación)
- Panel de administrador: ver, activar/desactivar y cambiar plan
- Usuarios guardados en JSON local (migrar a Supabase en producción)
"""

import json
import hashlib
from pathlib import Path
from pathlib import Path
from datetime import datetime

ARCHIVO_USUARIOS = Path("salidas/.usuarios.json")
ADMIN_EMAIL = "admin@rhfacil.co"

USUARIOS_INICIALES = {
    "demo@rhfacil.co": {
        "nombre": "Usuario Demo",
        "password_hash": hashlib.sha256("RHFacil2026".encode()).hexdigest(),
        "plan": "pro",
        "documentos_usados": 0,
        "fecha_registro": "2026-01-01",
        "activo": True,
        "activado_por_admin": True,
        "es_demo": True,
        "empresa": "Demo",
        "telefono": "",
    },
    "admin@rhfacil.co": {
        "nombre": "Administrador RH Fácil",
        "password_hash": hashlib.sha256("Admin2026*".encode()).hexdigest(),
        "plan": "empresarial",
        "documentos_usados": 0,
        "fecha_registro": "2026-01-01",
        "activo": True,
        "activado_por_admin": True,
        "es_demo": False,
        "es_admin": True,
        "empresa": "RH Fácil",
        "telefono": "",
    },
}


def _cargar() -> dict:
    if ARCHIVO_USUARIOS.exists():
        try:
            with open(ARCHIVO_USUARIOS) as f:
                return json.load(f)
        except Exception:
            pass
    _guardar(USUARIOS_INICIALES)
    return USUARIOS_INICIALES.copy()


def _guardar(usuarios: dict):
    ARCHIVO_USUARIOS.parent.mkdir(exist_ok=True)
    with open(ARCHIVO_USUARIOS, "w") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Autenticación ────────────────────────────────────────────────────────────

def login(email: str, password: str):
    """Retorna (ok, mensaje, datos_usuario|None)."""
    email = email.strip().lower()
    usuarios = _cargar()

    if email not in usuarios:
        return False, "Correo no registrado.", None

    u = usuarios[email]

    if not u.get("activo", False):
        return False, (
            "Tu cuenta aún no ha sido activada por el administrador. "
            "Recibirás un correo cuando esté lista."
        ), None

    if u["password_hash"] != _hash(password):
        return False, "Contraseña incorrecta.", None

    return True, "¡Bienvenido!", {
        "email": email,
        "nombre": u["nombre"],
        "plan": u["plan"],
        "documentos_usados": u.get("documentos_usados", 0),
        "es_admin": u.get("es_admin", False),
        "es_demo": u.get("es_demo", False),
        "empresa": u.get("empresa", ""),
    }


def registrar(email: str, nombre: str, password: str,
              empresa: str = "", telefono: str = ""):
    """
    Registra usuario con plan gratuito y activo=False
    (requiere activación del admin antes de poder ingresar).
    """
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Correo electrónico inválido."
    if len(password) < 6:
        return False, "La contraseña debe tener mínimo 6 caracteres."
    if not nombre.strip():
        return False, "Ingresa tu nombre completo."

    usuarios = _cargar()
    if email in usuarios:
        return False, "Ya existe una cuenta con ese correo."

    usuarios[email] = {
        "nombre": nombre.strip(),
        "password_hash": _hash(password),
        "plan": "gratuito",
        "documentos_usados": 0,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "activo": False,           # ← espera activación del admin
        "activado_por_admin": False,
        "es_demo": False,
        "es_admin": False,
        "empresa": empresa.strip(),
        "telefono": telefono.strip(),
    }
    _guardar(usuarios)
    return True, "Registro exitoso. El administrador activará tu cuenta pronto."


def registrar_uso_usuario(email: str, cantidad: int):
    usuarios = _cargar()
    if email in usuarios:
        usuarios[email]["documentos_usados"] = (
            usuarios[email].get("documentos_usados", 0) + cantidad
        )
        _guardar(usuarios)


def obtener_limite_plan(plan: str) -> dict:
    from utils.plan_control import PLANES
    info = PLANES.get(plan, PLANES["gratuito"])
    return {
        "max_docs": info["max_documentos"],
        "tiene_limite": info["limite"],
        "dias_prueba": info.get("dias_prueba"),
    }


# ── Panel de administrador ───────────────────────────────────────────────────

def listar_usuarios() -> list[dict]:
    """Retorna todos los usuarios (excepto admin) como lista de dicts."""
    usuarios = _cargar()
    resultado = []
    for email, datos in usuarios.items():
        if datos.get("es_admin"):
            continue
        resultado.append({
            "email": email,
            "nombre": datos.get("nombre", ""),
            "empresa": datos.get("empresa", ""),
            "telefono": datos.get("telefono", ""),
            "plan": datos.get("plan", "gratuito"),
            "activo": datos.get("activo", False),
            "activado_por_admin": datos.get("activado_por_admin", False),
            "documentos_usados": datos.get("documentos_usados", 0),
            "fecha_registro": datos.get("fecha_registro", ""),
            "es_demo": datos.get("es_demo", False),
        })
    # Más recientes primero
    resultado.sort(key=lambda x: x["fecha_registro"], reverse=True)
    return resultado


def activar_usuario(email: str) -> bool:
    usuarios = _cargar()
    if email in usuarios:
        usuarios[email]["activo"] = True
        usuarios[email]["activado_por_admin"] = True
        usuarios[email]["fecha_activacion"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _guardar(usuarios)
        return True
    return False


def desactivar_usuario(email: str) -> bool:
    usuarios = _cargar()
    if email in usuarios and not usuarios[email].get("es_admin"):
        usuarios[email]["activo"] = False
        _guardar(usuarios)
        return True
    return False


def cambiar_plan(email: str, nuevo_plan: str) -> bool:
    from utils.plan_control import PLANES
    if nuevo_plan not in PLANES:
        return False
    usuarios = _cargar()
    if email in usuarios:
        usuarios[email]["plan"] = nuevo_plan
        usuarios[email]["plan_actualizado"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _guardar(usuarios)
        return True
    return False


def eliminar_usuario(email: str) -> bool:
    usuarios = _cargar()
    if email in usuarios and not usuarios[email].get("es_admin"):
        del usuarios[email]
        _guardar(usuarios)
        return True
    return False


def stats_resumen() -> dict:
    """Estadísticas rápidas para el dashboard admin."""
    usuarios = _cargar()
    lista = [u for e, u in usuarios.items() if not u.get("es_admin")]
    pendientes = [u for u in lista if not u.get("activo") and not u.get("activado_por_admin")]
    return {
        "total": len(lista),
        "activos": sum(1 for u in lista if u.get("activo")),
        "pendientes_activacion": len(pendientes),
        "total_docs": sum(u.get("documentos_usados", 0) for u in lista),
        "por_plan": {
            p: sum(1 for u in lista if u.get("plan") == p)
            for p in ["gratuito", "basico", "pro", "empresarial"]
        },
    }

# ── Persistencia de datos de empresa por usuario ─────────────────────────────

CAMPOS_EMPRESA = [
    "nombre", "nit", "representante", "correo_empresa", "logo_path",
    "firmante_cert_nombre", "firmante_cert_cargo",
    "firmante_vac_nombre",  "firmante_vac_cargo",
    "firmante_liq_nombre",  "firmante_liq_cargo",
    "usar_logo_encabezado", "usar_marca_agua",
    "disenio_seleccionado", "membrete_path",
]


def guardar_empresa_usuario(email: str, datos_empresa: dict):
    """
    Guarda la configuración de empresa del usuario en el JSON de usuarios.
    Solo guarda los campos relevantes (no rutas de archivos temporales).
    """
    email = email.strip().lower()
    usuarios = _cargar()
    if email not in usuarios:
        return False
    # Guardar solo campos de texto — las rutas de archivos se manejan aparte
    empresa_guardada = {}
    for campo in CAMPOS_EMPRESA:
        if campo in datos_empresa:
            # No guardar rutas absolutas (pueden cambiar entre deploys)
            if campo in ("logo_path", "membrete_path"):
                # Solo guardar el nombre del archivo, no la ruta completa
                val = datos_empresa.get(campo)
                empresa_guardada[campo] = Path(val).name if val else None
            else:
                empresa_guardada[campo] = datos_empresa.get(campo)
    usuarios[email]["empresa_config"] = empresa_guardada
    _guardar(usuarios)
    return True


def cargar_empresa_usuario(email: str) -> dict | None:
    """
    Carga la configuración de empresa guardada para el usuario.
    Retorna None si no tiene configuración guardada.
    """
    email = email.strip().lower()
    usuarios = _cargar()
    if email not in usuarios:
        return None
    config = usuarios[email].get("empresa_config")
    if not config:
        return None
    # Reconstruir rutas absolutas si los archivos existen
    for campo in ("logo_path", "membrete_path"):
        nombre_archivo = config.get(campo)
        if nombre_archivo:
            ruta_posible = Path("assets") / nombre_archivo
            config[campo] = str(ruta_posible) if ruta_posible.exists() else None
        else:
            config[campo] = None
    return config
