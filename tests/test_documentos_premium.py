from datetime import date, datetime
from pathlib import Path

import fitz
import pandas as pd
import pytest

from scripts.generar_muestras_documentales import main
from utils.calcular_liquidacion import calcular_liquidacion_fila
from utils.documentos_premium import (
    generar_certificado_premium,
    generar_contrato_indefinido_premium,
    generar_dotacion_premium,
)

PROHIBIDOS = (
    "Reglas:",
    "parámetros confirmados por el usuario",
    "Existen confirmaciones pendientes",
    "no se incluye QR",
    "plantilla parametrizable",
    "no constituye concepto",
    "no registrados",
    "despido_sin_justa_causa",
    "Documento pendiente de firma",
    "Firma pendiente",
    "BORRADOR - PENDIENTE DE REVISION",
    "salario / 30",
    "base × días",
)


def _texto(pdf: Path) -> str:
    return "\n".join(p.get_text() for p in fitz.open(pdf))


def _empresa() -> dict:
    return {
        "nombre": "Empresa de Prueba S.A.S.", "nit": "900.123.456-7", "ciudad": "Medellín",
        "telefono": "+57 604 555 0000", "correo_empresa": "rh@empresa.com",
        "representante": "Ana Pérez", "_cargo_firmante": "Representante Legal",
    }


def _empleado() -> dict:
    return {
        "Nombre": "Marco Álvarez", "Documento": "123456789", "Tipo documento": "C.C.",
        "Cargo": "Analista de Operaciones", "Salario": 2_500_000,
        "Fecha ingreso": "2026-01-10", "Tipo contrato": "Indefinido", "Sede": "Medellín",
    }


def test_genera_cinco_pdfs_finales_sin_paginas_desperdiciadas(tmp_path: Path):
    archivos = main(tmp_path)
    assert len(archivos) == 5
    conteos = {}
    for pdf in archivos:
        assert pdf.exists() and pdf.stat().st_size > 8_000
        doc = fitz.open(pdf)
        assert doc.metadata.get("author") == "Gestor RH IA"
        conteos[pdf.name] = len(doc)
        for pagina in doc:
            texto = pagina.get_text().strip()
            assert len(texto) > 220, f"Página casi vacía en {pdf.name}"
            assert ("Página " in texto or "Pagina " in texto) and "Gestor RH IA" in texto
        total = _texto(pdf)
        for prohibido in PROHIBIDOS:
            assert prohibido.casefold() not in total.casefold(), f"Texto no permitido en {pdf.name}: {prohibido}"
    assert conteos[next(x for x in conteos if x.startswith("CERTIFICADO"))] == 1
    assert conteos[next(x for x in conteos if x.startswith("ACTA_DOTACION"))] == 1
    assert conteos[next(x for x in conteos if x.startswith("CONTRATO"))] in (2, 3)
    assert all(v == 1 for k, v in conteos.items() if k.startswith("LIQUIDACION"))


def test_contrato_final_sin_clausula_interna_y_con_pago_formal(tmp_path: Path):
    contrato = main(tmp_path)[0]
    texto = _texto(contrato)
    assert "REVISIÓN JURÍDICA" not in texto
    assert "PERÍODO DE PRUEBA" not in texto
    assert "quincenalmente" in texto
    assert "último día hábil" in " ".join(texto.split())
    assert "Gestionar las solicitudes de las áreas" in texto
    assert "Elaborar los horarios del personal a cargo" in texto


def test_contrato_bloquea_periodo_prueba_retroactivo(tmp_path: Path):
    with pytest.raises(ValueError, match="más de dos meses|retroactivamente"):
        generar_contrato_indefinido_premium(_empleado(), _empresa(), str(tmp_path / "retroactivo.pdf"), {
            "fecha_inicio_contrato": date(2026, 1, 10),
            "fecha_inicio_precargada": True,
            "fecha_inicio_confirmada": True,
            "fecha_celebracion": date(2026, 7, 30),
            "periodo_prueba": True,
            "periodicidad_pago": "quincenal",
            "forma_pago": "transferencia bancaria",
        })


def test_certificado_activo_usa_redaccion_correcta_y_no_inventa_qr(tmp_path: Path):
    certificado = main(tmp_path)[1]
    texto = _texto(certificado)
    assert "Actualmente devenga un salario mensual" in texto
    assert "último salario mensual registrado" not in texto
    assert "Para verificar la autenticidad" in texto
    assert "QR" not in texto
    assert len(fitz.open(certificado)) == 1


def test_acta_tiene_exactamente_cuatro_columnas_y_datos_sin_desplazamiento(tmp_path: Path):
    acta = main(tmp_path)[2]
    texto = _texto(acta)
    for encabezado in ("Descripción", "Talla", "Cantidad", "Estado"):
        assert encabezado in texto
    for encabezado in ("Tipo", "Color", "Marca", "Referencia", "Observaciones"):
        assert encabezado not in texto
    lineas = [x.strip() for x in texto.splitlines() if x.strip()]
    secuencias = [
        ("Camisa blanca", "XL", "3", "Nuevo"),
        ("Pantalón", "36", "3", "Nuevo"),
        ("Camisa tipo polo", "XL", "2", "Nuevo"),
    ]
    texto_lineal = " | ".join(lineas)
    for descripcion, talla, cantidad, estado in secuencias:
        posiciones = [texto_lineal.index(x, texto_lineal.index(descripcion)) for x in (descripcion, talla, cantidad, estado)]
        assert posiciones == sorted(posiciones)
    assert len(fitz.open(acta)) == 1


def test_acta_extensa_repite_solo_los_cuatro_encabezados(tmp_path: Path):
    items = [{"descripcion": f"Elemento corporativo número {i} con descripción amplia para validación de paginación", "talla": "M", "cantidad": 1, "estado": "Nuevo"} for i in range(1, 36)]
    ruta = tmp_path / "acta_extensa.pdf"
    generar_dotacion_premium(_empleado(), _empresa(), str(ruta), {
        "fecha_entrega": date(2026, 7, 30), "tipo_entrega": "uniforme_corporativo",
        "items": items, "responsable_entrega": "Ana Pérez", "lugar_entrega": "Medellín",
        "periodo_entrega": "Segundo semestre de 2026",
    })
    doc = fitz.open(ruta)
    assert len(doc) >= 2
    for page in doc:
        texto = page.get_text()
        assert all(x in texto for x in ("Descripción", "Talla", "Cantidad", "Estado"))
        assert "Observaciones" not in texto and "Referencia" not in texto
    total = _texto(ruta)
    for i in range(1, 36):
        assert f"Elemento corporativo número {i}" in total


def test_liquidacion_sin_salario_oculta_fila_y_separa_autorizadas(tmp_path: Path):
    liquidacion = main(tmp_path)[3]
    texto = _texto(liquidacion)
    assert "Salario pendiente" not in texto
    assert "DEDUCCIONES DE LEY" not in texto.upper()
    assert "DEDUCCIONES AUTORIZADAS" in texto.upper()
    assert "Fórmula" not in texto
    assert "Renuncia" in texto
    assert len(fitz.open(liquidacion)) == 1


def test_liquidacion_15_dias_muestra_periodo_y_aportes_solo_sobre_salario(tmp_path: Path):
    liquidacion = main(tmp_path)[4]
    texto = _texto(liquidacion)
    assert "Salario pendiente" in texto
    assert "16/07/2026 al 30/07/2026" in " ".join(texto.split())
    assert "15" in texto
    assert "Salud trabajador" in texto
    assert "Pensión trabajador" in texto
    assert "4%" in texto
    assert "DEDUCCIONES DE LEY" in texto.upper()
    assert "Fórmula" not in texto
    assert len(fitz.open(liquidacion)) == 1


def test_conciliacion_aportes_evitar_duplicados():
    base = {
        **_empleado(), "Fecha retiro": "2026-07-30", "Dias salario pendiente": 15,
        "Prima pagada": 0, "Cesantias consignadas": 0, "Vacaciones pagadas": 0,
    }
    completa = calcular_liquidacion_fila(pd.Series({**base, "Estado aportes periodo final": "descontados_completamente"}), datetime(2026, 7, 30))
    assert completa["TOTAL DEDUCCIONES DE LEY"] == 0
    parcial = calcular_liquidacion_fila(pd.Series({
        **base, "Estado aportes periodo final": "descontados_parcialmente",
        "Aporte salud ya descontado": 20_000, "Aporte pension ya descontado": 20_000,
    }), datetime(2026, 7, 30))
    pendiente = calcular_liquidacion_fila(pd.Series({**base, "Estado aportes periodo final": "no_descontados"}), datetime(2026, 7, 30))
    assert 0 < parcial["TOTAL DEDUCCIONES DE LEY"] < pendiente["TOTAL DEDUCCIONES DE LEY"]
    assert all(x["base"] == pendiente["Salario pendiente (estimado)"] for x in pendiente["Deducciones de ley"])


def test_borrador_muestra_marca_de_agua_y_final_no(tmp_path: Path):
    config = {"incluir_salario": False, "fecha_emision": date(2026, 7, 30)}
    borrador = tmp_path / "borrador.pdf"
    final = tmp_path / "final.pdf"
    generar_certificado_premium(_empleado(), _empresa(), str(borrador), False, usar_marca_agua=True, config=config)
    generar_certificado_premium(_empleado(), _empresa(), str(final), False, usar_marca_agua=False, config=config)
    assert "BORRADOR - PENDIENTE DE REVISION" in _texto(borrador)
    assert "BORRADOR - PENDIENTE DE REVISION" not in _texto(final)
