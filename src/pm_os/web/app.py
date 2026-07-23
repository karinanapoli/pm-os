import hashlib
import os
import re
import json
import shutil
import uuid
import urllib.parse
import time
import yaml
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse
from jinja2 import pass_context

from pm_os.bootstrap import (
    create_change_tracker,
    create_prd_validator,
)
from pm_os.infrastructure.ai.clients.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
)
from pm_os.infrastructure.ai.clients.openai_client import OpenAIClient
from pm_os.infrastructure.ai.clients.anthropic_client import AnthropicClient
from pm_os.infrastructure.ai.clients.fake_ai_client import FakeAIClient
from pm_os.infrastructure.security import hash_password, password_is_strong, verify_password
from pm_os.contracts.workflow_contracts import AIClient
from pm_os.domain.initiative import Initiative
from pm_os.domain.context_source import ContextSource
from pm_os.infrastructure.validators.prd_validator import PRDValidator
from pm_os.infrastructure.utils import (
    ALLOWED_EXTENSIONS,
    read_validation_history,
    read_validation_score_from_file,
    version_file,
)
from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.repositories.job_repository import JobRepository
from pm_os.workflows.workspace_scan_workflow import WorkspaceScanWorkflow
from pm_os.context_builder import ContextBuilder
from pm_os.prompt_builder import PromptBuilder
from pm_os.web.config_manager import ConfigManager
from pm_os.web.i18n import t as _t, LANGS
from pm_os.web.markdown_renderer import render_safe_markdown
from pm_os.web.product_docs_service import ProductDocsService
from pm_os.web.safe_http import fetch_public_url, validate_public_url
from pm_os.writers.markdown_writer import MarkdownWriter
import logging
_logger = logging.getLogger("pm_os")

_gen_executor = ThreadPoolExecutor(max_workers=2)

app = FastAPI(title="PM Studio")


# ─── Auth middleware (must be added before SessionMiddleware so it runs inside session scope) ───


# ─── CSRF (ASGI-level — buffers body so route handlers can still read it) ───

import secrets as _secrets_module

_CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_CSRF_EXCLUDED_PATHS = frozenset()

class _CSRFMiddleware:
    """ASGI middleware: buffers POST body, validates CSRF token, then passes body through."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")

        if "session" in scope and "csrf_token" not in scope["session"]:
            scope["session"]["csrf_token"] = _secrets_module.token_hex(32)

        if path.startswith("/static") or path in _CSRF_EXCLUDED_PATHS or method in _CSRF_SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        if os.environ.get("PM_OS_ENV") == "test":
            await self.app(scope, receive, send)
            return

        # Buffer the entire body
        chunks = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                chunks.append(message.get("body", b""))
                more_body = message.get("more_body", False)
        body_bytes = b"".join(chunks)

        # Validate CSRF token for all state-changing requests
        token = scope.get("session", {}).get("csrf_token", "")
        headers = dict(scope.get("headers", []))
        header_token = headers.get(b"x-csrf-token", b"").decode("utf-8", errors="replace")

        provided_token = header_token or _get_form_field(body_bytes, headers, "csrf_token")
        if not provided_token or not _secrets_module.compare_digest(token, provided_token):
            response_body = _t("csrf.invalid", _get_lang()).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"text/html; charset=utf-8"),
                    (b"content-length", str(len(response_body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": response_body})
            return

        # Pass body through to inner app
        async def receive_wrapper():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        await self.app(scope, receive_wrapper, send)


def _get_form_field(body_bytes: bytes, headers: dict, field: str) -> str:
    """Extract a single field from URL-encoded form data without consuming the body."""
    from urllib.parse import parse_qs
    ct = headers.get(b"content-type", b"").decode("utf-8", errors="replace")
    ct_lower = ct.lower()
    try:
        if "application/x-www-form-urlencoded" in ct_lower:
            params = parse_qs(body_bytes.decode("utf-8", errors="replace"))
            return params.get(field, [""])[0]
        if "multipart/form-data" in ct_lower:
            boundary_match = re.search(r'boundary="?([^";]+)', ct, re.IGNORECASE)
            if not boundary_match:
                return ""
            boundary = boundary_match.group(1).encode()
            marker = b'name="' + field.encode() + b'"'
            for part in body_bytes.split(b"--" + boundary):
                if marker in part:
                    _, _, value = part.partition(b"\r\n\r\n")
                    return value.rsplit(b"\r\n", 1)[0].decode("utf-8", errors="replace")
        return ""
    except Exception:
        return ""


# Persistent session key — survives server restarts
_session_key_path = Path(os.getenv("PM_OS_CONFIG_DIR", str(Path.home() / ".pm_os"))) / ".session_key"
_secret = os.getenv("PM_OS_SECRET")
if not _secret:
    if _session_key_path.exists():
        _secret = _session_key_path.read_text().strip()
        try:
            _session_key_path.chmod(0o600)
        except OSError:
            _logger.warning("Could not enforce permissions on the session key file.")
    else:
        _secret = os.urandom(64).hex()
        _session_key_path.parent.mkdir(parents=True, exist_ok=True)
        _session_key_path.write_text(_secret)
        try:
            _session_key_path.chmod(0o600)
        except OSError:
            _logger.warning("Could not enforce permissions on the session key file.")

class _NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if ct.startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        return response


app.add_middleware(_NoCacheMiddleware)
app.add_middleware(_CSRFMiddleware)


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)
        if request.url.path in ("/login", "/register", "/verify", "/verify/resend", "/forgot", "/reset"):
            return await call_next(request)
        if config_manager.get("auth_bypass_localhost", False):
            host = request.client.host if request.client else ""
            if host in ("127.0.0.1", "::1", "localhost"):
                # Auto-populate session so user_email is available for squads
                users = config_manager.get("users") or {}
                if not request.session.get("user_email"):
                    if users:
                        first_user = next(iter(users))
                        request.session["user_email"] = first_user
                        request.session["authenticated"] = True
                    else:
                        request.session["user_email"] = "local@localhost"
                        request.session["authenticated"] = True
                return await call_next(request)
        try:
            authenticated = request.session.get("authenticated")
            user_email = request.session.get("user_email")
        except (AssertionError, KeyError, RuntimeError):
            authenticated = False
            user_email = None
        users = config_manager.get("users") or {}
        if authenticated and user_email and user_email in users:
            return await call_next(request)
        if not users:
            return RedirectResponse(url="/register", status_code=302)
        return RedirectResponse(url="/login", status_code=302)


app.add_middleware(_AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=_secret,
    session_cookie="pm_os_session",
    same_site="lax",
    https_only=os.getenv("PM_OS_ENV") == "production",
)


_LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}
_MAX_LOGIN_ATTEMPTS = 10
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_ATTEMPTS_MAX_IPS = 1000


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_login_rate_limit(ip: str) -> None:
    now = datetime.now()
    if len(_LOGIN_ATTEMPTS) > _LOGIN_ATTEMPTS_MAX_IPS:
        cutoff = now - timedelta(seconds=_LOGIN_WINDOW_SECONDS)
        _LOGIN_ATTEMPTS.clear()
    attempts = _LOGIN_ATTEMPTS.get(ip, [])
    attempts = [t for t in attempts if (now - t).total_seconds() < _LOGIN_WINDOW_SECONDS]
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        _logger.warning("Rate limit hit for IP %s", ip)
        raise HTTPException(status_code=429, detail=_t("auth.rate_limit", _get_lang()))
    attempts.append(now)
    _LOGIN_ATTEMPTS[ip] = attempts

HERE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))

config_manager = ConfigManager()
job_repository = JobRepository()

# ALLOWED_EXTENSIONS imported from pm_os.infrastructure.utils


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    cfg = config_manager.get_all()
    if not cfg.get("users"):
        return RedirectResponse(url="/register", status_code=302)
    return templates.TemplateResponse("login.html", _ctx(request, error=error))


@app.post("/login")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    ip = _get_client_ip(request)
    _check_login_rate_limit(ip)
    cfg = config_manager.get_all()
    users = cfg.get("users") or {}
    valid, needs_rehash = verify_password(users.get(email, ""), password)
    if valid:
        if needs_rehash:
            users[email] = hash_password(password)
            config_manager.set("users", users)
        try:
            request.session["authenticated"] = True
            request.session["user_email"] = email
        except (AssertionError, KeyError, RuntimeError):
            pass
        _logger.info("Login success for '%s' from %s", email, ip)
        return RedirectResponse(url="/", status_code=302)
    _logger.warning("Login failed for '%s' from %s", email, ip)
    return await login_page(request, error=_t("auth.invalid_credentials", _get_lang()))


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = ""):
    try:
        authenticated = request.session.get("authenticated")
        user_email = request.session.get("user_email")
    except (AssertionError, KeyError, RuntimeError):
        authenticated = False
        user_email = None
    users = config_manager.get("users") or {}
    if authenticated and user_email and user_email in users:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("register.html", _ctx(request, error=error))


@app.post("/register")
async def register_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    cfg = config_manager.get_all()
    users = dict(cfg.get("users") or {})
    if email in users:
        return await register_page(request, error=_t("register.exists", _get_lang()))
    if not email or "@" not in email:
        return await register_page(request, error=_t("register.invalid_email", _get_lang()))
    if not password_is_strong(password):
        return await register_page(request, error=_t("register.short_password", _get_lang()))
    users[email] = hash_password(password)
    config_manager.set("users", users)
    config_manager.set("onboarding_dismissed", False)
    _logger.info("User registered: %s", email)

    from pm_os.web.email_service import is_smtp_configured, send_verification_email
    if is_smtp_configured(cfg):
        code = "".join(str(_secrets_module.randbelow(10)) for _ in range(6))
        try:
            request.session["verify_code"] = code
            request.session["verify_email"] = email
            request.session["verify_expires_at"] = time.time() + 600
        except Exception:
            pass
        sent = send_verification_email(cfg, email, code)
        return RedirectResponse(url=f"/verify?email={urllib.parse.quote(email)}&sent={'1' if sent else '0'}", status_code=302)

    return RedirectResponse(url="/login", status_code=302)


@app.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request, email: str = "", sent: str = ""):
    try:
        ses_email = request.session.get("verify_email", "")
    except Exception:
        ses_email = ""
    target = email or ses_email
    if not target:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("verify.html", _ctx(request, email=target, error="", sent=(sent == "1")))


@app.post("/verify")
async def verify_submit(request: Request, email: str = Form(...), code: str = Form(...)):
    try:
        stored_code = request.session.get("verify_code", "")
        stored_email = request.session.get("verify_email", "")
        expires_at = request.session.get("verify_expires_at", 0)
    except Exception:
        stored_code = ""
        stored_email = ""
    if not stored_email or stored_email != email or expires_at < time.time():
        return templates.TemplateResponse("verify.html", _ctx(request, email=email, error=_t("verify.expired", _get_lang()), sent=False))
    if not _secrets_module.compare_digest(stored_code, code.strip()):
        return templates.TemplateResponse("verify.html", _ctx(request, email=email, error=_t("verify.invalid", _get_lang()), sent=False))
    try:
        request.session.pop("verify_code", None)
        request.session.pop("verify_email", None)
        request.session.pop("verify_expires_at", None)
        request.session["verified"] = True
    except Exception:
        pass
    _logger.info("Email verified: %s", email)
    return await login_page(request, error=_t("verify.success", _get_lang()))


@app.post("/verify/resend")
async def verify_resend(request: Request, email: str = Form(...)):
    cfg = config_manager.get_all()
    from pm_os.web.email_service import is_smtp_configured, send_verification_email
    if not is_smtp_configured(cfg):
        return templates.TemplateResponse("verify.html", _ctx(request, email=email, error=_t("verify.no_smtp", _get_lang()), sent=False))
    code = "".join(str(_secrets_module.randbelow(10)) for _ in range(6))
    try:
        request.session["verify_code"] = code
        request.session["verify_email"] = email
        request.session["verify_expires_at"] = time.time() + 600
    except Exception:
        pass
    send_verification_email(cfg, email, code)
    return RedirectResponse(url=f"/verify?email={urllib.parse.quote(email)}&sent=1", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    try:
        request.session.pop("authenticated", None)
        request.session.pop("user_email", None)
    except (AssertionError, KeyError, RuntimeError):
        pass
    return RedirectResponse(url="/login", status_code=302)


# ─── Forgot Password ───


@app.get("/forgot", response_class=HTMLResponse)
async def forgot_page(request: Request, error: str = "", sent: str = ""):
    return templates.TemplateResponse("forgot.html", _ctx(request, error=error, sent=(sent == "1")))


@app.post("/forgot")
async def forgot_submit(request: Request, email: str = Form(...)):
    cfg = config_manager.get_all()
    users = cfg.get("users") or {}
    from pm_os.web.email_service import is_smtp_configured, send_password_reset_email
    if not is_smtp_configured(cfg):
        return await forgot_page(request, error=_t("forgot.no_smtp", _get_lang()))
    if email not in users:
        return await forgot_page(request, sent="1")
    token = _secrets_module.token_hex(32)
    reset_tokens = dict(cfg.get("reset_tokens") or {})
    reset_tokens[token] = {"email": email, "expires_at": time.time() + 1800}
    config_manager.set("reset_tokens", reset_tokens)
    reset_url = str(request.base_url).rstrip("/") + f"/reset?email={urllib.parse.quote(email)}&token={token}"
    sent = send_password_reset_email(cfg, email, reset_url)
    _logger.info("Password reset requested for %s", email)
    return RedirectResponse(
        url=f"/forgot?sent={'1' if sent else '0'}",
        status_code=302,
    )


@app.get("/reset", response_class=HTMLResponse)
async def reset_page(request: Request, email: str = "", token: str = "", code: str = "", error: str = ""):
    return templates.TemplateResponse(
        "reset.html",
        _ctx(request, email=email, token=token, sent=(code == "1"), error=error),
    )


@app.post("/reset")
async def reset_submit(request: Request, email: str = Form(...), token: str = Form(...), password: str = Form(...), confirm: str = Form(...)):
    cfg = config_manager.get_all()
    reset_tokens = cfg.get("reset_tokens") or {}
    stored = reset_tokens.get(token)
    if not stored or stored.get("email") != email or stored.get("expires_at", 0) < time.time():
        return await reset_page(request, email=email, token=token, error=_t("reset.invalid_token", _get_lang()))
    if password != confirm:
        return await reset_page(request, email=email, token=token, error=_t("reset.mismatch", _get_lang()))
    if not password_is_strong(password):
        return await reset_page(request, email=email, token=token, error=_t("reset.short_password", _get_lang()))
    users = dict(cfg.get("users") or {})
    if email not in users:
        return await reset_page(request, email=email, token=token, error=_t("forgot.not_found", _get_lang()))
    users[email] = hash_password(password)
    config_manager.set("users", users)
    del reset_tokens[token]
    config_manager.set("reset_tokens", reset_tokens)
    try:
        request.session.pop("reset_token", None)
        request.session.pop("reset_email", None)
    except Exception:
        pass
    _logger.info("Password reset completed for %s", email)
    return await login_page(request, error=_t("reset.success", _get_lang()))


# ─── i18n helper ───

def _get_lang() -> str:
    return config_manager.get("lang", "en")


def _get_session_squad(request: Request) -> str:
    try:
        return request.session.get("current_squad", "")
    except Exception:
        return ""


def _get_session_user_email(request: Request) -> str:
    try:
        return request.session.get("user_email", "")
    except Exception:
        return ""


def _product_docs_service(request: Request) -> ProductDocsService:
    squad_name = _get_session_squad(request)
    service = ProductDocsService(
        owner_email=_get_session_user_email(request),
        squad_name=squad_name,
    )
    # Safe automatic migration is limited to personal, single-user installations.
    if not squad_name and len(config_manager.get("users") or {}) <= 1:
        service.migrate_legacy_if_empty()
    return service


def _get_user_squads(email: str) -> list[str]:
    cfg = config_manager.get_all()
    squads = cfg.get("squads") or {}
    return [name for name, sq in squads.items() if email in sq.get("members", [])]


def _get_squad_names(cfg: dict) -> list[dict]:
    squads = cfg.get("squads") or {}
    return [{"name": k, "display_name": v.get("display_name", k), "member_count": len(v.get("members", []))} for k, v in squads.items()]


def _repo(squad_name: Optional[str] = None) -> InitiativeRepository:
    return InitiativeRepository(squad_name=squad_name)


@pass_context
def _t_filter(ctx, key: str) -> str:
    lang = ctx.get("lang", "en")
    return _t(key, lang)


templates.env.filters["t"] = _t_filter


def _markdown_filter(text: str) -> str:
    return render_safe_markdown(text)


templates.env.filters["markdown"] = _markdown_filter


def _ctx(request: Request, **extra: object) -> dict:
    """Build base context with i18n for every template."""
    cfg = config_manager.get_all()
    # Strip sensitive fields
    cfg.pop("users", None)
    cfg.pop("openai_api_key", None)
    cfg.pop("anthropic_api_key", None)
    cfg.pop("auth_password", None)
    cfg.pop("smtp_password", None)
    lang = cfg.get("lang", "en")
    try:
        user_email = request.session.get("user_email", "")
    except (AssertionError, KeyError, RuntimeError):
        user_email = ""
    try:
        current_squad = request.session.get("current_squad", "")
    except (AssertionError, KeyError, RuntimeError):
        current_squad = ""
    squads_all = cfg.get("squads") or {}
    user_squads_list = []
    for sk, sv in squads_all.items():
        if user_email in sv.get("members", []):
            user_squads_list.append({
                "name": sk,
                "display_name": sv.get("display_name", sk),
                "member_count": len(sv.get("members", [])),
                "is_admin": sv.get("created_by") == user_email,
            })
    base = {
        "request": request,
        "config": cfg,
        "lang": lang,
        "user_email": user_email,
        "current_squad": current_squad,
        "user_squads": user_squads_list,
        "csrf_token": "",
    }
    try:
        base["csrf_token"] = request.session.get("csrf_token", "")
    except (AssertionError, KeyError, RuntimeError):
        pass
    base.update(extra)
    return base


def _build_ai_client() -> AIClient:
    cfg = config_manager.get_all()
    provider = cfg.get("ai_provider", "ollama")
    if provider == "demo":
        return FakeAIClient()
    if provider == "openai":
        return OpenAIClient(
            model=cfg.get("openai_model", "gpt-4o-mini"),
            api_key=cfg.get("openai_api_key", ""),
        )
    if provider == "anthropic":
        return AnthropicClient(
            model=cfg.get("anthropic_model", "claude-3-haiku-20240307"),
            api_key=cfg.get("anthropic_api_key", ""),
        )
    for cp in cfg.get("custom_providers") or []:
        if cp.get("name") == provider:
            return OpenAIClient(
                model=cp.get("model", ""),
                api_key=cp.get("api_key", ""),
                base_url=cp.get("base_url", "https://api.openai.com/v1"),
            )
    return OllamaClient(
        model=cfg.get("model", "llama3.2"),
        base_url=cfg.get("ollama_url", "http://localhost:11434"),
    )


def _get_mcp_servers() -> list[dict]:
    return config_manager.get("mcp_servers") or []


def _validate_mcp_url(url: str) -> str:
    """Validate MCP URL structure before it is stored."""
    return validate_public_url(url, resolve_dns=False)


def _fetch_mcp_context() -> list[dict]:
    results = []
    for server in _get_mcp_servers():
        if not server.get("enabled"):
            continue
        name = server.get("name", "Unknown")
        url = server.get("url", "")
        if not url:
            continue
        try:
            raw_bytes, _ = fetch_public_url(url, timeout=5)
            raw = raw_bytes.decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
                if isinstance(data, (dict, list)):
                    content = json.dumps(data, indent=2, ensure_ascii=False)
                else:
                    content = str(data)
            except (json.JSONDecodeError, ValueError):
                content = raw
            content = content[:3000]
            if content.strip():
                digest = hashlib.sha256(f"mcp/{name}/{url}".encode("utf-8")).hexdigest()
                source = ContextSource(
                    source_id=f"SRC-{digest[:8].upper()}",
                    name=name,
                    content=content,
                    source_type="mcp",
                    confidentiality="internal",
                    size_bytes=len(content.encode("utf-8")),
                )
                results.append({
                    "name": name,
                    "content": ContextBuilder.build_sources([source]),
                })
        except Exception as exc:
            _logger.warning("MCP fetch failed for %s: %s", name, exc)
    return results


def _get_initiative_by_name(name: str, request_or_squad: Optional[Request] = None) -> Optional[Initiative]:
    if isinstance(request_or_squad, Request):
        squad_name = _get_session_squad(request_or_squad)
    else:
        squad_name = request_or_squad
    repo = InitiativeRepository(squad_name=squad_name)
    for i in repo.list_initiatives():
        if i.name == name:
            return i
    return None


def _get_initiative_by_name_sync(name: str, squad_name: Optional[str] = None) -> Optional[Initiative]:
    """Sync variant for background threads (no Request object)."""
    repo = InitiativeRepository(squad_name=squad_name)
    for i in repo.list_initiatives():
        if i.name == name:
            return i
    return None


# ─── Dashboard ───

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return await _dashboard(request, squad_name=_get_session_squad(request))


@app.post("/onboarding/dismiss", response_class=HTMLResponse)
async def dismiss_onboarding(request: Request):
    config_manager.set("onboarding_dismissed", True)
    return await dashboard(request)


@app.get("/onboarding/show", response_class=HTMLResponse)
async def show_onboarding(request: Request):
    config_manager.set("onboarding_dismissed", False)
    return await _dashboard(request, force_onboarding=True, squad_name=_get_session_squad(request))


async def _dashboard(request: Request, force_onboarding: bool = False, squad_name: Optional[str] = None) -> HTMLResponse:
    """Shared dashboard logic. force_onboarding ignores has_completed check."""
    repo = InitiativeRepository(squad_name=squad_name)
    initiatives = repo.list_initiatives()

    total_docs = 0
    has_prd = 0
    has_validation = 0
    total_score = 0.0
    scored_count = 0
    rows = []

    for init in initiatives:
        meta_path = init.path / "metadata.yaml"
        metadata = {}
        if meta_path.exists():
            try:
                metadata = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                metadata = {}
        score = read_validation_score_from_file(init.path / "artifacts" / "prd-validation.md")
        prd_exists = (init.path / "artifacts" / "prd.md").exists()
        if prd_exists:
            has_prd += 1

        if (init.path / "artifacts" / "prd-validation.md").exists():
            has_validation += 1

        ctx_dir = init.path / "context"
        doc_count = 0
        if ctx_dir.exists():
            doc_count = sum(1 for f in ctx_dir.iterdir() if f.is_file())
        total_docs += doc_count

        if score is not None:
            total_score += score
            scored_count += 1

        display_name = metadata.get("name", init.name) if metadata else init.name
        status = metadata.get("status", "unknown") if metadata else "unknown"
        score_str = f"{score}/10" if score is not None else "-"
        rows.append({
            "name": init.name,
            "display_name": display_name,
            "status": status,
            "owner": metadata.get("owner", "-") if metadata else "-",
            "score": score_str,
            "has_prd": prd_exists,
            "doc_count": doc_count,
        })

    avg_score = round(total_score / scored_count, 1) if scored_count > 0 else "-"

    lang = config_manager.get("lang", "en")
    today = date.today()
    attention_items = []
    for init in initiatives:
        meta_path = init.path / "metadata.yaml"
        meta = {}
        if meta_path.exists():
            try:
                meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                meta = {}
        score = read_validation_score_from_file(init.path / "artifacts" / "prd-validation.md")
        prd_exists = (init.path / "artifacts" / "prd.md").exists()
        display_name = meta.get("name", init.name) if meta else init.name
        created_raw = (meta or {}).get("created_at", "")
        age = 0
        if created_raw:
            try:
                if isinstance(created_raw, date):
                    created = created_raw
                else:
                    created = date.fromisoformat(created_raw)
                age = (today - created).days
            except (ValueError, TypeError):
                pass

        if not prd_exists and age > 7:
            attention_items.append({
                "name": init.name,
                "display_name": display_name,
                "reason": _t("attention.no_prd", lang),
                "action": "generate",
            })
        elif prd_exists and score is not None and score < 7:
            attention_items.append({
                "name": init.name,
                "display_name": display_name,
                "reason": _t("attention.low_score", lang),
                "action": "view",
            })

    archive_dir = repo.initiatives_path.parent / "archived"
    archived_count = 0
    if archive_dir.exists():
        archived_count = sum(1 for f in archive_dir.iterdir() if f.is_dir())

    dismissed = config_manager.get("onboarding_dismissed", False)
    has_completed = len(initiatives) > 0 and has_prd > 0 and has_validation > 0
    show_onboarding = (not dismissed and not has_completed) or force_onboarding

    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(request,
            initiatives=rows,
            total=len(rows),
            has_prd=has_prd,
            total_docs=total_docs,
            avg_score=avg_score,
            show_onboarding=show_onboarding,
            has_validation=has_validation,
            archived_count=archived_count,
            attention_items=attention_items,
        ),
    )


# ─── Quickstart ───

@app.post("/quickstart", response_class=HTMLResponse)
async def quickstart(request: Request) -> HTMLResponse:
    repo = _repo(_get_session_squad(request))
    init_id = "INT-QUICKSTART"
    base_path = repo.initiatives_path / init_id

    if base_path.exists():
        shutil.rmtree(base_path)

    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "artifacts").mkdir(exist_ok=True)
    (base_path / "context").mkdir(exist_ok=True)
    (base_path / "logs").mkdir(exist_ok=True)

    metadata = {
        "id": init_id,
        "name": _t("quickstart.name", _get_lang()),
        "status": "discovery",
        "squad": _get_session_squad(request),
        "created_at": str(date.today()),
        "artifacts": ["prd"],
        "workflows": ["create_prd"],
    }
    (base_path / "metadata.yaml").write_text(
        yaml.dump(metadata, default_flow_style=False, allow_unicode=True), encoding="utf-8"
    )

    fake_dir = Path(__file__).parent.parent.parent.parent / "fake-context"
    ctx_dir = base_path / "context"
    if fake_dir.exists():
        for f in fake_dir.iterdir():
            if f.is_file() and f.suffix in ALLOWED_EXTENSIONS:
                safe = _safe_filename(f.name)
                if safe:
                    shutil.copy2(str(f), str(ctx_dir / safe))

    tracker = create_change_tracker()
    tracker.update_manifest(str(base_path))

    try:
        ai_client = _build_ai_client()
        selected = _get_initiative_by_name(init_id, request)
        if selected and selected.documents:
            context_parts = []
            main_context = ContextBuilder().build(selected)
            if main_context.strip():
                context_parts.append(f"--- Contexto Principal: {selected.name} ---\n\n{main_context}")
            context = "\n\n".join(context_parts) if context_parts else ""
            prompt = PromptBuilder().build("create_prd", context, lang=_get_lang())
            prd_content = ai_client.generate(prompt)

            prd_path = str(selected.path / "artifacts" / "prd.md")
            (selected.path / "artifacts").mkdir(parents=True, exist_ok=True)
            MarkdownWriter().write(content=prd_content, output_path=prd_path)

            validator = create_prd_validator(ai_client=ai_client, lang=_get_lang())
            report = validator.validate(prd_content)
            report_path = str(selected.path / "artifacts" / "prd-validation.md")
            MarkdownWriter().write(content=report.to_markdown(lang=_get_lang()), output_path=report_path)

            tracker.update_manifest(str(selected.path))
    except OllamaConnectionError:
        _logger.warning("Quickstart: Ollama connection failed — PRD not generated.")

    return RedirectResponse(url="/initiative/INT-QUICKSTART?quickstart=1", status_code=303)


# ─── Initiative Detail ───

@app.get("/initiative/{initiative_name}", response_class=HTMLResponse)
async def initiative_detail(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    meta_path = selected.path / "metadata.yaml"
    metadata = {}
    if meta_path.exists():
        try:
            metadata = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            metadata = {}

    ctx_dir = selected.path / "context"
    docs = []
    if ctx_dir.exists():
        for f in sorted(ctx_dir.iterdir()):
            if f.is_file():
                size = f.stat().st_size
                size_str = f"{size} B" if size < 1024 else f"{size // 1024} KB"
                docs.append({"name": f.name, "size": size_str})

    prd_path = selected.path / "artifacts" / "prd.md"
    prd_exists = prd_path.exists()
    prd_content = prd_path.read_text(encoding="utf-8") if prd_exists else ""

    prd_versions = []
    artifacts_dir = selected.path / "artifacts"
    if artifacts_dir.exists():
        for f in sorted(artifacts_dir.iterdir(), reverse=True):
            if f.is_file() and f.name.startswith("prd-") and f.name.endswith(".md") and f.name != "prd.md":
                ts = f.stem.replace("prd-", "")
                prd_versions.append({"timestamp": ts, "filename": f.name, "size": f.stat().st_size})

    validation_score = "-"
    validation_report_content = ""
    report_path = selected.path / "artifacts" / "prd-validation.md"
    score = read_validation_score_from_file(report_path)
    validation_score = f"{score}/10" if score is not None else "-"
    if report_path.exists():
        try:
            validation_report_content = report_path.read_text(encoding="utf-8")
        except OSError:
            validation_report_content = ""

    is_quickstart = request.query_params.get("quickstart") == "1"

    return templates.TemplateResponse(
        "initiative_detail.html",
        _ctx(request,
            initiative=selected,
            initiative_display_name=metadata.get("name", selected.name),
            metadata=metadata,
            docs=docs,
            prd_exists=prd_exists,
            prd_content=prd_content,
            validation_score=validation_score,
            validation_report_content=validation_report_content,
            prd_versions=prd_versions,
            is_quickstart=is_quickstart,
            validation_history=read_validation_history(selected.path / "artifacts"),
        ),
    )


@app.get("/initiative/{initiative_name}/prd/download")
async def download_prd(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    prd_path = selected.path / "artifacts" / "prd.md"
    if not prd_path.exists():
        return HTMLResponse(_t("error.prd_not_found", _get_lang()), status_code=404)
    return FileResponse(
        str(prd_path),
        media_type="text/markdown",
        filename=f"{initiative_name}-prd.md",
    )


@app.post("/initiative/{initiative_name}/upload", response_class=HTMLResponse)
async def upload_context_doc(
    request: Request,
    initiative_name: str,
    docs: list[UploadFile] = File(...),
):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    ctx_dir = selected.path / "context"
    ctx_dir.mkdir(parents=True, exist_ok=True)

    uploaded = 0
    for doc in docs:
        if doc.filename:
            ext = Path(doc.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            safe_name = _safe_filename(doc.filename)
            if safe_name:
                content = await doc.read()
                if len(content) > 10 * 1024 * 1024:
                    continue
                (ctx_dir / safe_name).write_bytes(content)
                uploaded += 1

    if uploaded > 0:
        tracker = create_change_tracker()
        tracker.update_manifest(str(selected.path))

    return await initiative_detail(request, initiative_name)


@app.post("/initiative/{initiative_name}/delete-doc", response_class=HTMLResponse)
async def delete_context_doc(
    request: Request,
    initiative_name: str,
    filename: str = Form(...),
):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    safe_name = _safe_filename(filename)
    if safe_name:
        doc_path = (selected.path / "context" / safe_name).resolve()
        ctx_dir = (selected.path / "context").resolve()
        # Ensure the resolved path is still inside the context directory
        if str(doc_path).startswith(str(ctx_dir)) and doc_path.exists():
            doc_path.unlink()
            tracker = create_change_tracker()
            tracker.update_manifest(str(selected.path))

    return await initiative_detail(request, initiative_name)


# ─── PRD Version View ───

@app.get("/initiative/{initiative_name}/prd/{version}", response_class=HTMLResponse)
async def prd_version_view(request: Request, initiative_name: str, version: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    version_filename = f"prd-{version}.md"
    version_path = selected.path / "artifacts" / version_filename
    if not version_path.exists() or not version_path.is_file():
        # Try without .md extension
        version_filename = f"prd-{version}"
        version_path = selected.path / "artifacts" / version_filename
        if not version_path.exists() or not version_path.is_file():
            return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    content = version_path.read_text(encoding="utf-8")
    return templates.TemplateResponse(
        "initiative_detail.html",
        _ctx(request,
            initiative=selected,
            initiative_display_name=selected.name,
            metadata={},
            docs=[],
            prd_exists=True,
            prd_content=content,
            validation_score="-",
            version_label=version,
        ),
    )


# ─── New Initiative ───

@app.get("/initiatives/new", response_class=HTMLResponse)
async def new_initiative_page(request: Request):
    return templates.TemplateResponse(
        "initiative_new.html",
        _ctx(request),
    )


@app.post("/initiatives/new", response_class=HTMLResponse)
async def create_initiative(
    request: Request,
    name: str = Form(...),
    id: str = Form(""),
    status: str = Form("discovery"),
    context: str = Form(""),
):
    repo = _repo(_get_session_squad(request))

    init_id = id.strip()
    if not init_id:
        safe_name = re.sub(r'[^A-Z0-9]+', '-', name.strip().upper()).strip('-')
        init_id = f"INT-{safe_name[:30]}"
    else:
        if not re.match(r'^[A-Za-z0-9_-]+$', init_id):
            return templates.TemplateResponse(
                "initiative_new.html",
                _ctx(request, error=_t("initiative.new.invalid_id", _get_lang())),
            )
        init_id = init_id.strip('-_.')
        if not init_id:
            safe_name = re.sub(r'[^A-Z0-9]+', '-', name.strip().upper()).strip('-')
            init_id = f"INT-{safe_name[:30]}"

    base_path = repo.initiatives_path / init_id
    if base_path.exists():
        counter = 1
        while base_path.exists():
            suffixed = f"{init_id}-{counter:03d}"
            base_path = repo.initiatives_path / suffixed
            counter += 1
        init_id = base_path.name

    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "artifacts").mkdir(exist_ok=True)
    (base_path / "context").mkdir(exist_ok=True)
    (base_path / "logs").mkdir(exist_ok=True)

    metadata = {
        "id": init_id,
        "name": name.strip(),
        "status": status,
        "squad": _get_session_squad(request),
        "created_at": str(date.today()),
        "artifacts": ["prd"],
        "workflows": ["create_prd"],
    }
    meta_path = base_path / "metadata.yaml"
    meta_path.write_text(yaml.dump(metadata, default_flow_style=False, allow_unicode=True), encoding="utf-8")

    if context.strip():
        ctx_path = base_path / "context" / "context.md"
        ctx_path.write_text(context.strip(), encoding="utf-8")

    tracker = create_change_tracker()
    tracker.update_manifest(str(base_path))

    _logger.info("Initiative created: %s", init_id)
    return await dashboard(request)


# ─── Generate PRD ───

@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    repo = _repo(_get_session_squad(request))
    initiatives = repo.list_initiatives()
    pd_service = _product_docs_service(request)
    product_docs_count = pd_service.count_docs()
    selected_initiative = request.query_params.get("initiative", "")
    return templates.TemplateResponse(
        "generate.html",
        _ctx(request, initiatives=initiatives, result=None, error=None,
             product_docs_count=product_docs_count,
             mcp_count=len(_get_mcp_servers()),
             selected_initiative=selected_initiative),
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate_prd(
    request: Request,
    initiative_name: str = Form(...),
    additional_initiatives: list[str] = Form(default=[]),
    selected_source_ids: list[str] = Form(default=[]),
    source_selection_enabled: bool = Form(False),
    use_product_docs: bool = Form(False),
    use_mcp: bool = Form(False),
):
    repo = _repo(_get_session_squad(request))
    initiatives = repo.list_initiatives()

    selected = None
    for i in initiatives:
        if i.name == initiative_name:
            selected = i
            break

    if not selected:
        return templates.TemplateResponse(
            "generate.html",
            _ctx(request, initiatives=initiatives, result=None,
                 error=f"Initiative '{initiative_name}' {_t('error.not_found', _get_lang())}",
                 product_docs_count=0,
                 mcp_count=len(_get_mcp_servers())),
        )

    pd_service = _product_docs_service(request)
    additional = [n for n in additional_initiatives if n != initiative_name]
    selected_source_set = set(selected_source_ids)
    squad_name = _get_session_squad(request)
    owner_email = _get_session_user_email(request)

    # Kick off background generation task
    lang = _get_lang()

    def _set_step(step_idx: int, status: str, detail: str = ""):
        """Update step at index + keep task['step']/task['message'] for backward compat."""
        if 0 <= step_idx < 4:
            task["steps"][step_idx]["status"] = status
            task["steps"][step_idx]["detail"] = detail
            task["step"] = step_idx + 1
            task["message"] = detail
            job_repository.save(task_id, owner_email, squad_name, task)

    def _run_gen():
        """Runs PRD generation + validation in background thread, updating progress in _gen_tasks."""
        try:
            _set_step(0, "active", _t("generate.progress_context", lang))
            ai_client = _build_ai_client()

            context_parts = []
            main_context = (
                ContextBuilder().build_selected(selected, selected_source_set)
                if source_selection_enabled else ContextBuilder().build(selected)
            )
            if main_context.strip():
                context_parts.append(f"--- Contexto Principal: {selected.name} ---\n\n{main_context}")

            used_additional = []
            for add_name in additional:
                add_init = _get_initiative_by_name_sync(add_name, squad_name)
                if add_init and add_init.documents:
                    add_docs = (
                        ContextBuilder().build_selected(add_init, selected_source_set)
                        if source_selection_enabled else ContextBuilder().build(add_init)
                    )
                    if add_docs.strip():
                        context_parts.append(f"--- Contexto Adicional: {add_init.name} ---\n\n{add_docs}")
                        used_additional.append(add_name)

            used_product_docs = False
            if use_product_docs:
                pd_context = pd_service.build_context()
                if pd_context.strip():
                    context_parts.append(f"--- Documentação complementar ---\n\n{pd_context}")
                    used_product_docs = True

            used_mcp_servers = []
            if use_mcp:
                mcp_contexts = _fetch_mcp_context()
                for mc in mcp_contexts:
                    context_parts.append(f"--- Contexto MCP: {mc['name']} ---\n\n{mc['content']}")
                    used_mcp_servers.append(mc['name'])

            context = "\n\n".join(context_parts) if context_parts else ""

            _set_step(0, "done")
            _set_step(1, "active", _t("generate.progress_generating", lang))
            prompt = PromptBuilder().build("create_prd", context, lang=lang)

            _set_step(1, "done")
            _set_step(2, "active", detail="")
            prd_content = ai_client.generate(prompt)

            artifacts_dir = selected.path / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            version_file(artifacts_dir / "prd.md")
            version_file(artifacts_dir / "prd-validation.md")

            MarkdownWriter().write(content=prd_content, output_path=str(artifacts_dir / "prd.md"))

            _set_step(2, "done")
            _set_step(3, "active", _t("generate.progress_validating", lang))

            validator = PRDValidator(ai_client=ai_client, lang=lang)
            report = validator.validate(prd_content)

            report_path = str(artifacts_dir / "prd-validation.md")
            MarkdownWriter().write(content=report.to_markdown(lang=lang), output_path=report_path)

            tracker = create_change_tracker()
            tracker.update_manifest(str(selected.path))

            task["result"] = {
                "prd": prd_content,
                "score": report.overall_score,
                "sections": [asdict(section) for section in report.sections],
                "initiative": initiative_name,
                "additional": used_additional,
                "product_docs_used": used_product_docs,
                "mcp_used": used_mcp_servers,
                "source_ids": sorted(selected_source_set),
            }
            task["done"] = True
            task["steps"][3]["status"] = "done"
            task["step"] = 4
            job_repository.save(task_id, owner_email, squad_name, task)

        except OllamaConnectionError:
            task["error"] = _t("error.ollama", lang)
            task["done"] = True
            job_repository.save(task_id, owner_email, squad_name, task)
        except Exception as exc:
            _logger.exception("Background PRD generation failed")
            task["error"] = str(exc)
            task["done"] = True
            job_repository.save(task_id, owner_email, squad_name, task)

    task_id = uuid.uuid4().hex
    task = {
        "steps": [
            {"status": "pending", "detail": ""},
            {"status": "pending", "detail": ""},
            {"status": "pending", "detail": ""},
            {"status": "pending", "detail": ""},
        ],
        "step": 0,
        "message": _t("generate.progress_starting", lang),
        "done": False,
        "error": None,
        "result": None,
    }
    job_repository.create(task_id, owner_email, squad_name, task)

    _gen_executor.submit(_run_gen)

    # If called via fetch (JS stepper), return JSON; otherwise render fallback page
    if request.headers.get("x-requested-with") == "fetch":
        return JSONResponse({"job_id": task_id})

    pd_service = _product_docs_service(request)
    return templates.TemplateResponse(
        "generate_processing.html",
        _ctx(request,
             task_id=task_id,
             initiative_name=initiative_name,
             product_docs_count=pd_service.count_docs()),
    )


@app.get("/generate/status/{task_id}", response_class=JSONResponse)
async def generate_status(request: Request, task_id: str):
    task = job_repository.get_for_scope(
        task_id,
        _get_session_user_email(request),
        _get_session_squad(request),
    )
    if not task:
        return {"error": "not_found"}
    return {
        "steps": task["steps"],
        "step": task["step"],
        "message": task["message"],
        "done": task["done"],
        "error": task.get("error"),
    }


@app.get("/generate/result/{task_id}", response_class=HTMLResponse)
async def generate_result(request: Request, task_id: str):
    pd_service = _product_docs_service(request)
    task = job_repository.get_for_scope(
        task_id,
        _get_session_user_email(request),
        _get_session_squad(request),
    )
    is_fragment = request.query_params.get("fragment") == "1"

    if not task or not task.get("done"):
        if is_fragment:
            return _t("generate.error_not_ready", _get_lang())
        return templates.TemplateResponse(
            "generate.html",
            _ctx(request, initiatives=[], result=None,
                 error=_t("generate.error_not_ready", _get_lang()),
                 product_docs_count=pd_service.count_docs(),
                 mcp_count=len(_get_mcp_servers())),
        )

    if task.get("error"):
        if is_fragment:
            return templates.TemplateResponse(
                "generate_result_fragment.html",
                _ctx(request, result=None, error=task["error"]),
            )
        return templates.TemplateResponse(
            "generate.html",
            _ctx(request, initiatives=[], result=None,
                 error=task["error"],
                 product_docs_count=pd_service.count_docs(),
                 mcp_count=len(_get_mcp_servers())),
        )

    result = task["result"]
    if is_fragment:
        return templates.TemplateResponse(
            "generate_result_fragment.html",
            _ctx(request, result=result, error=None),
        )

    repo = _repo(_get_session_squad(request))
    initiatives = repo.list_initiatives()
    return templates.TemplateResponse(
        "generate.html",
        _ctx(request, initiatives=initiatives,
             result=result,
             error=None,
             product_docs_count=pd_service.count_docs(),
             mcp_count=len(_get_mcp_servers())),
    )


# ─── Validate PRD ───

@app.get("/validate/{initiative_name}", response_class=HTMLResponse)
async def validate_page(request: Request, initiative_name: str):
    repo = _repo(_get_session_squad(request))
    initiatives = repo.list_initiatives()

    selected = None
    for i in initiatives:
        if i.name == initiative_name:
            selected = i
            break

    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    prd_path = selected.path / "artifacts" / "prd.md"
    prd_content = prd_path.read_text(encoding="utf-8") if prd_path.exists() else ""

    validation_report_content = ""
    report_path = selected.path / "artifacts" / "prd-validation.md"
    if report_path.exists():
        try:
            validation_report_content = report_path.read_text(encoding="utf-8")
        except OSError:
            validation_report_content = ""

    return templates.TemplateResponse(
        "validate.html",
        _ctx(request, initiative=selected, report=None, error=None,
             validation_history=read_validation_history(selected.path / "artifacts"),
             prd_content=prd_content,
             validation_report_content=validation_report_content),
    )


@app.post("/validate/{initiative_name}", response_class=HTMLResponse)
async def validate_prd(request: Request, initiative_name: str):
    repo = _repo(_get_session_squad(request))

    selected = None
    for i in repo.list_initiatives():
        if i.name == initiative_name:
            selected = i
            break

    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    prd_path = selected.path / "artifacts" / "prd.md"

    form = await request.form()
    uploaded_file = form.get("prd_file")

    if uploaded_file and uploaded_file.filename and uploaded_file.filename != "":
        content_bytes = await uploaded_file.read()
        prd_path.parent.mkdir(parents=True, exist_ok=True)
        prd_path.write_bytes(content_bytes)

    if not prd_path.exists():
        return templates.TemplateResponse(
            "validate.html",
            _ctx(request, initiative=selected, report=None, error=_t("validate.no_prd", _get_lang()),
                 validation_history=read_validation_history(selected.path / "artifacts"),
                 prd_content=""),
        )

    previous_score = read_validation_score_from_file(selected.path / "artifacts" / "prd-validation.md")

    try:
        ai_client = _build_ai_client()
        validator = PRDValidator(ai_client=ai_client, lang=_get_lang())
        prd_content = prd_path.read_text(encoding="utf-8")
        report = validator.validate(prd_content)

        artifacts_dir = selected.path / "artifacts"
        version_file(artifacts_dir / "prd-validation.md")
        report_path = str(artifacts_dir / "prd-validation.md")
        MarkdownWriter().write(content=report.to_markdown(lang=_get_lang()), output_path=report_path)

        return templates.TemplateResponse(
            "validate.html",
            _ctx(request, initiative=selected, report=report, error=None,
                 previous_score=previous_score,
                 validation_history=read_validation_history(artifacts_dir),
                 prd_content=prd_content),
        )

    except OllamaConnectionError:
        return templates.TemplateResponse(
            "validate.html",
            _ctx(request, initiative=selected, report=None, error=_t("error.ollama", _get_lang()),
                 validation_history=read_validation_history(selected.path / "artifacts"),
                 prd_content=prd_content),
        )


@app.post("/validate/{initiative_name}/revalidate")
async def revalidate_prd(request: Request, initiative_name: str):
    """Re-validate a PRD and redirect back to initiative detail page."""
    repo = _repo(_get_session_squad(request))
    selected = None
    for i in repo.list_initiatives():
        if i.name == initiative_name:
            selected = i
            break
    if not selected:
        return RedirectResponse(url="/", status_code=302)
    prd_path = selected.path / "artifacts" / "prd.md"
    if not prd_path.exists():
        return RedirectResponse(url=f"/initiative/{initiative_name}", status_code=302)
    try:
        ai_client = _build_ai_client()
        validator = PRDValidator(ai_client=ai_client, lang=_get_lang())
        prd_content = prd_path.read_text(encoding="utf-8")
        report = validator.validate(prd_content)
        artifacts_dir = selected.path / "artifacts"
        version_file(artifacts_dir / "prd-validation.md")
        report_path = str(artifacts_dir / "prd-validation.md")
        MarkdownWriter().write(content=report.to_markdown(lang=_get_lang()), output_path=report_path)
    except OllamaConnectionError:
        pass
    return RedirectResponse(url=f"/initiative/{initiative_name}", status_code=302)


# ─── Config ───

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=False),
    )


@app.post("/config", response_class=HTMLResponse)
async def save_config(
    request: Request,
    model: str = Form(...),
    ollama_url: str = Form(...),
    lang: str = Form("en"),
    auth_enabled: str = Form(""),
    auth_bypass_localhost: str = Form(""),
    auth_username: str = Form(""),
    auth_password: str = Form(""),
    ai_provider: str = Form("ollama"),
    openai_api_key: str = Form(""),
    openai_model: str = Form(""),
    anthropic_api_key: str = Form(""),
    anthropic_model: str = Form(""),
    smtp_host: str = Form(""),
    smtp_port: str = Form("587"),
    smtp_user: str = Form(""),
    smtp_password: str = Form(""),
    smtp_from_email: str = Form(""),
    smtp_from_name: str = Form("PM Studio"),
):
    updates = {
        "model": model,
        "ollama_url": ollama_url,
        "lang": lang,
        "auth_enabled": auth_enabled == "true",
        "auth_bypass_localhost": auth_bypass_localhost == "true",
        "ai_provider": ai_provider,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_from_email": smtp_from_email,
        "smtp_from_name": smtp_from_name,
    }
    if auth_username:
        updates["auth_username"] = auth_username
    if auth_password:
        updates["auth_password"] = auth_password
    if ai_provider == "openai":
        if openai_api_key:
            updates["openai_api_key"] = openai_api_key
        if openai_model:
            updates["openai_model"] = openai_model
    if ai_provider == "anthropic":
        if anthropic_api_key:
            updates["anthropic_api_key"] = anthropic_api_key
        if anthropic_model:
            updates["anthropic_model"] = anthropic_model
    if smtp_password:
        updates["smtp_password"] = smtp_password
    config_manager.set_all(updates)
    _logger.info("Config updated by %s", request.client.host if request.client else "unknown")
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
    )


# ─── MCP Server Management ───


def _save_mcp_servers(servers: list[dict]):
    config_manager.set("mcp_servers", servers)


@app.post("/config/mcp/add", response_class=HTMLResponse)
async def add_mcp_server(
    request: Request,
    name: str = Form(...),
    url: str = Form(...),
):
    try:
        validated_url = _validate_mcp_url(url)
    except ValueError as e:
        return templates.TemplateResponse(
            "config.html",
            _ctx(request, saved=False, error=str(e)),
        )
    servers = _get_mcp_servers()
    if not any(s["url"] == validated_url for s in servers):
        servers.append({"name": name.strip(), "url": validated_url, "enabled": True})
        _save_mcp_servers(servers)
        _logger.info("MCP server added: %s", name.strip())
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
    )


@app.post("/config/mcp/toggle", response_class=HTMLResponse)
async def toggle_mcp_server(
    request: Request,
    url: str = Form(...),
):
    servers = _get_mcp_servers()
    for s in servers:
        if s["url"] == url:
            s["enabled"] = not s["enabled"]
            _logger.info("MCP server toggled: %s → %s", s["name"], "enabled" if s["enabled"] else "disabled")
            break
    _save_mcp_servers(servers)
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
    )


@app.post("/config/mcp/delete", response_class=HTMLResponse)
async def delete_mcp_server(
    request: Request,
    url: str = Form(...),
):
    removed = [s["name"] for s in _get_mcp_servers() if s["url"] == url]
    servers = [s for s in _get_mcp_servers() if s["url"] != url]
    _save_mcp_servers(servers)
    if removed:
        _logger.info("MCP server removed: %s", removed[0])
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
    )


@app.post("/config/mcp/test", response_class=HTMLResponse)
async def test_mcp_connection(request: Request, url: str = Form(...)):
    try:
        fetch_public_url(url, timeout=5)
        return HTMLResponse(
            f'<span style="color:var(--success);">✓ {_t("mcp.test_success", _get_lang())}</span>'
        )
    except ValueError as e:
        return HTMLResponse(
            f'<span style="color:var(--danger);">✗ {str(e)}</span>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<span style="color:var(--danger);">✗ {_t("mcp.test_fail", _get_lang())}: {str(e)[:80]}</span>'
        )


# ─── Custom Provider Management ───


def _get_custom_providers() -> list[dict]:
    return config_manager.get("custom_providers") or []


def _save_custom_providers(providers: list[dict]):
    config_manager.set("custom_providers", providers)


@app.post("/config/provider/add", response_class=HTMLResponse)
async def add_custom_provider(
    request: Request,
    name: str = Form(...),
    model: str = Form(...),
    api_key: str = Form(""),
    base_url: str = Form(...),
):
    providers = _get_custom_providers()
    # Avoid duplicates by name
    providers = [p for p in providers if p["name"] != name]
    providers.append({
        "name": name,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
    })
    _save_custom_providers(providers)
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
    )


@app.post("/config/provider/delete", response_class=HTMLResponse)
async def delete_custom_provider(
    request: Request,
    name: str = Form(...),
):
    providers = [p for p in _get_custom_providers() if p["name"] != name]
    _save_custom_providers(providers)
    # If the deleted provider was selected, reset to ollama
    if config_manager.get("ai_provider") == name:
        config_manager.set("ai_provider", "ollama")
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
    )


@app.post("/config/delete-account", response_class=HTMLResponse)
async def delete_account(request: Request, email: str = Form(...)):
    cfg = config_manager.get_all()
    users = dict(cfg.get("users") or {})
    try:
        session_email = request.session.get("user_email", "")
    except Exception:
        session_email = ""
    if email != session_email:
        return await login_page(request, error=_t("auth.invalid_credentials", _get_lang()))
    if email not in users:
        return await login_page(request, error=_t("auth.invalid_credentials", _get_lang()))
    del users[email]
    config_manager.set("users", users)
    try:
        request.session.pop("authenticated", None)
        request.session.pop("user_email", None)
    except Exception:
        pass
    _logger.info("Account deleted: %s", email)
    return RedirectResponse(url="/register", status_code=302)


# ─── Delete Initiative ───

@app.post("/initiative/{initiative_name}/delete", response_class=HTMLResponse)
async def delete_initiative(request: Request, initiative_name: str):
    repo = _repo(_get_session_squad(request))
    selected = None
    for i in repo.list_initiatives():
        if i.name == initiative_name:
            selected = i
            break

    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    # Archive instead of permanent delete
    archive_base = repo.initiatives_path.parent / "archived"
    archive_base.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = archive_base / f"{initiative_name}_{timestamp}"

    if selected.path.exists():
        shutil.move(str(selected.path), str(archive_path))

        # Write archive metadata
        archive_meta = archive_path / ".archive_meta"
        archive_meta.write_text(
            f"archived_at: {timestamp}\noriginal_name: {initiative_name}\n",
            encoding="utf-8",
        )

    _logger.info("Initiative archived: %s", initiative_name)
    return await dashboard(request)


# ─── Consult Documentation (Q&A) ───

@app.get("/consult", response_class=HTMLResponse)
async def consult_page(request: Request):
    repo = _repo(_get_session_squad(request))
    names = repo.list_names()
    return templates.TemplateResponse(
        "consult.html",
        _ctx(request, initiative_names=names, selected_initiatives=names,
             question="", result=None, error=None,
             mcp_count=len(_get_mcp_servers())),
    )


@app.post("/consult", response_class=HTMLResponse)
async def consult_docs(
    request: Request,
    question: str = Form(...),
    initiatives: list[str] = Form(default=[]),
    use_product_docs: bool = Form(False),
    use_mcp: bool = Form(False),
):
    if not question.strip():
        repo = _repo(_get_session_squad(request))
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=initiatives or names,
                 question=question, result=None, error=_t("consult.empty_question", _get_lang()),
                 mcp_count=len(_get_mcp_servers())),
        )

    if not initiatives and not use_product_docs and not use_mcp:
        repo = _repo(_get_session_squad(request))
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=names,
                 question=question, result=None,
                 error=_t("consult.empty_selection", _get_lang()),
                 mcp_count=len(_get_mcp_servers())),
        )

    try:
        ai_client = _build_ai_client()
        repo = _repo(_get_session_squad(request))

        context_parts = []
        all_inits = repo.list_initiatives()
        for init in all_inits:
            if init.name in initiatives:
                if init.documents:
                    docs_text = ContextBuilder().build(init)
                    context_parts.append(f"--- Iniciativa: {init.name} ---\n\n{docs_text}")

        if use_product_docs:
            pd_context = _product_docs_service(request).build_context()
            if pd_context.strip():
                context_parts.append(f"--- Documentação complementar ---\n\n{pd_context}")

        used_mcp_servers = []
        if use_mcp:
            mcp_contexts = _fetch_mcp_context()
            for mc in mcp_contexts:
                context_parts.append(f"--- Contexto MCP: {mc['name']} ---\n\n{mc['content']}")
                used_mcp_servers.append(mc['name'])

        if not context_parts:
            docs_context = "Nenhum documento disponível."
        else:
            docs_context = "\n\n".join(context_parts)

        prompt = PromptBuilder().build("consult", docs_context, question)

        answer = ai_client.generate(prompt)

        # Extract references: initiative names + product docs mentioned
        references = []
        for name in initiatives:
            if name in answer:
                references.append({"initiative": name})
        if use_product_docs and ("Documentação complementar" in answer or "produto" in answer.lower()):
            references.append({"initiative": "Documentação complementar"})
        for mc_name in used_mcp_servers:
            if mc_name.lower() in answer.lower():
                references.append({"initiative": mc_name})

        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=[i.name for i in all_inits],
                 selected_initiatives=initiatives,
                 question=question,
                 result={
                     "answer": answer,
                     "initiatives": initiatives + (["Documentação complementar"] if use_product_docs else []) + (used_mcp_servers if use_mcp else []),
                     "references": references,
                     "mcp_used": used_mcp_servers,
                 },
                 error=None,
                 mcp_count=len(_get_mcp_servers())),
        )

    except OllamaConnectionError:
        repo = _repo(_get_session_squad(request))
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=initiatives,
                 question=question, result=None,
                 error=_t("error.ollama", _get_lang()),
                 mcp_count=len(_get_mcp_servers())),
        )


# ─── Product Documentation ───

# ─── Product Docs Routes ───

@app.get("/product-docs", response_class=HTMLResponse)
async def product_docs_page(request: Request):
    pd_service = _product_docs_service(request)
    docs = []
    ctx = pd_service.context_dir
    if ctx.exists():
        for f in sorted(ctx.iterdir()):
            if f.is_file():
                size = f.stat().st_size
                size_str = f"{size} B" if size < 1024 else f"{size // 1024} KB"
                docs.append({"name": f.name, "size": size_str})
    links = pd_service.load_links()
    return templates.TemplateResponse(
        "product_docs.html",
        _ctx(request, docs=docs, links=links),
    )


@app.post("/product-docs/upload", response_class=HTMLResponse)
async def upload_product_docs(
    request: Request,
    docs: list[UploadFile] = File(...),
):
    ctx = _product_docs_service(request).context_dir
    ctx.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        if doc.filename:
            ext = Path(doc.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            safe_name = _safe_filename(doc.filename)
            if safe_name:
                content = await doc.read()
                if len(content) > 10 * 1024 * 1024:
                    continue
                (ctx / safe_name).write_bytes(content)
    return await product_docs_page(request)


@app.post("/product-docs/add-link", response_class=HTMLResponse)
async def add_product_link(
    request: Request,
    title: str = Form(...),
    url: str = Form(...),
):
    pd_service = _product_docs_service(request)
    links = pd_service.load_links()
    links.append({"title": title.strip(), "url": url.strip()})
    pd_service.save_links(links)
    return await product_docs_page(request)


@app.post("/product-docs/delete-doc/{filename}", response_class=HTMLResponse)
async def delete_product_doc(request: Request, filename: str):
    pd_service = _product_docs_service(request)
    safe_name = _safe_filename(filename)
    if safe_name:
        fp = (pd_service.context_dir / safe_name).resolve()
        ctx_dir = pd_service.context_dir.resolve()
        if str(fp).startswith(str(ctx_dir)) and fp.exists() and fp.is_file():
            fp.unlink()
    return await product_docs_page(request)


@app.post("/product-docs/delete-link", response_class=HTMLResponse)
async def delete_product_link(
    request: Request,
    url: str = Form(...),
):
    pd_service = _product_docs_service(request)
    links = [l for l in pd_service.load_links() if l["url"] != url]
    pd_service.save_links(links)
    return await product_docs_page(request)


# ─── Timeline / Roadmap ───

@app.get("/timeline", response_class=HTMLResponse)
async def timeline_page(request: Request):
    return templates.TemplateResponse(
        "timeline.html",
        _ctx(request),
    )


# ─── Archived Initiatives ───

@app.get("/archived", response_class=HTMLResponse)
async def archived_page(request: Request):
    repo = _repo(_get_session_squad(request))
    archive_dir = repo.initiatives_path.parent / "archived"
    archived = []
    if archive_dir.exists():
        for f in sorted(archive_dir.iterdir(), reverse=True):
            if f.is_dir():
                archived_at = ""
                meta_file = f / ".archive_meta"
                if meta_file.exists():
                    for line in meta_file.read_text(encoding="utf-8").splitlines():
                        if line.startswith("archived_at:"):
                            archived_at = line.split(":", 1)[1].strip()
                archived.append({
                    "name": f.name,
                    "archived_at": archived_at,
                })
    return templates.TemplateResponse(
        "archived.html",
        _ctx(request, archived=archived),
    )


@app.post("/archived/restore", response_class=HTMLResponse)
async def restore_initiative(request: Request, name: str = Form(...)):
    repo = _repo(_get_session_squad(request))
    archive_dir = repo.initiatives_path.parent / "archived"
    # Prevent path traversal: reject names with parent dir components
    clean_name = Path(name).name
    if not clean_name:
        return await archived_page(request)
    src = archive_dir / clean_name
    if src.exists() and src.is_dir():
        # Extract original name from archive name (format: name_YYYYMMDD_HHMMSS)
        parts = clean_name.rsplit("_", 2)
        original_name = parts[0] if len(parts) >= 2 else clean_name
        dst = repo.initiatives_path / original_name
        if dst.exists():
            dst = repo.initiatives_path / f"{original_name}_restored"
        shutil.move(str(src), str(dst))
        tracker = create_change_tracker()
        tracker.update_manifest(str(dst))
        _logger.info("Initiative restored: %s → %s", clean_name, dst.name)
    return await archived_page(request)


# ─── Squad ───


@app.get("/squad", response_class=HTMLResponse)
async def squad_page(request: Request, error: str = ""):
    return templates.TemplateResponse("squad.html", _ctx(request, error=error))


@app.get("/squad/create", response_class=HTMLResponse)
async def squad_create_page(request: Request, error: str = ""):
    return templates.TemplateResponse("squad_create.html", _ctx(request, error=error))


@app.get("/squad/join", response_class=HTMLResponse)
async def squad_join_page(request: Request, error: str = ""):
    cfg = config_manager.get_all()
    squads_list = _get_squad_names(cfg)
    user_email = _get_session_user_email(request)
    available = [sq for sq in squads_list if user_email not in (cfg.get("squads", {}).get(sq["name"], {}).get("members", []))]
    return templates.TemplateResponse("squad_join.html", _ctx(request, squads=available, error=error))


@app.post("/squad/create")
async def squad_create(request: Request, name: str = Form(...), display_name: str = Form(""), password: str = Form(...)):
    cfg = config_manager.get_all()
    squads = dict(cfg.get("squads") or {})
    squad_key = name.strip().lower().replace(" ", "-")
    if not squad_key:
        return await squad_page(request, error=_t("squad.exists", _get_lang()))
    if squad_key in squads:
        return await squad_page(request, error=_t("squad.exists", _get_lang()))
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    squads[squad_key] = {
        "display_name": display_name.strip() or squad_key,
        "password_hash": hash_password(password),
        "members": [user_email],
        "created_by": user_email,
        "created_at": str(date.today()),
    }
    config_manager.set("squads", squads)
    try:
        request.session["current_squad"] = squad_key
    except Exception:
        pass
    _logger.info("Squad created: %s by %s", squad_key, user_email)
    return RedirectResponse(url="/", status_code=302)


@app.post("/squad/join")
async def squad_join(request: Request, name: str = Form(...), password: str = Form(...)):
    cfg = config_manager.get_all()
    squads = dict(cfg.get("squads") or {})
    squad_key = name.strip().lower().replace(" ", "-")
    if squad_key not in squads:
        return await squad_page(request, error=_t("squad.not_found", _get_lang()))
    sq = squads[squad_key]
    stored_hash = sq.get("password_hash", "")
    valid, needs_rehash = verify_password(stored_hash, password)
    if not valid:
        return await squad_page(request, error=_t("squad.wrong_password", _get_lang()))
    if needs_rehash:
        sq["password_hash"] = hash_password(password)
        config_manager.set("squads", squads)
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    if user_email in sq.get("members", []):
        return await squad_page(request, error=_t("squad.already_member", _get_lang()))
    sq["members"].append(user_email)
    config_manager.set("squads", squads)
    try:
        request.session["current_squad"] = squad_key
    except Exception:
        pass
    _logger.info("Squad joined: %s by %s", squad_key, user_email)
    return RedirectResponse(url="/", status_code=302)


@app.get("/squad/select", response_class=HTMLResponse)
async def squad_select(request: Request, error: str = ""):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    user_squads = _get_user_squads(user_email)
    return templates.TemplateResponse("squad_select.html", _ctx(request, squads=user_squads, error=error))


@app.post("/squad/select")
async def squad_select_post(request: Request, squad: str = Form(...)):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    cfg = config_manager.get_all()
    squads = cfg.get("squads") or {}
    if squad not in squads or user_email not in squads[squad].get("members", []):
        return await squad_select(request, error=_t("squad.not_found", _get_lang()))
    try:
        request.session["current_squad"] = squad
    except Exception:
        pass
    return RedirectResponse(url="/", status_code=302)


@app.post("/squad/leave")
async def squad_leave(request: Request):
    try:
        user_email = request.session.get("user_email", "")
        current_squad = request.session.get("current_squad", "")
    except Exception:
        user_email = ""
        current_squad = ""
    if not user_email or not current_squad:
        return RedirectResponse(url="/", status_code=302)
    cfg = config_manager.get_all()
    squads = dict(cfg.get("squads") or {})
    sq = squads.get(current_squad)
    if sq and user_email in sq.get("members", []):
        sq["members"] = [m for m in sq["members"] if m != user_email]
        config_manager.set("squads", squads)
    try:
        request.session.pop("current_squad", None)
    except Exception:
        pass
    _logger.info("User %s left squad %s", user_email, current_squad)
    return RedirectResponse(url="/", status_code=302)


@app.get("/workspace/{squad_name}")
async def workspace_switch(request: Request, squad_name: str):
    if squad_name == "personal":
        try:
            request.session.pop("current_squad", None)
        except Exception:
            pass
        return RedirectResponse(url="/", status_code=302)
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    cfg = config_manager.get_all()
    squads = cfg.get("squads") or {}
    if squad_name not in squads or user_email not in squads[squad_name].get("members", []):
        return RedirectResponse(url="/", status_code=302)
    try:
        request.session["current_squad"] = squad_name
    except Exception:
        pass
    return RedirectResponse(url="/", status_code=302)


@app.get("/squad/admin/{squad_name}")
async def squad_admin_page(request: Request, squad_name: str):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    cfg = config_manager.get_all()
    squads = cfg.get("squads") or {}
    sq = squads.get(squad_name)
    if not sq or user_email not in sq.get("members", []):
        return RedirectResponse(url="/", status_code=302)
    is_admin = sq.get("created_by") == user_email
    return templates.TemplateResponse("squad_admin.html", _ctx(request, squad_name=squad_name, squad=sq, is_admin=is_admin))


@app.post("/squad/admin/{squad_name}/remove-member")
async def squad_remove_member(request: Request, squad_name: str, member_email: str = Form(...)):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    cfg = config_manager.get_all()
    squads = dict(cfg.get("squads") or {})
    sq = squads.get(squad_name)
    if not sq or sq.get("created_by") != user_email:
        return RedirectResponse(url="/", status_code=302)
    if member_email in sq["members"]:
        sq["members"] = [m for m in sq["members"] if m != member_email]
        config_manager.set("squads", squads)
    return RedirectResponse(url=f"/squad/admin/{squad_name}", status_code=302)


@app.post("/squad/admin/{squad_name}/rename")
async def squad_rename(request: Request, squad_name: str, display_name: str = Form(...)):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    cfg = config_manager.get_all()
    squads = dict(cfg.get("squads") or {})
    sq = squads.get(squad_name)
    if not sq or sq.get("created_by") != user_email:
        return RedirectResponse(url="/", status_code=302)
    display_name = display_name.strip()
    if display_name:
        sq["display_name"] = display_name
        config_manager.set("squads", squads)
    return RedirectResponse(url=f"/squad/admin/{squad_name}", status_code=302)


@app.post("/squad/admin/{squad_name}/disband")
async def squad_disband(request: Request, squad_name: str):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    cfg = config_manager.get_all()
    squads = dict(cfg.get("squads") or {})
    sq = squads.get(squad_name)
    if not sq or sq.get("created_by") != user_email:
        return RedirectResponse(url="/", status_code=302)
    del squads[squad_name]
    config_manager.set("squads", squads)
    try:
        if request.session.get("current_squad") == squad_name:
            request.session.pop("current_squad", None)
    except Exception:
        pass
    return RedirectResponse(url="/", status_code=302)


# ─── Helpers ───

def _safe_filename(name: str) -> str:
    if not name:
        return ""
    import unicodedata
    normalized = unicodedata.normalize("NFKC", name)
    if "/" in normalized or "\\" in normalized or ".." in normalized:
        return ""
    clean = Path(normalized).name
    if not clean or clean in (".", ".."):
        return ""
    if not re.match(r'^[a-zA-Z0-9 _.\-()\[\]]+$', clean):
        return ""
    return clean
