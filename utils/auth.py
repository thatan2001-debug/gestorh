"""
Autenticación Gestor RH IA.

⚠️  IMPORTANTE (S2.2, julio 2026):
Este módulo migró de SHA-256 a Argon2id con retrocompatibilidad.
- Nuevas contraseñas: se hashean con Argon2id
- Contraseñas legacy con SHA-256: se aceptan una vez, luego se re-hashean automáticamente

Este módulo mantiene la MISMA INTERFAZ pública (login, registrar) para no
romper el resto de la app. La lógica de hash/verify se delega a
services/auth_service.py.
"""

from utils.db import (
    usuario_obtener, usuario_existe, usuario_crear,
    usuario_activar, usuario_desactivar, usuario_cambiar_plan,
    usuario_sumar_docs, usuario_eliminar, usuarios_listar,
    empresa_guardar, empresa_cargar, empresa_onboarding_ok,
    stats_admin,
)

# ⚠️  ADMIN_EMAIL se mantiene por compatibilidad, pero YA NO existe un usuario
# hardcoded con este correo. El primer admin se crea con scripts/crear_primer_admin.py
ADMIN_EMAIL = "admin@gestorrh.co"


def login(email: str, password: str):
    """
    Verifica credenciales y retorna (ok, mensaje, datos_usuario).

    Aplica:
    - Rate limiting (bloqueo temporal tras N intentos fallidos)
    - Verificación Argon2 + retrocompat SHA-256
    - Re-hash automático si el hash es legacy

    Retorna (True, mensaje, dict_usuario) si todo bien.
    """
    from services.auth_service import auth_service
    from services.rate_limit_service import rate_limiter

    email = email.strip().lower()

    # ── 1. Verificar bloqueo por rate limiting ────────────────────────
    bloqueado, tiempo = rate_limiter.esta_bloqueado(email)
    if bloqueado:
        try:
            from utils.logs import log_warn
            log_warn("auth.login.bloqueado", email=email, tiempo_restante=tiempo)
        except Exception:
            pass
        return False, (
            f"⛔ Cuenta bloqueada temporalmente por seguridad. "
            f"Intenta de nuevo en {tiempo}. "
            f"Si olvidaste tu contraseña, contacta al administrador."
        ), None

    # ── 2. Buscar usuario ─────────────────────────────────────────────
    u = usuario_obtener(email)

    if not u:
        rate_limiter.registrar_intento(email, exitoso=False)
        return False, "Correo no registrado.", None

    if not u.get("activo", False):
        return False, (
            "Tu cuenta está pendiente de activación por el administrador. "
            "Recibirás confirmación pronto."
        ), None

    hash_almacenado = u.get("password_hash", "")

    # ── 3. Verificar contraseña ───────────────────────────────────────
    try:
        ok, needs_rehash = auth_service.verify_password(password, hash_almacenado)
    except Exception as e:
        try:
            from utils.logs import log_error
            log_error("auth.verify.excepcion", email=email, error=str(e))
        except Exception:
            pass
        rate_limiter.registrar_intento(email, exitoso=False)
        return False, "Contraseña incorrecta.", None

    if not ok:
        rate_limiter.registrar_intento(email, exitoso=False)
        return False, "Contraseña incorrecta.", None

    # Login exitoso — registrar y limpiar contador de intentos
    rate_limiter.registrar_intento(email, exitoso=True)
    rate_limiter.limpiar_intentos(email)

    # Login exitoso — si el hash es legacy, re-hashear automáticamente
    if needs_rehash:
        try:
            nuevo_hash = auth_service.hash_password(password)
            _actualizar_hash_usuario(email, nuevo_hash)
            try:
                from utils.logs import log_info
                log_info("auth.rehash.exitoso", email=email)
            except Exception:
                pass
        except Exception as e:
            # No bloquear el login si falla el rehash — solo loguearlo
            try:
                from utils.logs import log_warn
                log_warn("auth.rehash.fallo", email=email, error=str(e))
            except Exception:
                pass

    return True, "¡Bienvenido!", {
        "email":       email,
        "nombre":      u.get("nombre",""),
        "plan":        u.get("plan","gratuito"),
        "docs_usados": u.get("docs_usados",0),
        "es_admin":    u.get("es_admin",False),
        "es_demo":     u.get("es_demo",False),
    }


def registrar(email: str, nombre: str, password: str):
    """
    Registra un nuevo usuario. La contraseña se hashea con Argon2.
    Retorna (ok, mensaje).
    """
    from services.auth_service import auth_service, evaluar_fortaleza_password

    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Correo inválido."
    if not nombre.strip():
        return False, "Ingresa tu nombre completo."

    # Validación de fortaleza — antes solo eran 6 caracteres, ahora 8+
    cumple, problemas = evaluar_fortaleza_password(password)
    if not cumple:
        return False, "Contraseña insegura: " + "; ".join(problemas)

    if usuario_existe(email):
        return False, "Ya existe una cuenta con ese correo."

    try:
        hash_seguro = auth_service.hash_password(password)
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        try:
            from utils.logs import log_error
            log_error("auth.hash.excepcion", email=email, error=str(e))
        except Exception:
            pass
        return False, "Error interno. Inténtalo de nuevo."

    ok = usuario_crear(email, nombre.strip(), hash_seguro)
    if ok:
        try:
            from utils.logs import log_info
            log_info("auth.registro.exitoso", email=email)
        except Exception:
            pass
        return True, "Registro exitoso. El administrador activará tu cuenta pronto."
    return False, "Error al crear la cuenta. Intenta de nuevo."


def _actualizar_hash_usuario(email: str, nuevo_hash: str) -> bool:
    """
    Actualiza el hash de contraseña de un usuario en la BD (Supabase o JSON).
    Uso interno — normalmente llamado por login() al detectar rehash.
    """
    from utils.db import supabase_ok, _db, _jl, _js

    email = email.strip().lower()
    try:
        if supabase_ok():
            _db().table("usuarios").update(
                {"password_hash": nuevo_hash}
            ).eq("email", email).execute()
            return True
        # Fallback JSON
        d = _jl()
        if email in d:
            d[email]["password_hash"] = nuevo_hash
            _js(d)
            return True
        return False
    except Exception as e:
        try:
            from utils.logs import log_error
            log_error("auth.actualizar_hash.fallo", email=email, error=str(e))
        except Exception:
            pass
        return False


def cambiar_password(email: str, password_actual: str, password_nuevo: str):
    """
    Permite a un usuario cambiar su contraseña.
    Verifica la contraseña actual antes de aceptar la nueva.
    Retorna (ok, mensaje).
    """
    from services.auth_service import auth_service, evaluar_fortaleza_password

    email = email.strip().lower()

    # Validar la nueva
    cumple, problemas = evaluar_fortaleza_password(password_nuevo)
    if not cumple:
        return False, "Contraseña insegura: " + "; ".join(problemas)

    # Verificar la actual
    u = usuario_obtener(email)
    if not u:
        return False, "Usuario no encontrado."

    ok, _ = auth_service.verify_password(password_actual, u.get("password_hash",""))
    if not ok:
        return False, "Contraseña actual incorrecta."

    # Guardar la nueva
    try:
        nuevo_hash = auth_service.hash_password(password_nuevo)
        if _actualizar_hash_usuario(email, nuevo_hash):
            try:
                from utils.logs import log_info
                log_info("auth.cambio_password.exitoso", email=email)
            except Exception:
                pass
            return True, "Contraseña actualizada correctamente."
        return False, "Error al guardar. Inténtalo de nuevo."
    except Exception as e:
        return False, f"Error: {e}"


def obtener_limite_plan(plan: str) -> dict:
    from utils.plan_control import PLANES
    info = PLANES.get(plan, PLANES["gratuito"])
    return {"max_docs": info["max_documentos"], "tiene_limite": info["limite"]}


# ═══════════════════════════════════════════════════════════════════════════
# ALIASES DE COMPATIBILIDAD HACIA ATRÁS
# ═══════════════════════════════════════════════════════════════════════════
# Antes de la refactorización S2.2 algunos módulos importaban con nombres
# distintos (verbo primero). Se mantienen aquí como aliases para no romper
# archivos que aún importen los nombres viejos (pages/admin.py, etc.).

listar_usuarios     = usuarios_listar
activar_usuario     = usuario_activar
desactivar_usuario  = usuario_desactivar
cambiar_plan_usuario = usuario_cambiar_plan
eliminar_usuario    = usuario_eliminar
sumar_docs_usuario  = usuario_sumar_docs
obtener_usuario     = usuario_obtener

# ─── Aliases cortos (sin sufijo "_usuario") ───
# Cubre variantes usadas por pages/admin.py y otros módulos legacy
cambiar_plan   = usuario_cambiar_plan
activar        = usuario_activar
desactivar     = usuario_desactivar
eliminar       = usuario_eliminar
sumar_docs     = usuario_sumar_docs
listar         = usuarios_listar
listar_todos   = usuarios_listar


# Re-exportar para compatibilidad con el resto de la app
__all__ = [
    "login", "registrar", "cambiar_password", "obtener_limite_plan", "ADMIN_EMAIL",
    "usuario_activar", "usuario_desactivar", "usuario_cambiar_plan",
    "usuario_sumar_docs", "usuario_eliminar", "usuarios_listar",
    "empresa_guardar", "empresa_cargar", "empresa_onboarding_ok", "stats_admin",
    # Aliases retrocompat
    "listar_usuarios", "activar_usuario", "desactivar_usuario",
    "cambiar_plan_usuario", "eliminar_usuario", "sumar_docs_usuario",
    "obtener_usuario",
    # Aliases cortos
    "cambiar_plan", "activar", "desactivar", "eliminar",
    "sumar_docs", "listar", "listar_todos",
]
