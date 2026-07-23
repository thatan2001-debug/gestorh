"""
Panel de administrador (pages/admin.py).

⚠️ IMPORTANTE: si accedes a esta página directamente por URL
(/admin), Streamlit la carga automáticamente. Este archivo debe
importar SIEMPRE con los nombres actuales del backend.

Después de la Etapa 2 (S2.2), utils/auth.py exporta:
- usuarios_listar (era listar_usuarios)
- usuario_activar (era activar_usuario)
- usuario_desactivar (era desactivar_usuario)
- usuario_cambiar_plan (era cambiar_plan_usuario)
- usuario_eliminar (era eliminar_usuario)

Los aliases legacy también están disponibles, pero esta versión
usa los nombres nuevos por claridad.

Este archivo también verifica que el usuario tenga es_admin=True
antes de mostrar nada.
"""

import streamlit as st
from utils.auth import (
    usuarios_listar,
    usuario_activar,
    usuario_desactivar,
    usuario_cambiar_plan,
    usuario_eliminar,
    stats_admin,
)

# ══════════════════════════════════════════════════════════════════════════════
# GATE — Solo administradores
# ══════════════════════════════════════════════════════════════════════════════

usuario = st.session_state.get("usuario") or {}

if not usuario:
    st.error("⚠️ Debes iniciar sesión primero.")
    st.stop()

if not usuario.get("es_admin"):
    st.error("⚠️ No tienes permisos de administrador.")
    st.info("Contacta al administrador del sistema si crees que esto es un error.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PANEL DE ADMINISTRACIÓN
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 🛡️ Panel de Administrador")
st.caption("Gestión de usuarios y estadísticas del sistema")

# ─── ESTADÍSTICAS GENERALES ─────────────────────────────────────
try:
    stats = stats_admin()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total usuarios",   stats.get("total", 0))
    c2.metric("Activos",          stats.get("activos", 0))
    c3.metric("Pendientes",       stats.get("pendientes", 0))
    c4.metric("Docs generados",   stats.get("total_docs", 0))
except Exception as e:
    st.warning(f"No se pudieron cargar estadísticas: {e}")

st.divider()

# ─── LISTA DE USUARIOS ──────────────────────────────────────────
st.markdown("### 👥 Usuarios registrados")

try:
    usuarios = usuarios_listar()
except Exception as e:
    st.error(f"Error listando usuarios: {e}")
    usuarios = []

if not usuarios:
    st.info("No hay usuarios registrados aún.")
else:
    # Filtro rápido
    filtro = st.text_input("🔍 Buscar por correo o nombre",
                            placeholder="ej: juan@empresa.com")
    if filtro:
        f = filtro.lower().strip()
        usuarios = [u for u in usuarios
                     if f in (u.get("email", "") or "").lower()
                     or f in (u.get("nombre", "") or "").lower()]

    st.caption(f"Mostrando {len(usuarios)} usuario(s)")
    st.divider()

    for user in usuarios:
        email_u = user.get("email", "")
        nombre_u = user.get("nombre", "")
        plan_u = user.get("plan", "gratuito")
        activo_u = user.get("activo", False)
        es_admin_u = user.get("es_admin", False)
        docs = user.get("docs_usados") or user.get("documentos_usados", 0)

        # Card por usuario
        with st.container():
            c1, c2, c3 = st.columns([3, 2, 2])

            with c1:
                estado = "🟢" if activo_u else "🔴"
                admin_badge = " 👑" if es_admin_u else ""
                st.markdown(
                    f"**{estado} {nombre_u}**{admin_badge}  \n"
                    f"📧 {email_u}"
                )

            with c2:
                st.caption(f"Plan: **{plan_u.capitalize()}**")
                st.caption(f"Docs generados: {docs}")

            with c3:
                # Selector de plan
                nuevo_plan = st.selectbox(
                    "Plan",
                    options=["gratuito", "basico", "pro", "empresarial"],
                    index=["gratuito", "basico", "pro", "empresarial"].index(plan_u)
                            if plan_u in ["gratuito", "basico", "pro", "empresarial"]
                            else 0,
                    key=f"plan_{email_u}",
                    label_visibility="collapsed",
                )
                if nuevo_plan != plan_u:
                    if usuario_cambiar_plan(email_u, nuevo_plan):
                        st.success(f"Plan actualizado a {nuevo_plan}")
                        st.rerun()

            # Botones de acción
            cb1, cb2, cb3, cb4 = st.columns(4)
            with cb1:
                if activo_u:
                    if st.button("⏸️ Desactivar", key=f"desact_{email_u}",
                                  use_container_width=True):
                        if usuario_desactivar(email_u):
                            st.rerun()
                else:
                    if st.button("▶️ Activar", key=f"act_{email_u}",
                                  use_container_width=True, type="primary"):
                        if usuario_activar(email_u):
                            st.rerun()

            with cb4:
                if st.button("🗑️ Eliminar", key=f"del_{email_u}",
                              use_container_width=True):
                    if usuario_eliminar(email_u):
                        st.success(f"Usuario {email_u} eliminado")
                        st.rerun()

            st.divider()
