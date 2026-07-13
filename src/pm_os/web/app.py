import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, pass_context

from pm_os.infrastructure.ai.clients.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
)
from pm_os.infrastructure.tracking.change_tracker import ChangeTracker
from pm_os.infrastructure.validators.prd_validator import PRDValidator
from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.workflows.workspace_scan_workflow import WorkspaceScanWorkflow
from pm_os.web.config_manager import ConfigManager
from pm_os.web.i18n import t as _t, LANGS

app = FastAPI(title="PM OS")

HERE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))

config_manager = ConfigManager()


# ─── i18n helper ───

def _get_lang():
    return config_manager.get("lang", "pt-BR")


@pass_context
def _t_filter(ctx, key):
    lang = ctx.get("lang", "pt-BR")
    return _t(key, lang)


templates.env.filters["t"] = _t_filter


def _ctx(request, **extra):
    """Build base context with i18n for every template."""
    cfg = config_manager.get_all()
    lang = cfg.get("lang", "pt-BR")
    base = {
        "request": request,
        "config": cfg,
        "lang": lang,
    }
    base.update(extra)
    return base


def _build_ai_client():
    cfg = config_manager.get_all()
    return OllamaClient(
        model=cfg.get("model", "llama3.2"),
        base_url=cfg.get("ollama_url", "http://localhost:11434"),
    )


def _get_initiative_by_name(name: str):
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


async def _dashboard(request, force_onboarding=False):
    """Shared dashboard logic. force_onboarding ignores has_completed check."""
    repo = InitiativeRepository()
    logger = _SilentLogger()
    scan = WorkspaceScanWorkflow(initiative_repository=repo, logger=logger)
    initiatives = repo.list_initiatives()

    total_docs = 0
    has_prd = 0
    has_validation = 0
    total_score = 0.0
    scored_count = 0
    rows = []

    for init in initiatives:
        metadata = scan._load_metadata(init.path)
        score = scan._read_validation_score(init.path)
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

        status = metadata.get("status", "unknown") if metadata else "unknown"
        score_str = f"{score}/10" if score is not None else "-"
        rows.append({
            "name": init.name,
            "status": status,
            "owner": metadata.get("owner", "-") if metadata else "-",
            "score": score_str,
            "has_prd": prd_exists,
            "doc_count": doc_count,
        })

    avg_score = round(total_score / scored_count, 1) if scored_count > 0 else 0

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
        ),
    )


# ─── Initiative Detail ───

@app.get("/initiative/{initiative_name}", response_class=HTMLResponse)
async def initiative_detail(request: Request, initiative_name: str):
    selected = _get_initiative_by_name(initiative_name)
    if not selected:
        return HTMLResponse(_t("error.not_found", _get_lang()), status_code=404)

    metadata = {}
    meta_path = selected.path / "metadata.yaml"
    if meta_path.exists():
        import yaml
        metadata = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}

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

    validation_score = "-"
    report_path = selected.path / "artifacts" / "prd-validation.md"
    if report_path.exists():
        scan = WorkspaceScanWorkflow(initiative_repository=InitiativeRepository(), logger=_SilentLogger())
        score = scan._read_validation_score(selected.path)
        validation_score = f"{score}/10" if score is not None else "-"

    return templates.TemplateResponse(
        "initiative_detail.html",
        _ctx(request,
            initiative=selected,
            metadata=metadata,
            docs=docs,
            prd_exists=prd_exists,
            prd_content=prd_content,
            validation_score=validation_score,
        ),
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
            content = await doc.read()
            (ctx_dir / doc.filename).write_bytes(content)
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

    doc_path = selected.path / "context" / filename
    if doc_path.exists():
        doc_path.unlink()
        tracker = ChangeTracker()
        tracker.update_manifest(str(selected.path))

    return await initiative_detail(request, initiative_name)


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
    return templates.TemplateResponse(
        "generate.html",
        _ctx(request, initiatives=initiatives, result=None, error=None),
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate_prd(
    request: Request,
    initiative_name: str = Form(...),
    additional_initiatives: list[str] = Form(default=[]),
    use_product_docs: bool = Form(False),
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
                 error=f"Initiative '{initiative_name}' {_t('error.not_found', _get_lang())}"),
        )

    # Filter out the main initiative from additional list
    additional = [n for n in additional_initiatives if n != initiative_name]

    try:
        ai_client = _build_ai_client()

        from pm_os.context_builder import ContextBuilder
        from pm_os.prompt_builder import PromptBuilder
        from pm_os.writers.markdown_writer import MarkdownWriter

        # Build merged context with labels
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
            pd_context = _build_product_docs_context()
            if pd_context.strip():
                context_parts.append(f"--- Documentação do Produto ---\n\n{pd_context}")
                used_product_docs = True

        context = "\n\n".join(context_parts) if context_parts else ""
        prompt = PromptBuilder().build("create_prd", context)

        prd_content = ai_client.generate(prompt)

        prd_path = str(selected.path / "artifacts" / "prd.md")
        (selected.path / "artifacts").mkdir(parents=True, exist_ok=True)
        MarkdownWriter().write(content=prd_content, output_path=prd_path)

        validator = PRDValidator(ai_client=ai_client)
        report = validator.validate(prd_content)

        report_path = str(selected.path / "artifacts" / "prd-validation.md")
        MarkdownWriter().write(content=report.to_markdown(), output_path=report_path)

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
                 },
                 error=None),
        )

    except OllamaConnectionError:
        return templates.TemplateResponse(
            "generate.html",
            _ctx(request, initiatives=initiatives, result=None,
                 error=_t("error.ollama", _get_lang())),
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

    try:
        ai_client = _build_ai_client()
        validator = PRDValidator(ai_client=ai_client)
        prd_content = prd_path.read_text(encoding="utf-8")
        report = validator.validate(prd_content)

        from pm_os.writers.markdown_writer import MarkdownWriter

        report_path = str(selected.path / "artifacts" / "prd-validation.md")
        MarkdownWriter().write(content=report.to_markdown(), output_path=report_path)

        return templates.TemplateResponse(
            "validate.html",
            _ctx(request, initiative=selected, report=report, error=None),
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
    lang: str = Form("pt-BR"),
):
    config_manager.set("model", model)
    config_manager.set("ollama_url", ollama_url)
    config_manager.set("lang", lang)
    return templates.TemplateResponse(
        "config.html",
        _ctx(request, saved=True),
    )


# ─── MCP Server Management ───


def _get_mcp_servers() -> list[dict]:
    return config_manager.get("mcp_servers") or []


def _save_mcp_servers(servers: list[dict]):
    config_manager.set("mcp_servers", servers)


@app.post("/config/mcp/add", response_class=HTMLResponse)
async def add_mcp_server(
    request: Request,
    name: str = Form(...),
    url: str = Form(...),
):
    servers = _get_mcp_servers()
    if not any(s["url"] == url for s in servers):
        servers.append({"name": name.strip(), "url": url.strip(), "enabled": True})
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
             question="", result=None, error=None),
    )


@app.post("/consult", response_class=HTMLResponse)
async def consult_docs(
    request: Request,
    question: str = Form(...),
    initiatives: list[str] = Form(default=[]),
    use_product_docs: bool = Form(False),
):
    if not question.strip():
        repo = InitiativeRepository()
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=initiatives or names,
                 question=question, result=None, error=_t("consult.empty_question", _get_lang())),
        )

    if not initiatives and not use_product_docs:
        repo = InitiativeRepository()
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=names,
                 question=question, result=None,
                 error="Selecione iniciativas ou marque a documentação do produto para consultar."),
        )

    try:
        ai_client = _build_ai_client()
        repo = InitiativeRepository()

        # Gather documents from selected initiatives
        context_parts = []
        all_inits = repo.list_initiatives()
        for init in all_inits:
            if init.name in initiatives:
                if init.documents:
                    docs_text = "\n\n".join(init.documents)
                    context_parts.append(f"--- Iniciativa: {init.name} ---\n\n{docs_text}")

        # Include product documentation if checked
        if use_product_docs:
            pd_context = _build_product_docs_context()
            if pd_context.strip():
                context_parts.append(f"--- Documentação do Produto ---\n\n{pd_context}")

        if not context_parts:
            docs_context = "Nenhum documento disponível."
        else:
            docs_context = "\n\n".join(context_parts)

        prompt = f"""Você é um analista de documentação de produto.

Abaixo estão documentos de diversas fontes (iniciativas e/ou documentação do produto).
Cada bloco é precedido por um cabeçalho indicando a origem.

Documentos:
{docs_context}

Com base SOMENTE nos documentos acima, responda à pergunta abaixo.
Se a informação não estiver nos documentos, diga que não encontrou.
Cite a fonte (iniciativa ou documentação do produto) de onde cada informação foi extraída.

Pergunta: {question}"""

        answer = ai_client.generate(prompt)

        # Extract references: initiative names + product docs mentioned
        references = []
        for name in initiatives:
            if name in answer:
                references.append({"initiative": name})
        if use_product_docs and ("Documentação do Produto" in answer or "produto" in answer.lower()):
            references.append({"initiative": "Documentação do Produto"})

        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=[i.name for i in all_inits],
                 selected_initiatives=initiatives,
                 question=question,
                 result={
                     "answer": answer,
                     "initiatives": initiatives + (["Documentação do Produto"] if use_product_docs else []),
                     "references": references,
                 },
                 error=None),
        )

    except OllamaConnectionError:
        repo = InitiativeRepository()
        names = repo.list_names()
        return templates.TemplateResponse(
            "consult.html",
            _ctx(request, initiative_names=names, selected_initiatives=initiatives,
                 question=question, result=None,
                 error=_t("error.ollama", _get_lang())),
        )


# ─── Product Documentation ───

PRODUCT_DOCS_DIR = Path("workspace/product-docs")


def _load_product_docs() -> list[dict]:
    """Returns [{name, content}] from product-docs/context/."""
    ctx = PRODUCT_DOCS_DIR / "context"
    docs = []
    if ctx.exists():
        for f in sorted(ctx.iterdir()):
            if f.is_file() and f.suffix in (".md", ".txt"):
                docs.append({"name": f.name, "content": f.read_text(encoding="utf-8")})
    return docs


def _load_product_links() -> list[dict]:
    """Returns [{title, url}] from links.json."""
    fp = PRODUCT_DOCS_DIR / "links.json"
    if fp.exists():
        import json
        return json.loads(fp.read_text(encoding="utf-8"))
    return []


def _save_product_links(links: list[dict]):
    import json
    (PRODUCT_DOCS_DIR / "links.json").write_text(
        json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _build_product_docs_context() -> str:
    """Build labeled context string from product docs + links."""
    parts = []
    for d in _load_product_docs():
        parts.append(f"--- Documentação do Produto: {d['name']} ---\n\n{d['content']}")
    links = _load_product_links()
    if links:
        lines = "\n".join(f"- {l['title']}: {l['url']}" for l in links)
        parts.append(f"--- Links de Referência do Produto ---\n\n{lines}")
    return "\n\n".join(parts)


# ─── Product Docs Routes ───

@app.get("/product-docs", response_class=HTMLResponse)
async def product_docs_page(request: Request):
    docs = []
    ctx = PRODUCT_DOCS_DIR / "context"
    if ctx.exists():
        for f in sorted(ctx.iterdir()):
            if f.is_file():
                size = f.stat().st_size
                size_str = f"{size} B" if size < 1024 else f"{size // 1024} KB"
                docs.append({"name": f.name, "size": size_str})
    links = _load_product_links()
    return templates.TemplateResponse(
        "product_docs.html",
        _ctx(request, docs=docs, links=links),
    )


@app.post("/product-docs/upload", response_class=HTMLResponse)
async def upload_product_docs(
    request: Request,
    docs: list[UploadFile] = File(...),
):
    ctx = PRODUCT_DOCS_DIR / "context"
    ctx.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        if doc.filename:
            (ctx / doc.filename).write_bytes(await doc.read())
    return await product_docs_page(request)


@app.post("/product-docs/add-link", response_class=HTMLResponse)
async def add_product_link(
    request: Request,
    title: str = Form(...),
    url: str = Form(...),
):
    links = _load_product_links()
    links.append({"title": title.strip(), "url": url.strip()})
    _save_product_links(links)
    return await product_docs_page(request)


@app.post("/product-docs/delete-doc/{filename}", response_class=HTMLResponse)
async def delete_product_doc(request: Request, filename: str):
    fp = PRODUCT_DOCS_DIR / "context" / filename
    if fp.exists() and fp.is_file():
        fp.unlink()
    return await product_docs_page(request)


@app.post("/product-docs/delete-link", response_class=HTMLResponse)
async def delete_product_link(
    request: Request,
    url: str = Form(...),
):
    links = [l for l in _load_product_links() if l["url"] != url]
    _save_product_links(links)
    return await product_docs_page(request)


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
    src = archive_dir / name
    if src.exists() and src.is_dir():
        # Extract original name from archive name (format: name_timestamp)
        original_name = name.rsplit("_", 1)[0] if "_" in name else name
        dst = repo.initiatives_path / original_name
        if dst.exists():
            dst = repo.initiatives_path / f"{original_name}_restored"
        shutil.move(str(src), str(dst))
        tracker = ChangeTracker()
        tracker.update_manifest(str(dst))
    return await archived_page(request)


# ─── Helpers ───

class _SilentLogger:
    def info(self, msg):
        pass
