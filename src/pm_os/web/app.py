import os
import re
import json
import shutil
import urllib.parse
import urllib.request
import yaml
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse
from jinja2 import pass_context

from pm_os.infrastructure.ai.clients.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
)
from pm_os.infrastructure.ai.clients.openai_client import OpenAIClient
from pm_os.infrastructure.ai.clients.anthropic_client import AnthropicClient
from pm_os.infrastructure.tracking.change_tracker import ChangeTracker
from pm_os.infrastructure.validators.prd_validator import PRDValidator
from pm_os.contracts.workflow_contracts import AIClient
from pm_os.domain.initiative import Initiative
from pm_os.infrastructure.utils import (
    read_validation_score_from_file,
    version_file,
)
from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.workflows.workspace_scan_workflow import WorkspaceScanWorkflow
from pm_os.context_builder import ContextBuilder
from pm_os.prompt_builder import PromptBuilder
from pm_os.web.config_manager import ConfigManager
from pm_os.web.i18n import t as _t, LANGS
from pm_os.web.product_docs_service import ProductDocsService
from pm_os.writers.markdown_writer import MarkdownWriter

app = FastAPI(title="PM Studio")
_secret = os.getenv("PM_OS_SECRET")
if not _secret:
    import warnings
    warnings.warn("PM_OS_SECRET environment variable not set. Using generated random key.")
    _secret = os.urandom(64).hex()
app.add_middleware(SessionMiddleware, secret_key=_secret)


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
        return response


app.add_middleware(_NoCacheMiddleware)


_LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}
_MAX_LOGIN_ATTEMPTS = 10
_LOGIN_WINDOW_SECONDS = 300


def _check_login_rate_limit(ip: str) -> None:
    now = datetime.now()
    attempts = _LOGIN_ATTEMPTS.get(ip, [])
    attempts = [t for t in attempts if (now - t).total_seconds() < _LOGIN_WINDOW_SECONDS]
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    attempts.append(now)
    _LOGIN_ATTEMPTS[ip] = attempts

HERE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))

config_manager = ConfigManager()
pd_service = ProductDocsService()

ALLOWED_EXTENSIONS = {".md", ".txt"}


# ─── Auth middleware ───

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/static"):
        return await call_next(request)
    if request.url.path in ("/login",):
        return await call_next(request)
    cfg = config_manager.get_all()
    if not cfg.get("auth_enabled", False):
        return await call_next(request)
    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "::1", "localhost"):
        return await call_next(request)
    if request.session.get("authenticated"):
        return await call_next(request)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    cfg = config_manager.get_all()
    if not cfg.get("auth_enabled", False):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    client_host = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_host)
    cfg = config_manager.get_all()
    expected_user = cfg.get("auth_username", "")
    expected_pw = cfg.get("auth_password", "")
    import secrets as _secrets
    if _secrets.compare_digest(username, expected_user) and _secrets.compare_digest(password, expected_pw):
        request.session.clear()
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=302)
    return await login_page(request, error="Invalid credentials.")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# ─── i18n helper ───

def _get_lang() -> str:
    return config_manager.get("lang", "en")


@pass_context
def _t_filter(ctx, key: str) -> str:
    lang = ctx.get("lang", "en")
    return _t(key, lang)


templates.env.filters["t"] = _t_filter


def _ctx(request: Request, **extra) -> dict:
    """Build base context with i18n for every template."""
    cfg = config_manager.get_all()
    lang = cfg.get("lang", "en")
    base = {
        "request": request,
        "config": cfg,
        "lang": lang,
    }
    base.update(extra)
    return base


def _build_ai_client() -> AIClient:
    cfg = config_manager.get_all()
    provider = cfg.get("ai_provider", "ollama")
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
    """Validate and sanitize MCP server URL to prevent SSRF."""
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid scheme: {parsed.scheme}. Only http/https allowed.")
    host = parsed.hostname or ""
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise ValueError("Localhost URLs are not allowed for MCP servers.")
    if host.startswith("169.254."):
        raise ValueError("Link-local addresses are not allowed.")
    if host.startswith("10.") or host.startswith("172.") or host.startswith("192.168."):
        raise ValueError("Private IP ranges are not allowed for MCP servers.")
    return url


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
            _validate_mcp_url(url)
            req = urllib.request.Request(url, method="GET", headers={"Accept": "text/plain,application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
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
                    results.append({"name": name, "content": content})
        except Exception:
            pass
    return results


def _get_initiative_by_name(name: str) -> Optional[Initiative]:
    repo = InitiativeRepository()
    for i in repo.list_initiatives():
        if i.name == name:
            return i
    return None


# ─── Dashboard ───

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return await _dashboard(request)


@app.post("/onboarding/dismiss", response_class=HTMLResponse)
async def dismiss_onboarding(request: Request):
    config_manager.set("onboarding_dismissed", True)
    return await dashboard(request)


@app.get("/onboarding/show", response_class=HTMLResponse)
async def show_onboarding(request: Request):
    config_manager.set("onboarding_dismissed", False)
    # Pass a flag to force the onboarding modal
    return await _dashboard(request, force_onboarding=True)


async def _dashboard(request: Request, force_onboarding: bool = False) -> HTMLResponse:
    """Shared dashboard logic. force_onboarding ignores has_completed check."""
    repo = InitiativeRepository()
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

    avg_score = round(total_score / scored_count, 1) if scored_count > 0 else 0

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
    repo = InitiativeRepository()
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
            if f.is_file() and f.suffix in (".md", ".txt"):
                safe = _safe_filename(f.name)
                if safe:
                    shutil.copy2(str(f), str(ctx_dir / safe))

    tracker = ChangeTracker()
    tracker.update_manifest(str(base_path))

    try:
        ai_client = _build_ai_client()
        selected = _get_initiative_by_name(init_id)
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

            validator = PRDValidator(ai_client=ai_client, lang=_get_lang())
            report = validator.validate(prd_content)
            report_path = str(selected.path / "artifacts" / "prd-validation.md")
            MarkdownWriter().write(content=report.to_markdown(lang=_get_lang()), output_path=report_path)

            tracker.update_manifest(str(selected.path))
    except OllamaConnectionError:
        pass

    return await _dashboard(request)


# ─── Initiative Detail ───

@app.get("/initiative/{initiative_name}", response_class=HTMLResponse)
async def initiative_detail(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name)
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
    report_path = selected.path / "artifacts" / "prd-validation.md"
    score = read_validation_score_from_file(report_path)
    validation_score = f"{score}/10" if score is not None else "-"

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
            prd_versions=prd_versions,
        ),
    )


@app.get("/initiative/{initiative_name}/prd/download")
async def download_prd(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)
    prd_path = selected.path / "artifacts" / "prd.md"
    if not prd_path.exists():
        return HTMLResponse("PRD not found.", status_code=404)
    from starlette.responses import FileResponse
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
    selected = _get_initiative_by_name(initiative_name)
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
        tracker = ChangeTracker()
        tracker.update_manifest(str(selected.path))

    return await initiative_detail(request, initiative_name)


@app.post("/initiative/{initiative_name}/delete-doc", response_class=HTMLResponse)
async def delete_context_doc(
    request: Request,
    initiative_name: str,
    filename: str = Form(...),
):
    selected = _get_initiative_by_name(initiative_name)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    safe_name = _safe_filename(filename)
    if safe_name:
        doc_path = (selected.path / "context" / safe_name).resolve()
        ctx_dir = (selected.path / "context").resolve()
        # Ensure the resolved path is still inside the context directory
        if str(doc_path).startswith(str(ctx_dir)) and doc_path.exists():
            doc_path.unlink()
            tracker = ChangeTracker()
            tracker.update_manifest(str(selected.path))

    return await initiative_detail(request, initiative_name)


# ─── PRD Version View ───

@app.get("/initiative/{initiative_name}/prd/{version}", response_class=HTMLResponse)
async def prd_version_view(request: Request, initiative_name: str, version: str):
    selected = _get_initiative_by_name(initiative_name)
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
    import re
    from datetime import date

    repo = InitiativeRepository()

    init_id = id.strip()
    if not init_id:
        safe_name = re.sub(r'[^A-Z0-9]+', '-', name.strip().upper()).strip('-')
        init_id = f"INT-{safe_name[:30]}"
    else:
        # Sanitize user-supplied ID: remove path separators and dangerous chars
        init_id = re.sub(r'[^A-Za-z0-9_-]+', '', init_id).strip('-_.')
        if not init_id:
            safe_name = re.sub(r'[^A-Z0-9]+', '-', name.strip().upper()).strip('-')
            init_id = f"INT-{safe_name[:30]}"

    base_path = repo.initiatives_path / init_id
    if base_path.exists():
        return templates.TemplateResponse(
            "initiative_new.html",
            _ctx(request, error=f"Initiative '{init_id}' {_t('error.exists', _get_lang())}"),
        )

    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "artifacts").mkdir(exist_ok=True)
    (base_path / "context").mkdir(exist_ok=True)
    (base_path / "logs").mkdir(exist_ok=True)

    import yaml
    metadata = {
        "id": init_id,
        "name": name.strip(),
        "status": status,
        "created_at": str(date.today()),
        "artifacts": ["prd"],
        "workflows": ["create_prd"],
    }
    meta_path = base_path / "metadata.yaml"
    meta_path.write_text(yaml.dump(metadata, default_flow_style=False, allow_unicode=True), encoding="utf-8")

    if context.strip():
        ctx_path = base_path / "context" / "context.md"
        ctx_path.write_text(context.strip(), encoding="utf-8")

    tracker = ChangeTracker()
    tracker.update_manifest(str(base_path))

    return await dashboard(request)


# ─── Generate PRD ───

@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    repo = InitiativeRepository()
    initiatives = repo.list_initiatives()
    pd_service = ProductDocsService()
    product_docs_count = pd_service.count_docs()
    return templates.TemplateResponse(
        "generate.html",
        _ctx(request, initiatives=initiatives, result=None, error=None,
             product_docs_count=product_docs_count,
             mcp_count=len(_get_mcp_servers())),
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate_prd(
    request: Request,
    initiative_name: str = Form(...),
    additional_initiatives: list[str] = Form(default=[]),
    use_product_docs: bool = Form(False),
    use_mcp: bool = Form(False),
):
    repo = InitiativeRepository()
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
                 product_docs_count=pd_service.count_docs(),
                 mcp_count=len(_get_mcp_servers())),
        )

    additional = [n for n in additional_initiatives if n != initiative_name]

    try:
        ai_client = _build_ai_client()

        context_parts = []
        main_context = ContextBuilder().build(selected)
        if main_context.strip():
            context_parts.append(f"--- Contexto Principal: {selected.name} ---\n\n{main_context}")

        used_additional = []
        for add_name in additional:
            add_init = _get_initiative_by_name(add_name)
            if add_init and add_init.documents:
                add_docs = "\n\n".join(add_init.documents)
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
        prompt = PromptBuilder().build("create_prd", context, lang=_get_lang())

        prd_content = ai_client.generate(prompt)

        artifacts_dir = selected.path / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        version_file(artifacts_dir / "prd.md")
        version_file(artifacts_dir / "prd-validation.md")

        MarkdownWriter().write(content=prd_content, output_path=str(prd_md))

        validator = PRDValidator(ai_client=ai_client, lang=_get_lang())
        report = validator.validate(prd_content)

        report_path = str(artifacts_dir / "prd-validation.md")
        MarkdownWriter().write(content=report.to_markdown(lang=_get_lang()), output_path=report_path)

        tracker = ChangeTracker()
        tracker.update_manifest(str(selected.path))

        return templates.TemplateResponse(
            "generate.html",
            _ctx(request, initiatives=initiatives,
                 result={
                     "prd": prd_content,
                     "score": report.overall_score,
                     "sections": report.sections,
                     "initiative": initiative_name,
                     "additional": used_additional,
                     "product_docs_used": used_product_docs,
                     "mcp_used": used_mcp_servers,
                 },
                 error=None,
                 product_docs_count=pd_service.count_docs(),
                 mcp_count=len(_get_mcp_servers())),
        )

    except OllamaConnectionError:
        return templates.TemplateResponse(
            "generate.html",
            _ctx(request, initiatives=initiatives, result=None,
                 error=_t("error.ollama", _get_lang()),
                 product_docs_count=pd_service.count_docs(),
                 mcp_count=len(_get_mcp_servers())),
        )


# ─── Validate PRD ───

@app.get("/validate/{initiative_name}", response_class=HTMLResponse)
async def validate_page(request: Request, initiative_name: str):
    repo = InitiativeRepository()
    initiatives = repo.list_initiatives()

    selected = None
    for i in initiatives:
        if i.name == initiative_name:
            selected = i
            break

    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    return templates.TemplateResponse(
        "validate.html",
        _ctx(request, initiative=selected, report=None, error=None),
    )


@app.post("/validate/{initiative_name}", response_class=HTMLResponse)
async def validate_prd(request: Request, initiative_name: str):
    repo = InitiativeRepository()

    selected = None
    for i in repo.list_initiatives():
        if i.name == initiative_name:
            selected = i
            break

    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    prd_path = selected.path / "artifacts" / "prd.md"
    if not prd_path.exists():
        return templates.TemplateResponse(
            "validate.html",
            _ctx(request, initiative=selected, report=None, error=_t("validate.no_prd", _get_lang())),
        )

    previous_score = read_validation_score_from_file(selected.path / "artifacts" / "prd-validation.md")

    try:
        ai_client = _build_ai_client()
        validator = PRDValidator(ai_client=ai_client, lang=_get_lang())
        prd_content = prd_path.read_text(encoding="utf-8")
        report = validator.validate(prd_content)

        from pm_os.writers.markdown_writer import MarkdownWriter

        artifacts_dir = selected.path / "artifacts"
        version_file(artifacts_dir / "prd-validation.md")
        report_path = str(artifacts_dir / "prd-validation.md")
        MarkdownWriter().write(content=report.to_markdown(lang=_get_lang()), output_path=report_path)

        return templates.TemplateResponse(
            "validate.html",
            _ctx(request, initiative=selected, report=report, error=None,
                 previous_score=previous_score),
        )

    except OllamaConnectionError:
        return templates.TemplateResponse(
            "validate.html",
            _ctx(request, initiative=selected, report=None, error=_t("error.ollama", _get_lang())),
        )


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
    auth_username: str = Form(""),
    auth_password: str = Form(""),
    ai_provider: str = Form("ollama"),
    openai_api_key: str = Form(""),
    openai_model: str = Form(""),
    anthropic_api_key: str = Form(""),
    anthropic_model: str = Form(""),
):
    config_manager.set("model", model)
    config_manager.set("ollama_url", ollama_url)
    config_manager.set("lang", lang)
    config_manager.set("auth_enabled", auth_enabled == "true")
    if auth_username:
        config_manager.set("auth_username", auth_username)
    if auth_password:
        config_manager.set("auth_password", auth_password)
    if ai_provider:
        config_manager.set("ai_provider", ai_provider)
    if ai_provider == "openai":
        if openai_api_key:
            config_manager.set("openai_api_key", openai_api_key)
        if openai_model:
            config_manager.set("openai_model", openai_model)
    if ai_provider == "anthropic":
        if anthropic_api_key:
            config_manager.set("anthropic_api_key", anthropic_api_key)
        if anthropic_model:
            config_manager.set("anthropic_model", anthropic_model)
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
    servers = [s for s in _get_mcp_servers() if s["url"] != url]
    _save_mcp_servers(servers)
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
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


# ─── Delete Initiative ───

@app.post("/initiative/{initiative_name}/delete", response_class=HTMLResponse)
async def delete_initiative(request: Request, initiative_name: str):
    from datetime import datetime
    import shutil

    repo = InitiativeRepository()
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

    return await dashboard(request)


# ─── Consult Documentation (Q&A) ───

@app.get("/consult", response_class=HTMLResponse)
async def consult_page(request: Request):
    repo = InitiativeRepository()
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
        repo = InitiativeRepository()
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=initiatives or names,
                 question=question, result=None, error=_t("consult.empty_question", _get_lang()),
                 mcp_count=len(_get_mcp_servers())),
        )

    if not initiatives and not use_product_docs and not use_mcp:
        repo = InitiativeRepository()
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=names,
                 question=question, result=None,
                 error="Selecione iniciativas, documentação do produto ou servidores MCP para consultar.",
                 mcp_count=len(_get_mcp_servers())),
        )

    try:
        ai_client = _build_ai_client()
        repo = InitiativeRepository()

        context_parts = []
        all_inits = repo.list_initiatives()
        for init in all_inits:
            if init.name in initiatives:
                if init.documents:
                    docs_text = "\n\n".join(init.documents)
                    context_parts.append(f"--- Iniciativa: {init.name} ---\n\n{docs_text}")

        if use_product_docs:
            pd_context = pd_service.build_context()
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
        repo = InitiativeRepository()
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
    docs = []
    ctx = Path("workspace/product-docs") / "context"
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
    ctx = Path("workspace/product-docs") / "context"
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
    links = pd_service.load_links()
    links.append({"title": title.strip(), "url": url.strip()})
    pd_service.save_links(links)
    return await product_docs_page(request)


@app.post("/product-docs/delete-doc/{filename}", response_class=HTMLResponse)
async def delete_product_doc(request: Request, filename: str):
    safe_name = _safe_filename(filename)
    if safe_name:
        fp = (Path("workspace/product-docs") / "context" / safe_name).resolve()
        ctx_dir = (Path("workspace/product-docs") / "context").resolve()
        if str(fp).startswith(str(ctx_dir)) and fp.exists() and fp.is_file():
            fp.unlink()
    return await product_docs_page(request)


@app.post("/product-docs/delete-link", response_class=HTMLResponse)
async def delete_product_link(
    request: Request,
    url: str = Form(...),
):
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
    repo = InitiativeRepository()
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
    import shutil
    repo = InitiativeRepository()
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
        tracker = ChangeTracker()
        tracker.update_manifest(str(dst))
    return await archived_page(request)


# ─── Helpers ───

def _safe_filename(name: str) -> str:
    """Strip directory components from a filename to prevent path traversal.
    Returns empty string if the name is unsafe.
    """
    # Reject names with parent-dir traversal or absolute paths
    if ".." in name or name.startswith("/"):
        return ""
    return Path(name).name


class _SilentLogger:
    def info(self, msg):
        pass
