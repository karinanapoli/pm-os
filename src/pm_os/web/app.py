import os
import json
import re
import shutil
import urllib.parse
import time
import yaml
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse
from jinja2 import pass_context

from pm_os.bootstrap import (
    create_change_tracker,
    create_prd_validator,
)
from pm_os.citation_verifier import extract_source_ids, verify_citations
from pm_os.infrastructure.ai.clients.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
)
from pm_os.infrastructure.ai.clients.openai_client import OpenAIClient
from pm_os.infrastructure.ai.clients.anthropic_client import AnthropicClient
from pm_os.infrastructure.ai.clients.fake_ai_client import FakeAIClient
from pm_os.infrastructure.ai.clients.gateway_client import GatewayClient
from pm_os.infrastructure.security import hash_password, password_is_strong, verify_password
from pm_os.contracts.workflow_contracts import AIClient, AIProviderError
from pm_os.domain.initiative import Initiative
from pm_os.infrastructure.validators.prd_validator import PRDValidator
from pm_os.infrastructure.utils import (
    ALLOWED_EXTENSIONS,
    read_validation_history,
    read_validation_score_from_file,
    safe_upload_filename,
)
from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.repositories.job_repository import JobRepository
from pm_os.workflows.workspace_scan_workflow import WorkspaceScanWorkflow
from pm_os.context_builder import ContextBuilder
from pm_os.prompt_builder import PromptBuilder
from pm_os.web.config_manager import ConfigManager
from pm_os.web import config_operations as config_ops
from pm_os.web.i18n import t as _t, LANGS
from pm_os.web.account_tokens import prune_expired, token_digest
from pm_os.web.login_security import LoginRateLimiter, resolve_client_ip
from pm_os.web.squad_access import authorized_squad, normalize_squad_key
from pm_os.web.markdown_renderer import render_safe_markdown
from pm_os.web.middleware import AuthMiddleware, CSRFMiddleware, NoCacheMiddleware
from pm_os.web.product_docs_service import ProductDocsService
from pm_os.web.prd_validation_service import PRDValidationService
from pm_os.web.generation_job_service import GenerationJobService
from pm_os.web.prd_generation_operation import (
    PRDGenerationOperation,
    PRDGenerationRequest,
)
from pm_os.web.product_consultation_service import ProductConsultationService
from pm_os.web.product_specification_service import (
    ProductSpecificationService,
    SPECIFICATION_FIELDS,
)
from pm_os.web.mcp_context_service import MCPContextService
from pm_os.web.mcp_client import MCPAuthorizationRequired, MCPClient, MCPError
from pm_os.web.mcp_connections import (
    build_connection,
    businessmap_endpoint,
    normalize_connection,
    public_connection,
    sanitize_capabilities,
)
from pm_os.web.initiative_lifecycle_service import (
    InitiativeLifecycleService,
    InvalidInitiativeId,
)
from pm_os.web.public_urls import allowed_hosts_from_env, external_base_url
from pm_os.web.request_limits import (
    MAX_UPLOAD_FILE_BYTES,
    RequestBodyLimitMiddleware,
)
from pm_os.web.safe_http import fetch_public_url, validate_public_url
from pm_os.writers.markdown_writer import MarkdownWriter
import logging
_logger = logging.getLogger("pm_os")

_gen_executor = ThreadPoolExecutor(max_workers=2)
product_specification_service = ProductSpecificationService()

app = FastAPI(title="PM Studio")


import secrets as _secrets_module

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

app.add_middleware(NoCacheMiddleware)
app.add_middleware(
    CSRFMiddleware,
    error_message=lambda: _t("csrf.invalid", _get_lang()),
)
app.add_middleware(
    AuthMiddleware,
    config_get=lambda key, default=None: config_manager.get(key, default),
)
app.add_middleware(
    SessionMiddleware,
    secret_key=_secret,
    session_cookie="pm_os_session",
    same_site="lax",
    https_only=os.getenv("PM_OS_ENV") == "production",
)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts_from_env(os.getenv("PM_OS_ALLOWED_HOSTS", "")),
    www_redirect=False,
)


_login_rate_limiter = LoginRateLimiter()
_MAX_VERIFICATION_ATTEMPTS = 5
_VERIFICATION_RESEND_SECONDS = 60


def _get_client_ip(request: Request) -> str:
    remote_address = request.client.host if request.client else "unknown"
    try:
        trusted_proxy_count = max(
            0,
            min(10, int(os.getenv("PM_OS_TRUSTED_PROXY_COUNT", "0"))),
        )
    except ValueError:
        trusted_proxy_count = 0
    return resolve_client_ip(
        remote_address,
        request.headers.get("X-Forwarded-For", ""),
        trusted_proxy_count,
    )


def _check_login_rate_limit(ip: str) -> None:
    if _login_rate_limiter.is_blocked(ip):
        _logger.warning("Rate limit hit for IP %s", ip)
        raise HTTPException(status_code=429, detail=_t("auth.rate_limit", _get_lang()))

HERE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))

config_manager = ConfigManager()
job_repository = JobRepository()
generation_job_service = GenerationJobService(job_repository, _gen_executor)

# ALLOWED_EXTENSIONS imported from pm_os.infrastructure.utils


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    cfg = config_manager.get_all()
    if not cfg.get("users"):
        return RedirectResponse(url="/register", status_code=302)
    return templates.TemplateResponse(request, "login.html", _ctx(request, error=error))


@app.post("/login")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    ip = _get_client_ip(request)
    _check_login_rate_limit(ip)
    cfg = config_manager.get_all()
    users = cfg.get("users") or {}
    valid, needs_rehash = verify_password(users.get(email, ""), password)
    if valid:
        _login_rate_limiter.reset(ip)
        if needs_rehash:
            upgraded_hash = hash_password(password)
            config_manager.transaction(
                lambda config: config_ops.rehash_user(
                    config,
                    email,
                    users.get(email, ""),
                    upgraded_hash,
                )
            )
        try:
            request.session["authenticated"] = True
            request.session["user_email"] = email
        except (AssertionError, KeyError, RuntimeError):
            pass
        _logger.info("Login success for '%s' from %s", email, ip)
        return RedirectResponse(url="/", status_code=302)
    _login_rate_limiter.record_failure(ip)
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
    return templates.TemplateResponse(request, "register.html", _ctx(request, error=error))


@app.post("/register")
async def register_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    cfg = config_manager.get_all()
    users = dict(cfg.get("users") or {})
    pending_registrations = prune_expired(
        dict(cfg.get("pending_registrations") or {}),
        time.time(),
    )
    if email in users or email in pending_registrations:
        return await register_page(request, error=_t("register.exists", _get_lang()))
    if not email or "@" not in email:
        return await register_page(request, error=_t("register.invalid_email", _get_lang()))
    if not password_is_strong(password):
        return await register_page(request, error=_t("register.short_password", _get_lang()))
    from pm_os.web.email_service import is_smtp_configured, send_verification_email
    if is_smtp_configured(cfg):
        code = "".join(str(_secrets_module.randbelow(10)) for _ in range(6))
        code_digest = token_digest(_secret, "verify", email, code)
        pending_record = {
            "password_hash": hash_password(password),
            "code_digest": code_digest,
            "expires_at": time.time() + 600,
            "attempts": 0,
            "last_sent_at": 0,
        }

        if not config_manager.transaction(
            lambda config: config_ops.reserve_registration(
                config,
                email,
                pending_record,
                time.time(),
            )
        ):
            return await register_page(
                request,
                error=_t("register.exists", _get_lang()),
            )
        try:
            request.session["verify_email"] = email
        except Exception:
            pass
        sent = send_verification_email(cfg, email, code)
        if sent:
            config_manager.transaction(
                lambda config: config_ops.mark_pending_sent(
                    config,
                    email,
                    code_digest,
                    time.time(),
                )
            )
        return RedirectResponse(url=f"/verify?email={urllib.parse.quote(email)}&sent={'1' if sent else '0'}", status_code=302)

    password_hash = hash_password(password)

    if not config_manager.transaction(
        lambda config: config_ops.create_local_user(
            config,
            email,
            password_hash,
            time.time(),
        )
    ):
        return await register_page(
            request,
            error=_t("register.exists", _get_lang()),
        )
    _logger.info("User registered: %s", email)
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
    error = _t("verify.send_failed", _get_lang()) if sent == "0" else ""
    return templates.TemplateResponse(request, "verify.html", _ctx(request, email=target, error=error, sent=(sent == "1")))


@app.post("/verify")
async def verify_submit(request: Request, email: str = Form(...), code: str = Form(...)):
    status = config_manager.transaction(
        lambda config: config_ops.complete_verification(
            config,
            email,
            code,
            _secret,
            time.time(),
            _MAX_VERIFICATION_ATTEMPTS,
        )
    )
    if status == "expired":
        return templates.TemplateResponse(request, "verify.html", _ctx(request, email=email, error=_t("verify.expired", _get_lang()), sent=False))
    if status != "verified":
        error_key = "verify.too_many" if status == "too_many" else "verify.invalid"
        error = _t(error_key, _get_lang())
        return templates.TemplateResponse(request, "verify.html", _ctx(request, email=email, error=error, sent=False))
    try:
        request.session.pop("verify_email", None)
    except Exception:
        pass
    _logger.info("Email verified: %s", email)
    return await login_page(request, error=_t("verify.success", _get_lang()))


@app.post("/verify/resend")
async def verify_resend(request: Request, email: str = Form(...)):
    cfg = config_manager.get_all()
    from pm_os.web.email_service import is_smtp_configured, send_verification_email
    if not is_smtp_configured(cfg):
        return templates.TemplateResponse(request, "verify.html", _ctx(request, email=email, error=_t("verify.no_smtp", _get_lang()), sent=False))
    now = time.time()
    code = "".join(str(_secrets_module.randbelow(10)) for _ in range(6))
    code_digest = token_digest(_secret, "verify", email, code)

    resend_status = config_manager.transaction(
        lambda config: config_ops.reserve_verification_resend(
            config,
            email,
            code_digest,
            now,
            now + 600,
            _VERIFICATION_RESEND_SECONDS,
        )
    )
    if resend_status == "expired":
        return templates.TemplateResponse(request, "verify.html", _ctx(request, email=email, error=_t("verify.expired", _get_lang()), sent=False))
    if resend_status == "wait":
        return templates.TemplateResponse(request, "verify.html", _ctx(request, email=email, error=_t("verify.wait", _get_lang()), sent=False))
    try:
        request.session["verify_email"] = email
    except Exception:
        pass
    sent = send_verification_email(cfg, email, code)
    if sent:
        config_manager.transaction(
            lambda config: config_ops.mark_pending_sent(
                config,
                email,
                code_digest,
                time.time(),
            )
        )
    return RedirectResponse(
        url=f"/verify?email={urllib.parse.quote(email)}&sent={'1' if sent else '0'}",
        status_code=302,
    )


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
    return templates.TemplateResponse(request, "forgot.html", _ctx(request, error=error, sent=(sent == "1")))


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
    digest = token_digest(_secret, "reset", email, token)
    reset_record = {"email": email, "expires_at": time.time() + 1800}

    config_manager.transaction(
        lambda config: config_ops.add_reset_token(
            config,
            digest,
            reset_record,
            time.time(),
        )
    )
    try:
        public_base_url = external_base_url(
            str(request.base_url),
            os.getenv("PM_OS_PUBLIC_URL", ""),
            production=os.getenv("PM_OS_ENV") == "production",
        )
    except ValueError:
        config_manager.transaction(
            lambda config: config_ops.remove_reset_token(config, digest)
        )
        _logger.error("Password reset public URL is invalid.")
        return await forgot_page(
            request,
            error=_t("forgot.invalid_public_url", _get_lang()),
        )
    reset_url = public_base_url + f"/reset?email={urllib.parse.quote(email)}&token={token}"
    sent = send_password_reset_email(cfg, email, reset_url)
    _logger.info("Password reset requested for %s", email)
    if not sent:
        config_manager.transaction(
            lambda config: config_ops.remove_reset_token(config, digest)
        )
        return await forgot_page(request, error=_t("forgot.send_failed", _get_lang()))
    return RedirectResponse(
        url="/forgot?sent=1",
        status_code=302,
    )


@app.get("/reset", response_class=HTMLResponse)
async def reset_page(request: Request, email: str = "", token: str = "", code: str = "", error: str = ""):
    return templates.TemplateResponse(
        request,
        "reset.html",
        _ctx(request, email=email, token=token, sent=(code == "1"), error=error),
    )


@app.post("/reset")
async def reset_submit(request: Request, email: str = Form(...), token: str = Form(...), password: str = Form(...), confirm: str = Form(...)):
    cfg = config_manager.get_all()
    reset_tokens = dict(cfg.get("reset_tokens") or {})
    digest = token_digest(_secret, "reset", email, token)
    stored_key = digest if digest in reset_tokens else token
    stored = reset_tokens.get(stored_key)
    if not stored or stored.get("email") != email or stored.get("expires_at", 0) < time.time():
        if stored and stored.get("expires_at", 0) < time.time():
            config_manager.transaction(
                lambda config: config_ops.remove_reset_token(
                    config,
                    stored_key,
                )
            )
        return await reset_page(request, email=email, token=token, error=_t("reset.invalid_token", _get_lang()))
    if password != confirm:
        return await reset_page(request, email=email, token=token, error=_t("reset.mismatch", _get_lang()))
    if not password_is_strong(password):
        return await reset_page(request, email=email, token=token, error=_t("reset.short_password", _get_lang()))
    users = dict(cfg.get("users") or {})
    if email not in users:
        return await reset_page(request, email=email, token=token, error=_t("forgot.not_found", _get_lang()))
    new_password_hash = hash_password(password)

    if not config_manager.transaction(
        lambda config: config_ops.complete_password_reset(
            config,
            email,
            stored_key,
            new_password_hash,
            time.time(),
        )
    ):
        return await reset_page(
            request,
            email=email,
            token=token,
            error=_t("reset.invalid_token", _get_lang()),
        )
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
        current_squad = request.session.get("current_squad", "")
    except Exception:
        return ""
    user_email = _get_session_user_email(request)
    squads = config_manager.get("squads") or {}
    allowed_squad = authorized_squad(current_squad, user_email, squads)
    if current_squad and not allowed_squad:
        try:
            request.session.pop("current_squad", None)
        except Exception:
            pass
    return allowed_squad


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
    cfg.pop("gateway_api_key", None)
    cfg.pop("auth_password", None)
    cfg.pop("smtp_password", None)
    cfg.pop("pending_registrations", None)
    cfg.pop("reset_tokens", None)
    cfg.pop("retired_squad_names", None)
    cfg.pop("squads", None)
    cfg["mcp_servers"] = [
        public_connection(server)
        for server in (cfg.get("mcp_servers") or [])
    ]
    lang = cfg.get("lang", "en")
    try:
        user_email = request.session.get("user_email", "")
    except (AssertionError, KeyError, RuntimeError):
        user_email = ""
    current_squad = _get_session_squad(request)
    squads_all = config_manager.get("squads") or {}
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


def _build_ai_client(provider_override: str = "") -> AIClient:
    cfg = config_manager.get_all()
    provider = provider_override or cfg.get("ai_provider", "ollama")
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
    if provider == "gateway":
        return GatewayClient(
            base_url=cfg.get("gateway_url", ""),
            provider=cfg.get("gateway_provider", ""),
            project_id=cfg.get("gateway_project_id", ""),
            identifier=cfg.get("gateway_identifier", ""),
            api_key=cfg.get("gateway_api_key", ""),
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


def _available_ai_providers() -> list[dict]:
    cfg = config_manager.get_all()
    providers = [
        {"id": "ollama", "label": f"Ollama · {cfg.get('model', 'llama3.2')}"},
        {"id": "demo", "label": "Demo · conteúdo ilustrativo"},
    ]
    if cfg.get("openai_api_key"):
        providers.append({
            "id": "openai",
            "label": f"OpenAI · {cfg.get('openai_model', 'gpt-4o-mini')}",
        })
    if cfg.get("anthropic_api_key"):
        providers.append({
            "id": "anthropic",
            "label": f"Anthropic · {cfg.get('anthropic_model', 'claude-3-haiku-20240307')}",
        })
    if cfg.get("gateway_url") and cfg.get("gateway_identifier"):
        providers.append({
            "id": "gateway",
            "label": f"Gateway · {cfg.get('gateway_identifier')}",
        })
    for provider in cfg.get("custom_providers") or []:
        if provider.get("name") and provider.get("api_key"):
            providers.append({
                "id": provider["name"],
                "label": f"{provider['name']} · {provider.get('model', '')}",
            })
    return providers


def _validate_gateway_config(
    url: str,
    provider: str,
    project_id: str,
    identifier: str,
) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(_t("gateway.invalid_url", _get_lang()))
    if not all(value.strip() for value in (
        provider,
        project_id,
        identifier,
    )):
        raise ValueError(_t("gateway.required_fields", _get_lang()))


def _build_prd_validation_service(lang: str) -> PRDValidationService:
    validator = PRDValidator(ai_client=_build_ai_client(), lang=lang)
    return PRDValidationService(validator=validator, lang=lang)


def _get_mcp_servers() -> list[dict]:
    return [
        normalize_connection(server)
        for server in (config_manager.get("mcp_servers") or [])
    ]


def _validate_mcp_url(url: str) -> str:
    """Validate MCP URL structure before it is stored."""
    return validate_public_url(url, resolve_dns=False)


def _get_mcp_context_servers() -> list[dict]:
    return [
        server
        for server in _get_mcp_servers()
        if server.get("type") == "legacy_http"
    ]


def _fetch_mcp_context() -> list[dict]:
    return MCPContextService(fetcher=fetch_public_url).fetch(
        _get_mcp_context_servers()
    )


def _get_initiative_by_name(name: str, request_or_squad: Optional[Request] = None) -> Optional[Initiative]:
    if isinstance(request_or_squad, Request):
        squad_name = _get_session_squad(request_or_squad)
    else:
        squad_name = request_or_squad
    repo = InitiativeRepository(squad_name=squad_name)
    return repo.get(name)


def _get_initiative_by_name_sync(name: str, squad_name: Optional[str] = None) -> Optional[Initiative]:
    """Sync variant for background threads (no Request object)."""
    repo = InitiativeRepository(squad_name=squad_name)
    return repo.get(name)


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
    initiatives = repo.list_initiatives(load_content=False)

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

        doc_count = init.document_count
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
        request,
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
async def initiative_detail(
    request: Request,
    initiative_name: str,
    notice: str = "",
    notice_kind: str = "success",
):
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
    specification = product_specification_service.load(selected.path)

    return templates.TemplateResponse(
        request,
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
            notice=notice,
            notice_kind=notice_kind,
            specification=specification,
            specification_completion=product_specification_service.completion(specification),
        ),
    )


@app.get("/initiative/{initiative_name}/specification", response_class=HTMLResponse)
async def specification_page(
    request: Request,
    initiative_name: str,
    notice: str = "",
    notice_kind: str = "success",
):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    specification = product_specification_service.load(selected.path)
    artifacts = specification.get("artifacts") or {}
    return templates.TemplateResponse(
        request,
        "initiative_specification.html",
        _ctx(
            request,
            initiative=selected,
            specification=specification,
            specification_fields=SPECIFICATION_FIELDS,
            completion=product_specification_service.completion(specification),
            clarifications=product_specification_service.clarifications(
                specification,
                _get_lang(),
            ),
            consistency_findings=product_specification_service.analyze(
                specification,
                _get_lang(),
            ),
            history=product_specification_service.history(selected.path),
            backlog_exists=(selected.path / "artifacts" / "backlog.md").exists(),
            prd_exists=(selected.path / "artifacts" / "prd.md").exists(),
            artifacts=artifacts,
            available_sources=selected.sources,
            available_ai_providers=_available_ai_providers(),
            active_ai_provider=config_manager.get("ai_provider", "ollama"),
            notice=notice,
            notice_kind=notice_kind,
        ),
    )


@app.get("/initiative/{initiative_name}/deliverables", response_class=HTMLResponse)
async def initiative_deliverables(
    request: Request,
    initiative_name: str,
    notice: str = "",
    notice_kind: str = "success",
):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    specification = product_specification_service.load(selected.path)
    return templates.TemplateResponse(
        request,
        "initiative_deliverables.html",
        _ctx(
            request,
            initiative=selected,
            specification=specification,
            completion=product_specification_service.completion(specification),
            backlog_exists=(selected.path / "artifacts" / "backlog.md").exists(),
            prd_exists=(selected.path / "artifacts" / "prd.md").exists(),
            artifacts=specification.get("artifacts") or {},
            notice=notice,
            notice_kind=notice_kind,
        ),
    )


@app.post("/initiative/{initiative_name}/specification/prepare")
async def prepare_specification_from_context(
    request: Request,
    initiative_name: str,
    selected_source_ids: list[str] = Form(default=[]),
    ai_provider: str = Form(""),
):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    selected_ids = set(selected_source_ids)
    builder = ContextBuilder()
    context = (
        builder.build_selected(selected, selected_ids)
        if selected_ids else builder.build(selected)
    )
    if not context.strip():
        return RedirectResponse(
            url=f"/initiative/{initiative_name}/specification?notice=spec.prepare_no_context&notice_kind=error",
            status_code=303,
        )
    allowed_providers = {
        provider["id"] for provider in _available_ai_providers()
    }
    chosen_provider = ai_provider or config_manager.get("ai_provider", "ollama")
    if chosen_provider not in allowed_providers:
        return RedirectResponse(
            url=f"/initiative/{initiative_name}/specification?notice=spec.prepare_provider_unavailable&notice_kind=error",
            status_code=303,
        )
    try:
        prompt = PromptBuilder().build(
            "create_specification",
            context,
            lang=_get_lang(),
        )
        generated = _build_ai_client(chosen_provider).generate(prompt)
        product_specification_service.prepare_from_generated(
            selected.path,
            generated,
            source_ids=selected_ids or extract_source_ids(context),
            actor=_get_session_user_email(request),
        )
    except OllamaConnectionError:
        notice = "spec.prepare_ollama_error"
        notice_kind = "error"
    except AIProviderError:
        _logger.exception("AI provider failed while preparing specification")
        notice = "spec.prepare_provider_error"
        notice_kind = "error"
    except Exception:
        _logger.exception("Specification preparation failed")
        notice = "spec.prepare_error"
        notice_kind = "error"
    else:
        notice = "spec.prepared"
        notice_kind = "success"
    return RedirectResponse(
        url=(
            f"/initiative/{initiative_name}/specification"
            f"?notice={notice}&notice_kind={notice_kind}"
        ),
        status_code=303,
    )


@app.post("/initiative/{initiative_name}/specification")
async def save_specification(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    form = await request.form()
    sections = {
        field: str(form.get(field, ""))
        for field in SPECIFICATION_FIELDS
    }
    product_specification_service.save(
        selected.path,
        sections,
        source_ids=[source.source_id for source in selected.sources],
        actor=_get_session_user_email(request),
    )
    return RedirectResponse(
        url=f"/initiative/{initiative_name}/specification?notice=spec.saved",
        status_code=303,
    )


@app.post("/initiative/{initiative_name}/specification/approve")
async def approve_specification(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    try:
        product_specification_service.approve(
            selected.path,
            actor=_get_session_user_email(request),
        )
    except ValueError:
        return RedirectResponse(
            url=f"/initiative/{initiative_name}/specification?notice=spec.approve_error&notice_kind=error",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/initiative/{initiative_name}/specification?notice=spec.approved",
        status_code=303,
    )


@app.post("/initiative/{initiative_name}/decisions")
async def add_specification_decision(
    request: Request,
    initiative_name: str,
    title: str = Form(...),
    rationale: str = Form(...),
):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    try:
        product_specification_service.add_decision(
            selected.path,
            title=title,
            rationale=rationale,
            actor=_get_session_user_email(request),
        )
    except ValueError:
        return RedirectResponse(
            url=f"/initiative/{initiative_name}/specification?notice=spec.decision_error&notice_kind=error#decisions",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/initiative/{initiative_name}/specification?notice=spec.decision_saved#decisions",
        status_code=303,
    )


@app.post("/initiative/{initiative_name}/backlog/generate")
async def generate_specification_backlog(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    try:
        product_specification_service.generate_backlog(
            selected.path,
            actor=_get_session_user_email(request),
        )
    except ValueError:
        return RedirectResponse(
            url=f"/initiative/{initiative_name}/specification?notice=spec.backlog_error&notice_kind=error",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/initiative/{initiative_name}/specification?notice=spec.backlog_created",
        status_code=303,
    )


@app.get("/initiative/{initiative_name}/backlog/download")
async def download_backlog(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    path = selected.path / "artifacts" / "backlog.md"
    if not path.exists():
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    return FileResponse(
        str(path),
        media_type="text/markdown",
        filename=f"{initiative_name}-backlog.md",
    )


@app.get("/initiative/{initiative_name}/specification/download")
async def download_specification(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name, request)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    path = selected.path / "artifacts" / "specification.md"
    if not path.exists():
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    return FileResponse(
        str(path),
        media_type="text/markdown",
        filename=f"{initiative_name}-specification.md",
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
    rejected = 0
    for doc in docs:
        if doc.filename:
            ext = Path(doc.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                rejected += 1
                continue
            safe_name = _safe_filename(doc.filename)
            if safe_name:
                content = await doc.read(MAX_UPLOAD_FILE_BYTES + 1)
                if len(content) > MAX_UPLOAD_FILE_BYTES:
                    rejected += 1
                    continue
                (ctx_dir / safe_name).write_bytes(content)
                uploaded += 1
            else:
                rejected += 1

    if uploaded > 0:
        tracker = create_change_tracker()
        tracker.update_manifest(str(selected.path))

    if uploaded and rejected:
        return await initiative_detail(
            request,
            initiative_name,
            "initiative.detail.upload_partial",
            "warning",
        )
    if uploaded:
        return await initiative_detail(
            request,
            initiative_name,
            "initiative.detail.uploaded",
        )
    return await initiative_detail(
        request,
        initiative_name,
        "initiative.detail.upload_failed",
        "error",
    )


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
        request,
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
        request,
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
    experience_mode: str = Form("quick"),
):
    repo = _repo(_get_session_squad(request))
    service = InitiativeLifecycleService(repo, create_change_tracker)
    try:
        init_id = service.create(
            name=name,
            initiative_id=id,
            status=status,
            context=context,
            squad_name=_get_session_squad(request),
            experience_mode=experience_mode,
        )
    except InvalidInitiativeId:
        return templates.TemplateResponse(
            request,
            "initiative_new.html",
            _ctx(request, error=_t("initiative.new.invalid_id", _get_lang())),
        )
    _logger.info("Initiative created: %s", init_id)
    if experience_mode == "guided":
        return RedirectResponse(
            url=f"/initiative/{init_id}/specification",
            status_code=303,
        )
    return await dashboard(request)


# ─── Generate PRD ───

@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    repo = _repo(_get_session_squad(request))
    initiatives = repo.list_initiatives(load_content=False)
    pd_service = _product_docs_service(request)
    product_docs_count = pd_service.count_docs()
    selected_initiative = request.query_params.get("initiative", "")
    return templates.TemplateResponse(
        request,
        "generate.html",
        _ctx(request, initiatives=initiatives, result=None, error=None,
             product_docs_count=product_docs_count,
             mcp_count=len(_get_mcp_context_servers()),
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
    initiatives = repo.list_initiatives(load_content=False)
    selected = repo.get(initiative_name)

    if not selected:
        return templates.TemplateResponse(
            request,
            "generate.html",
            _ctx(request, initiatives=initiatives, result=None,
                 error=f"Initiative '{initiative_name}' {_t('error.not_found', _get_lang())}",
                 product_docs_count=0,
                 mcp_count=len(_get_mcp_context_servers())),
        )

    pd_service = _product_docs_service(request)
    additional = [n for n in additional_initiatives if n != initiative_name]
    selected_source_set = set(selected_source_ids)
    squad_name = _get_session_squad(request)
    owner_email = _get_session_user_email(request)

    # Kick off background generation task
    lang = _get_lang()

    operation = PRDGenerationOperation(
        ai_client_factory=_build_ai_client,
        initiative_loader=_get_initiative_by_name_sync,
        product_docs_service=pd_service,
        mcp_context_loader=_fetch_mcp_context,
        change_tracker_factory=create_change_tracker,
        translate=_t,
    )
    generation_request = PRDGenerationRequest(
        initiative_name=initiative_name,
        selected=selected,
        additional=additional,
        selected_source_ids=selected_source_set,
        source_selection_enabled=source_selection_enabled,
        use_product_docs=use_product_docs,
        use_mcp=use_mcp,
        squad_name=squad_name,
        lang=lang,
    )

    task_id = generation_job_service.start(
        owner_email,
        squad_name,
        _t("generate.progress_starting", lang),
        lambda job: operation.run(job, generation_request),
    )

    # If called via fetch (JS stepper), return JSON; otherwise render fallback page
    if request.headers.get("x-requested-with") == "fetch":
        return JSONResponse({"job_id": task_id})

    pd_service = _product_docs_service(request)
    return templates.TemplateResponse(
        request,
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
            request,
            "generate.html",
            _ctx(request, initiatives=[], result=None,
                 error=_t("generate.error_not_ready", _get_lang()),
                 product_docs_count=pd_service.count_docs(),
                 mcp_count=len(_get_mcp_context_servers())),
        )

    if task.get("error"):
        if is_fragment:
            return templates.TemplateResponse(
                request,
                "generate_result_fragment.html",
                _ctx(request, result=None, error=task["error"]),
            )
        return templates.TemplateResponse(
            request,
            "generate.html",
            _ctx(request, initiatives=[], result=None,
                 error=task["error"],
                 product_docs_count=pd_service.count_docs(),
                 mcp_count=len(_get_mcp_context_servers())),
        )

    result = task["result"]
    if is_fragment:
        return templates.TemplateResponse(
            request,
            "generate_result_fragment.html",
            _ctx(request, result=result, error=None),
        )

    repo = _repo(_get_session_squad(request))
    initiatives = repo.list_initiatives(load_content=False)
    return templates.TemplateResponse(
        request,
        "generate.html",
        _ctx(request, initiatives=initiatives,
             result=result,
             error=None,
             product_docs_count=pd_service.count_docs(),
             mcp_count=len(_get_mcp_context_servers())),
    )


# ─── Validate PRD ───

@app.get("/validate/{initiative_name}", response_class=HTMLResponse)
async def validate_page(request: Request, initiative_name: str):
    repo = _repo(_get_session_squad(request))
    selected = repo.get(initiative_name, load_content=False)

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
        request,
        "validate.html",
        _ctx(request, initiative=selected, report=None, error=None,
             validation_history=read_validation_history(selected.path / "artifacts"),
             prd_content=prd_content,
             validation_report_content=validation_report_content),
    )


@app.post("/validate/{initiative_name}", response_class=HTMLResponse)
async def validate_prd(request: Request, initiative_name: str):
    repo = _repo(_get_session_squad(request))

    selected = repo.get(initiative_name, load_content=False)

    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    prd_path = selected.path / "artifacts" / "prd.md"

    form = await request.form()
    uploaded_file = form.get("prd_file")

    if uploaded_file and uploaded_file.filename and uploaded_file.filename != "":
        content_bytes = await uploaded_file.read(MAX_UPLOAD_FILE_BYTES + 1)
        if len(content_bytes) > MAX_UPLOAD_FILE_BYTES:
            return templates.TemplateResponse(
                request,
                "validate.html",
                _ctx(
                    request,
                    initiative=selected,
                    report=None,
                    error=_t("upload.too_large", _get_lang()),
                    validation_history=read_validation_history(selected.path / "artifacts"),
                    prd_content=prd_path.read_text(encoding="utf-8") if prd_path.exists() else "",
                ),
                status_code=413,
            )
        prd_path.parent.mkdir(parents=True, exist_ok=True)
        prd_path.write_bytes(content_bytes)

    if not prd_path.exists():
        return templates.TemplateResponse(
            request,
            "validate.html",
            _ctx(request, initiative=selected, report=None, error=_t("validate.no_prd", _get_lang()),
                 validation_history=read_validation_history(selected.path / "artifacts"),
                 prd_content=""),
        )

    try:
        result = _build_prd_validation_service(_get_lang()).validate(prd_path)

        if not result.report.is_valid:
            return templates.TemplateResponse(
                request,
                "validate.html",
                _ctx(request, initiative=selected, report=None, error=result.report.summary,
                     validation_history=result.history,
                     prd_content=result.prd_content),
                status_code=502,
            )

        return templates.TemplateResponse(
            request,
            "validate.html",
            _ctx(request, initiative=selected, report=result.report, error=None,
                 previous_score=result.previous_score,
                 validation_history=result.history,
                 prd_content=result.prd_content),
        )

    except OllamaConnectionError:
        return templates.TemplateResponse(
            request,
            "validate.html",
            _ctx(request, initiative=selected, report=None, error=_t("error.ollama", _get_lang()),
                 validation_history=read_validation_history(selected.path / "artifacts"),
                 prd_content=prd_path.read_text(encoding="utf-8")),
        )


@app.post("/validate/{initiative_name}/revalidate")
async def revalidate_prd(request: Request, initiative_name: str):
    """Re-validate a PRD and redirect back to initiative detail page."""
    repo = _repo(_get_session_squad(request))
    selected = repo.get(initiative_name, load_content=False)
    if not selected:
        return RedirectResponse(url="/", status_code=302)
    prd_path = selected.path / "artifacts" / "prd.md"
    if not prd_path.exists():
        return RedirectResponse(url=f"/initiative/{initiative_name}", status_code=302)
    try:
        _build_prd_validation_service(_get_lang()).validate(prd_path)
    except OllamaConnectionError:
        pass
    return RedirectResponse(url=f"/initiative/{initiative_name}", status_code=302)


# ─── Config ───

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse(
        request,
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
    gateway_url: str = Form(""),
    gateway_provider: str = Form(""),
    gateway_project_id: str = Form(""),
    gateway_identifier: str = Form(""),
    gateway_api_key: str = Form(""),
    smtp_host: str = Form(""),
    smtp_port: str = Form("587"),
    smtp_user: str = Form(""),
    smtp_password: str = Form(""),
    smtp_from_email: str = Form(""),
    smtp_from_name: str = Form("PM Studio"),
):
    if ai_provider == "gateway":
        try:
            _validate_gateway_config(
                gateway_url,
                gateway_provider,
                gateway_project_id,
                gateway_identifier,
            )
        except ValueError as exc:
            return templates.TemplateResponse(
                request,
                "config.html",
                _ctx(request, saved=False, error=str(exc)),
                status_code=422,
            )
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
        "gateway_url": gateway_url.strip(),
        "gateway_provider": gateway_provider.strip(),
        "gateway_project_id": gateway_project_id.strip(),
        "gateway_identifier": gateway_identifier.strip(),
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
    if ai_provider == "gateway" and gateway_api_key:
        updates["gateway_api_key"] = gateway_api_key
    if smtp_password:
        updates["smtp_password"] = smtp_password
    config_manager.set_all(updates)
    _logger.info("Config updated by %s", request.client.host if request.client else "unknown")
    return templates.TemplateResponse(
        request,
        "config.html",
        _ctx(request, saved=False, notice="config.saved"),
    )


# ─── MCP Server Management ───

@app.post("/config/gateway/test", response_class=JSONResponse)
async def test_gateway_connection(
    request: Request,
    gateway_url: str = Form(...),
    gateway_provider: str = Form(...),
    gateway_project_id: str = Form(...),
    gateway_identifier: str = Form(...),
    gateway_api_key: str = Form(""),
):
    try:
        _validate_gateway_config(
            gateway_url,
            gateway_provider,
            gateway_project_id,
            gateway_identifier,
        )
        client = GatewayClient(
            base_url=gateway_url.strip(),
            provider=gateway_provider.strip(),
            project_id=gateway_project_id.strip(),
            identifier=gateway_identifier.strip(),
            api_key=(
                gateway_api_key
                or config_manager.get("gateway_api_key", "")
            ),
            timeout=15,
        )
        client.generate("Reply only with OK.")
        return JSONResponse({
            "ok": True,
            "message": _t("gateway.test_success", _get_lang()),
        })
    except (ValueError, AIProviderError) as exc:
        return JSONResponse(
            {"ok": False, "message": str(exc)},
            status_code=422,
        )


@app.post("/config/mcp/add", response_class=HTMLResponse)
async def add_mcp_server(
    request: Request,
    name: str = Form(...),
    url: str = Form(""),
    connection_type: str = Form("legacy_http"),
    preset: str = Form("custom"),
    businessmap_subdomain: str = Form(""),
    auth_type: str = Form("none"),
    auth_secret: str = Form(""),
    auth_header: str = Form(""),
    policy_mode: str = Form("read_only"),
    discovery_json: str = Form(""),
):
    try:
        if preset == "businessmap":
            url = businessmap_endpoint(businessmap_subdomain)
            auth_type = "oauth"
            connection_type = "mcp"
        validated_url = _validate_mcp_url(url)
        connection = build_connection(
            name=name,
            url=validated_url,
            connection_type=connection_type,
            preset=preset,
            auth_type=auth_type,
            auth_secret=auth_secret,
            auth_header=auth_header,
            policy_mode=policy_mode,
        )
        if discovery_json:
            connection["capabilities"] = sanitize_capabilities(
                json.loads(discovery_json)
            )
            connection["status"] = {
                "state": "connected",
                "message": "",
            }
    except (ValueError, json.JSONDecodeError) as e:
        return templates.TemplateResponse(
            request,
            "config.html",
            _ctx(request, saved=False, error=str(e)),
        )
    added = config_manager.transaction(
        lambda config: config_ops.add_mcp_server(
            config,
            connection,
        )
    )
    if added:
        _logger.info("MCP server added: %s", name.strip())
    return templates.TemplateResponse(
        request,
        "config.html",
        _ctx(request, saved=False, notice="config.mcp_added"),
    )


@app.post("/config/mcp/toggle", response_class=HTMLResponse)
async def toggle_mcp_server(
    request: Request,
    url: str = Form(...),
):
    toggled = config_manager.transaction(
        lambda config: config_ops.toggle_mcp_server(config, url)
    )
    if toggled:
        _logger.info("MCP server toggled: %s → %s", toggled[0], toggled[1])
    return templates.TemplateResponse(
        request,
        "config.html",
        _ctx(request, saved=False, notice="config.mcp_updated"),
    )


@app.post("/config/mcp/delete", response_class=HTMLResponse)
async def delete_mcp_server(
    request: Request,
    url: str = Form(...),
):
    removed = config_manager.transaction(
        lambda config: config_ops.remove_mcp_server(config, url)
    )
    if removed:
        _logger.info("MCP server removed: %s", removed)
    return templates.TemplateResponse(
        request,
        "config.html",
        _ctx(request, saved=False, notice="config.mcp_removed"),
    )


@app.post("/config/mcp/test", response_class=JSONResponse)
async def test_mcp_connection(
    request: Request,
    name: str = Form("MCP"),
    url: str = Form(""),
    connection_type: str = Form("mcp"),
    preset: str = Form("custom"),
    businessmap_subdomain: str = Form(""),
    auth_type: str = Form("none"),
    auth_secret: str = Form(""),
    auth_header: str = Form(""),
    policy_mode: str = Form("read_only"),
):
    try:
        if preset == "businessmap":
            url = businessmap_endpoint(businessmap_subdomain)
            auth_type = "oauth"
            connection_type = "mcp"
        validated_url = _validate_mcp_url(url)
        connection = build_connection(
            name=name,
            url=validated_url,
            connection_type=connection_type,
            preset=preset,
            auth_type=auth_type,
            auth_secret=auth_secret,
            auth_header=auth_header,
            policy_mode=policy_mode,
        )
        if connection_type == "legacy_http":
            fetch_public_url(validated_url, timeout=5)
            return JSONResponse({"ok": True, "message": _t("mcp.test_success", _get_lang())})
        discovery = MCPClient().discover(connection).as_dict()
        return JSONResponse({
            "ok": True,
            "message": _t("mcp.test_success", _get_lang()),
            "discovery": discovery,
        })
    except MCPAuthorizationRequired as exc:
        return JSONResponse({
            "ok": False,
            "authorization_required": True,
            "message": str(exc),
        }, status_code=401)
    except (ValueError, MCPError) as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=422)
    except Exception:
        _logger.exception("MCP connection test failed")
        return JSONResponse({
            "ok": False,
            "message": _t("mcp.test_fail", _get_lang()),
        }, status_code=502)


# ─── Custom Provider Management ───


@app.post("/config/provider/add", response_class=HTMLResponse)
async def add_custom_provider(
    request: Request,
    name: str = Form(...),
    model: str = Form(...),
    api_key: str = Form(""),
    base_url: str = Form(...),
):
    config_manager.transaction(
        lambda config: config_ops.upsert_custom_provider(
            config,
            {
                "name": name,
                "model": model,
                "api_key": api_key,
                "base_url": base_url,
            },
        )
    )
    return templates.TemplateResponse(
        request,
        "config.html",
        _ctx(request, saved=False, notice="config.provider_added"),
    )


@app.post("/config/provider/delete", response_class=HTMLResponse)
async def delete_custom_provider(
    request: Request,
    name: str = Form(...),
):
    config_manager.transaction(
        lambda config: config_ops.remove_custom_provider(config, name)
    )
    return templates.TemplateResponse(
        request,
        "config.html",
        _ctx(request, saved=False, notice="config.provider_removed"),
    )


@app.post("/config/delete-account", response_class=HTMLResponse)
async def delete_account(request: Request, email: str = Form(...)):
    try:
        session_email = request.session.get("user_email", "")
    except Exception:
        session_email = ""
    if email != session_email:
        return await login_page(request, error=_t("auth.invalid_credentials", _get_lang()))
    if email not in (config_manager.get("users") or {}):
        return await login_page(request, error=_t("auth.invalid_credentials", _get_lang()))

    config_manager.transaction(
        lambda config: config_ops.delete_user(config, email)
    )
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
    archived_name = InitiativeLifecycleService(
        repo, create_change_tracker
    ).archive(initiative_name)
    if not archived_name:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    _logger.info("Initiative archived: %s", initiative_name)
    return await dashboard(request)


# ─── Consult Documentation (Q&A) ───

@app.get("/consult", response_class=HTMLResponse)
async def consult_page(request: Request):
    repo = _repo(_get_session_squad(request))
    names = repo.list_names()
    return templates.TemplateResponse(
        request,
        "consult.html",
        _ctx(request, initiative_names=names, selected_initiatives=names,
             question="", result=None, error=None,
             mcp_count=len(_get_mcp_context_servers())),
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
            request,
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=initiatives or names,
                 question=question, result=None, error=_t("consult.empty_question", _get_lang()),
                 mcp_count=len(_get_mcp_context_servers())),
        )

    if not initiatives and not use_product_docs and not use_mcp:
        repo = _repo(_get_session_squad(request))
        names = repo.list_names()
        return templates.TemplateResponse(
            request,
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=names,
                 question=question, result=None,
                 error=_t("consult.empty_selection", _get_lang()),
                 mcp_count=len(_get_mcp_context_servers())),
        )

    try:
        ai_client = _build_ai_client()
        repo = _repo(_get_session_squad(request))
        all_names = repo.list_names()
        service = ProductConsultationService(
            ai_client=ai_client,
            initiative_repository=repo,
            product_docs_context_loader=_product_docs_service(request).build_context,
            mcp_context_loader=_fetch_mcp_context,
        )
        result = service.consult(
            question=question,
            initiative_names=initiatives,
            use_product_docs=use_product_docs,
            use_mcp=use_mcp,
            lang=_get_lang(),
        )

        return templates.TemplateResponse(
            request,
            "consult.html",
            _ctx(request, initiative_names=all_names,
                 selected_initiatives=initiatives,
                 question=question,
                 result=result.to_dict(),
                 error=None,
                 mcp_count=len(_get_mcp_context_servers())),
        )

    except OllamaConnectionError:
        repo = _repo(_get_session_squad(request))
        names = repo.list_names()
        return templates.TemplateResponse(
            request,
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=initiatives,
                 question=question, result=None,
                 error=_t("error.ollama", _get_lang()),
                 mcp_count=len(_get_mcp_context_servers())),
        )


# ─── Product Documentation ───

# ─── Product Docs Routes ───

def _render_product_docs(
    request: Request,
    notice: Optional[str] = None,
    notice_kind: str = "success",
):
    pd_service = _product_docs_service(request)
    return templates.TemplateResponse(
        request,
        "product_docs.html",
        _ctx(
            request,
            docs=pd_service.list_doc_metadata(),
            links=pd_service.load_links(),
            notice=notice,
            notice_kind=notice_kind,
        ),
    )


@app.get("/product-docs", response_class=HTMLResponse)
async def product_docs_page(request: Request):
    return _render_product_docs(request)


@app.post("/product-docs/upload", response_class=HTMLResponse)
async def upload_product_docs(
    request: Request,
    docs: list[UploadFile] = File(...),
):
    pd_service = _product_docs_service(request)
    uploaded = 0
    rejected = 0
    for doc in docs:
        if doc.filename:
            content = await doc.read(MAX_UPLOAD_FILE_BYTES + 1)
            if pd_service.save_document(
                doc.filename,
                content,
                MAX_UPLOAD_FILE_BYTES,
            ):
                uploaded += 1
            else:
                rejected += 1
    if uploaded and rejected:
        return _render_product_docs(
            request,
            "product_docs.upload_partial",
            "warning",
        )
    if uploaded:
        return _render_product_docs(request, "product_docs.uploaded")
    return _render_product_docs(
        request,
        "product_docs.upload_failed",
        "error",
    )


@app.post("/product-docs/add-link", response_class=HTMLResponse)
async def add_product_link(
    request: Request,
    title: str = Form(...),
    url: str = Form(...),
):
    pd_service = _product_docs_service(request)
    pd_service.add_link(title, url)
    return _render_product_docs(request, "product_docs.link_added")


@app.post("/product-docs/delete-doc/{filename}", response_class=HTMLResponse)
async def delete_product_doc(request: Request, filename: str):
    pd_service = _product_docs_service(request)
    pd_service.delete_document(filename)
    return _render_product_docs(
        request,
        "product_docs.document_deleted",
    )


@app.post("/product-docs/delete-link", response_class=HTMLResponse)
async def delete_product_link(
    request: Request,
    url: str = Form(...),
):
    pd_service = _product_docs_service(request)
    pd_service.delete_link(url)
    return _render_product_docs(request, "product_docs.link_deleted")


# ─── Timeline / Roadmap ───

@app.get("/timeline", response_class=HTMLResponse)
async def timeline_page(request: Request):
    return templates.TemplateResponse(
        request,
        "timeline.html",
        _ctx(request),
    )


# ─── Archived Initiatives ───

@app.get("/archived", response_class=HTMLResponse)
async def archived_page(request: Request):
    repo = _repo(_get_session_squad(request))
    archived = InitiativeLifecycleService(
        repo, create_change_tracker
    ).list_archived()
    return templates.TemplateResponse(
        request,
        "archived.html",
        _ctx(request, archived=archived),
    )


@app.post("/archived/restore", response_class=HTMLResponse)
async def restore_initiative(request: Request, name: str = Form(...)):
    repo = _repo(_get_session_squad(request))
    restored_name = InitiativeLifecycleService(
        repo, create_change_tracker
    ).restore(name)
    if restored_name:
        _logger.info("Initiative restored: %s → %s", name, restored_name)
    return await archived_page(request)


# ─── Squad ───


@app.get("/squad", response_class=HTMLResponse)
async def squad_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "squad.html", _ctx(request, error=error))


@app.get("/squad/create", response_class=HTMLResponse)
async def squad_create_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "squad_create.html", _ctx(request, error=error))


@app.get("/squad/join", response_class=HTMLResponse)
async def squad_join_page(request: Request, error: str = ""):
    cfg = config_manager.get_all()
    squads_list = _get_squad_names(cfg)
    user_email = _get_session_user_email(request)
    available = [sq for sq in squads_list if user_email not in (cfg.get("squads", {}).get(sq["name"], {}).get("members", []))]
    return templates.TemplateResponse(request, "squad_join.html", _ctx(request, squads=available, error=error))


@app.post("/squad/create")
async def squad_create(request: Request, name: str = Form(...), display_name: str = Form(""), password: str = Form(...)):
    squad_key = normalize_squad_key(name)
    if not squad_key:
        return await squad_page(request, error=_t("squad.invalid_name", _get_lang()))
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    new_squad = {
        "display_name": display_name.strip() or squad_key,
        "password_hash": hash_password(password),
        "members": [user_email],
        "created_by": user_email,
        "created_at": str(date.today()),
    }

    if not config_manager.transaction(
        lambda config: config_ops.create_squad(
            config,
            squad_key,
            new_squad,
        )
    ):
        return await squad_page(request, error=_t("squad.exists", _get_lang()))
    try:
        request.session["current_squad"] = squad_key
    except Exception:
        pass
    _logger.info("Squad created: %s by %s", squad_key, user_email)
    return RedirectResponse(url="/", status_code=302)


@app.post("/squad/join")
async def squad_join(request: Request, name: str = Form(...), password: str = Form(...)):
    squad_key = normalize_squad_key(name)
    squads = config_manager.get("squads") or {}
    if squad_key not in squads:
        return await squad_page(request, error=_t("squad.not_found", _get_lang()))
    sq = squads[squad_key]
    stored_hash = sq.get("password_hash", "")
    valid, needs_rehash = verify_password(stored_hash, password)
    if not valid:
        return await squad_page(request, error=_t("squad.wrong_password", _get_lang()))
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    replacement_hash = hash_password(password) if needs_rehash else stored_hash

    join_result = config_manager.transaction(
        lambda config: config_ops.join_squad(
            config,
            squad_key,
            user_email,
            stored_hash,
            replacement_hash,
        )
    )
    if join_result == "member":
        return await squad_page(request, error=_t("squad.already_member", _get_lang()))
    if join_result != "joined":
        return await squad_page(request, error=_t("squad.not_found", _get_lang()))
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
    return templates.TemplateResponse(request, "squad_select.html", _ctx(request, squads=user_squads, error=error))


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
    leave_result = config_manager.transaction(
        lambda config: config_ops.leave_squad(
            config,
            current_squad,
            user_email,
        )
    )
    if leave_result == "owner":
        return await squad_page(
            request,
            error=_t("squad.owner_cannot_leave", _get_lang()),
        )
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
    return templates.TemplateResponse(request, "squad_admin.html", _ctx(request, squad_name=squad_name, squad=sq, is_admin=is_admin))


@app.post("/squad/admin/{squad_name}/remove-member")
async def squad_remove_member(request: Request, squad_name: str, member_email: str = Form(...)):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    squads = config_manager.get("squads") or {}
    sq = squads.get(squad_name)
    if not sq or sq.get("created_by") != user_email:
        return RedirectResponse(url="/", status_code=302)
    if member_email == sq.get("created_by"):
        return RedirectResponse(url=f"/squad/admin/{squad_name}", status_code=302)
    config_manager.transaction(
        lambda config: config_ops.remove_squad_member(
            config,
            squad_name,
            user_email,
            member_email,
        )
    )
    return RedirectResponse(url=f"/squad/admin/{squad_name}", status_code=302)


@app.post("/squad/admin/{squad_name}/rename")
async def squad_rename(request: Request, squad_name: str, display_name: str = Form(...)):
    try:
        user_email = request.session.get("user_email", "")
    except Exception:
        user_email = ""
    if not user_email:
        return RedirectResponse(url="/login", status_code=302)
    squads = config_manager.get("squads") or {}
    sq = squads.get(squad_name)
    if not sq or sq.get("created_by") != user_email:
        return RedirectResponse(url="/", status_code=302)
    display_name = display_name.strip()
    if display_name:
        config_manager.transaction(
            lambda config: config_ops.rename_squad(
                config,
                squad_name,
                user_email,
                display_name,
            )
        )
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
    squads = cfg.get("squads") or {}
    sq = squads.get(squad_name)
    if not sq or sq.get("created_by") != user_email:
        return RedirectResponse(url="/", status_code=302)
    if not config_manager.transaction(
        lambda config: config_ops.disband_squad(
            config,
            squad_name,
            user_email,
        )
    ):
        return RedirectResponse(url="/", status_code=302)
    try:
        if request.session.get("current_squad") == squad_name:
            request.session.pop("current_squad", None)
    except Exception:
        pass
    return RedirectResponse(url="/", status_code=302)


# ─── Helpers ───

def _safe_filename(name: str) -> str:
    return safe_upload_filename(name)
