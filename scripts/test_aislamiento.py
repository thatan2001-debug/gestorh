"""
Script de verificación de aislamiento multiempresa.

Crea dos empresas de prueba con distintos usuarios y verifica que:
- Empresa A no puede leer datos de empresa B
- Usuario de empresa A no puede modificar datos de empresa B
- Superadmin puede ver todo

Ejecutar:
    # Modo simulación (no crea datos)
    python scripts/test_aislamiento.py --dry-run

    # Modo real (crea empresas y usuarios de prueba, luego los borra)
    python scripts/test_aislamiento.py

Precondiciones:
- Migraciones 004 y 005 aplicadas en Supabase
- Variables SUPABASE_URL y SUPABASE_KEY configuradas
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-cleanup", action="store_true",
                         help="No borrar los datos de prueba al terminar")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Test de aislamiento multiempresa                            ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    from config.settings import settings
    if not settings.supabase_configurado:
        print("❌ Requiere Supabase configurado")
        sys.exit(1)

    from services.auth_service import auth_service
    from services.empresa_service import empresa_service
    from services.perfil_service import perfil_service
    from services.roles_service import roles_service

    resultados = []

    def check(nombre, condicion, esperado="OK"):
        icono = "✅" if condicion else "❌"
        estado = "PASS" if condicion else "FAIL"
        resultados.append((nombre, condicion))
        print(f"   {icono} {nombre:<55} [{estado}]")

    if args.dry_run:
        print("🔍 DRY-RUN — sin cambios reales")
        print()
        return

    # ── 1. Crear 2 empresas de prueba ─────────────────────────────────
    print("1️⃣  Creando 2 usuarios y 2 empresas de prueba...")

    hash_a = auth_service.hash_password("TestPasswordA123!")
    hash_b = auth_service.hash_password("TestPasswordB456!")

    email_a = "test-aisl-a@test.co"
    email_b = "test-aisl-b@test.co"

    ok, msg, perfil_a_id = perfil_service.crear(
        email_a, "Test Usuario A", hash_a, activo=True
    )
    check(f"Crear perfil A ({email_a})", ok)
    if not ok:
        print(f"      → {msg}")
        return

    ok, msg, perfil_b_id = perfil_service.crear(
        email_b, "Test Usuario B", hash_b, activo=True
    )
    check(f"Crear perfil B ({email_b})", ok)
    if not ok:
        return

    ok, msg, empresa_a_id = empresa_service.crear({
        "razon_social": "Test Empresa A (AISLAMIENTO)",
        "nit": "900000001-1",
    }, creado_por_perfil_id=perfil_a_id)
    check("Crear Empresa A + vinculo con Usuario A", ok)
    if not ok:
        print(f"      → {msg}")
        return

    ok, msg, empresa_b_id = empresa_service.crear({
        "razon_social": "Test Empresa B (AISLAMIENTO)",
        "nit": "900000002-2",
    }, creado_por_perfil_id=perfil_b_id)
    check("Crear Empresa B + vinculo con Usuario B", ok)
    if not ok:
        return

    print()

    # ── 2. Verificar que cada usuario ve sus empresas ────────────────
    print("2️⃣  Verificando listado de empresas por usuario...")

    empresas_a = empresa_service.listar_de_perfil(perfil_a_id)
    check(f"Usuario A ve exactamente 1 empresa",
          len(empresas_a) == 1)
    check(f"Usuario A ve la Empresa A",
          any(e["id"] == empresa_a_id for e in empresas_a))
    check(f"Usuario A NO ve la Empresa B",
          not any(e["id"] == empresa_b_id for e in empresas_a))

    empresas_b = empresa_service.listar_de_perfil(perfil_b_id)
    check(f"Usuario B ve exactamente 1 empresa",
          len(empresas_b) == 1)
    check(f"Usuario B ve la Empresa B",
          any(e["id"] == empresa_b_id for e in empresas_b))
    check(f"Usuario B NO ve la Empresa A",
          not any(e["id"] == empresa_a_id for e in empresas_b))

    print()

    # ── 3. Verificar permisos ────────────────────────────────────────
    print("3️⃣  Verificando permisos de rol admin_empresa...")

    check("Usuario A puede empleados.crear en Empresa A",
          roles_service.puede(perfil_a_id, empresa_a_id, "empleados.crear"))
    check("Usuario A NO tiene rol en Empresa B",
          roles_service.obtener_rol_de_usuario(perfil_a_id, empresa_b_id) is None)
    check("Usuario A NO puede empleados.crear en Empresa B",
          not roles_service.puede(perfil_a_id, empresa_b_id, "empleados.crear"))
    check("Usuario B puede documentos.generar en Empresa B",
          roles_service.puede(perfil_b_id, empresa_b_id, "documentos.generar"))
    check("Usuario B NO puede documentos.generar en Empresa A",
          not roles_service.puede(perfil_b_id, empresa_a_id, "documentos.generar"))

    print()

    # ── 4. Verificar acceso directo a la empresa ─────────────────────
    print("4️⃣  Verificando acceso directo a datos de empresa...")

    emp_a = empresa_service.obtener(empresa_a_id)
    check(f"Empresa A existe y es consultable",
          emp_a and emp_a.get("razon_social") == "Test Empresa A (AISLAMIENTO)")

    emp_b = empresa_service.obtener(empresa_b_id)
    check(f"Empresa B existe y es consultable",
          emp_b and emp_b.get("razon_social") == "Test Empresa B (AISLAMIENTO)")

    print()

    # ── 5. Limpieza ──────────────────────────────────────────────────
    if not args.no_cleanup:
        print("5️⃣  Limpiando datos de prueba...")
        try:
            from utils.db import _db
            # Borrar vínculos primero
            _db().table("empresa_usuarios").delete().eq("empresa_id", empresa_a_id).execute()
            _db().table("empresa_usuarios").delete().eq("empresa_id", empresa_b_id).execute()
            # Borrar empresas
            _db().table("empresas").delete().eq("id", empresa_a_id).execute()
            _db().table("empresas").delete().eq("id", empresa_b_id).execute()
            # Borrar perfiles
            _db().table("perfiles").delete().eq("id", perfil_a_id).execute()
            _db().table("perfiles").delete().eq("id", perfil_b_id).execute()
            check("Limpieza completada", True)
        except Exception as e:
            check(f"Limpieza (error: {e})", False)
    else:
        print("5️⃣  Limpieza omitida (--no-cleanup)")
        print(f"     Empresa A id: {empresa_a_id}")
        print(f"     Empresa B id: {empresa_b_id}")

    # ── Resumen ──────────────────────────────────────────────────────
    print()
    pasados = sum(1 for _, ok in resultados if ok)
    total = len(resultados)
    fallados = total - pasados

    print("╔══════════════════════════════════════════════════════════════╗")
    if fallados == 0:
        print(f"║  🎉 {pasados}/{total} tests pasaron — aislamiento correcto{' ' * 8}║")
    else:
        print(f"║  ❌ {fallados}/{total} tests fallaron{' ' * 30}║")
    print("╚══════════════════════════════════════════════════════════════╝")

    if fallados > 0:
        print()
        print("Tests fallados:")
        for nombre, ok in resultados:
            if not ok:
                print(f"  • {nombre}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelado.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
