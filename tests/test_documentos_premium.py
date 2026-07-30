from pathlib import Path

import fitz

from scripts.generar_muestras_documentales import main


def test_genera_cuatro_pdfs_con_control_y_sin_paginas_vacias(tmp_path: Path):
    archivos = main(tmp_path)
    assert len(archivos) == 4
    page_counts = {}
    for pdf in archivos:
        assert pdf.exists() and pdf.stat().st_size > 10_000
        doc = fitz.open(pdf)
        assert doc.metadata.get("author") == "Gestor RH IA"
        page_counts[pdf.name] = len(doc)
        for pagina in doc:
            texto = pagina.get_text().strip()
            assert len(texto) > 180, f"Página vacía o desperdiciada en {pdf.name}"
            assert "Página " in texto
            assert "Gestor RH IA" in texto
    assert page_counts[next(x for x in page_counts if x.startswith("CERTIFICADO"))] == 1
    assert page_counts[next(x for x in page_counts if x.startswith("ACTA_DOTACION"))] == 1
    assert page_counts[next(x for x in page_counts if x.startswith("CONTRATO"))] in (2, 3)
    assert page_counts[next(x for x in page_counts if x.startswith("LIQUIDACION"))] in (1, 2)


def test_contrato_numera_clausulas_sin_salto(tmp_path: Path):
    contrato = main(tmp_path)[0]
    texto = "\n".join(p.get_text() for p in fitz.open(contrato))
    assert "PRIMERA —" in texto and "SEGUNDA —" in texto and "TERCERA —" in texto
    assert texto.index("PRIMERA —") < texto.index("SEGUNDA —") < texto.index("TERCERA —")


def test_liquidacion_no_descuenta_salud_pension_indiscriminadamente(tmp_path: Path):
    liquidacion = main(tmp_path)[-1]
    texto = "\n".join(p.get_text() for p in fitz.open(liquidacion))
    assert "DEDUCCIONES AUTORIZADAS" in texto
    assert "EPS (4%)" not in texto
    assert "Pensión (4%)" not in texto


def test_acta_extensa_repite_encabezado_y_no_corta_filas(tmp_path: Path):
    from datetime import date
    from utils.documentos_premium import generar_dotacion_premium
    empresa = {"nombre":"Empresa de Prueba SAS","nit":"900123456-7","ciudad":"Medellín","representante":"Ana Pérez"}
    empleado = {"Nombre":"Trabajador con Nombre Extenso de Prueba","Documento":"123456789","Cargo":"Técnico de Operaciones","Salario":2_000_000,"Fecha ingreso":"2025-01-01"}
    items = [{
        "descripcion": f"Elemento corporativo de prueba número {i} con descripción extendida",
        "tipo":"Uniforme", "talla":"M", "color":"Azul", "referencia":f"REF-{i:02d}",
        "cantidad":1, "estado":"Nuevo", "observaciones":"Entrega verificada sin novedad",
    } for i in range(1, 16)]
    ruta = tmp_path / "acta_extensa.pdf"
    generar_dotacion_premium(empleado, empresa, str(ruta), {
        "fecha_entrega":date(2026,7,30), "tipo_entrega":"uniforme_corporativo",
        "items":items, "responsable_entrega":"Ana Pérez", "lugar_entrega":"Medellín",
    })
    doc = fitz.open(ruta)
    assert len(doc) >= 2
    for page in doc:
        text = page.get_text()
        assert "Descripción" in text and "Observaciones" in text
    texto_total = "\n".join(p.get_text() for p in doc)
    for i in range(1, 16):
        assert f"número {i}" in texto_total


def test_contrato_sin_periodo_prueba_no_salta_numeracion(tmp_path: Path):
    from datetime import date
    from utils.documentos_premium import generar_contrato_indefinido_premium
    empresa = {"nombre":"Empresa SAS","nit":"900123456-7","ciudad":"Medellín","representante":"Ana Pérez"}
    empleado = {"Nombre":"Marco Álvarez","Documento":"123456","Cargo":"Analista","Salario":2_500_000,"Fecha ingreso":"2026-01-10"}
    ruta = tmp_path / "contrato_sin_prueba.pdf"
    generar_contrato_indefinido_premium(empleado, empresa, str(ruta), {
        "fecha_inicio_contrato":date(2026,1,10), "fecha_inicio_precargada":True,
        "fecha_inicio_confirmada":True, "periodo_prueba":False,
        "periodicidad_pago":"Mensual", "forma_pago":"Transferencia", "dia_pago":"30",
    })
    texto = "\n".join(p.get_text() for p in fitz.open(ruta))
    assert "PRIMERA —" in texto and "SEGUNDA —" in texto and "TERCERA —" in texto
    assert "PERÍODO DE PRUEBA" not in texto
