"""Parche temporal para corregir la integración del acta de dotación.

Este script se elimina después de aplicar el cambio sobre la rama de integración.
"""
from pathlib import Path

RUTA = Path("utils/documentos_premium.py")

BLOQUE_TABLA_ANTERIOR = '''    # ─── Tabla con columna # (numeración) como en el modelo del cliente ──────
    cell = ParagraphStyle("CeldaDotacion", parent=estilos["cuerpo_izq"],
                            fontSize=9.5, leading=11, spaceAfter=0, alignment=TA_LEFT)
    cell_center = ParagraphStyle("CeldaDotacionCentro", parent=cell, alignment=TA_CENTER)
    header_cell = ParagraphStyle("CabeceraDotacion", parent=cell_center,
                                    textColor=colors.white, fontName="Helvetica-Bold",
                                    fontSize=10)

    headers = ["#", "Descripción", "Cantidad", "Estado"]
    filas = [[Paragraph(h, header_cell) for h in headers]]
    items = config.get("items") or []
    for idx, item in enumerate(items, start=1):
        filas.append([
            Paragraph(str(idx), cell_center),
            Paragraph(_txt(item.get("descripcion")), cell),
            Paragraph(_txt(item.get("cantidad")), cell_center),
            Paragraph(_txt(item.get("estado") or "Nuevo"), cell_center),
        ])

    # Anchos (A4 con márgenes 22/22 mm → ancho útil ~166 mm = 16.6 cm)
    tabla = Table(filas, colWidths=[1.2 * cm, 10.2 * cm, 2.2 * cm, 3.0 * cm],
                    repeatRows=1, splitByRow=1, hAlign="CENTER")
'''

BLOQUE_TABLA_NUEVO = '''    # ─── Tabla formal solicitada: Descripción, Talla, Cantidad y Estado ──────
    cell = ParagraphStyle("CeldaDotacion", parent=estilos["cuerpo_izq"],
                            fontSize=9.5, leading=11, spaceAfter=0, alignment=TA_LEFT)
    cell_center = ParagraphStyle("CeldaDotacionCentro", parent=cell, alignment=TA_CENTER)
    header_left = ParagraphStyle(
        "CabeceraDotacionIzq", parent=cell, textColor=colors.white,
        fontName="Helvetica-Bold", fontSize=10,
    )
    header_center = ParagraphStyle(
        "CabeceraDotacionCentro", parent=cell_center, textColor=colors.white,
        fontName="Helvetica-Bold", fontSize=10,
    )

    headers = [
        Paragraph("Descripción", header_left),
        Paragraph("Talla", header_center),
        Paragraph("Cantidad", header_center),
        Paragraph("Estado", header_center),
    ]
    filas = [headers]
    items = config.get("items") or []
    for item in items:
        filas.append([
            Paragraph(_txt(item.get("descripcion")), cell),
            Paragraph(_txt(item.get("talla") or "—"), cell_center),
            Paragraph(_txt(item.get("cantidad")), cell_center),
            Paragraph(_txt(item.get("estado") or "Nuevo"), cell_center),
        ])

    # A4 con márgenes de 22 mm: ancho útil aproximado de 16,6 cm.
    tabla = Table(
        filas,
        colWidths=[8.8 * cm, 2.2 * cm, 2.6 * cm, 3.0 * cm],
        repeatRows=1,
        splitByRow=1,
        hAlign="CENTER",
    )
'''

BLOQUE_DECLARACION_ANTERIOR = '''    # ─── Declaración de recibido ────────────────────────────────────────────
    if tipo_entrega in ("dotacion_legal", "uniforme", "epp"):
        declaracion_texto = (
            "El(la) trabajador(a) se compromete a hacer buen uso de los elementos entregados, "
            "mantenerlos en buen estado y devolverlos en caso de terminación del contrato de trabajo o "
            "cuando la empresa así lo requiera. Con su firma manifiesta haber recibido a satisfacción "
            "los elementos detallados."
        )
    else:
        declaracion_texto = (
            "El(la) trabajador(a) manifiesta haber recibido los elementos relacionados, se compromete "
            "a destinarlos al desarrollo de sus funciones y a utilizarlos conforme a las políticas "
            "internas de la empresa."
        )
'''

BLOQUE_DECLARACION_NUEVO = '''    # ─── Declaración de recibido ────────────────────────────────────────────
    # La dotación legal, el uniforme y los EPP no se tratan automáticamente
    # como elementos devolutivos. Las herramientas o activos sí pueden usar
    # una declaración separada de custodia y devolución.
    if tipo_entrega in ("herramienta", "herramienta_devolutiva", "activo", "elemento_devolutivo"):
        declaracion_texto = (
            "La persona trabajadora manifiesta haber recibido los elementos relacionados, se compromete "
            "a conservarlos adecuadamente, destinarlos al desarrollo de sus funciones y devolverlos "
            "cuando finalice su asignación o cuando la empresa lo requiera, conforme a las políticas internas."
        )
    else:
        declaracion_texto = (
            "La persona trabajadora manifiesta haber recibido a satisfacción los elementos relacionados "
            "y se compromete a destinarlos al desarrollo de sus funciones, conservarlos adecuadamente "
            "y utilizarlos conforme a las políticas internas de la empresa."
        )
'''


def reemplazar_unico(texto: str, anterior: str, nuevo: str, etiqueta: str) -> str:
    cantidad = texto.count(anterior)
    if cantidad != 1:
        raise RuntimeError(
            f"No se pudo aplicar {etiqueta}: se esperó una coincidencia y se encontraron {cantidad}."
        )
    return texto.replace(anterior, nuevo, 1)


def main() -> None:
    texto = RUTA.read_text(encoding="utf-8")
    texto = reemplazar_unico(texto, BLOQUE_TABLA_ANTERIOR, BLOQUE_TABLA_NUEVO, "tabla de dotación")
    texto = reemplazar_unico(
        texto,
        BLOQUE_DECLARACION_ANTERIOR,
        BLOQUE_DECLARACION_NUEVO,
        "declaración de recibido",
    )
    RUTA.write_text(texto, encoding="utf-8")
    print("Parche aplicado correctamente a utils/documentos_premium.py")


if __name__ == "__main__":
    main()
