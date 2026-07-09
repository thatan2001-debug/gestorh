"""
Utilidades de fechas para RH Fácil.
Normaliza cualquier formato de fecha a dd/mm/aaaa legible.
Supabase devuelve timestamps como "2026-05-01 00:00:00" o "2026-05-01T00:00:00".
Excel devuelve objetos datetime o strings "01/05/2026".
"""

from datetime import datetime, date
import pandas as pd


def fmt_fecha(valor, salida: str = "%d/%m/%Y") -> str:
    """
    Convierte cualquier representación de fecha a formato legible.
    
    Acepta:
    - datetime / date
    - pd.Timestamp
    - "2026-05-01"
    - "2026-05-01 00:00:00"
    - "2026-05-01T00:00:00"
    - "01/05/2026"
    - "01-05-2026"
    - None / "" / NaN → retorna ""
    """
    if valor is None:
        return ""
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor or valor.lower() in ("none", "nan", "nat", "null"):
            return ""
    if pd.isna(valor) if not isinstance(valor, (str, datetime, date)) else False:
        return ""
    if isinstance(valor, (datetime, date)):
        return valor.strftime(salida)
    if isinstance(valor, pd.Timestamp):
        return valor.strftime(salida)

    # String — intentar varios formatos
    texto = str(valor).strip()
    # Quitar parte de hora si existe: "2026-05-01 00:00:00" → "2026-05-01"
    if " " in texto:
        texto = texto.split(" ")[0]
    if "T" in texto:
        texto = texto.split("T")[0]

    formatos = [
        "%Y-%m-%d",   # ISO: 2026-05-01
        "%d/%m/%Y",   # colombiano: 01/05/2026
        "%d-%m-%Y",   # alternativo: 01-05-2026
        "%d/%m/%y",   # dos dígitos año: 01/05/26
        "%Y/%m/%d",   # raro pero posible
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt).strftime(salida)
        except ValueError:
            continue

    # Si no pudo parsear, devolver el texto limpio sin la parte de hora
    return texto


def fmt_fecha_larga(valor) -> str:
    """Retorna fecha en formato largo español: "01 de mayo de 2026"."""
    fecha_fmt = fmt_fecha(valor, "%d/%m/%Y")
    if not fecha_fmt:
        return ""
    try:
        dt = datetime.strptime(fecha_fmt, "%d/%m/%Y")
        meses = [
            "enero","febrero","marzo","abril","mayo","junio",
            "julio","agosto","septiembre","octubre","noviembre","diciembre"
        ]
        return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"
    except Exception:
        return fecha_fmt


def fecha_hoy_fmt() -> str:
    """Fecha de hoy en formato dd/mm/aaaa."""
    return datetime.today().strftime("%d/%m/%Y")


def fecha_hoy_larga() -> str:
    """Fecha de hoy en formato largo: 'el día 08 de julio de 2026'."""
    meses = [
        "enero","febrero","marzo","abril","mayo","junio",
        "julio","agosto","septiembre","octubre","noviembre","diciembre"
    ]
    hoy = datetime.today()
    return f"{hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
