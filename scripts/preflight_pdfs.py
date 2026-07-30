"""Preflight automatizado de PDFs: contenido, límites, páginas y renders."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz

FOOTER_LIMIT = 742  # y superior aproximada del pie en página Letter (792 pt)


def revisar(pdf_path: Path, renders_root: Path) -> dict:
    doc = fitz.open(pdf_path)
    out_dir = renders_root / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    paginas = []
    errores = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        blocks = page.get_text("blocks")
        body_blocks = [b for b in blocks if b[1] < FOOTER_LIMIT]
        if len(text) < 180:
            errores.append(f"Página {i+1}: contenido insuficiente ({len(text)} caracteres)")
        if not body_blocks:
            errores.append(f"Página {i+1}: sin bloques de contenido")
        for b in body_blocks:
            x0, y0, x1, y1 = b[:4]
            if x0 < -1 or y0 < -1 or x1 > page.rect.width + 1 or y1 > page.rect.height + 1:
                errores.append(f"Página {i+1}: bloque fuera de límites {b[:4]}")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        render = out_dir / f"page-{i+1}.png"
        pix.save(render)
        paginas.append({
            "pagina": i + 1,
            "caracteres": len(text),
            "bloques": len(body_blocks),
            "render": str(render),
        })
    return {
        "archivo": str(pdf_path),
        "paginas": len(doc),
        "detalle": paginas,
        "errores": errores,
        "ok": not errores,
    }


def main():
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
    if len(resultados) != 4 or fallos:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
