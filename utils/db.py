"""
Capa de datos con Supabase (PostgreSQL en la nube).
Funciona con fallback JSON si Supabase no está configurado.

SQL para crear tablas en Supabase → SQL Editor:
──────────────────────────────────────────────────
create table if not exists usuarios (
  email text primary key,
  nombre text not null,
  password_hash text not null,
  plan text default 'gratuito',
  activo boolean default false,
  activado_admin boolean default false,
  es_admin boolean default false,
  es_demo boolean default false,
  docs_usados int default 0,
  fecha_registro timestamptz default now(),
  empresa_config jsonb
);

create table if not exists empresas (
  id uuid primary key default gen_random_uuid(),
  email_usuario text references usuarios(email) on delete cascade,
  nombre text, nit text, representante text, correo_empresa text,
  logo_nombre text,
  firmante_cert_nombre text, firmante_cert_cargo text,
  firmante_vac_nombre text,  firmante_vac_cargo text,
  firmante_liq_nombre text,  firmante_liq_cargo text,
  usar_logo_enc boolean default true,
  usar_mda boolean default false,
  disenio int default 1,
  ciudad text, telefono text, sector text, num_empleados text,
  onboarding_ok boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists historial_docs (
  id uuid primary key default gen_random_uuid(),
  email_usuario text references usuarios(email) on delete cascade,
  tipo_doc text, cantidad int, empresa_nombre text,
  created_at timestamptz default now()
);

alter table usuarios disable row level security;
alter table empresas disable row level security;
alter table historial_docs disable row level security;
──────────────────────────────────────────────────
"""

import os, json, hashlib
from datetime import datetime
from pathlib import Path

_client = None

def _db():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise EnvironmentError("Faltan SUPABASE_URL y SUPABASE_KEY en variables de entorno.")
        from supabase import create_client
        _client = create_client(url, key)
    return _client

def supabase_ok() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))

# ── Fallback JSON ─────────────────────────────────────────────────────────────
_JP = Path("salidas/.usuarios.json")
_DEMO = {
    "demo@rhfacil.co": {
        "nombre":"Usuario Demo","plan":"pro","activo":True,
        "activado_admin":True,"es_demo":True,"es_admin":False,"docs_usados":0,
        "password_hash":hashlib.sha256(b"RHFacil2026").hexdigest(),"empresa_config":None,
    },
    "admin@rhfacil.co": {
        "nombre":"Administrador","plan":"empresarial","activo":True,
        "activado_admin":True,"es_demo":False,"es_admin":True,"docs_usados":0,
        "password_hash":hashlib.sha256(b"Admin2026*").hexdigest(),"empresa_config":None,
    },
}
def _jl():
    if _JP.exists():
        try:
            with open(_JP) as f: return json.load(f)
        except: pass
    _JP.parent.mkdir(exist_ok=True)
    with open(_JP,"w") as f: json.dump(_DEMO, f, indent=2)
    return _DEMO.copy()
def _js(d):
    _JP.parent.mkdir(exist_ok=True)
    with open(_JP,"w") as f: json.dump(d, f, indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════════════════════════
def usuario_obtener(email):
    email = email.strip().lower()
    if supabase_ok():
        r = _db().table("usuarios").select("*").eq("email",email).execute()
        return r.data[0] if r.data else None
    return _jl().get(email)

def usuario_existe(email): return usuario_obtener(email) is not None

def usuario_crear(email, nombre, pw_hash, plan="gratuito"):
    email = email.strip().lower()
    if supabase_ok():
        try:
            _db().table("usuarios").insert({
                "email":email,"nombre":nombre,"password_hash":pw_hash,
                "plan":plan,"activo":False,"activado_admin":False,
                "es_admin":False,"es_demo":False,"docs_usados":0,
            }).execute()
            return True
        except Exception as e:
            print(f"Error creando usuario: {e}"); return False
    d = _jl()
    d[email] = {"nombre":nombre,"password_hash":pw_hash,"plan":plan,
                "activo":False,"activado_admin":False,"es_admin":False,
                "es_demo":False,"docs_usados":0,
                "fecha_registro":datetime.now().isoformat(),"empresa_config":None}
    _js(d); return True

def usuario_activar(email):
    if supabase_ok():
        _db().table("usuarios").update({"activo":True,"activado_admin":True}).eq("email",email).execute()
        return True
    d = _jl()
    if email in d: d[email].update({"activo":True,"activado_admin":True}); _js(d)
    return True

def usuario_desactivar(email):
    if supabase_ok():
        _db().table("usuarios").update({"activo":False}).eq("email",email).execute()
        return True
    d = _jl()
    if email in d: d[email]["activo"] = False; _js(d)
    return True

def usuario_cambiar_plan(email, plan):
    if supabase_ok():
        _db().table("usuarios").update({"plan":plan}).eq("email",email).execute()
        return True
    d = _jl()
    if email in d: d[email]["plan"] = plan; _js(d)
    return True

def usuario_sumar_docs(email, cantidad):
    if supabase_ok():
        u = usuario_obtener(email)
        nuevo = (u.get("docs_usados") or 0) + cantidad if u else cantidad
        _db().table("usuarios").update({"docs_usados":nuevo}).eq("email",email).execute()
    else:
        d = _jl()
        if email in d: d[email]["docs_usados"] = d[email].get("docs_usados",0)+cantidad; _js(d)

def usuario_eliminar(email):
    if supabase_ok():
        _db().table("usuarios").delete().eq("email",email).execute(); return True
    d = _jl()
    if email in d and not d[email].get("es_admin"): del d[email]; _js(d)
    return True

def usuarios_listar():
    if supabase_ok():
        r = _db().table("usuarios").select(
            "email,nombre,plan,activo,activado_admin,es_admin,es_demo,docs_usados,fecha_registro"
        ).eq("es_admin",False).order("fecha_registro",desc=True).execute()
        return r.data or []
    d = _jl()
    return [{"email":e,**{k:v for k,v in u.items() if k!="password_hash"}}
            for e,u in d.items() if not u.get("es_admin")]

# ══════════════════════════════════════════════════════════════════════════════
# EMPRESA
# ══════════════════════════════════════════════════════════════════════════════
def empresa_guardar(email, datos):
    email = email.strip().lower()
    p = {
        "email_usuario":        email,
        "nombre":               datos.get("nombre",""),
        "nit":                  datos.get("nit",""),
        "representante":        datos.get("representante",""),
        "correo_empresa":       datos.get("correo_empresa",""),
        "logo_nombre":          Path(datos["logo_path"]).name if datos.get("logo_path") else None,
        "firmante_cert_nombre": datos.get("firmante_cert_nombre",""),
        "firmante_cert_cargo":  datos.get("firmante_cert_cargo",""),
        "firmante_vac_nombre":  datos.get("firmante_vac_nombre",""),
        "firmante_vac_cargo":   datos.get("firmante_vac_cargo",""),
        "firmante_liq_nombre":  datos.get("firmante_liq_nombre",""),
        "firmante_liq_cargo":   datos.get("firmante_liq_cargo",""),
        "usar_logo_enc":        datos.get("usar_logo_encabezado",True),
        "usar_mda":             datos.get("usar_marca_agua",False),
        "disenio":              datos.get("disenio_seleccionado",1),
        "ciudad":               datos.get("ciudad",""),
        "telefono":             datos.get("telefono",""),
        "sector":               datos.get("sector",""),
        "num_empleados":        datos.get("num_empleados",""),
        "onboarding_ok":        datos.get("onboarding_ok",False),
        "updated_at":           datetime.now().isoformat(),
    }
    if supabase_ok():
        ex = _db().table("empresas").select("id").eq("email_usuario",email).execute()
        if ex.data: _db().table("empresas").update(p).eq("email_usuario",email).execute()
        else:       _db().table("empresas").insert(p).execute()
        return True
    d = _jl()
    if email in d: d[email]["empresa_config"] = p; _js(d)
    return True

def empresa_cargar(email):
    email = email.strip().lower()
    if supabase_ok():
        r = _db().table("empresas").select("*").eq("email_usuario",email).execute()
        if not r.data: return None
        row = r.data[0]
        ln = row.get("logo_nombre")
        lp = str(Path("assets")/ln) if ln and (Path("assets")/ln).exists() else None
        return {
            "nombre":               row.get("nombre",""),
            "nit":                  row.get("nit",""),
            "representante":        row.get("representante",""),
            "correo_empresa":       row.get("correo_empresa",""),
            "logo_path":            lp,
            "firmante_cert_nombre": row.get("firmante_cert_nombre",""),
            "firmante_cert_cargo":  row.get("firmante_cert_cargo",""),
            "firmante_vac_nombre":  row.get("firmante_vac_nombre",""),
            "firmante_vac_cargo":   row.get("firmante_vac_cargo",""),
            "firmante_liq_nombre":  row.get("firmante_liq_nombre",""),
            "firmante_liq_cargo":   row.get("firmante_liq_cargo",""),
            "usar_logo_encabezado": row.get("usar_logo_enc",True),
            "usar_marca_agua":      row.get("usar_mda",False),
            "disenio_seleccionado": row.get("disenio",1),
            "ciudad":               row.get("ciudad",""),
            "telefono":             row.get("telefono",""),
            "sector":               row.get("sector",""),
            "num_empleados":        row.get("num_empleados",""),
            "onboarding_ok":        row.get("onboarding_ok",False),
        }
    d = _jl()
    cfg = d.get(email,{}).get("empresa_config")
    if not cfg: return None
    ln = cfg.get("logo_nombre")
    if ln:
        ruta = Path("assets")/ln
        cfg["logo_path"] = str(ruta) if ruta.exists() else None
    return cfg

def empresa_onboarding_ok(email):
    emp = empresa_cargar(email)
    return bool(emp and emp.get("onboarding_ok") and emp.get("nombre") and emp.get("nit"))

# ══════════════════════════════════════════════════════════════════════════════
# HISTORIAL
# ══════════════════════════════════════════════════════════════════════════════
def historial_registrar(email, tipo_doc, cantidad, empresa_nombre):
    if supabase_ok():
        try:
            _db().table("historial_docs").insert({
                "email_usuario":email,"tipo_doc":tipo_doc,
                "cantidad":cantidad,"empresa_nombre":empresa_nombre,
            }).execute()
        except Exception as e: print(f"Error historial: {e}")

def historial_obtener(email, limite=20):
    if supabase_ok():
        r = _db().table("historial_docs").select("*").eq(
            "email_usuario",email).order("created_at",desc=True).limit(limite).execute()
        return r.data or []
    return []

def stats_admin():
    from utils.plan_control import PLANES
    us = usuarios_listar()
    return {
        "total":      len(us),
        "activos":    sum(1 for u in us if u.get("activo")),
        "pendientes": sum(1 for u in us if not u.get("activado_admin")),
        "total_docs": sum(u.get("docs_usados",0) for u in us),
        "por_plan":   {p: sum(1 for u in us if u.get("plan")==p) for p in PLANES},
    }
