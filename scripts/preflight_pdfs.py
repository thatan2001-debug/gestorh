"""Preflight automatizado de los cinco PDF finales y sus renders por página."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz

EXPECTED_PDFS = 5
FOOTER_Y = 742
FORBIDDEN_TEXT = (
    "Reglas:",
    "Versión de reglas",
    "parámetros confirmados por el usuario",
    "Existen confirmaciones pendientes",
    "no se incluye QR",
    "plantilla parametrizable",
    "no constituye concepto",
    "Auxilios, comisiones o bonificaciones: no registrados",
    "despido_sin_justa_causa",
    "Documento pendiente de firma",
    "Firma pendiente",
    "BORRADOR - PENDIENTE DE REVISION",
    "BORRADOR — PENDIENTE DE REVISIÓN",
    "salario / 30",
    "base × días",
)


def _normalizar(texto: str) -> str:
    return " ".join(texto.replace("\u00a0", " ").split())


def revisar(pdf_path: Path, renders_root: Path) -> dict:
    doc = fitz.open(pdf_path)
    out_dir = renders_root / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    paginas: list[dict] = []
    errores: list[str] = []
    texto_total = "\n".join(page.get_text() for page in doc)
    texto_normalizado = _normalizar(texto_total)

    for patron in FORBIDDEN_TEXT:
        if patron.casefold() in texto_normalizado.casefold():
            errores.append(f"Texto técnico o no permitido visible: {patron}")
    if re.search(r"\b(?:undefined|null|none)\b", texto_normalizado, flags=re.I):
        errores.append("Existe un valor técnico undefined/null/none visible")
    if re.search(r"\b[a-záéíóúñ]+_[a-záéíóúñ_]+\b", texto_total, flags=re.I):
        errores.append("Existe una clave interna con guion bajo visible")

    for i, page in enumerate(doc):
        text = page.get_text().strip()
        blocks = page.get_text("blocks")
        body_blocks = [b for b in blocks if b[1] < FOOTER_Y and b[4].strip()]
        body_chars = sum(len(str(b[4]).strip()) for b in body_blocks)
        max_body_y = max((float(b[3]) for b in body_blocks), default=0)

        minimo = 220 if len(doc) == 1 else (520 if i > 0 else 350)
        if body_chars < minimo:
            errores.append(f"Página {i + 1}: contenido insuficiente ({body_chars} caracteres útiles)")
        if not body_blocks:
            errores.append(f"Página {i + 1}: sin bloques de contenido")
        if len(doc) > 1 and i == len(doc) - 1 and max_body_y < 430:
            errores.append(f"Página {i + 1}: posible página casi vacía (contenido hasta y={max_body_y:.1f})")
        if "Página " not in text and "Pagina " not in text:
            errores.append(f"Página {i + 1}: pie sin numeración")
        for b in body_blocks:
            x0, y0, x1, y1 = map(float, b[:4])
            if x0 < -1 or y0 < -1 or x1 > page.rect.width + 1 or y1 > page.rect.height + 1:
                errores.append(f"Página {i + 1}: bloque fuera de límites {(x0, y0, x1, y1)}")
            if y1 > FOOTER_Y + 1:
                errores.append(f"Página {i + 1}: contenido invade el pie documental")

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        render = out_dir / f"page-{i + 1}.png"
        pix.save(render)
        paginas.append({
            "pagina": i + 1,
            "caracteres": len(text),
            "caracteres_utiles": body_chars,
            "bloques": len(body_blocks),
            "ultimo_bloque_y": round(max_body_y, 2),
            "render": str(render),
        })

    nombre = pdf_path.name.upper()
    if nombre.startswith("CERTIFICADO") and len(doc) != 1:
        errores.append("El certificado debe ocupar exactamente una página")
    if nombre.startswith("ACTA_DOTACION") and len(doc) != 1:
        errores.append("El acta de dotación normal debe ocupar exactamente una página")
    if nombre.startswith("LIQUIDACION") and len(doc) != 1:
        errores.append("La liquidación de aceptación debe ocupar exactamente una página")
    if nombre.startswith("CONTRATO") and len(doc) not in (2, 3):
        errores.append("El contrato debe ocupar dos o tres páginas")

    return {
        "archivo": str(pdf_path),
        "paginas": len(doc),
        "detalle": paginas,
        "errores": sorted(set(errores)),
        "ok": not errores,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directorio", nargs="?", default="artifacts/documentos_finales")
    parser.add_argument("--renders", default="artifacts/renders")
    parser.add_argument("--report", default="artifacts/preflight.json")
    args = parser.parse_args()
    root = Path(args.directorio)
    renders = Path(args.renders)
    resultados = [revisar(p, renders) for p in sorted(root.glob("*.pdf"))]
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    fallos = [r for r in resultados if not r["ok"]]
    print(json.dumps({"pdfs": len(resultados), "fallos": len(fallos)}, ensure_ascii=False))
    for fallo in fallos:
        print(Path(fallo["archivo"]).name, *fallo["errores"], sep="\n  - ")
    if len(resultados) != EXPECTED_PDFS or fallos:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
