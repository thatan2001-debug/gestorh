"""
Gestión de base de empleados por empresa.
- CRUD completo: crear, leer, actualizar, desactivar
- Búsqueda por nombre o documento
- Importación masiva desde Excel
- Persistencia en Supabase con fallback JSON
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.db import _db

def _json_path(email: str) -> Path:
    p = Path("salidas") / f"emp_{email.split('@')[0]}.json"
    p.parent.mkdir(exist_ok=True)
    return p

def _json_load(email: str) -> list:
    p = _json_path(email)
    if p.exists():
        try: return json.load(open(p, encoding="utf-8"))
        except: pass
    return []

def _json_save(email: str, emp: list):
    with open(_json_path(email), "w", encoding="utf-8") as f:
        json.dump(emp, f, indent=2, ensure_ascii=False, default=str)

def _usar_sb(): return _db() is not None

# ══════════════════════════════════════════════════════════════════════════════
# LISTADO Y BÚSQUEDA
# ══════════════════════════════════════════════════════════════════════════════

def empleados_listar(email: str, solo_activos: bool = True) -> list:
    sb = _db()
    if sb:
        try:
            q = sb.table("empleados").select("*").eq("email_empresa", email)
            if solo_activos: q = q.eq("activo", True)
            return (q.order("nombre").execute().data or [])
        except Exception as e:
            print(f"Supabase error: {e}")
    emp = _json_load(email)
    return [e for e in emp if e.get("activo", True)] if solo_activos else emp


def empleados_buscar(email: str, termino: str) -> list:
    termino = termino.strip().lower()
    if not termino: return empleados_listar(email)
    todos = empleados_listar(email, solo_activos=False)
    return [e for e in todos if
            termino in str(e.get("nombre","")).lower() or
            termino in str(e.get("documento","")).lower() or
            termino in str(e.get("cargo","")).lower()]


def empleado_obtener(email: str, documento: str) -> dict | None:
    sb = _db()
    if sb:
        try:
            r = sb.table("empleados").select("*")\
                .eq("email_empresa", email).eq("documento", documento)\
                .single().execute()
            return r.data
        except: pass
    return next((e for e in _json_load(email) if e.get("documento") == documento), None)

# ══════════════════════════════════════════════════════════════════════════════
# GUARDAR / ACTUALIZAR
# ══════════════════════════════════════════════════════════════════════════════

def empleado_guardar(email: str, datos: dict) -> tuple[bool, str]:
    doc    = str(datos.get("documento","")).strip()
    nombre = str(datos.get("nombre","")).strip()
    if not doc:    return False, "Documento obligatorio."
    if not nombre: return False, "Nombre obligatorio."

    payload = {
        "email_empresa":              email,
        "documento":                  doc,
        "nombre":                     nombre,
        "cargo":                      str(datos.get("cargo","")).strip(),
        "salario":                    float(datos.get("salario", 0) or 0),
        "fecha_ingreso":              str(datos.get("fecha_ingreso","")).strip(),
        "fecha_retiro":               str(datos.get("fecha_retiro","")).strip() or None,
        "tipo_contrato":              datos.get("tipo_contrato","Indefinido"),
        "correo":                     datos.get("correo",""),
        "cuenta_bancaria":            datos.get("cuenta_bancaria",""),
        "tipo_salario":               datos.get("tipo_salario","fijo"),
        "salario_variable":           float(datos.get("salario_variable", 0) or 0),
        "ingreso_promedio_variable":  float(datos.get("ingreso_promedio_variable", 0) or 0),
        "activo":                     datos.get("activo", True),
        "updated_at":                 datetime.now().isoformat(),
    }

    existe = empleado_obtener(email, doc) is not None
    sb = _db()
    if sb:
        try:
            sb.table("empleados").upsert(payload,
                on_conflict="email_empresa,documento").execute()
            accion = "actualizado" if existe else "creado"
            return True, f"Empleado {nombre} {accion}."
        except Exception as e:
            return False, f"Error: {e}"
    else:
        emp = _json_load(email)
        for i, e in enumerate(emp):
            if e.get("documento") == doc:
                emp[i] = payload
                _json_save(email, emp)
                return True, f"{nombre} actualizado."
        emp.append(payload)
        _json_save(email, emp)
        return True, f"{nombre} creado."


def empleado_desactivar(email: str, documento: str) -> tuple[bool, str]:
    sb = _db()
    if sb:
        try:
            sb.table("empleados").update({"activo": False})\
                .eq("email_empresa", email).eq("documento", documento).execute()
            return True, "Empleado marcado como retirado."
        except Exception as e:
            return False, str(e)
    emp = _json_load(email)
    for e in emp:
        if e.get("documento") == documento: e["activo"] = False
    _json_save(email, emp)
    return True, "Empleado marcado como retirado."


def empleado_eliminar(email: str, documento: str) -> tuple[bool, str]:
    sb = _db()
    if sb:
        try:
            sb.table("empleados").delete()\
                .eq("email_empresa", email).eq("documento", documento).execute()
            return True, "Eliminado."
        except Exception as e:
            return False, str(e)
    emp = [e for e in _json_load(email) if e.get("documento") != documento]
    _json_save(email, emp)
    return True, "Eliminado."

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTACIÓN DESDE EXCEL
# ══════════════════════════════════════════════════════════════════════════════

def importar_desde_excel(email: str, archivo) -> tuple[int, int, list]:
    try:
        df = pd.read_excel(archivo, dtype={"Documento": str})
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        return 0, 0, [f"No se pudo leer el Excel: {e}"]

    creados = actualizados = 0
    errores = []

    for idx, fila in df.iterrows():
        n = idx + 2
        doc    = str(fila.get("Documento","")).strip()
        nombre = str(fila.get("Nombre","")).strip()
        if not doc or doc.lower() == "nan":
            errores.append(f"Fila {n}: sin documento"); continue
        if not nombre or nombre.lower() == "nan":
            errores.append(f"Fila {n}: sin nombre"); continue

        existe = empleado_obtener(email, doc)
        ing_var = float(fila.get("Ingreso promedio variable", 0) or 0)

        datos = {
            "documento": doc, "nombre": nombre,
            "cargo":     str(fila.get("Cargo","")).strip(),
            "salario":   fila.get("Salario", 0),
            "fecha_ingreso": str(fila.get("Fecha ingreso","")).strip(),
            "fecha_retiro":  "" if pd.isna(fila.get("Fecha retiro","")) else
                             str(fila.get("Fecha retiro","")).strip(),
            "tipo_contrato": str(fila.get("Tipo contrato","Indefinido")).strip(),
            "correo":        str(fila.get("Correo","")).strip(),
            "cuenta_bancaria": str(fila.get("Cuenta bancaria","")).strip(),
            "ingreso_promedio_variable": ing_var,
            "tipo_salario": "variable" if ing_var > 0 else "fijo",
        }
        ok, msg = empleado_guardar(email, datos)
        if ok:
            if existe: actualizados += 1
            else: creados += 1
        else:
            errores.append(f"Fila {n} ({nombre}): {msg}")

    return creados, actualizados, errores


def empleados_stats(email: str) -> dict:
    todos     = empleados_listar(email, solo_activos=False)
    activos   = [e for e in todos if e.get("activo", True)]
    retirados = [e for e in todos if not e.get("activo", True)]
    return {
        "total": len(todos), "activos": len(activos),
        "retirados": len(retirados),
        "con_variable": sum(1 for e in activos
            if float(e.get("ingreso_promedio_variable", 0) or 0) > 0),
    }
