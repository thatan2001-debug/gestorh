"""
Sistema de logs para Gestor RH IA.
Guarda logs en salidas/logs.jsonl (una línea por evento).
Persiste entre reruns de Streamlit y permite diagnosticar problemas
sin depender de la UI.

Uso:
    from utils.logs import log_info, log_error, log_debug, ver_logs

    log_info("liquidacion.iniciada", empleado="Juan", motivo="renuncia")
    try:
        ...
    except Exception as e:
        log_error("liquidacion.fallo", error=str(e), empleado="Juan")

    # Para ver últimos 50 logs
    ver_logs(limite=50, nivel="error")
"""

import json
import traceback
from datetime import datetime
from pathlib import Path

LOGS_FILE = Path("salidas/logs.jsonl")
LOGS_FILE.parent.mkdir(exist_ok=True)

# Máximo de líneas en el archivo (rota cuando pasa el límite)
MAX_LINES = 5000


def _escribir(nivel: str, evento: str, **kwargs):
    """Escribe una línea JSON al archivo de logs."""
    try:
        entry = {
            "ts":     datetime.now().isoformat(timespec="seconds"),
            "nivel":  nivel,
            "evento": evento,
            **kwargs,
        }
        with open(LOGS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

        # Rotar si el archivo crece mucho
        _rotar_si_necesario()
    except Exception:
        # Nunca fallar por logs — es la primera regla
        pass


def _rotar_si_necesario():
    """Si el archivo pasa MAX_LINES, deja solo las últimas 3000."""
    try:
        if not LOGS_FILE.exists():
            return
        with open(LOGS_FILE, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > MAX_LINES:
            with open(LOGS_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[-3000:])
    except Exception:
        pass


def log_info(evento: str, **kwargs):
    """Evento normal — algo bien que ocurrió."""
    _escribir("info", evento, **kwargs)


def log_debug(evento: str, **kwargs):
    """Detalle para diagnosticar — datos intermedios de un cálculo."""
    _escribir("debug", evento, **kwargs)


def log_warn(evento: str, **kwargs):
    """Advertencia — algo raro pero recuperable."""
    _escribir("warn", evento, **kwargs)


def log_error(evento: str, **kwargs):
    """Error — algo falló. Guarda también el traceback si aplica."""
    tb = traceback.format_exc()
    if tb and tb.strip() != "NoneType: None":
        kwargs.setdefault("traceback", tb)
    _escribir("error", evento, **kwargs)


def ver_logs(limite: int = 100, nivel: str = None,
              evento_contiene: str = None) -> list:
    """
    Lee y filtra logs.
      limite:            número máximo a retornar (los más recientes)
      nivel:             'info', 'debug', 'warn', 'error' o None (todos)
      evento_contiene:   filtrar eventos que contengan este texto
    """
    if not LOGS_FILE.exists():
        return []
    try:
        with open(LOGS_FILE, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    resultados = []
    for line in reversed(lines):  # Los más recientes primero
        try:
            entry = json.loads(line.strip())
        except Exception:
            continue
        if nivel and entry.get("nivel") != nivel:
            continue
        if evento_contiene and evento_contiene not in entry.get("evento", ""):
            continue
        resultados.append(entry)
        if len(resultados) >= limite:
            break
    return resultados


def limpiar_logs():
    """Borra todo el archivo (usar con cuidado)."""
    try:
        LOGS_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def stats_logs() -> dict:
    """Retorna un resumen de eventos en las últimas 24h."""
    if not LOGS_FILE.exists():
        return {"total": 0, "por_nivel": {}, "errores_recientes": []}

    try:
        with open(LOGS_FILE, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return {"total": 0, "por_nivel": {}, "errores_recientes": []}

    from collections import Counter
    por_nivel = Counter()
    errores = []
    for line in lines:
        try:
            e = json.loads(line.strip())
            por_nivel[e.get("nivel", "?")] += 1
            if e.get("nivel") == "error":
                errores.append(e)
        except Exception:
            continue

    return {
        "total":             len(lines),
        "por_nivel":         dict(por_nivel),
        "errores_recientes": errores[-10:],
    }
