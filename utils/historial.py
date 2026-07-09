"""
Historial de documentos generados — RH Fácil.
Registra cada documento en Supabase con fallback JSON local.
"""

import json
from datetime import datetime
from pathlib import Path
from utils.db import _db

_JSON_PATH = Path("salidas/.historial.json")

NOMBRES_DOCUMENTO = {
    "certificado_con_salario":     "Certificado Laboral con Salario",
    "certificado_sin_salario":     "Certificado Laboral sin Salario",
    "carta_vacaciones":            "Carta de Vacaciones",
    "solicitud_vacaciones":        "Solicitud de Vacaciones",
    "liquidacion_prestaciones":    "Liquidación de Prestaciones Sociales",
    "paz_salvo":                   "Paz y Salvo Laboral",
    "carta_terminacion":           "Carta de Terminación de Contrato",
    "carta_no_renovacion":         "Carta de No Renovación",
    "contrato_fijo":               "Contrato a Término Fijo",
    "contrato_indefinido":         "Contrato a Término Indefinido",
    "contrato_obra":               "Contrato por Obra o Labor",
    "contrato_prestacion":         "Contrato de Prestación de Servicios",
    "autorizacion_descuento":      "Autorización de Descuento",
    "carta_ingresos":              "Carta de Ingresos",
    "autorizacion_datos":          "Autorización Tratamiento de Datos",
    "acta_entrega_cargo":          "Acta de Entrega de Cargo",
    "acta_entrega_equipos":        "Acta de Entrega de Equipos",
    "entrega_dotacion":            "Acta de Entrega de Dotación",
    "cambio_salario":              "Comunicación de Cambio de Salario",
    "cambio_cargo":                "Comunicación de Cambio de Cargo",
    "llamado_atencion":            "Llamado de Atención",
    "citacion_descargos":          "Citación a Descargos",
    "acta_descargos":              "Acta de Descargos",
    "licencia_no_remunerada":      "Licencia No Remunerada",
    "permiso_remunerado":          "Permiso Remunerado",
    "permiso_no_remunerado":       "Permiso No Remunerado",
    "carta_aceptacion_renuncia":   "Carta de Aceptación de Renuncia",
    "carta_retiro_voluntario":     "Carta de Retiro Voluntario",
    "certificacion_funciones":     "Certificación de Funciones",
}


def _json_load() -> list:
    if _JSON_PATH.exists():
        try:
            return json.load(open(_JSON_PATH, encoding="utf-8"))
        except Exception:
            pass
    return []


def _json_save(data: list):
    _JSON_PATH.parent.mkdir(exist_ok=True)
    with open(_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def registrar(
    email_usuario: str,
    email_empresa: str,
    nombre_empresa: str,
    tipo_documento: str,
    empleado_documento: str = "",
    empleado_nombre: str = "",
    nombre_archivo: str = "",
    estado: str = "generado",
    observaciones: str = "",
    datos_extra: dict = None,
    enviado_correo: bool = False,
    correo_destino: str = "",
) -> bool:
    """Registra un documento generado en el historial."""
    payload = {
        "email_usuario":      email_usuario,
        "email_empresa":      email_empresa,
        "nombre_empresa":     nombre_empresa,
        "empleado_documento": empleado_documento,
        "empleado_nombre":    empleado_nombre,
        "tipo_documento":     tipo_documento,
        "nombre_documento":   NOMBRES_DOCUMENTO.get(tipo_documento, tipo_documento),
        "estado":             estado,
        "nombre_archivo":     nombre_archivo,
        "observaciones":      observaciones,
        "datos_extra":        datos_extra or {},
        "enviado_correo":     enviado_correo,
        "correo_destino":     correo_destino,
        "generado_en":        datetime.now().isoformat(),
    }

    sb = _db()
    if sb:
        try:
            sb.table("historial_documentos").insert(payload).execute()
            return True
        except Exception as e:
            print(f"Error registrando historial: {e}")

    # Fallback JSON
    hist = _json_load()
    hist.insert(0, payload)  # más reciente primero
    hist = hist[:500]        # máximo 500 entradas en JSON
    _json_save(hist)
    return True


def obtener(
    email_usuario: str,
    limite: int = 50,
    tipo_documento: str = None,
    empleado_documento: str = None,
) -> list:
    """Obtiene el historial del usuario con filtros opcionales."""
    sb = _db()
    if sb:
        try:
            q = sb.table("historial_documentos")\
                .select("*")\
                .eq("email_usuario", email_usuario)\
                .order("generado_en", desc=True)\
                .limit(limite)
            if tipo_documento:
                q = q.eq("tipo_documento", tipo_documento)
            if empleado_documento:
                q = q.eq("empleado_documento", empleado_documento)
            return q.execute().data or []
        except Exception as e:
            print(f"Error leyendo historial: {e}")

    # Fallback JSON
    hist = _json_load()
    hist = [h for h in hist if h.get("email_usuario") == email_usuario]
    if tipo_documento:
        hist = [h for h in hist if h.get("tipo_documento") == tipo_documento]
    if empleado_documento:
        hist = [h for h in hist if h.get("empleado_documento") == empleado_documento]
    return hist[:limite]


def obtener_por_empleado(email_empresa: str, documento: str, limite: int = 20) -> list:
    """Historial de documentos de un empleado específico."""
    sb = _db()
    if sb:
        try:
            return sb.table("historial_documentos")\
                .select("*")\
                .eq("email_empresa", email_empresa)\
                .eq("empleado_documento", documento)\
                .order("generado_en", desc=True)\
                .limit(limite)\
                .execute().data or []
        except Exception as e:
            print(f"Error: {e}")

    hist = _json_load()
    return [h for h in hist
            if h.get("email_empresa") == email_empresa
            and h.get("empleado_documento") == documento][:limite]


def stats_mes(email_usuario: str) -> dict:
    """Estadísticas de documentos generados este mes."""
    from datetime import datetime
    hoy = datetime.today()
    mes_str = f"{hoy.year}-{hoy.month:02d}"

    sb = _db()
    if sb:
        try:
            r = sb.table("historial_documentos")\
                .select("tipo_documento")\
                .eq("email_usuario", email_usuario)\
                .gte("generado_en", f"{mes_str}-01")\
                .execute()
            datos = r.data or []
        except Exception:
            datos = []
    else:
        hist = _json_load()
        datos = [h for h in hist
                 if h.get("email_usuario") == email_usuario
                 and str(h.get("generado_en","")).startswith(mes_str)]

    total = len(datos)
    por_tipo = {}
    for d in datos:
        t = d.get("tipo_documento","otro")
        por_tipo[t] = por_tipo.get(t, 0) + 1

    return {"total_mes": total, "por_tipo": por_tipo}


def marcar_enviado(historial_id: str, correo_destino: str) -> bool:
    """Marca un documento como enviado por correo."""
    sb = _db()
    if sb:
        try:
            sb.table("historial_documentos").update({
                "estado": "enviado",
                "enviado_correo": True,
                "correo_destino": correo_destino,
                "fecha_envio": datetime.now().isoformat(),
            }).eq("id", historial_id).execute()
            return True
        except Exception:
            pass
    return False
