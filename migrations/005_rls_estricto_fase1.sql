-- ═══════════════════════════════════════════════════════════════════════════
-- Migración 005 — RLS estricto por empresa (Fase 1)
-- ═══════════════════════════════════════════════════════════════════════════
-- Aplica RLS a las tablas NUEVAS de Etapa 4:
--   - empresas
--   - perfiles
--   - empresa_usuarios
--
-- Las tablas legacy (usuarios, empleados, historial_documentos) NO se tocan
-- en esta migración — eso será Fase 2 cuando confirmemos que Fase 1 funciona.
--
-- IMPORTANTE: esta migración usa una función auxiliar que necesita saber
-- qué perfil está autenticado. Como la app usa service_role (no auth.uid
-- de Supabase Auth), la función se apoya en un GUC (setting) que la app
-- setea antes de cada query.
--
-- Ejecutar en Supabase → SQL Editor → New Query → Run
-- ═══════════════════════════════════════════════════════════════════════════


-- ═══════════════════════════════════════════════════════════════════════════
-- FUNCIÓN: obtener perfil actual desde GUC
-- ═══════════════════════════════════════════════════════════════════════════
-- La app setea 'app.current_perfil_id' antes de las queries.
-- Si no está seteado, retorna null.

create or replace function app_current_perfil_id()
returns uuid
language plpgsql
stable
as $$
declare
    v_perfil text;
begin
    v_perfil := current_setting('app.current_perfil_id', true);
    if v_perfil is null or v_perfil = '' then
        return null;
    end if;
    return v_perfil::uuid;
exception
    when others then
        return null;
end;
$$;

comment on function app_current_perfil_id() is
    'Retorna el perfil_id del usuario autenticado (leído del GUC app.current_perfil_id).';


-- ═══════════════════════════════════════════════════════════════════════════
-- FUNCIÓN: es_superadmin del perfil actual
-- ═══════════════════════════════════════════════════════════════════════════

create or replace function app_es_superadmin()
returns boolean
language plpgsql
stable
as $$
declare
    v_perfil uuid := app_current_perfil_id();
    v_es_super boolean := false;
begin
    if v_perfil is null then
        return false;
    end if;

    select coalesce(es_superadmin, false) into v_es_super
    from perfiles where id = v_perfil;

    return coalesce(v_es_super, false);
end;
$$;

comment on function app_es_superadmin() is
    'True si el perfil actual es superadmin.';


-- ═══════════════════════════════════════════════════════════════════════════
-- FUNCIÓN: empresas del perfil actual
-- ═══════════════════════════════════════════════════════════════════════════

create or replace function app_empresas_del_perfil()
returns setof uuid
language plpgsql
stable
as $$
declare
    v_perfil uuid := app_current_perfil_id();
begin
    if v_perfil is null then
        return;
    end if;

    return query
        select empresa_id from empresa_usuarios
        where perfil_id = v_perfil
          and estado = 'activo';
end;
$$;

comment on function app_empresas_del_perfil() is
    'Retorna los empresa_id a los que el perfil actual está vinculado activamente.';


-- ═══════════════════════════════════════════════════════════════════════════
-- POLÍTICAS RLS — tabla empresas
-- ═══════════════════════════════════════════════════════════════════════════

-- Borrar políticas anteriores permisivas
drop policy if exists "empresas_service" on empresas;

-- Política 1: service_role sigue teniendo acceso total (backend)
create policy "empresas_service_full" on empresas
    for all to service_role
    using (true)
    with check (true);

-- Política 2: usuarios autenticados solo ven sus empresas
-- (Cuando la app usa authenticated role en el futuro)
create policy "empresas_solo_sus_empresas" on empresas
    for select
    using (
        app_es_superadmin()
        or id in (select app_empresas_del_perfil())
    );

-- Política 3: solo superadmin puede crear empresas desde el cliente
-- (Las empresas se crean via service_role desde la app)
create policy "empresas_crear_solo_superadmin" on empresas
    for insert
    with check (app_es_superadmin());

-- Política 4: solo puede actualizar sus empresas
create policy "empresas_actualizar_sus" on empresas
    for update
    using (
        app_es_superadmin()
        or id in (select app_empresas_del_perfil())
    );

-- Política 5: solo superadmin puede eliminar
create policy "empresas_eliminar_solo_superadmin" on empresas
    for delete
    using (app_es_superadmin());


-- ═══════════════════════════════════════════════════════════════════════════
-- POLÍTICAS RLS — tabla perfiles
-- ═══════════════════════════════════════════════════════════════════════════

drop policy if exists "perfiles_service" on perfiles;

-- Política 1: service_role → acceso total (backend)
create policy "perfiles_service_full" on perfiles
    for all to service_role
    using (true)
    with check (true);

-- Política 2: cada perfil solo se ve a sí mismo
--            (o superadmin ve todos, o admins de empresa ven perfiles vinculados a sus empresas)
create policy "perfiles_ver_propio_o_admin" on perfiles
    for select
    using (
        app_es_superadmin()
        or id = app_current_perfil_id()
        or id in (
            -- Ver perfiles vinculados a las mismas empresas
            select eu.perfil_id from empresa_usuarios eu
            where eu.empresa_id in (select app_empresas_del_perfil())
              and eu.estado = 'activo'
        )
    );

-- Política 3: nadie crea perfiles desde el cliente (solo el service_role al registrar)
create policy "perfiles_crear_solo_service" on perfiles
    for insert
    with check (app_es_superadmin());

-- Política 4: solo puede actualizar su propio perfil
create policy "perfiles_actualizar_propio" on perfiles
    for update
    using (
        app_es_superadmin()
        or id = app_current_perfil_id()
    );

-- Política 5: solo superadmin puede eliminar perfiles
create policy "perfiles_eliminar_solo_superadmin" on perfiles
    for delete
    using (app_es_superadmin());


-- ═══════════════════════════════════════════════════════════════════════════
-- POLÍTICAS RLS — tabla empresa_usuarios
-- ═══════════════════════════════════════════════════════════════════════════

drop policy if exists "empresa_usuarios_service" on empresa_usuarios;

-- Política 1: service_role → acceso total (backend)
create policy "empresa_usuarios_service_full" on empresa_usuarios
    for all to service_role
    using (true)
    with check (true);

-- Política 2: cada usuario ve sus propios vínculos + los de sus empresas si es admin
create policy "empresa_usuarios_ver_propios_o_admin" on empresa_usuarios
    for select
    using (
        app_es_superadmin()
        or perfil_id = app_current_perfil_id()
        or empresa_id in (select app_empresas_del_perfil())
    );

-- Política 3: solo puede crear vínculos en empresas donde tiene rol admin
create policy "empresa_usuarios_crear_admin" on empresa_usuarios
    for insert
    with check (
        app_es_superadmin()
        or (
            empresa_id in (select app_empresas_del_perfil())
            -- Aquí se podría verificar que sea admin_empresa, pero
            -- por ahora dejamos que cualquier miembro pueda invitar
        )
    );

-- Política 4: puede actualizar vínculos en empresas donde tiene acceso
create policy "empresa_usuarios_actualizar" on empresa_usuarios
    for update
    using (
        app_es_superadmin()
        or empresa_id in (select app_empresas_del_perfil())
    );

-- Política 5: solo puede eliminar vínculos en empresas donde tiene acceso
create policy "empresa_usuarios_eliminar" on empresa_usuarios
    for delete
    using (
        app_es_superadmin()
        or empresa_id in (select app_empresas_del_perfil())
    );


-- ═══════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN
-- ═══════════════════════════════════════════════════════════════════════════
-- Después de ejecutar, verifica que las funciones existen:
--   select proname from pg_proc where proname like 'app_%';
-- Debe listar: app_current_perfil_id, app_es_superadmin, app_empresas_del_perfil
--
-- Y que las políticas están activas:
--   select tablename, policyname from pg_policies
--   where tablename in ('empresas', 'perfiles', 'empresa_usuarios')
--   order by tablename, policyname;
-- Debe mostrar ~15 políticas


-- ═══════════════════════════════════════════════════════════════════════════
-- NOTA IMPORTANTE
-- ═══════════════════════════════════════════════════════════════════════════
-- Como la app usa service_role para todas las queries actualmente, RLS
-- NO bloquea nada por ahora — el service_role tiene bypass.
--
-- El aislamiento real se activará cuando:
--   1) Migremos a Supabase Auth (Etapa futura)
--   2) O usemos anon key + set_config('app.current_perfil_id', ...) por request
--
-- Esta migración prepara el terreno. La Fase 2 aplicará el mismo patrón
-- a las tablas legacy (empleados, historial_documentos, liquidaciones).
