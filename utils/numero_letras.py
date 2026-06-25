"""Convierte un número a su representación en letras (español, pesos colombianos)."""

UNIDADES = [
    "", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
    "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS",
    "DIECISIETE", "DIECIOCHO", "DIECINUEVE", "VEINTE", "VEINTIÚN", "VEINTIDÓS",
    "VEINTITRÉS", "VEINTICUATRO", "VEINTICINCO", "VEINTISÉIS", "VEINTISIETE",
    "VEINTIOCHO", "VEINTINUEVE",
]
DECENAS = [
    "", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
    "SESENTA", "SETENTA", "OCHENTA", "NOVENTA",
]
CENTENAS = [
    "", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
    "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS",
]


def _centenas(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    c = n // 100
    resto = n % 100
    if resto == 0:
        return CENTENAS[c]
    if resto < 30:
        return f"{CENTENAS[c]} {UNIDADES[resto]}".strip()
    d = resto // 10
    u = resto % 10
    if u == 0:
        return f"{CENTENAS[c]} {DECENAS[d]}".strip()
    return f"{CENTENAS[c]} {DECENAS[d]} Y {UNIDADES[u]}".strip()


def _miles(n: int) -> str:
    if n == 0:
        return ""
    miles = n // 1000
    resto = n % 1000
    if miles == 1:
        prefijo = "MIL"
    else:
        prefijo = f"{_centenas(miles)} MIL"
    if resto == 0:
        return prefijo
    return f"{prefijo} {_centenas(resto)}"


def _millones(n: int) -> str:
    if n == 0:
        return "CERO"
    millones = n // 1_000_000
    resto = n % 1_000_000
    if millones == 0:
        return _miles(n)
    if millones == 1:
        prefijo = "UN MILLÓN"
    else:
        prefijo = f"{_centenas(millones)} MILLONES"
    if resto == 0:
        return prefijo
    return f"{prefijo} {_miles(resto)}"


def numero_a_letras(valor: float) -> str:
    """
    Convierte un valor numérico a letras en español (mayúsculas).
    Ejemplo: 4_640_000 → 'CUATRO MILLONES SEISCIENTOS CUARENTA MIL PESOS'
    """
    try:
        entero = int(round(float(valor)))
    except (ValueError, TypeError):
        return "VALOR INVÁLIDO"

    if entero < 0:
        return f"MENOS {_millones(-entero)} PESOS"
    return f"{_millones(entero)} PESOS"
