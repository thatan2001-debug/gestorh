"""
Gestión de empleados para RH Fácil.
Persiste en Supabase (tabla empleados) con fallback a JSON local.
Cada empresa tiene su propio repositorio de empleados.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.db import _db, supabase_ok

# ── Fallback JSON ─────────────────────────────────────────────────────────────
def _json_path(email: str) -> Path:
    p = Path("salidas") / f".empleados_{email.split('@')[0]}.json"
    p.parent.mkdir(exist_ok=True)
    return p

def _json_load(email: str) -> list:
    p = _json_path(email)
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _json_save(email: str, empleados: list):
    with open(_json_path(email), "w") as f:
        json.dump(empleados, f, indent=2, ensure_ascii=False, default=str)

# ── CRUD principal ─────────────────────────────────────────────────────────────

def empleados_listar(email: str) -> list[dict]:
    """Retorna todos los empleados activos e inactivos de la empresa."""
    email = email.strip().lower()
    if supabase_ok():
        try:
            r = _db().table("empleados") \
                .select("*") \
                .eq("email_empresa", email) \
                .order("nombre") \
                .execute()
            return r.data or []
        except Exception as e:
            print(f"Error listando empleados: {e}")
    return _json_load(email)


def empleados_buscar(email: str, query: str) -> list[dict]:
    """Busca por nombre o documento (parcial, insensible a mayúsculas)."""
    query = query.strip().lower()
    if not query:
        return empleados_listar(email)
    todos = empleados_listar(email)
    return [
        e for e in todos
        if query in str(e.get("nombre","")).lower()
        or query in str(e.get("documento","")).lower()
    ]


def empleado_guardar(email: str, empleado: dict) -> tuple[bool, str]:
    """
    Crea o actualiza un empleado.
    Si tiene 'id', actualiza. Si no, crea nuevo.
    Retorna (ok, mensaje).
    """
    email = email.strip().lower()
    ahora = datetime.now().isoformat()

    payload = {
        "email_empresa":    email,
        "documento":        str(empleado.get("documento","")).strip(),
        "nombre":           str(empleado.get("nombre","")).strip(),
        "cargo":            str(empleado.get("cargo","")).strip(),
        "salario":          float(empleado.get("salario", 0) or 0),
        "fecha_ingreso":    str(empleado.get("fecha_ingreso","")).strip(),
        "fecha_retiro":     str(empleado.get("fecha_retiro","")).strip() or None,
        "tipo_contrato":    str(empleado.get("tipo_contrato","Indefinido")).strip(),
        "correo":           str(empleado.get("correo","")).strip(),
        "cuenta_bancaria":  str(empleado.get("cuenta_bancaria","")).strip(),
        "activo":           bool(empleado.get("activo", True)),
        "updated_at":       ahora,
    }

    if not payload["documento"]:
        return False, "El documento es obligatorio."
    if not payload["nombre"]:
        return False, "El nombre es obligatorio."

    if supabase_ok():
        try:
            # Verificar si ya existe por documento+empresa
            existe = _db().table("empleados") \
                .select("id") \
                .eq("email_empresa", email) \
                .eq("documento", payload["documento"]) \
                .execute()
            if existe.data:
                _db().table("empleados") \
                    .update(payload) \
                    .eq("email_empresa", email) \
                    .eq("documento", payload["documento"]) \
                    .execute()
                return True, f"Empleado {payload['nombre']} actualizado."
            else:
                payload["created_at"] = ahora
                _db().table("empleados").insert(payload).execute()
                return True, f"Empleado {payload['nombre']} agregado."
        except Exception as e:
            return False, f"Error guardando empleado: {e}"
    else:
        # Fallback JSON
        lista = _json_load(email)
        for i, emp in enumerate(lista):
            if str(emp.get("documento","")) == payload["documento"]:
                lista[i] = {**emp, **payload}
                _json_save(email, lista)
                return True, f"Empleado {payload['nombre']} actualizado."
        payload["created_at"] = ahora
        lista.append(payload)
        _json_save(email, lista)
        return True, f"Empleado {payload['nombre']} agregado."


def empleado_retirar(email: str, documento: str, fecha_retiro: str) -> tuple[bool, str]:
    """Marca un empleado como inactivo y registra su fecha de retiro."""
    email = email.strip().lower()
    if supabase_ok():
        try:
            _db().table("empleados") \
                .update({"activo": False, "fecha_retiro": fecha_retiro,
                         "updated_at": datetime.now().isoformat()}) \
                .eq("email_empresa", email) \
                .eq("documento", documento) \
                .execute()
            return True, "Empleado marcado como retirado."
        except Exception as e:
            return False, f"Error: {e}"
    else:
        lista = _json_load(email)
        for emp in lista:
            if str(emp.get("documento","")) == documento:
                emp["activo"] = False
                emp["fecha_retiro"] = fecha_retiro
        _json_save(email, lista)
        return True, "Empleado marcado como retirado."


def empleado_eliminar(email: str, documento: str) -> tuple[bool, str]:
    """Elimina permanentemente un empleado."""
    email = email.strip().lower()
    if supabase_ok():
        try:
            _db().table("empleados") \
                .delete() \
                .eq("email_empresa", email) \
                .eq("documento", documento) \
                .execute()
            return True, "Empleado eliminado."
        except Exception as e:
            return False, f"Error: {e}"
    else:
        lista = _json_load(email)
        nueva = [e for e in lista if str(e.get("documento","")) != documento]
        _json_save(email, nueva)
        return True, "Empleado eliminado."


def empleados_importar_excel(email: str, df: pd.DataFrame) -> tuple[int, int, list]:
    """
    Importa o actualiza empleados desde un DataFrame.
    Retorna (nuevos, actualizados, errores).
    """
    nuevos = actualizados = 0
    errores = []
    for _, fila in df.iterrows():
        emp = {
            "documento":       str(fila.get("Documento","")).strip(),
            "nombre":          str(fila.get("Nombre","")).strip(),
            "cargo":           str(fila.get("Cargo","")).strip(),
            "salario":         fila.get("Salario", 0),
            "fecha_ingreso":   str(fila.get("Fecha ingreso","")).strip(),
            "fecha_retiro":    str(fila.get("Fecha retiro","")).strip(),
            "tipo_contrato":   str(fila.get("Tipo contrato","Indefinido")).strip(),
            "correo":          str(fila.get("Correo","")).strip(),
            "cuenta_bancaria": str(fila.get("Cuenta bancaria","")).strip(),
            "activo":          True,
        }
        if not emp["documento"] or not emp["nombre"]:
            errores.append(f"Fila sin documento o nombre: {emp}")
            continue

        # ¿Ya existe?
        existentes = empleados_buscar(email, emp["documento"])
        ya_existe = any(str(e.get("documento","")) == emp["documento"]
                       for e in existentes)
        ok, msg = empleado_guardar(email, emp)
        if ok:
            if ya_existe: actualizados += 1
            else: nuevos += 1
        else:
            errores.append(f"{emp['nombre']}: {msg}")

    return nuevos, actualizados, errores


def empleados_stats(email: str) -> dict:
    """Estadísticas rápidas de la base de empleados."""
    todos = empleados_listar(email)
    activos   = [e for e in todos if e.get("activo", True)]
    inactivos = [e for e in todos if not e.get("activo", True)]
    return {
        "total":    len(todos),
        "activos":  len(activos),
        "retirados": len(inactivos),
    }
