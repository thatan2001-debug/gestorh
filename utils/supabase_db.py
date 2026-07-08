"""
Capa de base de datos para RH Fácil.
Usa Supabase (PostgreSQL) si las variables de entorno están configuradas.
Fallback transparente a JSON local si no lo están (desarrollo/demo).
"""

import os, json, hashlib
from datetime import datetime
from pathlib import Path

_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        return _client
    except Exception as e:
        print(f"Supabase no disponible: {e}")
        return None

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def supabase_activo() -> bool:
    return _get_client() is not None

# ── Fallback JSON ─────────────────────────────────────────────────────────────
_JSON_PATH = Path("salidas/.usuarios.json")

USUARIOS_INICIALES = {
    "demo@rhfacil.co": {
        "nombre": "Usuario Demo", "password_hash": _hash("RHFacil2026"),
        "plan": "pro", "documentos_usados": 0, "activo": True,
        "es_admin": False, "es_demo": True, "empresa": "",
        "empresa_config": {}
    },
    "admin@rhfacil.co": {
        "nombre": "Administrador", "password_hash": _hash("Admin2026*"),
        "plan": "empresarial", "documentos_usados": 0, "activo": True,
        "es_admin": True, "es_demo": False, "empresa": "",
        "empresa_config": {}
    },
}

def _json_load() -> dict:
    if _JSON_PATH.exists():
        try:
            with open(_JSON_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    _JSON_PATH.parent.mkdir(exist_ok=True)
    with open(_JSON_PATH, "w") as f:
        json.dump(USUARIOS_INICIALES, f, indent=2)
    return USUARIOS_INICIALES.copy()

def _json_save(data: dict):
    _JSON_PATH.parent.mkdir(exist_ok=True)
    with open(_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════════════════════════

def usuario_login(email: str, password: str):
    """(ok, mensaje, datos|None)"""
    email = email.strip().lower()
    sb = _get_client()
    if sb:
        try:
            r = sb.table("usuarios").select("*").eq("email", email).single().execute()
            u = r.data
            if not u: return False, "Correo no registrado.", None
            if not u.get("activo"): return False, "Cuenta pendiente de activación.", None
            if u["password_hash"] != _hash(password): return False, "Contraseña incorrecta.", None
            return True, "Bienvenido", {
                "email": email, "nombre": u["nombre"], "plan": u["plan"],
                "documentos_usados": u.get("documentos_usados", 0),
                "es_admin": u.get("es_admin", False), "es_demo": u.get("es_demo", False),
            }
        except Exception as e:
            if "no rows" in str(e).lower() or "PGRST116" in str(e):
                return False, "Correo no registrado.", None
            return False, f"Error: {e}", None
    else:
        usuarios = _json_load()
        if email not in usuarios: return False, "Correo no registrado.", None
        u = usuarios[email]
        if not u.get("activo"): return False, "Cuenta pendiente de activación.", None
        if u["password_hash"] != _hash(password): return False, "Contraseña incorrecta.", None
        return True, "Bienvenido", {
            "email": email, "nombre": u["nombre"], "plan": u["plan"],
            "documentos_usados": u.get("documentos_usados", 0),
            "es_admin": u.get("es_admin", False), "es_demo": u.get("es_demo", False),
        }


def usuario_registrar(email: str, nombre: str, password: str,
                       empresa: str = "", telefono: str = ""):
    email = email.strip().lower()
    if not email or "@" not in email: return False, "Correo inválido."
    if len(password) < 6: return False, "Contraseña mínimo 6 caracteres."
    if not nombre.strip(): return False, "Nombre requerido."
    sb = _get_client()
    if sb:
        try:
            existe = sb.table("usuarios").select("email").eq("email", email).execute()
            if existe.data: return False, "Ya existe una cuenta con ese correo."
            sb.table("usuarios").insert({
                "email": email, "nombre": nombre.strip(),
                "password_hash": _hash(password), "plan": "gratuito",
                "activo": False, "es_admin": False, "es_demo": False,
                "empresa_nombre": empresa.strip(), "telefono": telefono.strip(),
            }).execute()
            return True, "Registro exitoso. El administrador activará tu cuenta pronto."
        except Exception as e:
            return False, f"Error al registrar: {e}"
    else:
        usuarios = _json_load()
        if email in usuarios: return False, "Ya existe una cuenta con ese correo."
        usuarios[email] = {
            "nombre": nombre.strip(), "password_hash": _hash(password),
            "plan": "gratuito", "documentos_usados": 0,
            "activo": False, "es_admin": False, "es_demo": False,
            "empresa": empresa.strip(), "telefono": telefono.strip(),
            "empresa_config": {}
        }
        _json_save(usuarios)
        return True, "Registro exitoso. El administrador activará tu cuenta pronto."


def usuario_registrar_uso(email: str, cantidad: int):
    sb = _get_client()
    if sb:
        try:
            r = sb.table("usuarios").select("documentos_usados").eq("email", email).single().execute()
            actual = r.data.get("documentos_usados", 0)
            sb.table("usuarios").update({"documentos_usados": actual + cantidad}).eq("email", email).execute()
        except Exception: pass
    else:
        u = _json_load()
        if email in u:
            u[email]["documentos_usados"] = u[email].get("documentos_usados", 0) + cantidad
            _json_save(u)


def usuarios_listar() -> list:
    sb = _get_client()
    if sb:
        try:
            r = sb.table("usuarios").select("*").eq("es_admin", False).execute()
            return r.data or []
        except Exception: return []
    else:
        u = _json_load()
        return [{"email": e, **d} for e, d in u.items() if not d.get("es_admin")]


def usuario_activar(email: str) -> bool:
    sb = _get_client()
    if sb:
        try:
            sb.table("usuarios").update({"activo": True}).eq("email", email).execute()
            return True
        except Exception: return False
    else:
        u = _json_load(); u[email]["activo"] = True; _json_save(u); return True


def usuario_desactivar(email: str) -> bool:
    sb = _get_client()
    if sb:
        try:
            sb.table("usuarios").update({"activo": False}).eq("email", email).execute()
            return True
        except Exception: return False
    else:
        u = _json_load(); u[email]["activo"] = False; _json_save(u); return True


def usuario_cambiar_plan(email: str, plan: str) -> bool:
    sb = _get_client()
    if sb:
        try:
            sb.table("usuarios").update({"plan": plan}).eq("email", email).execute()
            return True
        except Exception: return False
    else:
        u = _json_load(); u[email]["plan"] = plan; _json_save(u); return True


def usuario_eliminar(email: str) -> bool:
    sb = _get_client()
    if sb:
        try:
            sb.table("usuarios").delete().eq("email", email).execute()
            return True
        except Exception: return False
    else:
        u = _json_load()
        if email in u: del u[email]; _json_save(u)
        return True


def usuarios_stats() -> dict:
    lista = usuarios_listar()
    from utils.plan_control import PLANES
    pendientes = [u for u in lista if not u.get("activo")]
    return {
        "total": len(lista),
        "activos": sum(1 for u in lista if u.get("activo")),
        "pendientes_activacion": len(pendientes),
        "total_docs": sum(u.get("documentos_usados", 0) for u in lista),
        "por_plan": {p: sum(1 for u in lista if u.get("plan") == p)
                     for p in ["gratuito","basico","pro","empresarial"]},
    }

# ══════════════════════════════════════════════════════════════════════════════
# EMPRESAS — repositorio completo del perfil de empresa
# ══════════════════════════════════════════════════════════════════════════════

CAMPOS_EMPRESA = [
    "nombre","nit","ciudad","direccion","telefono_empresa","correo_empresa","sector",
    "num_empleados","representante",
    "firmante_cert_nombre","firmante_cert_cargo",
    "firmante_vac_nombre","firmante_vac_cargo",
    "firmante_liq_nombre","firmante_liq_cargo",
    "logo_nombre","membrete_nombre",
    "usar_logo_encabezado","usar_marca_agua","disenio_seleccionado",
    "onboarding_completo",
]


def empresa_guardar(email: str, datos: dict) -> bool:
    """Guarda o actualiza el perfil completo de empresa del usuario."""
    email = email.strip().lower()
    # Solo guardar campos conocidos
    payload = {k: datos.get(k) for k in CAMPOS_EMPRESA if k in datos}
    payload["email"] = email
    payload["updated_at"] = datetime.now().isoformat()

    sb = _get_client()
    if sb:
        try:
            sb.table("empresas").upsert(payload).execute()
            return True
        except Exception as e:
            print(f"Error guardando empresa: {e}")
            return False
    else:
        u = _json_load()
        if email in u:
            u[email]["empresa_config"] = payload
            _json_save(u)
        return True


def empresa_cargar(email: str) -> dict | None:
    """Carga el perfil completo de empresa del usuario."""
    email = email.strip().lower()
    sb = _get_client()
    if sb:
        try:
            r = sb.table("empresas").select("*").eq("email", email).single().execute()
            return r.data or None
        except Exception:
            return None
    else:
        u = _json_load()
        return u.get(email, {}).get("empresa_config")


def empresa_onboarding_completo(email: str) -> bool:
    """¿El usuario ya completó el onboarding de empresa?"""
    datos = empresa_cargar(email)
    if not datos: return False
    return bool(datos.get("onboarding_completo") and datos.get("nombre") and datos.get("nit"))

# ══════════════════════════════════════════════════════════════════════════════
# LOG DE DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════

def log_documento(email: str, tipo: str, cantidad: int, empleado: str = ""):
    sb = _get_client()
    if sb:
        try:
            sb.table("documentos_log").insert({
                "email": email, "tipo_documento": tipo,
                "cantidad": cantidad, "empleado_nombre": empleado,
            }).execute()
        except Exception: pass
