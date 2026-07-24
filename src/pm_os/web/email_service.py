import logging
import smtplib
import ssl
from email.utils import formataddr
from email.mime.text import MIMEText
from typing import Optional

_logger = logging.getLogger("pm_os")
_SMTP_TIMEOUT_SECONDS = 15


def _smtp_port(cfg: dict) -> Optional[int]:
    try:
        port = int(cfg.get("smtp_port", "587"))
    except (ValueError, TypeError):
        return None
    return port if 1 <= port <= 65535 else None


def _safe_header(value: object) -> Optional[str]:
    text = str(value or "").strip()
    if not text or "\r" in text or "\n" in text:
        return None
    return text


def _masked_recipient(email: str) -> str:
    _, separator, domain = email.rpartition("@")
    return f"***@{domain}" if separator and domain else "***"


def is_smtp_configured(cfg: dict) -> bool:
    host = _safe_header(cfg.get("smtp_host", ""))
    user = _safe_header(cfg.get("smtp_user", ""))
    return bool(host and user and _smtp_port(cfg) is not None)


def _send_email(cfg: dict, to_email: str, subject: str, body: str) -> bool:
    host = _safe_header(cfg.get("smtp_host", ""))
    port = _smtp_port(cfg)
    user = _safe_header(cfg.get("smtp_user", ""))
    password = cfg.get("smtp_password", "")
    from_email = _safe_header(cfg.get("smtp_from_email", user))
    from_name = _safe_header(cfg.get("smtp_from_name", "PM Studio"))
    recipient = _safe_header(to_email)
    safe_subject = _safe_header(subject)
    masked_recipient = _masked_recipient(to_email)

    if not host or port is None or not user:
        _logger.warning("SMTP not configured, skipping account email")
        return False
    if not from_email or not from_name or not recipient or not safe_subject:
        _logger.warning("Invalid account email headers for %s", masked_recipient)
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = safe_subject
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = recipient
    tls_context = ssl.create_default_context()

    try:
        if port == 465:
            with smtplib.SMTP_SSL(
                host,
                port,
                timeout=_SMTP_TIMEOUT_SECONDS,
                context=tls_context,
            ) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(
                host,
                port,
                timeout=_SMTP_TIMEOUT_SECONDS,
            ) as server:
                server.starttls(context=tls_context)
                server.login(user, password)
                server.send_message(msg)
        _logger.info("Account email sent to %s", masked_recipient)
        return True
    except Exception:
        _logger.exception("Failed to send account email to %s", masked_recipient)
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
