-- ================================================================
-- RH Fácil — Schema Supabase
-- Ejecutar en: Supabase → SQL Editor → New Query
-- ================================================================

-- ── Tabla usuarios ───────────────────────────────────────────────
create table if not exists usuarios (
  email               text primary key,
  nombre              text not null,
  password_hash       text not null,
  plan                text default 'gratuito',
  documentos_usados   int  default 0,
  activo              boolean default false,
  es_admin            boolean default false,
  es_demo             boolean default false,
  empresa_nombre      text default '',
  telefono            text default '',
  fecha_registro      timestamptz default now(),
  fecha_activacion    timestamptz
);

-- ── Tabla empresas ───────────────────────────────────────────────
create table if not exists empresas (
  email                   text primary key references usuarios(email) on delete cascade,
  -- Datos básicos
  nombre                  text,
  nit                     text,
  ciudad                  text,
  direccion               text,
  telefono_empresa        text,
  correo_empresa          text,
  sector                  text,
  num_empleados           text,
  -- Representantes y firmantes
  representante           text,
  firmante_cert_nombre    text,
  firmante_cert_cargo     text,
  firmante_vac_nombre     text,
  firmante_vac_cargo      text,
  firmante_liq_nombre     text,
  firmante_liq_cargo      text,
  -- Diseño y logo
  logo_nombre             text,
  membrete_nombre         text,
  usar_logo_encabezado    boolean default true,
  usar_marca_agua         boolean default false,
  disenio_seleccionado    int default 1,
  -- Onboarding completado
  onboarding_completo     boolean default false,
  updated_at              timestamptz default now()
);

-- ── Tabla log de documentos ──────────────────────────────────────
create table if not exists documentos_log (
  id              uuid primary key default gen_random_uuid(),
  email           text references usuarios(email) on delete cascade,
  tipo_documento  text,   -- 'certificado', 'vacaciones', 'liquidacion'
  cantidad        int default 1,
  empleado_nombre text,
  generado_en     timestamptz default now()
);

-- ── Usuarios iniciales ───────────────────────────────────────────
insert into usuarios (email, nombre, password_hash, plan, activo, es_admin, es_demo)
values
  ('demo@rhfacil.co',  'Usuario Demo',   '3f5c2e77e3f42c44f2a53f2b27e91b0c3e88e4e6d9c76d37cf2f7b57a44e8ab9', 'pro',          true, false, true),
  ('admin@rhfacil.co', 'Administrador',  'b2d4a1f8c3e5g7h9j0k2l4m6n8p0q2r4s6t8u0v2w4x6y8z0a1b3c5d7e9f0g2', 'empresarial',  true, true,  false)
on conflict (email) do nothing;

-- ── RLS (Row Level Security) — básico para producción ────────────
alter table usuarios       enable row level security;
alter table empresas       enable row level security;
alter table documentos_log enable row level security;

-- Política: la anon key solo puede leer/escribir con service_role
-- (para producción real, configurar políticas más granulares)
create policy "service_role_all" on usuarios       for all using (true);
create policy "service_role_all" on empresas       for all using (true);
create policy "service_role_all" on documentos_log for all using (true);
