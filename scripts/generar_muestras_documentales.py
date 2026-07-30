"""Genera los cinco PDFs finales de aceptación con datos ficticios reproducibles."""
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


def _empresa() -> dict:
    return {
        "nombre": "JC Típico de la Costa S.A.S.",
        "nit": "901.456.789-3",
        "ciudad": "Medellín",
        "direccion": "Carrera 43A No. 18 Sur - 135, Oficina 804",
        "telefono": "+57 604 444 8899",
        "correo_empresa": "gestionhumana@jctipicodelacosta.com.co",
        "representante": "Laura Marcela Fernández Rodríguez",
        "_cargo_firmante": "Representante Legal",
        "logo_path": str(ROOT / "assets" / "logo_gestorrh.png"),
    }


def _empleado() -> dict:
    return {
        "Nombre": "Marco Alejandro Álvarez Ibarra",
        "Documento": "19.967.473",
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


def _resultado_liquidacion(empleado: dict, dias_pendientes: int, estado_aportes: str,
                           deducciones_autorizadas: float = 0) -> dict:
    fila = pd.Series({
        **empleado,
        "Fecha retiro": "2026-07-30",
        "Dias salario pendiente": dias_pendientes,
        "Estado aportes periodo final": estado_aportes,
        "Prima pagada": 0,
        "Cesantias consignadas": 0,
        "Vacaciones pagadas": 0,
        "Deducciones autorizadas": deducciones_autorizadas,
    })
    resultado = calcular_liquidacion_fila(fila, datetime(2026, 7, 30), motivo_retiro="renuncia")
    resultado.update({
        "Cuenta bancaria": empleado["Cuenta bancaria"],
        "Pagos previos confirmados": True,
        "Novedades confirmadas": True,
    })
    return resultado


def main(salida: str | Path | None = None) -> list[Path]:
    out = Path(salida or ROOT / "artifacts" / "documentos_finales")
    out.mkdir(parents=True, exist_ok=True)
    empresa = _empresa()
    empleado = _empleado()

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
            "periodo_prueba": False,
            "funciones": [
                "Coordinar la operación diaria y el cumplimiento de los niveles de servicio.",
                "Gestionar las solicitudes de las áreas y documentar las novedades operativas.",
                "Administrar el inventario del personal y preparar reportes ejecutivos.",
                "Elaborar los horarios del personal a cargo y acompañar los planes de mejora.",
            ],
            "otros_pagos": "auxilio de conectividad sujeto a la modalidad y a la política vigente",
            "numero_documento": "CONT-2026-000045",
            "usuario_generador": "jhonathan.castano",
            "estado_documento": "Aprobado",
        }, usar_marca_agua=False,
    )

    certificado = out / "CERTIFICADO_MARCO_ALVAREZ_2026-07-30_CERT-001.pdf"
    generar_certificado_premium(
        empleado, empresa, str(certificado), incluir_salario=True,
        usar_marca_agua=False,
        config={
            "incluir_salario": True,
            "proposito": "ser presentado ante una entidad financiera",
            "dirigido_a": "A quien corresponda",
            "fecha_emision": date(2026, 7, 30),
            "numero_documento": "CERT-2026-000045",
            "usuario_generador": "jhonathan.castano",
            "estado_documento": "Emitido",
        },
    )

    dotacion = out / "ACTA_DOTACION_MARCO_ALVAREZ_2026-07-30_DOT-001.pdf"
    generar_dotacion_premium(
        empleado, empresa, str(dotacion), {
            "fecha_entrega": date(2026, 7, 6),
            "tipo_entrega": "dotacion_legal",
            "cumple_requisitos_dotacion": True,
            "lugar_entrega": "Sede Medellín",
            "periodo_entrega": "Segundo semestre de 2026",
            "responsable_entrega": "Catalina Restrepo Gómez — Analista de Gestión Humana",
            "items": [
                {"descripcion": "Camisa blanca", "talla": "XL", "cantidad": 3, "estado": "Nuevo"},
                {"descripcion": "Pantalón", "talla": "36", "cantidad": 3, "estado": "Nuevo"},
                {"descripcion": "Camisa tipo polo", "talla": "XL", "cantidad": 2, "estado": "Nuevo"},
            ],
            "numero_documento": "DOT-2026-000045",
            "usuario_generador": "jhonathan.castano",
            "estado_documento": "Aprobado",
        }, usar_marca_agua=False,
    )

    resultado_sin = _resultado_liquidacion(
        empleado, dias_pendientes=0,
        estado_aportes="no_existe_salario_pendiente",
        deducciones_autorizadas=125_000,
    )
    liquidacion_sin = out / "LIQUIDACION_SIN_SALARIO_PENDIENTE_MARCO_ALVAREZ_LIQ-001.pdf"
    generar_liquidacion_premium(
        resultado_sin, empresa, str(liquidacion_sin), usar_marca_agua=False,
        config={
            "pagos_previos_confirmados": True,
            "novedades_confirmadas": True,
            "numero_documento": "LIQ-2026-000045",
            "usuario_generador": "jhonathan.castano",
            "estado_documento": "Aprobado",
        },
    )

    resultado_15 = _resultado_liquidacion(
        empleado, dias_pendientes=15,
        estado_aportes="no_descontados",
        deducciones_autorizadas=0,
    )
    liquidacion_15 = out / "LIQUIDACION_CON_15_DIAS_PENDIENTES_MARCO_ALVAREZ_LIQ-002.pdf"
    generar_liquidacion_premium(
        resultado_15, empresa, str(liquidacion_15), usar_marca_agua=False,
        config={
            "pagos_previos_confirmados": True,
            "novedades_confirmadas": True,
            "numero_documento": "LIQ-2026-000046",
            "usuario_generador": "jhonathan.castano",
            "estado_documento": "Aprobado",
        },
    )

    paths = [contrato, certificado, dotacion, liquidacion_sin, liquidacion_15]
    manifest = {
        "generados": [p.name for p in paths],
        "fecha_prueba": "2026-07-30",
        "estado": "documentos finales sin marca de agua",
        "nota": "Datos ficticios para validación visual y automatizada.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


if __name__ == "__main__":
    for path in main():
        print(path)
