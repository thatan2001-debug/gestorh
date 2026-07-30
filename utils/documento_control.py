"""Control documental, metadatos, nombres seguros y canvas multipágina."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

BOGOTA = ZoneInfo("America/Bogota")
VERSION_PLANTILLA = "2.1"
VERSION_REGLAS = "2026.1"

CODIGOS = {
    "contrato_indefinido": "RH-CONT-IND",
    "certificado": "RH-CERT",
    "dotacion": "RH-DOT",
    "liquidacion": "RH-LIQ",
}


@dataclass(frozen=True)
class ControlDocumento:
    tipo: str
    numero: str
    codigo: str
    version_plantilla: str
    version_reglas: str
    generado_en: datetime
    usuario: str
    estado: str
    trabajador_id: str
    empresa_id: str
    hash_corto: str


def _limpiar_id(valor: object) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(valor or ""))


def crear_control_documental(
    tipo: str,
    trabajador_id: object,
    empresa_id: object,
    usuario: str = "Usuario autenticado",
    estado: str = "Generado",
    numero: Optional[str] = None,
    ahora: Optional[datetime] = None,
) -> ControlDocumento:
    ahora = ahora or datetime.now(BOGOTA)
    codigo = CODIGOS.get(tipo, f"RH-{tipo[:8].upper()}")
    base = f"{tipo}|{trabajador_id}|{empresa_id}|{ahora.isoformat()}"
    hash_corto = hashlib.sha256(base.encode("utf-8")).hexdigest()[:12].upper()
    secuencia = int(hash_corto[:6], 16) % 1_000_000
    numero = numero or f"{codigo.split('-')[-1]}-{ahora.year}-{secuencia:06d}"
    return ControlDocumento(
        tipo=tipo,
        numero=numero,
        codigo=codigo,
        version_plantilla=VERSION_PLANTILLA,
        version_reglas=VERSION_REGLAS,
        generado_en=ahora,
        usuario=usuario or "Usuario autenticado",
        estado=estado,
        trabajador_id=_limpiar_id(trabajador_id),
        empresa_id=_limpiar_id(empresa_id),
        hash_corto=hash_corto,
    )


def nombre_archivo_seguro(tipo: str, nombre: str, fecha: object, numero: str) -> str:
    texto = unicodedata.normalize("NFKD", str(nombre or "SIN_NOMBRE"))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").upper()
    fecha_txt = str(fecha)[:10].replace("/", "-")
    numero_txt = re.sub(r"[^A-Za-z0-9-]", "", numero)
    return f"{tipo.upper()}_{texto}_{fecha_txt}_{numero_txt}.pdf"


class ControlDocumentalCanvas(canvas.Canvas):
    """Canvas de dos pasadas para Página X de Y y metadatos consistentes."""

    def __init__(self, *args, control: ControlDocumento, paleta: dict,
                 logo_path: str | None = None, usar_marca_agua: bool = False,
                 impresion_economica: bool = False, titulo: str = "Documento laboral",
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.control = control
        self.paleta = paleta
        self.logo_path = logo_path
        self.usar_marca_agua = bool(usar_marca_agua and not impresion_economica)
        self.titulo_doc = titulo
        self.setTitle(titulo)
        self.setAuthor("Gestor RH IA")
        self.setCreator("Gestor RH IA · motor documental 2.1")
        self.setSubject(f"{control.codigo} · {control.numero}")
        self.setKeywords(f"recursos humanos, {control.tipo}, {control.numero}, Colombia")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._dibujar_fondo_y_pie(total)
            super().showPage()
        super().save()

    def _dibujar_fondo_y_pie(self, total_paginas: int) -> None:
        ancho, alto = letter
        if self.usar_marca_agua and self.logo_path and Path(self.logo_path).exists():
            self.saveState()
            try:
                self.setFillAlpha(0.02)
                self.setStrokeAlpha(0.02)
                max_w, max_h = 9.0 * cm, 9.0 * cm
                self.drawImage(
                    self.logo_path,
                    (ancho - max_w) / 2,
                    (alto - max_h) / 2,
                    width=max_w,
                    height=max_h,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
            except Exception:
                pass
            self.restoreState()

        # Identificación de páginas continuadas sin repetir el encabezado completo.
        if self.getPageNumber() > 1:
            self.saveState()
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(self.paleta.get("primario", colors.HexColor("#1B3F6E")))
            etiqueta = f"{self.titulo_doc} — CONTINUACIÓN · Trabajador {self.control.trabajador_id}"
            self.drawString(2.0 * cm, alto - 1.25 * cm, etiqueta[:120])
            self.setStrokeColor(self.paleta.get("borde_suave", colors.HexColor("#E5E7EB")))
            self.line(2.0 * cm, alto - 1.42 * cm, ancho - 2.0 * cm, alto - 1.42 * cm)
            self.restoreState()

        self.saveState()
        gris = self.paleta.get("texto_suave", colors.HexColor("#6B7280"))
        borde = self.paleta.get("borde_suave", colors.HexColor("#E5E7EB"))
        self.setStrokeColor(borde)
        self.setLineWidth(0.45)
        self.line(2.0 * cm, 1.48 * cm, ancho - 2.0 * cm, 1.48 * cm)
        self.setFont("Helvetica", 7.2)
        self.setFillColor(gris)
        fecha = self.control.generado_en.strftime("%d/%m/%Y %H:%M")
        izquierda = (
            f"Gestor RH IA · {self.control.codigo} · {self.control.numero} · v{self.control.version_plantilla} · "
            f"{self.control.estado} · {fecha} COT"
        )
        self.drawString(2.0 * cm, 1.08 * cm, izquierda[:112])
        self.drawRightString(ancho - 2.0 * cm, 1.08 * cm,
                             f"Página {self.getPageNumber()} de {total_paginas}")
        self.restoreState()


def canvas_factory(control: ControlDocumento, paleta: dict, **opciones):
    def _factory(*args, **kwargs):
        return ControlDocumentalCanvas(
            *args, control=control, paleta=paleta, **opciones, **kwargs
        )
    return _factory
