import smtplib
import logging
from email.mime.text import MIMEText

_logger = logging.getLogger("pm_os")


def is_smtp_configured(cfg: dict) -> bool:
    host = cfg.get("smtp_host", "")
    user = cfg.get("smtp_user", "")
    return bool(host and user)


def _send_email(cfg: dict, to_email: str, subject: str, body: str) -> bool:
    host = cfg.get("smtp_host", "")
    port_str = cfg.get("smtp_port", "587")
    user = cfg.get("smtp_user", "")
    password = cfg.get("smtp_password", "")
    from_email = cfg.get("smtp_from_email", user)
    from_name = cfg.get("smtp_from_name", "PM Studio")

    if not host or not user:
        _logger.warning("SMTP not configured, skipping email to %s", to_email)
        return False

    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 587

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        _logger.info("Account email sent to %s", to_email)
        return True
    except Exception:
        _logger.exception("Failed to send account email to %s", to_email)
        return False


def send_verification_email(cfg: dict, to_email: str, code: str) -> bool:
    from_name = cfg.get("smtp_from_name", "PM Studio")
    return _send_email(
        cfg,
        to_email,
        f"{from_name} — Código de verificação",
        f"""Olá,

Seu código de verificação do PM Studio é:

    {code}

Este código expira em 10 minutos.

Se você não solicitou este código, ignore este email.
""",
    )


def send_password_reset_email(cfg: dict, to_email: str, reset_url: str) -> bool:
    from_name = cfg.get("smtp_from_name", "PM Studio")
    return _send_email(
        cfg,
        to_email,
        f"{from_name} — Redefinição de senha",
        f"""Olá,

Use o link abaixo para redefinir sua senha:

{reset_url}

O link expira em 30 minutos e só pode ser usado uma vez.

Se você não solicitou esta alteração, ignore este email.
""",
    )
