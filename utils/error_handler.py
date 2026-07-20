"""
Decoradores para envolver funciones con manejo de errores amigable.

Uso:
    from utils.error_handler import con_manejo_errores

    @con_manejo_errores("Error al guardar empleado")
    def guardar_empleado(...):
        ...

Si la función falla, se registra en logs y se muestra un mensaje
amigable al usuario en vez de un traceback técnico.
"""

import functools
import streamlit as st
from utils.logs import log_error


def con_manejo_errores(mensaje_usuario: str = "Ocurrió un error inesperado"):
    """
    Decorador que atrapa excepciones, las registra en logs y muestra
    un mensaje amigable al usuario.

    Parámetros:
        mensaje_usuario: qué ve el usuario si algo falla
                         (el traceback técnico va al log)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Registrar en logs
                log_error(f"funcion.{func.__name__}.fallo",
                    error=str(e),
                    args=str(args)[:200],
                    kwargs={k: str(v)[:100] for k, v in kwargs.items()},
                )
                # Mensaje amigable al usuario
                st.error(f"❌ {mensaje_usuario}")
                with st.expander("Detalles técnicos"):
                    st.code(f"{type(e).__name__}: {e}")
                    st.caption("Este error quedó registrado. Si persiste, "
                                "notifícalo al administrador.")
                return None
        return wrapper
    return decorator


def validar_o_error(condicion: bool, mensaje: str):
    """
    Muestra un error rojo y detiene el flujo si la condición NO se cumple.

    Uso:
        validar_o_error(salario > 0, "El salario debe ser mayor a 0")
    """
    if not condicion:
        st.error(f"❌ {mensaje}")
        log_error("validacion.fallo", mensaje=mensaje)
        st.stop()


def try_o_default(func, default=None, evento_log: str = "operacion.fallo"):
    """
    Ejecuta una función y retorna default si falla.
    No muestra nada al usuario, solo registra en logs.

    Útil para operaciones opcionales que no deben interrumpir el flujo.
    """
    try:
        return func()
    except Exception as e:
        log_error(evento_log, error=str(e))
        return default
