"""Autenticación RH Fácil — usa db.py como capa de datos."""

import hashlib
from pathlib import Path
from utils.db import (
    usuario_obtener, usuario_existe, usuario_crear,
    usuario_activar, usuario_desactivar, usuario_cambiar_plan,
    usuario_sumar_docs, usuario_eliminar, usuarios_listar,
    empresa_guardar, empresa_cargar, empresa_onboarding_ok,
    stats_admin,
)

ADMIN_EMAIL = "admin@rhfacil.co"

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def login(email: str, password: str):
    email = email.strip().lower()
    u = usuario_obtener(email)
    if not u:
        return False, "Correo no registrado.", None
    if not u.get("activo", False):
        return False, ("Tu cuenta está pendiente de activación por el administrador. "
                       "Recibirás confirmación pronto."), None
    if u.get("password_hash") != _hash(password):
        return False, "Contraseña incorrecta.", None
    return True, "¡Bienvenido!", {
        "email":      email,
        "nombre":     u.get("nombre",""),
        "plan":       u.get("plan","gratuito"),
        "docs_usados":u.get("docs_usados",0),
        "es_admin":   u.get("es_admin",False),
        "es_demo":    u.get("es_demo",False),
    }

def registrar(email: str, nombre: str, password: str):
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Correo inválido."
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."
    if not nombre.strip():
        return False, "Ingresa tu nombre completo."
    if usuario_existe(email):
        return False, "Ya existe una cuenta con ese correo."
    ok = usuario_crear(email, nombre.strip(), _hash(password))
    if ok:
        return True, "Registro exitoso. El administrador activará tu cuenta pronto."
    return False, "Error al crear la cuenta. Intenta de nuevo."

def obtener_limite_plan(plan: str) -> dict:
    from utils.plan_control import PLANES
    info = PLANES.get(plan, PLANES["gratuito"])
    return {"max_docs": info["max_documentos"], "tiene_limite": info["limite"]}

# Re-exportar para compatibilidad con admin.py
__all__ = [
    "login","registrar","obtener_limite_plan","ADMIN_EMAIL",
    "usuario_activar","usuario_desactivar","usuario_cambiar_plan",
    "usuario_sumar_docs","usuario_eliminar","usuarios_listar",
    "empresa_guardar","empresa_cargar","empresa_onboarding_ok","stats_admin",
]
