"""
Envío de documentos por correo electrónico vía SMTP.
Compatible con Gmail (requiere contraseña de aplicación) y otros proveedores.

Configuración en Render → Environment Variables:
  SMTP_HOST     smtp.gmail.com
  SMTP_PORT     587
  SMTP_USER     tucorreo@gmail.com
  SMTP_PASS     contraseña_de_aplicacion_gmail
  SMTP_FROM     GestorRH Colombia <tucorreo@gmail.com>
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path


def _config_smtp() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", 587)),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
        "from": os.getenv("SMTP_FROM", "GestorRH Colombia <noreply@gestorrh.co>"),
    }


def smtp_configurado() -> bool:
    cfg = _config_smtp()
    return bool(cfg["user"] and cfg["password"])


def enviar_documentos(
    destinatario_email: str,
    destinatario_nombre: str,
    empresa_nombre: str,
    tipo_documento: str,
    rutas_pdf: list[str],
    correo_empresa: str = "",
) -> tuple[bool, str]:
    """
    Envía uno o varios PDFs por correo al empleado.

    Retorna (éxito, mensaje).
    """
    cfg = _config_smtp()
    if not cfg["user"] or not cfg["password"]:
        return False, (
            "SMTP no configurado. Agrega las variables de entorno "
            "SMTP_HOST, SMTP_USER y SMTP_PASS en Render → Environment."
        )

    remitente = correo_empresa if correo_empresa else cfg["from"]

    msg = MIMEMultipart()
    msg["From"]    = cfg["from"]
    msg["To"]      = destinatario_email
    msg["Subject"] = f"{tipo_documento} — {empresa_nombre}"
    msg["Reply-To"] = correo_empresa if correo_empresa else cfg["user"]

    cuerpo = f"""Estimado(a) {destinatario_nombre},

Adjunto encontrará su {tipo_documento.lower()} emitido por {empresa_nombre}.

Si tiene alguna inquietud sobre este documento, no dude en comunicarse con el área administrativa.

Cordialmente,
{empresa_nombre}

---
Documento generado automáticamente por GestorRH Colombia.
Este correo fue enviado desde {remitente}.
"""
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    # Adjuntar PDFs
    for ruta in rutas_pdf:
        p = Path(ruta)
        if p.exists():
            with open(p, "rb") as f:
                parte = MIMEApplication(f.read(), Name=p.name)
            parte["Content-Disposition"] = f'attachment; filename="{p.name}"'
            msg.attach(parte)

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from"], [destinatario_email], msg.as_string())
        return True, f"Correo enviado a {destinatario_email}"
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Error de autenticación SMTP. Verifica usuario y contraseña de aplicación."
        )
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {e}"
    except Exception as e:
        return False, f"Error inesperado al enviar correo: {e}"


def instrucciones_gmail() -> str:
    return """
**Cómo configurar Gmail para envío automático:**

1. Entra a tu cuenta Google → Seguridad → Verificación en 2 pasos (actívala si no está)
2. En Seguridad → Contraseñas de aplicaciones → crea una para "GestorRH Colombia"
3. Copia la contraseña de 16 caracteres que genera Google
4. En Render → tu servicio → Environment → agrega:
   - `SMTP_HOST` = `smtp.gmail.com`
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = `tucorreo@gmail.com`
   - `SMTP_PASS` = `contraseña de 16 caracteres`
   - `SMTP_FROM` = `GestorRH Colombia <tucorreo@gmail.com>`
5. Guarda y redespliega. Listo.
"""
