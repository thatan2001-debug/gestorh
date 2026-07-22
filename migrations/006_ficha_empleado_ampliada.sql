-- ═══════════════════════════════════════════════════════════════════════════
-- Migración 006 — Ampliar ficha de empleado
-- ═══════════════════════════════════════════════════════════════════════════
-- Agrega los campos faltantes a la ficha del empleado.
-- Todo es ADITIVO: no borra ni modifica columnas existentes.
--
-- Ejecutar en Supabase → SQL Editor → New Query → Run
-- ═══════════════════════════════════════════════════════════════════════════


-- ─── Datos personales adicionales ──────────────────────────────────────────
alter table empleados add column if not exists tipo_documento text default 'CC';
alter table empleados add column if not exists fecha_nacimiento text;
alter table empleados add column if not exists direccion text;
alter table empleados add column if not exists ciudad text;
alter table empleados add column if not exists correo_personal text;
alter table empleados add column if not exists estado_civil text;
alter table empleados add column if not exists genero text;

-- ─── Contacto de emergencia ────────────────────────────────────────────────
alter table empleados add column if not exists emergencia_nombre text;
alter table empleados add column if not exists emergencia_parentesco text;
alter table empleados add column if not exists emergencia_telefono text;

-- ─── Seguridad social ampliada ─────────────────────────────────────────────
alter table empleados add column if not exists caja_compensacion text;
alter table empleados add column if not exists fondo_cesantias text;

-- ─── Datos laborales adicionales ───────────────────────────────────────────
alter table empleados add column if not exists area text;
alter table empleados add column if not exists sede text;
alter table empleados add column if not exists jefe_inmediato text;
alter table empleados add column if not exists centro_costo text;
alter table empleados add column if not exists modalidad text default 'presencial'
    check (modalidad in ('presencial','remoto','hibrido'));
alter table empleados add column if not exists horario text;
alter table empleados add column if not exists jornada text default 'completa'
    check (jornada in ('completa','media','por_horas'));

-- ─── Auxilio de transporte (útil para liquidaciones) ────────────────────────
alter table empleados add column if not exists auxilio_transporte numeric(14,2) default 0;

-- ─── Metadata ──────────────────────────────────────────────────────────────
-- Vínculo con la nueva estructura multiempresa (opcional, la app llena esto
-- cuando el empleado se crea desde el flujo nuevo)
alter table empleados add column if not exists empresa_id uuid references empresas(id);


-- ─── Índices para búsquedas comunes ────────────────────────────────────────
create index if not exists idx_empleados_area on empleados(area);
create index if not exists idx_empleados_sede on empleados(sede);
create index if not exists idx_empleados_empresa_id on empleados(empresa_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN
-- ═══════════════════════════════════════════════════════════════════════════
-- Ejecuta después para confirmar:
-- select column_name, data_type from information_schema.columns
-- where table_name = 'empleados' order by ordinal_position;
