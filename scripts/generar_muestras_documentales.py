"""Genera los cuatro PDFs de aceptación y sus datos de prueba reproducibles."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.calcular_liquidacion import calcular_liquidacion_fila
from utils.documentos_premium import (
    generar_certificado_premium,
    generar_contrato_indefinido_premium,
    generar_dotacion_premium,
    generar_liquidacion_premium,
)


def main(salida: str | Path | None = None) -> list[Path]:
    out = Path(salida or ROOT / "artifacts" / "documentos_finales")
    out.mkdir(parents=True, exist_ok=True)
    empresa = {
        "nombre": "Soluciones Empresariales del Caribe S.A.S.",
        "nit": "901.456.789-3",
        "ciudad": "Medellín",
        "direccion": "Carrera 43A No. 18 Sur - 135, Oficina 804",
        "telefono": "+57 604 444 8899",
        "correo_empresa": "gestionhumana@solucionescaribe.com.co",
        "representante": "Laura Marcela Fernández Rodríguez",
        "_cargo_firmante": "Representante Legal",
        "logo_path": str(ROOT / "assets" / "logo_gestorrh.png"),
    }
    empleado = {
        "Nombre": "Marco Alejandro Álvarez Ibarra",
        "Documento": "1.045.678.912",
        "Tipo documento": "C.C.",
        "Cargo": "Coordinador de Operaciones y Experiencia del Cliente",
        "Área": "Operaciones",
        "Sede": "Medellín",
        "Centro de costos": "OP-ANT-001",
        "Salario": 3_250_000,
        "Fecha ingreso": "2025-02-03",
        "Tipo contrato": "Indefinido",
        "Cuenta bancaria": "Cuenta de ahorros terminada en 4182",
    }

    contrato = out / "CONTRATO_MARCO_ALVAREZ_2026-07-30_CONT-001.pdf"
    generar_contrato_indefinido_premium(
        empleado, empresa, str(contrato), {
            "fecha_inicio_contrato": date(2025, 2, 3),
            "fecha_inicio_precargada": True,
            "fecha_inicio_confirmada": True,
            "fecha_celebracion": date(2026, 7, 30),
            "lugar_trabajo": "Medellín, Antioquia",
            "modalidad_laboral": "Híbrida",
            "jornada": "Diurna",
            "horario": "lunes a viernes de 8:00 a.m. a 5:00 p.m.",
            "distribucion_semanal": "42 horas semanales",
            "dia_descanso": "domingo",
            "periodicidad_pago": "quincenal",
            "forma_pago": "transferencia bancaria",
            "dia_pago": "15 y último día de cada mes",
            "periodo_prueba": True,
            "funciones": [
                "Coordinar la operación diaria y el cumplimiento de los niveles de servicio.",
                "Preparar indicadores, reportes ejecutivos y planes de mejora.",
                "Acompañar al equipo, documentar novedades y escalar riesgos operativos.",
                "Custodiar la información y los activos asignados a su cargo.",
            ],
            "version_anexo_funciones": "1.1",
            "politica_datos": "Política de Tratamiento de Datos Personales versión 2026.1",
            "otros_pagos": "auxilio de conectividad sujeto a la modalidad y política vigente",
            "numero_documento": "CONT-2026-000045",
            "usuario_generador": "jhonathan.castano",
        }, usar_marca_agua=True,
    )

    certificado = out / "CERTIFICADO_MARCO_ALVAREZ_2026-07-30_CERT-001.pdf"
    generar_certificado_premium(
        empleado, empresa, str(certificado), incluir_salario=False,
        usar_marca_agua=True,
        config={
            "incluir_salario": False,
            "proposito": "ser presentado ante una entidad financiera",
            "dirigido_a": "A quien corresponda",
            "numero_documento": "CERT-2026-000045",
            "usuario_generador": "jhonathan.castano",
        },
    )

    dotacion = out / "ACTA_DOTACION_MARCO_ALVAREZ_2026-07-30_DOT-001.pdf"
    generar_dotacion_premium(
        empleado, empresa, str(dotacion), {
            "fecha_entrega": date(2026, 7, 30),
            "tipo_entrega": "uniforme_corporativo",
            "cumple_requisitos_dotacion": False,
            "lugar_entrega": "Sede Medellín",
            "periodo_entrega": "Segundo semestre de 2026",
            "responsable_entrega": "Catalina Restrepo Gómez — Analista de Gestión Humana",
            "items": [
                {"descripcion": "Camisa tipo polo bordada", "tipo": "Uniforme", "talla": "M", "color": "Azul oscuro", "referencia": "POLO-GH-2026", "cantidad": 3, "estado": "Nuevo", "observaciones": "Entrega completa"},
                {"descripcion": "Pantalón de dril corporativo", "tipo": "Uniforme", "talla": "32", "color": "Gris", "referencia": "DRIL-32-GR", "cantidad": 2, "estado": "Nuevo", "observaciones": "Sin novedad"},
                {"descripcion": "Chaqueta impermeable liviana", "tipo": "Uniforme", "talla": "M", "color": "Azul", "referencia": "CH-IMP-M", "cantidad": 1, "estado": "Nuevo", "observaciones": "Uso en visitas"},
            ],
            "observaciones": "Los elementos fueron verificados en presencia del trabajador.",
            "numero_documento": "DOT-2026-000045",
            "usuario_generador": "jhonathan.castano",
        }, usar_marca_agua=True,
    )

    fila = pd.Series({
        **empleado,
        "Fecha retiro": "2026-07-30",
        "Dias salario pendiente": 5,
        "Prima pagada": 0,
        "Cesantias consignadas": 0,
        "Vacaciones pagadas": 0,
        "Deducciones autorizadas": 125_000,
    })
    resultado = calcular_liquidacion_fila(
        fila, datetime(2026, 7, 30), motivo_retiro="renuncia"
    )
    resultado.update({
        "Cuenta bancaria": empleado["Cuenta bancaria"],
        "Pagos previos confirmados": True,
        "Novedades confirmadas": True,
    })
    liquidacion = out / "LIQUIDACION_MARCO_ALVAREZ_2026-07-30_LIQ-001.pdf"
    generar_liquidacion_premium(
        resultado, empresa, str(liquidacion), usar_marca_agua=True,
        config={
            "pagos_previos_confirmados": True,
            "novedades_confirmadas": True,
            "numero_documento": "LIQ-2026-000045",
            "usuario_generador": "jhonathan.castano",
        },
    )

    paths = [contrato, certificado, dotacion, liquidacion]
    manifest = {
        "generados": [p.name for p in paths],
        "fecha_prueba": "2026-07-30",
        "nota": "Datos ficticios para validación visual y automatizada.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


if __name__ == "__main__":
    for path in main():
        print(path)
