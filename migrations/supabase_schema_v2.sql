-- ================================================================
-- RH Fácil — Schema Supabase v2 (COMPLETO con RLS y historial)
-- 
-- INSTRUCCIONES:
-- 1. Ve a supabase.com → tu proyecto → SQL Editor → New Query
-- 2. Pega TODO este contenido y haz clic en "Run"
-- 3. Verifica en Table Editor que se crearon todas las tablas
--
-- Script idempotente: se puede correr varias veces sin duplicar datos
-- ================================================================

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ================================================================
-- TABLA: usuarios
-- ================================================================
create table if not exists usuarios (
  email                 text primary key,
  nombre                text not null,
  password_hash         text not null,
  plan                  text default 'gratuito'
                        check (plan in ('gratuito','basico','pro','empresarial')),
  documentos_usados     int default 0,
  documentos_mes        int default 0,
  mes_actual            text default '',
  activo                boolean default false,
  es_admin              boolean default false,
  es_demo               boolean default false,
  empresa_nombre        text default '',
  telefono              text default '',
  fecha_registro        timestamptz default now(),
  fecha_activacion      timestamptz,
  ultimo_login          timestamptz,
  created_at            timestamptz default now(),
  updated_at            timestamptz default now()
);

create index if not exists idx_usuarios_activo on usuarios(activo);
create index if not exists idx_usuarios_plan   on usuarios(plan);

-- ================================================================
-- TABLA: empresas
-- ================================================================
create table if not exists empresas (
  id                      uuid primary key default gen_random_uuid(),
  email                   text unique not null references usuarios(email) on delete cascade,
  nombre                  text,
  nit                     text,
  ciudad                  text,
  direccion               text,
  telefono_empresa        text,
  correo_empresa          text,
  sector                  text,
  num_empleados           text,
  representante           text,
  firmante_cert_nombre    text,
  firmante_cert_cargo     text default 'Representante Legal',
  firmante_vac_nombre     text,
  firmante_vac_cargo      text default 'Representante Legal',
  firmante_liq_nombre     text,
  firmante_liq_cargo      text default 'Representante Legal',
  logo_nombre             text,
  membrete_nombre         text,
  usar_logo_encabezado    boolean default true,
  usar_marca_agua         boolean default false,
  disenio_seleccionado    int default 1,
  onboarding_completo     boolean default false,
  created_at              timestamptz default now(),
  updated_at              timestamptz default now()
);

create index if not exists idx_empresas_email on empresas(email);

-- ================================================================
-- TABLA: empleados
-- ================================================================
create table if not exists empleados (
  id                          uuid primary key default gen_random_uuid(),
  email_empresa               text not null references usuarios(email) on delete cascade,
  documento                   text not null,
  nombre                      text not null,
  cargo                       text,
  tipo_contrato               text default 'Indefinido',
  salario                     numeric(14,2) default 0,
  tipo_salario                text default 'fijo',
  salario_variable            numeric(14,2) default 0,
  ingreso_promedio_variable   numeric(14,2) default 0,
  fecha_ingreso               text,
  fecha_retiro                text,
  fecha_vencimiento_contrato  text,
  correo                      text,
  telefono                    text,
  cuenta_bancaria             text,
  entidad_bancaria            text,
  tipo_cuenta                 text,
  eps                         text,
  pension                     text,
  arl                         text,
  activo                      boolean default true,
  created_at                  timestamptz default now(),
  updated_at                  timestamptz default now(),
  unique (email_empresa, documento)
);

create index if not exists idx_empleados_empresa   on empleados(email_empresa);
create index if not exists idx_empleados_documento on empleados(documento);
create index if not exists idx_empleados_activo    on empleados(activo);
create index if not exists idx_empleados_nombre    on empleados(lower(nombre));

-- Agregar columnas nuevas si ya existe la tabla (para actualizaciones)
alter table empleados add column if not exists tipo_salario text default 'fijo';
alter table empleados add column if not exists salario_variable numeric(14,2) default 0;
alter table empleados add column if not exists ingreso_promedio_variable numeric(14,2) default 0;
alter table empleados add column if not exists fecha_vencimiento_contrato text;
alter table empleados add column if not exists entidad_bancaria text;
alter table empleados add column if not exists tipo_cuenta text;
alter table empleados add column if not exists eps text;
alter table empleados add column if not exists pension text;
alter table empleados add column if not exists arl text;

-- ================================================================
-- TABLA: historial_documentos
-- ================================================================
create table if not exists historial_documentos (
  id                  uuid primary key default gen_random_uuid(),
  email_usuario       text not null references usuarios(email) on delete cascade,
  email_empresa       text not null,
  nombre_empresa      text,
  empleado_documento  text,
  empleado_nombre     text,
  tipo_documento      text not null,
  nombre_documento    text,
  subtipo             text,
  estado              text default 'generado'
                      check (estado in ('generado','enviado','firmado','anulado')),
  nombre_archivo      text,
  observaciones       text,
  datos_extra         jsonb,
  enviado_correo      boolean default false,
  correo_destino      text,
  fecha_envio         timestamptz,
  generado_en         timestamptz default now(),
  created_at          timestamptz default now()
);

create index if not exists idx_hist_usuario  on historial_documentos(email_usuario);
create index if not exists idx_hist_empresa  on historial_documentos(email_empresa);
create index if not exists idx_hist_empleado on historial_documentos(empleado_documento);
create index if not exists idx_hist_tipo     on historial_documentos(tipo_documento);
create index if not exists idx_hist_fecha    on historial_documentos(generado_en desc);

-- ================================================================
-- TABLA: parametros_legales
-- ================================================================
create table if not exists parametros_legales (
  id          uuid primary key default gen_random_uuid(),
  anio        int not null,
  codigo      text not null,
  nombre      text not null,
  valor       numeric(14,2) not null,
  descripcion text,
  fuente      text,
  activo      boolean default true,
  created_at  timestamptz default now(),
  unique (anio, codigo)
);

insert into parametros_legales (anio, codigo, nombre, valor, fuente) values
  (2026,'SMMLV',           'Salario Mínimo Mensual',           1750905, 'Decreto 159/2026'),
  (2026,'AUX_TRANSPORTE',  'Auxilio de Transporte',             249095, 'Decreto 1470/2025'),
  (2026,'TOPE_AUX_TRANSP', 'Tope auxilio (2 SMMLV)',           3501810, 'Decreto 1470/2025'),
  (2026,'CESANTIAS_PCT',   'Cesantías %',                         8.33, 'Art. 249 CST'),
  (2026,'INT_CESANTIAS',   'Intereses cesantías %',              12.00, 'Ley 52/1975'),
  (2026,'PRIMA_PCT',       'Prima servicios %',                   8.33, 'Art. 306 CST'),
  (2026,'VACACIONES_PCT',  'Vacaciones %',                        4.17, 'Art. 186 CST'),
  (2026,'EPS_EMPLEADO',    'Aporte EPS empleado %',               4.00, 'Ley 100/1993'),
  (2026,'PENSION_EMPLEADO','Aporte Pensión empleado %',           4.00, 'Ley 100/1993')
on conflict (anio, codigo) do update set
  valor = excluded.valor, fuente = excluded.fuente;

-- ================================================================
-- TABLA: plantillas_personalizadas
-- ================================================================
create table if not exists plantillas_personalizadas (
  id              uuid primary key default gen_random_uuid(),
  email_empresa   text not null references usuarios(email) on delete cascade,
  nombre          text not null,
  tipo_documento  text not null,
  descripcion     text,
  nombre_archivo  text,
  activa          boolean default true,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ================================================================
-- TRIGGERS: updated_at automático
-- ================================================================
create or replace function fn_set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

do $$ declare t text; begin
  foreach t in array array[
    'usuarios','empresas','empleados','plantillas_personalizadas'
  ] loop
    execute format('
      drop trigger if exists trg_%I_updated_at on %I;
      create trigger trg_%I_updated_at before update on %I
      for each row execute function fn_set_updated_at();
    ', t, t, t, t);
  end loop;
end; $$;

-- ================================================================
-- ROW LEVEL SECURITY
-- ================================================================
alter table usuarios                  enable row level security;
alter table empresas                  enable row level security;
alter table empleados                 enable row level security;
alter table historial_documentos      enable row level security;
alter table parametros_legales        enable row level security;
alter table plantillas_personalizadas enable row level security;

-- service_role (backend Python) tiene acceso total
-- Para anon key se aplican las siguientes políticas:

drop policy if exists "usuarios_service" on usuarios;
create policy "usuarios_service" on usuarios
  for all to service_role using (true) with check (true);

drop policy if exists "empresas_service" on empresas;
create policy "empresas_service" on empresas
  for all to service_role using (true) with check (true);

drop policy if exists "empleados_service" on empleados;
create policy "empleados_service" on empleados
  for all to service_role using (true) with check (true);

drop policy if exists "historial_service" on historial_documentos;
create policy "historial_service" on historial_documentos
  for all to service_role using (true) with check (true);

drop policy if exists "params_read" on parametros_legales;
create policy "params_read" on parametros_legales
  for select using (true);

drop policy if exists "plantillas_service" on plantillas_personalizadas;
create policy "plantillas_service" on plantillas_personalizadas
  for all to service_role using (true) with check (true);

-- ================================================================
-- USUARIOS INICIALES
-- ================================================================
insert into usuarios (email, nombre, password_hash, plan, activo, es_admin, es_demo)
values
  ('demo@rhfacil.co',
   'Usuario Demo',
   encode(digest('RHFacil2026', 'sha256'), 'hex'),
   'pro', true, false, true),
  ('admin@rhfacil.co',
   'Administrador RH Fácil',
   encode(digest('Admin2026*', 'sha256'), 'hex'),
   'empresarial', true, true, false)
on conflict (email) do nothing;

-- ================================================================
-- VISTAS
-- ================================================================
create or replace view v_usuarios_resumen as
select
  u.email, u.nombre, u.plan, u.activo,
  u.documentos_usados, u.documentos_mes,
  u.fecha_registro, u.ultimo_login,
  e.nombre as empresa_nombre, e.nit, e.ciudad,
  e.sector, e.num_empleados, e.onboarding_completo,
  (select count(*) from empleados emp
   where emp.email_empresa = u.email and emp.activo = true
  ) as empleados_activos,
  (select count(*) from historial_documentos h
   where h.email_usuario = u.email
     and h.generado_en >= date_trunc('month', now())
  ) as docs_este_mes
from usuarios u
left join empresas e on e.email = u.email
where u.es_admin = false;

-- ================================================================
-- FIN DEL SCHEMA v2
-- ================================================================
