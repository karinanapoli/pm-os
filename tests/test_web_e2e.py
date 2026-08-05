"""End-to-end tests for the web layer (FastAPI routes + templates).

Covers:
- All GET routes render successfully (200)
- All POST routes with valid data
- Security: path traversal in file uploads and deletions
- Security: unsanitized initiative ID
- Security: unsanitized archive restore name
- Auth: registration, login, middleware redirect
- Template rendering with context variables
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Generator

import hashlib
import pytest
from fastapi.testclient import TestClient

os.environ["PM_OS_ENV"] = "test"


# ─── Session-scoped: one workspace + config for all tests ───

@pytest.fixture(scope="session")
def _session_base(tmp_path_factory) -> Path:
    """Create a single temp workspace for the entire session."""
    base = tmp_path_factory.mktemp("pmos_e2e")
    config_dir = base / ".pm_os"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(json.dumps({
        "model": "llama3.2:1b",
        "ollama_url": "http://localhost:11434",
        "lang": "pt-BR",
        "onboarding_dismissed": False,
        "mcp_servers": [],
    }), encoding="utf-8")

    (base / "workspace" / "initiatives").mkdir(parents=True, exist_ok=True)
    (base / "workspace" / "product-docs" / "context").mkdir(parents=True, exist_ok=True)
    PRODUCT_DOCS_DIR = base / "workspace" / "product-docs"
    return base


@pytest.fixture(autouse=True)
def _isolate_each_test(_session_base: Path, monkeypatch):
    """Reset env/state before each test. Import app here so config_manager reads our env."""
    monkeypatch.setenv("PM_OS_CONFIG_DIR", str(_session_base / ".pm_os"))
    import hashlib
    # Reset the config file to defaults before each test
    config_file = _session_base / ".pm_os" / "config.json"
    config_file.write_text(json.dumps({
        "model": "llama3.2:1b",
        "ollama_url": "http://localhost:11434",
        "lang": "pt-BR",
        "onboarding_dismissed": False,
        "mcp_servers": [],
        "users": {"test@pmstudio.app": hashlib.sha256("secret123".encode()).hexdigest()},
        "squads": {"default": {"display_name": "Default", "password_hash": hashlib.sha256("squad123".encode()).hexdigest(), "members": ["test@pmstudio.app"], "created_by": "test@pmstudio.app", "created_at": "2024-01-01"}},
    }), encoding="utf-8")
    # Clean initiatives dir
    initiatives_dir = _session_base / "workspace" / "initiatives"
    for d in list(initiatives_dir.iterdir()):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    # Clean archived dir
    archived_dir = _session_base / "workspace" / "archived"
    if archived_dir.exists():
        for d in list(archived_dir.iterdir()):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
    # Clean all personal, squad and legacy product-doc scopes.
    product_docs_root = _session_base / "workspace" / "product-docs"
    shutil.rmtree(product_docs_root, ignore_errors=True)
    (product_docs_root / "context").mkdir(parents=True)
    shutil.rmtree(_session_base / "workspace" / "signals", ignore_errors=True)

    monkeypatch.chdir(_session_base)

    # Now import app — config_manager reads PM_OS_CONFIG_DIR at import time
    import importlib
    for mod in list(sys.modules.keys()):
        if mod.startswith("pm_os"):
            del sys.modules[mod]
    # Need to re-import config_manager to pick up new env
    import pm_os.web.config_manager
    importlib.reload(pm_os.web.config_manager)


@pytest.fixture
def unauth_client() -> Generator[TestClient, None, None]:
    """Client without auto-login (for auth tests)."""
    from pm_os.web.app import app as _app
    with TestClient(_app) as c:
        yield c


@pytest.fixture
def client(unauth_client) -> Generator[TestClient, None, None]:
    """Client that is already logged in with the default test user."""
    unauth_client.post("/login", data={"email": "test@pmstudio.app", "password": "secret123"})
    yield unauth_client


@pytest.fixture
def session_base(_session_base: Path) -> Path:
    return _session_base


# ─── Helpers ───

def _create_initiative(client, name: str = "Test Initiative", init_id: str = "") -> str:
    resp = client.post("/initiatives/new", data={
        "name": name,
        "id": init_id,
        "status": "discovery",
        "context": "# Contexto\n\nTeste de contexto.",
    })
    assert resp.status_code == 200, f"Failed to create initiative: {resp.text[:200]}"
    if init_id:
        return init_id
    safe = re.sub(r'[^A-Z0-9]+', '-', name.upper()).strip('-')
    return f"INT-{safe[:30]}"


class TestSignals:
    def test_signals_page_uses_progressive_disclosure(self, client):
        response = client.get("/signals")

        assert response.status_code == 200
        assert '<details class="card signal-upload-card" id="signal-upload"' in response.text
        assert '<details class="card signal-form-card" id="new-signal"' in response.text
        assert 'href="#signal-upload"' in response.text
        assert 'href="#new-signal"' in response.text
        assert "openSignalPanel" in response.text

    def test_create_signal_and_show_it_on_linked_initiative(self, client):
        initiative_id = _create_initiative(client, "Onboarding", "INT-ONBOARDING")

        response = client.post(
            "/signals",
            data={
                "title": "Abandono na etapa fiscal",
                "summary": "Três clientes relataram dificuldade na mesma etapa.",
                "source_type": "customer_feedback",
                "theme": "onboarding",
                "strength": "strong",
                "initiative_ids": initiative_id,
                "source_reference": "Entrevistas de julho",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"].startswith("/signals/SIG-")
        signals_page = client.get("/signals")
        assert "Abandono na etapa fiscal" in signals_page.text
        initiative_page = client.get(f"/initiative/{initiative_id}")
        assert "Abandono na etapa fiscal" in initiative_page.text

    def test_upload_source_review_confirm_and_download(self, client):
        response = client.post(
            "/signals/extract",
            files={
                "source_file": (
                    "relatorio.md",
                    b"# Relatorio\n\nQuatro clientes abandonaram o cadastro fiscal.",
                    "text/markdown",
                )
            },
        )

        assert response.status_code == 200
        assert "Quatro clientes abandonaram" in response.text
        source_id = re.search(r'name="source_id" value="(SSRC-[A-F0-9]+)"', response.text)
        assert source_id

        confirmed = client.post(
            "/signals",
            data={
                "title": "Abandono no cadastro fiscal",
                "summary": "Quatro clientes abandonaram o cadastro fiscal.",
                "source_type": "research",
                "theme": "onboarding",
                "strength": "strong",
                "source_id": source_id.group(1),
                "source_reference": "relatorio.md",
            },
            follow_redirects=False,
        )
        assert confirmed.status_code == 303
        detail = client.get(confirmed.headers["location"])
        assert "relatorio.md" in detail.text

        download = client.get(f"/signals/sources/{source_id.group(1)}")
        assert download.status_code == 200
        assert b"Quatro clientes" in download.content


class TestInitiativeMap:
    def test_map_connects_context_specification_and_deliverables(self, client):
        initiative_id = _create_initiative(
            client,
            "Mapa rastreável",
            "INT-MAP",
        )
        client.post(
            f"/initiative/{initiative_id}/decisions",
            data={
                "title": "Manter fluxo guiado",
                "rationale": "Reduz lacunas antes da entrega.",
                "revisit_if": "O tempo de preparação ultrapassar dois dias.",
            },
        )
        client.post(
            "/signals",
            data={
                "title": "PMs perdem contexto entre ferramentas",
                "summary": "Entrevistas indicaram perda de rastreabilidade.",
                "source_type": "research",
                "theme": "workflow",
                "strength": "medium",
                "initiative_ids": initiative_id,
            },
        )

        response = client.get(f"/initiative/{initiative_id}/map")

        assert response.status_code == 200
        assert "PMs perdem contexto entre ferramentas" in response.text
        assert "Manter fluxo guiado" in response.text
        assert "context.md" in response.text
        assert "Mapa da iniciativa" in response.text


class TestGuidedSpecification:
    def test_quick_prd_offers_direct_backlog_journey(self, client, session_base):
        init_id = _create_initiative(client, "Quick Backlog", "INT-QUICK-BACKLOG")
        artifacts = (
            session_base / "workspace" / "initiatives" / init_id / "artifacts"
        )
        artifacts.mkdir(exist_ok=True)
        (artifacts / "prd.md").write_text(
            "# PRD\n\n## Requisitos\n\n- Consultar fornecedor\n",
            encoding="utf-8",
        )

        initiative = client.get(f"/initiative/{init_id}")
        backlog = client.get(f"/initiative/{init_id}/backlog?source=prd")

        assert f"/initiative/{init_id}/backlog?source=prd" in initiative.text
        assert "Criar backlog deste PRD" in initiative.text
        assert backlog.status_code == 200
        assert "Modo rápido · PRD" in backlog.text
        assert 'name="source" value="prd" checked' in backlog.text

    def test_quick_prd_accepts_requirements_grouped_in_subsections(self, client, session_base):
        init_id = _create_initiative(client, "Quick Nested Backlog", "INT-QUICK-NESTED")
        artifacts = session_base / "workspace" / "initiatives" / init_id / "artifacts"
        artifacts.mkdir(exist_ok=True)
        (artifacts / "prd.md").write_text(
            "# PRD\n\n## Requisitos Funcionais\n\n### Básicos\n\n- Consultar fornecedor\n",
            encoding="utf-8",
        )

        page = client.get(f"/initiative/{init_id}/backlog?source=prd")

        assert page.status_code == 200
        assert 'name="source" value="prd" checked' in page.text
        assert 'class="btn btn-ai" disabled' not in page.text
        assert "Usar PRD atual" in page.text
        assert "Caminho rápido para transformar os requisitos" in page.text

        generated = client.post(
            f"/initiative/{init_id}/backlog/generate",
            data={
                "source": "prd",
                "story_format": "automatic",
                "granularity": "standard",
                "epic_count": "0",
                "ai_provider": "demo",
            },
            follow_redirects=False,
        )
        assert generated.status_code == 303
        assert "notice=backlog.created" in generated.headers["location"]
        state_path = artifacts / "specification.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["artifacts"]["backlog"]["source"] == "prd"
        assert state["artifacts"]["backlog"]["story_format"] == "automatic"

    def test_uses_uploaded_file_as_source_to_generate_backlog(self, client, session_base):
        init_id = _create_initiative(client, "Uploaded Source", "INT-UPLOADED-SOURCE")
        content = "# Descoberta\n\nPrecisamos consultar fornecedores por CNPJ."

        upload_page = client.get(f"/initiative/{init_id}/backlog?source=upload")
        assert 'name="source" value="upload" checked' in upload_page.text
        assert "Usar arquivo de referência" in upload_page.text
        assert "Escolher automaticamente — recomendado" in upload_page.text
        assert "Cada história deve entregar valor" in upload_page.text
        assert "backlog.upload." not in upload_page.text

        uploaded = client.post(
            f"/initiative/{init_id}/backlog/generate",
            data={
                "source": "upload",
                "story_format": "automatic",
                "granularity": "standard",
                "epic_count": "0",
                "ai_provider": "demo",
            },
            files={"backlog_source_file": ("descoberta.md", content, "text/markdown")},
            follow_redirects=False,
        )

        assert uploaded.status_code == 303
        assert "notice=backlog.created" in uploaded.headers["location"]
        page = client.get(f"/initiative/{init_id}/backlog")
        assert "Em revisão" in page.text
        assert f'/initiative/{init_id}/backlog/download' not in page.text
        state_path = (
            session_base / "workspace" / "initiatives" / init_id
            / "artifacts" / "specification.json"
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["artifacts"]["backlog"]["source"] == "upload"
        assert state["artifacts"]["backlog"]["story_format"] == "automatic"
        assert state["artifacts"]["backlog_source"]["source_filename"] == "descoberta.md"

    def test_rejects_invalid_uploaded_generation_source(self, client):
        init_id = _create_initiative(client, "Invalid Uploaded Source", "INT-INVALID-UPLOAD")

        response = client.post(
            f"/initiative/{init_id}/backlog/generate",
            data={"source": "upload", "ai_provider": "demo"},
            files={"backlog_source_file": ("fonte.pdf", b"invalid", "application/pdf")},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert "notice=backlog.upload.type_error" in response.headers["location"]

    def test_initiative_assistant_keeps_conversation_history(self, client, session_base):
        init_id = _create_initiative(client, "Assistant Context", "INT-ASSISTANT")

        page = client.get(f"/initiative/{init_id}/chat")
        assert page.status_code == 200
        assert "Assistente da iniciativa" in page.text
        assert "Nenhuma ferramenta MCP altera dados" in page.text

        response = client.post(
            f"/initiative/{init_id}/chat",
            data={
                "question": "Quais são os principais riscos?",
                "ai_provider": "demo",
            },
        )

        assert response.status_code == 200
        assert "Quais são os principais riscos?" in response.text
        history_path = (
            session_base / "workspace" / "initiatives" / init_id
            / "artifacts" / "assistant-chat.json"
        )
        history = json.loads(history_path.read_text(encoding="utf-8"))
        assert [item["role"] for item in history] == ["user", "assistant"]

        cleared = client.post(
            f"/initiative/{init_id}/chat/clear", follow_redirects=False
        )
        assert cleared.status_code == 303
        assert not history_path.exists()

    def test_guided_initiative_opens_specification_without_breaking_quick_mode(
        self, client, session_base
    ):
        response = client.post(
            "/initiatives/new",
            data={
                "name": "Guided Checkout",
                "id": "INT-GUIDED",
                "status": "discovery",
                "context": "Pesquisa inicial.",
                "experience_mode": "guided",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/initiative/INT-GUIDED/specification"

        quick_id = _create_initiative(client, "Quick Checkout", "INT-QUICK")
        metadata = (
            session_base / "workspace" / "initiatives" / quick_id / "metadata.yaml"
        ).read_text()
        assert "experience_mode: quick" in metadata

    def test_saves_approves_and_generates_traceable_backlog(self, client, session_base):
        init_id = _create_initiative(client, "Guided Checkout", "INT-GUIDED")
        sections = {
            "problem": "Abandono no checkout.",
            "users": "Clientes autenticados.",
            "evidence": "Pesquisa com clientes.",
            "outcome": "Reduzir esforço.",
            "metrics": "Conversão.",
            "scope": "Checkout autenticado.",
            "out_of_scope": "Visitantes.",
            "requirements": "- Reutilizar endereço\n- Confirmar pagamento",
            "constraints": "Consentimento.",
            "risks": "Dispositivo compartilhado.",
            "dependencies": "Identidade.",
            "hypotheses": "Menos campos melhora conversão.",
            "open_questions": "Qual a meta?",
            "acceptance_criteria": "- Exigir consentimento\n- Exigir confirmação",
        }
        saved = client.post(
            f"/initiative/{init_id}/specification",
            data=sections,
            follow_redirects=False,
        )
        assert saved.status_code == 303

        approved = client.post(
            f"/initiative/{init_id}/specification/approve",
            follow_redirects=False,
        )
        assert approved.status_code == 303

        backlog = client.post(
            f"/initiative/{init_id}/backlog/generate",
            data={
                "source": "specification",
                "story_format": "user_story",
                "granularity": "standard",
                "epic_count": "0",
                "ai_provider": "demo",
            },
            follow_redirects=False,
        )
        assert backlog.status_code == 303
        assert backlog.headers["location"].startswith(f"/initiative/{init_id}/backlog")
        path = (
            session_base / "workspace" / "initiatives" / init_id
            / "artifacts" / "backlog.md"
        )
        assert "SPEC-v1" in path.read_text(encoding="utf-8")

        review = client.get(f"/initiative/{init_id}/backlog")
        assert review.status_code == 200
        assert "Criação e revisão do backlog" in review.text
        assert "um único arquivo Markdown" in review.text
        assert '<option value="demo" selected>' in review.text
        assert f'/initiative/{init_id}/backlog/download' not in review.text

        blocked_download = client.get(
            f"/initiative/{init_id}/backlog/download", follow_redirects=False
        )
        assert blocked_download.status_code == 303
        assert "notice=backlog.download_requires_approval" in blocked_download.headers["location"]

        edited = client.post(
            f"/initiative/{init_id}/backlog/save",
            data={"content": "## Iniciativa: Checkout\n\n## Épico: Pagamento\n\n### História: Confirmar pagamento"},
            follow_redirects=False,
        )
        assert "notice=backlog.saved" in edited.headers["location"]
        approved_backlog = client.post(
            f"/initiative/{init_id}/backlog/approve",
            follow_redirects=False,
        )
        assert "notice=backlog.approved" in approved_backlog.headers["location"]

        page = client.get(f"/initiative/{init_id}/specification")
        assert page.status_code == 200
        assert "Especificação da iniciativa" in page.text
        assert "Atualizado" in page.text
        assert f'/initiative/{init_id}/deliverables' in page.text

        deliverables = client.get(f"/initiative/{init_id}/deliverables")
        assert deliverables.status_code == 200
        assert "Entregáveis" in deliverables.text
        assert "Backlog de implementação" in deliverables.text
        assert f'/initiative/{init_id}/prd/download' not in deliverables.text
        assert f'/initiative/{init_id}/backlog/download' in deliverables.text

    def test_legacy_fallback_report_is_presented_with_one_actionable_warning(
        self, client, session_base
    ):
        init_id = _create_initiative(client, "Legacy Validation", "INT-LEGACY-VALIDATION")
        artifacts = session_base / "workspace" / "initiatives" / init_id / "artifacts"
        artifacts.mkdir(exist_ok=True)
        (artifacts / "prd.md").write_text("# PRD\n", encoding="utf-8")
        repeated = (
            "**Por que esta nota:** Avaliação estrutural de recuperação; "
            "revise o conteúdo e valide novamente."
        )
        (artifacts / "prd-validation.md").write_text(
            "# Relatório de Validação de PRD\n\n**Nota Geral:** 5.0/10\n\n"
            "## Resumo\n\nResposta incompleta.\n\n## Detalhamento por Seção\n\n"
            f"### Métricas\n\n{repeated}\n\n### Riscos\n\n{repeated}\n",
            encoding="utf-8",
        )

        page = client.get(f"/initiative/{init_id}")

        assert page.status_code == 200
        assert page.text.count("Verificação estrutural — avaliação incompleta") == 1
        assert "Avaliação estrutural de recuperação" not in page.text

    def test_records_decision_and_rejects_backlog_before_approval(self, client):
        init_id = _create_initiative(client, "Decision Flow", "INT-DECISION")
        response = client.post(
            f"/initiative/{init_id}/decisions",
            data={
                "title": "Pedir consentimento",
                "rationale": "Protege pessoas em dispositivos compartilhados.",
                "revisit_if": "A adoção ficar abaixo de 30%.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        memory = client.get("/decisions")
        assert memory.status_code == 200
        assert "Pedir consentimento" in memory.text
        assert "A adoção ficar abaixo de 30%." in memory.text

        updated = client.post(
            f"/initiative/{init_id}/decisions/DEC-001/status",
            data={"status": "superseded", "return_to": "memory"},
            follow_redirects=False,
        )
        assert updated.status_code == 303
        filtered = client.get("/decisions?status=superseded")
        assert "Pedir consentimento" in filtered.text

        blocked = client.post(
            f"/initiative/{init_id}/backlog/generate",
            follow_redirects=False,
        )
        assert "notice=backlog.specification_requires_approval" in blocked.headers["location"]

        deliverables = client.get(f"/initiative/{init_id}/deliverables")
        assert "BACKLOG · BETA" in deliverables.text
        assert "Revisar e aprovar especificação" in deliverables.text
        assert 'disabled title="Aprove uma versão' not in deliverables.text

    def test_prepares_specification_from_overview_context(self, client, session_base, monkeypatch):
        from pm_os.infrastructure.ai.clients.fake_ai_client import FakeAIClient

        monkeypatch.setattr(
            "pm_os.web.app._build_ai_client",
            lambda provider_override="": FakeAIClient(),
        )
        init_id = _create_initiative(
            client,
            "Context Based Specification",
            "INT-CONTEXT-SPEC",
        )

        response = client.post(
            f"/initiative/{init_id}/specification/prepare",
            data={"ai_provider": "demo"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert "notice=spec.prepared" in response.headers["location"]
        state_path = (
            session_base / "workspace" / "initiatives" / init_id
            / "artifacts" / "specification.json"
        )
        specification = json.loads(state_path.read_text(encoding="utf-8"))
        assert specification["sections"]["problem"]
        assert specification["sections"]["requirements"]
        assert specification["status"] == "draft"


@pytest.mark.skipif(
    os.getenv("PM_OS_RUN_OLLAMA_E2E") != "1",
    reason="requires a running local Ollama model",
)
def test_real_ollama_upload_generation_and_nonzero_validation(
    client, session_base
):
    from pm_os.infrastructure.utils import read_validation_score_from_file
    from pm_os.web.app import config_manager, job_repository

    config_manager.set("ai_provider", "ollama")
    init_id = _create_initiative(
        client,
        "E2E Real Ollama Validation",
        "INT-E2E-REAL-OLLAMA",
    )
    context = (
        "# Pesquisa com usuários\n\n"
        "8 de 10 analistas de operações descobrem rupturas de estoque tarde demais. "
        "O objetivo é reduzir em 30% o tempo médio entre a previsão de ruptura e a ação. "
        "O MVP deve enviar alertas, mostrar estoque projetado e registrar a decisão tomada. "
        "Ficam fora do escopo compras automáticas e previsão de demanda por machine learning. "
        "Riscos: alertas falsos, atraso na integração e fadiga de notificações. "
        "A aceitação exige alertas em até 5 minutos e trilha de auditoria."
    )
    uploaded = client.post(
        f"/initiative/{init_id}/upload",
        files={"docs": ("pesquisa-usuarios.md", context.encode("utf-8"), "text/markdown")},
    )
    assert uploaded.status_code == 200
    assert "pesquisa-usuarios.md" in uploaded.text

    started = client.post(
        "/generate",
        data={"initiative_name": init_id},
        headers={"x-requested-with": "fetch"},
    )
    assert started.status_code == 200
    task_id = started.json()["job_id"]

    deadline = time.monotonic() + 360
    status = {}
    while time.monotonic() < deadline:
        status = job_repository.get_for_scope(task_id, "test@pmstudio.app", "") or {}
        if status.get("done"):
            break
        time.sleep(1)

    assert status.get("done") is True, "Ollama generation exceeded six minutes"
    assert not status.get("error"), status.get("error")

    artifacts = (
        session_base / "workspace" / "initiatives" / init_id / "artifacts"
    )
    prd = (artifacts / "prd.md").read_text(encoding="utf-8")
    report_path = artifacts / "prd-validation.md"
    score = read_validation_score_from_file(report_path)

    assert len(prd) > 500
    assert score is not None
    assert score > 0


def _personal_product_docs_base(session_base: Path) -> Path:
    from pm_os.web.product_docs_service import ProductDocsService

    return ProductDocsService(
        owner_email="test@pmstudio.app",
        root_dir=session_base / "workspace" / "product-docs",
    ).base_dir


# ═══════════════════════════════════════════
# 1. ROUTE ACCESSIBILITY
# ═══════════════════════════════════════════

class TestRouteAccessibility:
    def test_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_dashboard_with_initiatives(self, client):
        _create_initiative(client)
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Test Initiative" in resp.content

    def test_generate_page(self, client):
        resp = client.get("/generate")
        assert resp.status_code == 200

    def test_consult_page(self, client):
        resp = client.get("/consult")
        assert resp.status_code == 200

    def test_config_page(self, client):
        resp = client.get("/config")
        assert resp.status_code == 200

    def test_new_initiative_page(self, client):
        resp = client.get("/initiatives/new")
        assert resp.status_code == 200

    def test_initiative_detail_not_found(self, client):
        resp = client.get("/initiative/nonexistent")
        assert resp.status_code == 404

    def test_initiative_detail_found(self, client):
        init_name = _create_initiative(client)
        resp = client.get(f"/initiative/{init_name}")
        assert resp.status_code == 200
        assert b"Test Initiative" in resp.content

    def test_validate_page_not_found(self, client):
        resp = client.get("/validate/nonexistent")
        assert resp.status_code == 404

    def test_validate_page_found(self, client):
        init_name = _create_initiative(client)
        resp = client.get(f"/validate/{init_name}")
        assert resp.status_code == 200

    def test_product_docs_page(self, client):
        resp = client.get("/product-docs")
        assert resp.status_code == 200

    def test_archived_page(self, client):
        resp = client.get("/archived")
        assert resp.status_code == 200

    def test_onboarding_show(self, client):
        resp = client.get("/onboarding/show")
        assert resp.status_code == 200


# ═══════════════════════════════════════════
# 2. INITIATIVE CRUD
# ═══════════════════════════════════════════

class TestInitiativeCRUD:
    def test_create_initiative(self, client, session_base):
        init_name = _create_initiative(client)
        dir_path = session_base / "workspace" / "initiatives" / init_name
        assert dir_path.exists()
        assert (dir_path / "metadata.yaml").exists()
        assert (dir_path / "context" / "context.md").exists()

    def test_create_duplicate_id_auto_suffix(self, client, session_base):
        _create_initiative(client, init_id="INT-DUP")
        resp = client.post("/initiatives/new", data={
            "name": "Another",
            "id": "INT-DUP",
            "status": "discovery",
        })
        assert resp.status_code == 200
        duplicated_dir = session_base / "workspace" / "initiatives" / "INT-DUP-001"
        assert duplicated_dir.exists()

    def test_upload_context_doc(self, client, session_base):
        init_name = _create_initiative(client)
        resp = client.post(
            f"/initiative/{init_name}/upload",
            files={"docs": ("Pesquisa de usuários.txt", b"Test content 123")},
        )
        assert resp.status_code == 200
        doc_path = (
            session_base
            / "workspace"
            / "initiatives"
            / init_name
            / "context"
            / "Pesquisa de usuários.txt"
        )
        assert doc_path.exists()
        assert doc_path.read_text() == "Test content 123"
        assert "Pesquisa de usuários.txt" in resp.text
        assert "Arquivo adicionado à iniciativa." in resp.text

    def test_upload_context_doc_shows_failure(self, client):
        init_name = _create_initiative(client)
        resp = client.post(
            f"/initiative/{init_name}/upload",
            files={"docs": ("arquivo.exe", b"not supported")},
        )
        assert resp.status_code == 200
        assert "Nenhum arquivo foi adicionado." in resp.text

    def test_upload_context_doc_md(self, client, session_base):
        init_name = _create_initiative(client)
        resp = client.post(
            f"/initiative/{init_name}/upload",
            files={"docs": ("test.md", b"# Test\n\nContent")},
        )
        assert resp.status_code == 200
        doc_path = session_base / "workspace" / "initiatives" / init_name / "context" / "test.md"
        assert doc_path.exists()

    def test_delete_context_doc(self, client, session_base):
        init_name = _create_initiative(client)
        doc_path = session_base / "workspace" / "initiatives" / init_name / "context" / "todelete.md"
        doc_path.write_text("# Delete me")
        resp = client.post(f"/initiative/{init_name}/delete-doc", data={"filename": "todelete.md"})
        assert resp.status_code == 200
        assert not doc_path.exists()

    def test_delete_context_doc_modal_submits_selected_filename(self, client, session_base):
        init_name = _create_initiative(client)
        context_dir = session_base / "workspace" / "initiatives" / init_name / "context"
        (context_dir / "keep.md").write_text("# Keep")
        (context_dir / "delete.md").write_text("# Delete")

        resp = client.get(f"/initiative/{init_name}")

        assert resp.status_code == 200
        assert 'id="deleteDocFilename"' in resp.text
        assert 'name="filename"' in resp.text
        assert "confirmFilename.value = filenameInput.value" in resp.text

    def test_context_metadata_file_is_not_listed_as_document(self, client, session_base):
        init_name = _create_initiative(client)
        context_dir = session_base / "workspace" / "initiatives" / init_name / "context"
        (context_dir / ".sources.yaml").write_text("sources: {}")
        (context_dir / "visible.md").write_text("# Visible")

        resp = client.get(f"/initiative/{init_name}")

        assert resp.status_code == 200
        assert "visible.md" in resp.text
        assert ".sources.yaml" not in resp.text

    def test_archive_initiative(self, client, session_base):
        init_name = _create_initiative(client)
        resp = client.post(f"/initiative/{init_name}/delete")
        assert resp.status_code == 200
        init_dir = session_base / "workspace" / "initiatives" / init_name
        assert not init_dir.exists()
        archive_dir = session_base / "workspace" / "archived"
        assert archive_dir.exists()
        archived_dirs = [d for d in archive_dir.iterdir() if d.is_dir()]
        assert len(archived_dirs) == 1
        assert init_name in archived_dirs[0].name

    def test_restore_initiative(self, client, session_base):
        init_name = _create_initiative(client)
        client.post(f"/initiative/{init_name}/delete")
        archive_dir = session_base / "workspace" / "archived"
        archived_name = next(d.name for d in archive_dir.iterdir() if d.is_dir())
        resp = client.post("/archived/restore", data={"name": archived_name})
        assert resp.status_code == 200
        init_dir = session_base / "workspace" / "initiatives" / init_name
        assert init_dir.exists()

    def test_archive_and_restore_preserves_docs(self, client, session_base):
        init_name = _create_initiative(client)
        client.post(f"/initiative/{init_name}/upload", files={"docs": ("doc1.md", b"# Doc 1")})
        client.post(f"/initiative/{init_name}/delete")
        archive_dir = session_base / "workspace" / "archived"
        archived_name = next(d.name for d in archive_dir.iterdir() if d.is_dir())
        client.post("/archived/restore", data={"name": archived_name})
        doc_path = session_base / "workspace" / "initiatives" / init_name / "context" / "doc1.md"
        assert doc_path.exists()


# ═══════════════════════════════════════════
# 3. SECURITY — PATH TRAVERSAL
# ═══════════════════════════════════════════

class TestSecurityPathTraversal:
    def test_upload_traversal_filename_with_slashes(self, client, session_base):
        """Filenames with / should not create subdirectories."""
        init_name = _create_initiative(client)
        resp = client.post(
            f"/initiative/{init_name}/upload",
            files={"docs": ("subdir/evil.md", b"malicious")},
        )
        assert resp.status_code == 200
        init_dir = session_base / "workspace" / "initiatives" / init_name
        subdir_file = init_dir / "context" / "subdir" / "evil.md"
        assert not subdir_file.exists(), "Filename with / created subdirectories!"

    def test_delete_doc_traversal_rejected(self, client, session_base):
        """Traversal in filename should not delete files outside context."""
        init_name = _create_initiative(client)
        init_dir = session_base / "workspace" / "initiatives" / init_name
        real_file = init_dir / "context" / "real.md"
        real_file.write_text("# Real")
        resp = client.post(
            f"/initiative/{init_name}/delete-doc",
            data={"filename": "../context/real.md"},
        )
        assert resp.status_code == 200
        assert real_file.exists(), "File deleted via path traversal — critical bug!"

    def test_product_docs_upload_traversal(self, client, session_base):
        """Product docs upload should not write outside product-docs/context/."""
        resp = client.post(
            "/product-docs/upload",
            files={"docs": ("../../../pwned.txt", b"malicious")},
        )
        assert resp.status_code == 200
        pwned = session_base / "pwned.txt"
        assert not pwned.exists(), "Path traversal in product-docs upload succeeded!"

    def test_create_initiative_traversal_id(self, client, session_base):
        """Initiative ID with ../ should not create directories outside initiatives."""
        resp = client.post("/initiatives/new", data={
            "name": "Traversal Test",
            "id": "../../evil",
            "status": "discovery",
        })
        assert resp.status_code == 200
        evil_dir = session_base / "evil"
        assert not evil_dir.exists(), "Traversal ID created directory outside initiatives!"

    def test_restore_traversal_rejected(self, client, session_base):
        """Archive restore should not move arbitrary directories."""
        target = session_base / "sensitive"
        target.mkdir()
        resp = client.post("/archived/restore", data={"name": "../../sensitive"})
        assert resp.status_code == 200
        assert target.exists(), "Restore moved directory outside archive via traversal!"

    def test_generate_bad_initiative(self, client):
        resp = client.post("/generate", data={"initiative_name": "INVALID"})
        assert resp.status_code == 200
        assert b"not found" in resp.content.lower() or b"n\xc3\xa3o encontrada" in resp.content


# ═══════════════════════════════════════════
# 4. PRODUCT DOCS CRUD
# ═══════════════════════════════════════════

class TestProductDocs:
    def test_upload_product_doc(self, client, session_base):
        resp = client.post(
            "/product-docs/upload",
            files={"docs": ("Visão do produto.md", b"# Guide\n\nContent")},
        )
        assert resp.status_code == 200
        doc_path = (
            _personal_product_docs_base(session_base)
            / "context"
            / "Visão do produto.md"
        )
        assert doc_path.exists()
        assert doc_path.read_text() == "# Guide\n\nContent"
        assert "Visão do produto.md" in resp.text

    def test_upload_product_doc_shows_failure(self, client):
        resp = client.post(
            "/product-docs/upload",
            files={"docs": ("arquivo.exe", b"not supported")},
        )
        assert resp.status_code == 200
        assert "Nenhum arquivo foi adicionado." in resp.text

    def test_add_link(self, client, session_base):
        resp = client.post("/product-docs/add-link", data={
            "title": "Google",
            "url": "https://google.com",
        })
        assert resp.status_code == 200
        links_file = _personal_product_docs_base(session_base) / "links.json"
        assert links_file.exists()
        links = json.loads(links_file.read_text())
        assert any(l["title"] == "Google" and l["url"] == "https://google.com" for l in links)

    def test_delete_product_doc(self, client, session_base):
        doc_path = _personal_product_docs_base(session_base) / "context" / "delete_me.md"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# Delete")
        resp = client.post("/product-docs/delete-doc/delete_me.md")
        assert resp.status_code == 200
        assert not doc_path.exists()

    def test_delete_link(self, client, session_base):
        client.post("/product-docs/add-link", data={
            "title": "To Delete",
            "url": "https://example.com/delete",
        })
        resp = client.post("/product-docs/delete-link", data={"url": "https://example.com/delete"})
        assert resp.status_code == 200
        links_file = _personal_product_docs_base(session_base) / "links.json"
        links = json.loads(links_file.read_text())
        assert not any(l["url"] == "https://example.com/delete" for l in links)

    def test_squad_docs_do_not_appear_in_personal_scope(self, client):
        client.get("/workspace/default")
        client.post(
            "/product-docs/upload",
            files={"docs": ("squad-only.md", b"# Squad only")},
        )
        squad_page = client.get("/product-docs")

        client.get("/workspace/personal")
        personal_page = client.get("/product-docs")

        assert "squad-only.md" in squad_page.text
        assert "squad-only.md" not in personal_page.text


# ═══════════════════════════════════════════
# 5. AUTHENTICATION
# ═══════════════════════════════════════════

class TestAuth:
    USER_EMAIL = "test@example.com"
    USER_PASS = "secret123"

    def _enable_auth(self, session_base: Path) -> None:
        """Write minimal auth config with one user."""
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        cfg["auth_bypass_localhost"] = False
        import hashlib
        cfg["users"] = {self.USER_EMAIL: hashlib.sha256(self.USER_PASS.encode()).hexdigest()}
        cfg["squads"] = {"default": {"display_name": "Default", "password_hash": hashlib.sha256("squad123".encode()).hexdigest(), "members": [self.USER_EMAIL], "created_by": self.USER_EMAIL, "created_at": "2024-01-01"}}
        (session_base / ".pm_os" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self._sync_live_config(cfg)

    def _sync_live_config(self, cfg: dict) -> None:
        """Sync live config_manager with given config dict."""
        import pm_os.web.app as _web_app
        for k, v in cfg.items():
            _web_app.config_manager.set(k, v)

    def _add_pending_registration(self) -> None:
        import pm_os.web.app as web_app

        web_app.config_manager.set(
            "pending_registrations",
            {
                self.USER_EMAIL: {
                    "password_hash": "pending-password-hash",
                    "code_digest": "pending-code-digest",
                    "expires_at": time.time() + 600,
                    "attempts": 0,
                    "last_sent_at": 0,
                }
            },
        )

    def test_register_page_renders(self, unauth_client, session_base):
        self._enable_auth(session_base)
        resp = unauth_client.get("/register")
        assert resp.status_code == 200
        assert b"Criar Conta" in resp.content or b"Create Account" in resp.content

    def test_register_creates_user(self, unauth_client, session_base):
        self._enable_auth(session_base)
        # Clear existing users so register flow works
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        cfg["users"] = {}
        (session_base / ".pm_os" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self._sync_live_config(cfg)

        resp = unauth_client.post("/register", data={
            "email": "new@example.com",
            "password": "mypassword1",
        })
        assert resp.status_code == 200  # redirects to login page
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        assert "new@example.com" in cfg["users"]
        from pm_os.infrastructure.security import verify_password
        assert verify_password(cfg["users"]["new@example.com"], "mypassword1")[0]

    def test_register_rejects_existing_email(self, unauth_client, session_base):
        self._enable_auth(session_base)
        resp = unauth_client.post("/register", data={
            "email": self.USER_EMAIL,
            "password": self.USER_PASS,
        })
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "já está cadastrado" in content or "already registered" in content

    def test_register_rejects_short_password(self, unauth_client, session_base):
        self._enable_auth(session_base)
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        cfg["users"] = {}
        (session_base / ".pm_os" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self._sync_live_config(cfg)

        resp = unauth_client.post("/register", data={
            "email": "new@example.com",
            "password": "ab",
        })
        assert resp.status_code == 200
        assert b"10 caracteres" in resp.content or b"10 characters" in resp.content

    def test_register_rejects_invalid_email(self, unauth_client, session_base):
        self._enable_auth(session_base)
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        cfg["users"] = {}
        (session_base / ".pm_os" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self._sync_live_config(cfg)

        resp = unauth_client.post("/register", data={
            "email": "not-an-email",
            "password": "secret123",
        })
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "e-mail válido" in content or "informe um e-mail válido" in content or "Enter a valid email" in content

    def test_smtp_registration_activates_account_only_after_verification(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        captured = {}
        from pm_os.web import email_service

        monkeypatch.setattr(email_service, "is_smtp_configured", lambda cfg: True)
        monkeypatch.setattr(
            email_service,
            "send_verification_email",
            lambda cfg, email, code: captured.update(email=email, code=code) or True,
        )
        email = "pending@example.com"

        response = unauth_client.post(
            "/register",
            data={"email": email, "password": "newpassword1"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        assert email not in cfg["users"]
        assert email in cfg["pending_registrations"]
        assert captured["code"] not in json.dumps(cfg)

        invalid_login = unauth_client.post(
            "/login",
            data={"email": email, "password": "newpassword1"},
        )
        assert invalid_login.status_code == 200

        verified = unauth_client.post(
            "/verify",
            data={"email": email, "code": captured["code"]},
        )

        assert verified.status_code == 200
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        assert email in cfg["users"]
        assert email not in cfg["pending_registrations"]

    def test_verification_invalid_attempts_cancel_pending_registration(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        from pm_os.web import email_service

        captured = {}
        monkeypatch.setattr(email_service, "is_smtp_configured", lambda cfg: True)
        monkeypatch.setattr(
            email_service,
            "send_verification_email",
            lambda cfg, email, code: captured.update(code=code) or True,
        )
        email = "attempts@example.com"
        unauth_client.post(
            "/register",
            data={"email": email, "password": "newpassword1"},
        )
        wrong_code = "000000" if captured["code"] != "000000" else "111111"

        for _ in range(5):
            response = unauth_client.post(
                "/verify",
                data={"email": email, "code": wrong_code},
            )

        assert "Muitas tentativas" in response.text
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        assert email not in cfg["pending_registrations"]

    def test_login_page_renders(self, unauth_client, session_base):
        self._enable_auth(session_base)
        resp = unauth_client.get("/login")
        assert resp.status_code == 200
        assert b"E-mail" in resp.content or b"Email" in resp.content

    def test_untrusted_host_is_rejected(self, unauth_client, session_base):
        self._enable_auth(session_base)

        response = unauth_client.get(
            "/login",
            headers={"Host": "attacker.example.com"},
        )

        assert response.status_code == 400

    def test_login_success(self, unauth_client, session_base):
        self._enable_auth(session_base)
        resp = unauth_client.post("/login", data={
            "email": self.USER_EMAIL,
            "password": self.USER_PASS,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/"

    def test_login_failure(self, unauth_client, session_base):
        self._enable_auth(session_base)
        resp = unauth_client.post("/login", data={
            "email": self.USER_EMAIL,
            "password": "wrongpassword",
        })
        assert resp.status_code == 200  # re-renders login page with error
        assert b"Invalid" in resp.content or b"inv" in resp.content

    def test_successful_logins_do_not_trigger_rate_limit(
        self, unauth_client, session_base
    ):
        self._enable_auth(session_base)
        for _ in range(11):
            resp = unauth_client.post(
                "/login",
                data={"email": self.USER_EMAIL, "password": self.USER_PASS},
                follow_redirects=False,
            )
            assert resp.status_code == 302

    def test_forwarded_ip_is_ignored_without_trusted_proxy(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        monkeypatch.delenv("PM_OS_TRUSTED_PROXY_COUNT", raising=False)
        import pm_os.web.app as web_app

        captured = []

        class CapturingLimiter:
            def is_blocked(self, client_key):
                captured.append(client_key)
                return False

            def record_failure(self, _client_key):
                pass

            def reset(self, _client_key):
                pass

        monkeypatch.setattr(web_app, "_login_rate_limiter", CapturingLimiter())
        unauth_client.post(
            "/login",
            data={"email": self.USER_EMAIL, "password": self.USER_PASS},
            headers={"X-Forwarded-For": "198.51.100.5"},
        )

        assert captured == ["unknown"]

    def test_password_reset_sends_expiring_link_and_updates_password(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        captured = {}
        from pm_os.web import email_service

        monkeypatch.setattr(email_service, "is_smtp_configured", lambda cfg: True)
        monkeypatch.setattr(
            email_service,
            "send_password_reset_email",
            lambda cfg, email, url: captured.update(email=email, url=url) or True,
        )

        resp = unauth_client.post(
            "/forgot",
            data={"email": self.USER_EMAIL},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert captured["email"] == self.USER_EMAIL
        assert "/reset?" in captured["url"]

        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(captured["url"]).query)
        token = params["token"][0]
        raw_config = (session_base / ".pm_os" / "config.json").read_text()
        assert token not in raw_config
        resp = unauth_client.post(
            "/reset",
            data={
                "email": self.USER_EMAIL,
                "token": token,
                "password": "newpassword1",
                "confirm": "newpassword1",
            },
        )
        assert resp.status_code == 200
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        from pm_os.infrastructure.security import verify_password
        assert verify_password(cfg["users"][self.USER_EMAIL], "newpassword1")[0]
        assert token not in cfg["reset_tokens"]

    def test_password_reset_uses_configured_public_url(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        captured = {}
        from pm_os.web import email_service

        monkeypatch.setenv("PM_OS_PUBLIC_URL", "https://pm.example.com/studio/")
        monkeypatch.setattr(email_service, "is_smtp_configured", lambda cfg: True)
        monkeypatch.setattr(
            email_service,
            "send_password_reset_email",
            lambda cfg, email, url: captured.update(url=url) or True,
        )

        response = unauth_client.post(
            "/forgot",
            data={"email": self.USER_EMAIL},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert captured["url"].startswith(
            "https://pm.example.com/studio/reset?"
        )

    def test_verify_resend_generates_a_new_code(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        self._add_pending_registration()
        sent = {}
        from pm_os.web import email_service

        monkeypatch.setattr(email_service, "is_smtp_configured", lambda cfg: True)
        monkeypatch.setattr(
            email_service,
            "send_verification_email",
            lambda cfg, email, code: sent.update(email=email, code=code) or True,
        )
        resp = unauth_client.post(
            "/verify/resend",
            data={"email": self.USER_EMAIL},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert sent["email"] == self.USER_EMAIL
        assert len(sent["code"]) == 6

    def test_verify_resend_reports_delivery_failure(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        self._add_pending_registration()
        from pm_os.web import email_service

        monkeypatch.setattr(email_service, "is_smtp_configured", lambda cfg: True)
        monkeypatch.setattr(
            email_service, "send_verification_email", lambda *_args: False
        )

        resp = unauth_client.post(
            "/verify/resend",
            data={"email": self.USER_EMAIL},
            follow_redirects=False,
        )

        assert resp.status_code == 302
        assert "sent=0" in resp.headers["location"]
        page = unauth_client.get(resp.headers["location"])
        assert "Não foi possível enviar" in page.text

    def test_password_reset_reports_delivery_failure(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
        from pm_os.web import email_service

        monkeypatch.setattr(email_service, "is_smtp_configured", lambda cfg: True)
        monkeypatch.setattr(
            email_service, "send_password_reset_email", lambda *_args: False
        )

        resp = unauth_client.post("/forgot", data={"email": self.USER_EMAIL})

        assert resp.status_code == 200
        assert "Não foi possível enviar" in resp.text

    def test_auth_middleware_blocks_unauthenticated(self, unauth_client, session_base):
        self._enable_auth(session_base)
        resp = unauth_client.get("/generate", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/login"

    def test_auth_middleware_allows_authenticated(self, unauth_client, session_base):
        self._enable_auth(session_base)
        # Login first to get session cookie
        login_resp = unauth_client.post("/login", data={
            "email": self.USER_EMAIL,
            "password": self.USER_PASS,
        }, follow_redirects=False)
        assert login_resp.status_code == 302
        # Follow redirect (this sets the session cookie)
        resp = unauth_client.get("/", follow_redirects=True)
        assert resp.status_code == 200

    def test_redirects_to_register_when_no_users(self, unauth_client, session_base):
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        cfg["users"] = {}  # No users
        (session_base / ".pm_os" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self._sync_live_config(cfg)

        resp = unauth_client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/register"

    def test_register_redirects_to_login_when_authenticated(self, unauth_client, session_base):
        self._enable_auth(session_base)
        # Login first
        unauth_client.post("/login", data={
            "email": self.USER_EMAIL,
            "password": self.USER_PASS,
        })
        resp = unauth_client.get("/register", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/"

    def test_logout_clears_session(self, unauth_client, session_base):
        self._enable_auth(session_base)
        unauth_client.post("/login", data={
            "email": self.USER_EMAIL,
            "password": self.USER_PASS,
        })
        resp = unauth_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/login"


# ═══════════════════════════════════════════
# 6. CONFIGURATION
# ═══════════════════════════════════════════

class TestConfiguration:
    def test_save_config(self, client, session_base):
        resp = client.post("/config", data={
            "model": "gemma4:e2b",
            "ollama_url": "http://localhost:11434",
            "lang": "en",
            "auth_bypass_localhost": "true",
        })
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert cfg["model"] == "gemma4:e2b"
        assert cfg["lang"] == "en"

    def test_add_mcp_server(self, client, session_base):
        resp = client.post("/config/mcp/add", data={
            "name": "Test Server",
            "url": "http://mcp-test.example.com/mcp",
        })
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert len(cfg["mcp_servers"]) == 1
        assert cfg["mcp_servers"][0]["name"] == "Test Server"
        assert cfg["mcp_servers"][0]["type"] == "legacy_http"

    def test_add_businessmap_preset(self, client, session_base):
        response = client.post("/config/mcp/add", data={
            "name": "Businessmap",
            "preset": "businessmap",
            "businessmap_subdomain": "acme",
        })
        assert response.status_code == 200
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        server = cfg["mcp_servers"][0]
        assert server["url"] == "https://acme.businessmap.io/baiApi/v1/mcp"
        assert server["auth"]["type"] == "oauth"
        assert server["policy"]["mode"] == "read_only"
        assert server["status"]["state"] == "authorization_required"

    def test_adds_generic_stdio_server_and_protects_environment(
        self, client, session_base
    ):
        response = client.post("/config/mcp/add", data={
            "name": "Local Files",
            "transport": "stdio",
            "command": "npx",
            "stdio_args": "-y\n@modelcontextprotocol/server-filesystem\n/tmp/docs",
            "stdio_env": "PRIVATE_TOKEN=stdio-secret",
            "policy_mode": "read_only",
        })

        assert response.status_code == 200
        raw = (session_base / ".pm_os" / "config.json").read_text()
        assert "stdio-secret" not in raw
        cfg = json.loads(raw)
        server = cfg["mcp_servers"][0]
        assert server["type"] == "stdio"
        assert server["transport"] == "stdio"
        assert server["command"] == "npx"
        assert server["args"] == [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "/tmp/docs",
        ]

    def test_mcp_secret_is_encrypted_and_not_rendered(self, client, session_base):
        response = client.post("/config/mcp/add", data={
            "name": "Private MCP",
            "url": "https://mcp.example/mcp",
            "preset": "custom",
            "auth_type": "bearer",
            "auth_secret": "very-secret-token",
        })
        raw = (session_base / ".pm_os" / "config.json").read_text()
        assert "very-secret-token" not in raw
        assert "very-secret-token" not in response.text

    def test_persists_sanitized_mcp_discovery(self, client, session_base):
        discovery = {
            "protocol_version": "2025-06-18",
            "server_name": "Example",
            "server_version": "1.0",
            "tools": [{"name": "search", "description": "Search docs"}],
            "resources_supported": True,
            "prompts_supported": False,
            "ignored": "not persisted",
        }
        response = client.post("/config/mcp/add", data={
            "name": "Discovered MCP",
            "url": "https://mcp.example/mcp",
            "connection_type": "mcp",
            "preset": "custom",
            "discovery_json": json.dumps(discovery),
        })
        assert response.status_code == 200
        cfg = json.loads((session_base / ".pm_os" / "config.json").read_text())
        server = cfg["mcp_servers"][0]
        assert server["status"]["state"] == "connected"
        assert server["capabilities"]["tools"][0]["name"] == "search"
        assert "ignored" not in server["capabilities"]

    def test_save_gateway_config(self, client, session_base):
        response = client.post("/config", data={
            "model": "llama3.2:1b",
            "ollama_url": "http://localhost:11434",
            "lang": "pt-BR",
            "ai_provider": "gateway",
            "gateway_url": "https://gateway.example/v1",
            "gateway_provider": "openai",
            "gateway_project_id": "pm-studio",
            "gateway_identifier": "gpt-prod",
            "gateway_api_key": "secret-token",
        })

        assert response.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert cfg["ai_provider"] == "gateway"
        assert cfg["gateway_project_id"] == "pm-studio"
        assert cfg["gateway_identifier"] == "gpt-prod"
        assert cfg["gateway_api_key"] != "secret-token"

    def test_rejects_incomplete_gateway_config(self, client):
        response = client.post("/config", data={
            "model": "llama3.2:1b",
            "ollama_url": "http://localhost:11434",
            "lang": "pt-BR",
            "ai_provider": "gateway",
            "gateway_url": "not-a-url",
        })

        assert response.status_code == 422
        assert "gateway" in response.text.lower()

    def test_gateway_connection_test_succeeds(
        self,
        client,
        monkeypatch,
    ):
        monkeypatch.setattr(
            "pm_os.web.app.GatewayClient.generate",
            lambda self, prompt: "OK",
        )
        response = client.post("/config/gateway/test", data={
            "gateway_url": "https://gateway.example/v1",
            "gateway_provider": "openai",
            "gateway_project_id": "pm-studio",
            "gateway_identifier": "gpt-prod",
        })

        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_gateway_connection_test_returns_safe_diagnostic(
        self,
        client,
        monkeypatch,
    ):
        def reject(_self, _prompt):
            from pm_os.contracts.workflow_contracts import (
                AIProviderError,
            )
            raise AIProviderError(
                "Gateway credentials were rejected."
            )

        monkeypatch.setattr(
            "pm_os.web.app.GatewayClient.generate",
            reject,
        )
        response = client.post("/config/gateway/test", data={
            "gateway_url": "https://gateway.example/v1",
            "gateway_provider": "openai",
            "gateway_project_id": "pm-studio",
            "gateway_identifier": "gpt-prod",
        })

        assert response.status_code == 422
        assert response.json() == {
            "ok": False,
            "message": "Gateway credentials were rejected.",
        }

    def test_base_page_exposes_favicon(self, client):
        response = client.get("/")
        favicon = client.get("/static/favicon.svg")

        assert 'href="/static/favicon.svg"' in response.text
        assert favicon.status_code == 200

    def test_toggle_mcp_server(self, client, session_base):
        client.post("/config/mcp/add", data={
            "name": "Toggle Me",
            "url": "http://mcp-test.example.com/mcp",
        })
        resp = client.post("/config/mcp/toggle", data={"url": "http://mcp-test.example.com/mcp"})
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        server = next(s for s in cfg["mcp_servers"] if s["url"] == "http://mcp-test.example.com/mcp")
        assert server["enabled"] is False

    def test_delete_mcp_server(self, client, session_base):
        client.post("/config/mcp/add", data={
            "name": "Delete Me",
            "url": "http://mcp-test.example.com/mcp",
        })
        resp = client.post("/config/mcp/delete", data={"url": "http://mcp-test.example.com/mcp"})
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert len(cfg["mcp_servers"]) == 0


# ═══════════════════════════════════════════
# 7. CONSULT / Q&A
# ═══════════════════════════════════════════

class TestConsult:
    def test_consult_page(self, client):
        resp = client.get("/consult")
        assert resp.status_code == 200

    def test_consult_without_initiatives(self, client):
        resp = client.post("/consult", data={
            "question": "What is PM OS?",
            "initiatives": [],
            "use_product_docs": False,
        })
        assert resp.status_code == 200


# ═══════════════════════════════════════════
# 8. ONBOARDING
# ═══════════════════════════════════════════

class TestOnboarding:
    def test_onboarding_dismiss(self, client, session_base):
        resp = client.post("/onboarding/dismiss")
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert cfg["onboarding_dismissed"] is True

    def test_onboarding_show_resets_dismissed(self, client, session_base):
        client.post("/onboarding/dismiss")
        resp = client.get("/onboarding/show")
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert cfg["onboarding_dismissed"] is False

    def test_tour_dismiss_includes_csrf_token(self, client):
        dashboard = client.get("/")
        assert '<meta name="csrf-token"' in dashboard.text

        tour = client.get("/static/tour.js")
        assert tour.status_code == 200
        assert 'meta[name="csrf-token"]' in tour.text
        assert "csrfInput.name = 'csrf_token'" in tour.text


# ═══════════════════════════════════════════
# 9. TEMPLATE CONTENT CHECKS
# ═══════════════════════════════════════════

class TestTemplateContent:
    def test_generate_progress_has_complete_responsive_component(self, client):
        _create_initiative(client)
        response = client.get("/generate")
        assert response.status_code == 200
        assert "Organizando as fontes" in response.text
        assert "Gerando o documento" in response.text
        assert "generate.stepper_" not in response.text

        stylesheet = client.get("/static/style.css")
        assert stylesheet.status_code == 200
        assert ".prd-progress-track" in stylesheet.text
        assert ".prd-step.is-active" in stylesheet.text
        assert "@media (max-width: 640px)" in stylesheet.text

    def test_upload_fields_explain_and_validate_filename_rules(self, client):
        product_docs = client.get("/product-docs")
        assert product_docs.status_code == 200
        assert "Acentos são aceitos" in product_docs.text
        assert "PMOS.validateUploadFiles(this)" in product_docs.text

        init_name = _create_initiative(client)
        initiative = client.get(f"/initiative/{init_name}")
        assert initiative.status_code == 200
        assert "Acentos são aceitos" in initiative.text
        assert "PMOS.validateUploadFiles(this)" in initiative.text

    def test_dashboard_shows_initiative_names(self, client):
        _create_initiative(client, name="Alpha Initiative")
        _create_initiative(client, name="Beta Initiative")
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Alpha Initiative" in resp.content
        assert b"Beta Initiative" in resp.content

    def test_dashboard_empty_state(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Nenhuma iniciativa" in resp.content or b"No initiatives" in resp.content

    def test_dashboard_shows_attention_panel(self, client, session_base):
        init_name = _create_initiative(client, name="Old Initiative")
        import yaml
        meta_path = session_base / "workspace" / "initiatives" / init_name / "metadata.yaml"
        meta = yaml.safe_load(meta_path.read_text())
        meta["created_at"] = "2024-01-01"
        meta_path.write_text(yaml.dump(meta, default_flow_style=False, allow_unicode=True), encoding="utf-8")
        resp = client.get("/")
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Precisa de aten" in content or "Needs attention" in content

    def test_initiative_detail_shows_display_name(self, client):
        init_name = _create_initiative(client, name="My Display Name")
        resp = client.get(f"/initiative/{init_name}")
        assert resp.status_code == 200
        assert b"My Display Name" in resp.content

    def test_archived_page_with_archived_initiative(self, client, session_base):
        init_name = _create_initiative(client, name="To Archive")
        client.post(f"/initiative/{init_name}/delete")
        resp = client.get("/archived")
        assert resp.status_code == 200
        # The archived page shows the archive folder name, not the display name
        # Archive folder format is: init_name_timestamp
        # Check that the init_name appears in some form
        assert b"To Archive" in resp.content or init_name.encode() in resp.content


# ═══════════════════════════════════════════
# 10. ERROR HANDLING
# ═══════════════════════════════════════════

class TestErrorHandling:
    def test_404_for_unknown_initiative(self, client):
        resp = client.get("/initiative/does-not-exist")
        assert resp.status_code == 404

    def test_404_for_unknown_validate(self, client):
        resp = client.get("/validate/does-not-exist")
        assert resp.status_code == 404

    def test_delete_doc_nonexistent(self, client):
        init_name = _create_initiative(client)
        resp = client.post(f"/initiative/{init_name}/delete-doc", data={"filename": "ghost.md"})
        assert resp.status_code == 200

    def test_product_docs_delete_nonexistent(self, client):
        resp = client.post("/product-docs/delete-doc/ghost.md")
        assert resp.status_code == 200

    def test_restore_nonexistent(self, client):
        resp = client.post("/archived/restore", data={"name": "ghost_20240101_000000"})
        assert resp.status_code == 200


# ═══════════════════════════════════════════
# 10. TODAY'S CHANGES (Jul 17)
# ═══════════════════════════════════════════

@pytest.fixture
def no_ai_client(client, monkeypatch):
    """Client with AI disabled to avoid timeouts on PRD generation."""
    from pm_os.infrastructure.ai.clients.ollama_client import OllamaConnectionError

    def _mock_build():
        raise OllamaConnectionError()

    import pm_os.web.app
    monkeypatch.setattr(pm_os.web.app, "_build_ai_client", _mock_build)
    yield client


class TestQuickstartFlow:
    """Quickstart: redirect, metadata, banner."""

    def test_quickstart_redirects_to_initiative(self, no_ai_client):
        """Quickstart should redirect to the initiative page, not dashboard."""
        resp = no_ai_client.post("/quickstart", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/initiative/INT-QUICKSTART" in resp.headers.get("location", "")

    def test_quickstart_creates_initiative_with_squad(self, no_ai_client):
        """Quickstart metadata must include the 'squad' field."""
        no_ai_client.post("/quickstart")
        meta_path = Path("workspace/initiatives/INT-QUICKSTART/metadata.yaml")
        assert meta_path.exists(), f"Metadata not found at {meta_path}"
        import yaml
        meta = yaml.safe_load(meta_path.read_text())
        assert "squad" in meta, "Metadata missing 'squad' field"
        assert meta["squad"] == "", "Personal squad metadata should be empty string"

    def test_quickstart_creates_context_docs(self, no_ai_client):
        """Quickstart should copy fake-context files."""
        no_ai_client.post("/quickstart")
        ctx_dir = Path("workspace/initiatives/INT-QUICKSTART/context")
        assert ctx_dir.exists()
        files = list(ctx_dir.iterdir())
        assert len(files) > 0, "No context files copied by quickstart"

    def test_quickstart_detail_has_banner(self, no_ai_client):
        """Initiative detail with ?quickstart=1 shows success banner."""
        no_ai_client.post("/quickstart")
        resp = no_ai_client.get("/initiative/INT-QUICKSTART?quickstart=1")
        assert resp.status_code == 200
        assert "Iniciativa de exemplo" in resp.text or "quickstart.success" in resp.text or "PRD" in resp.text

    def test_quickstart_with_squad_context(self, no_ai_client):
        """Quickstart in a squad context sets squad metadata."""
        # Switch to default squad via workspace
        no_ai_client.get("/workspace/default", follow_redirects=False)
        resp = no_ai_client.post("/quickstart", follow_redirects=False)
        assert resp.status_code in (302, 303)
        # Clean up
        import shutil
        shutil.rmtree("workspace/initiatives/INT-QUICKSTART", ignore_errors=True)


class TestSquadAdminRename:
    """Squad admin rename functionality."""

    def test_admin_page_has_rename_form(self, client):
        """Squad admin page should contain a rename form."""
        resp = client.get("/squad/admin/default")
        assert resp.status_code == 200
        assert "change display name" in resp.text.lower() or "alterar nome" in resp.text.lower()
        assert 'name="display_name"' in resp.text

    def test_rename_squad_as_admin(self, client):
        """Admin can rename squad display_name."""
        resp = client.post("/squad/admin/default/rename", data={"display_name": "Novo Nome"}, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location", "").endswith("/squad/admin/default")
        # Verify the name was updated in test config
        cfg = json.loads((Path(os.environ["PM_OS_CONFIG_DIR"]) / "config.json").read_text())
        assert cfg["squads"]["default"]["display_name"] == "Novo Nome"

    def test_rename_fails_for_non_admin(self, unauth_client):
        """Non-admin cannot rename squad (should redirect to login)."""
        # Login as different user not in squad
        resp = unauth_client.post("/squad/admin/default/rename", data={"display_name": "Hack"}, follow_redirects=False)
        assert resp.status_code == 302  # redirects to login because not authenticated


class TestGeneratePreSelection:
    """Generate page pre-selection via ?initiative= query param."""

    def test_generate_page_loads(self, client, session_base):
        """Generate page renders successfully."""
        _create_initiative(client, name="Alpha")
        resp = client.get("/generate")
        assert resp.status_code == 200

    def test_generate_with_initiative_query(self, client, session_base):
        """?initiative=INT-XXX pre-selects the initiative in the <select>."""
        _create_initiative(client, name="Alpha", init_id="INT-ALPHA")
        _create_initiative(client, name="Beta", init_id="INT-BETA")
        resp = client.get("/generate?initiative=INT-ALPHA")
        assert resp.status_code == 200
        assert 'value="INT-ALPHA"' in resp.text
        # The selected initiative should show as selected in the dropdown
        assert "INT-ALPHA" in resp.text

    def test_generate_lists_individual_source_controls(self, client, session_base):
        _create_initiative(client, name="Alpha", init_id="INT-SOURCES")
        resp = client.get("/generate?initiative=INT-SOURCES")

        assert resp.status_code == 200
        assert 'name="selected_source_ids"' in resp.text
        assert "gen-source" in resp.text
        assert "Fontes incluídas" in resp.text or "Included sources" in resp.text

    def test_demo_mode_does_not_pretend_to_read_uploaded_files(self, client):
        init_id = _create_initiative(client, "Demo upload", "INT-DEMO-UPLOAD")
        client.post(
            f"/initiative/{init_id}/upload",
            files={"docs": ("pesquisa.md", b"Contexto exclusivo do upload")},
        )

        response = client.post(
            "/generate",
            data={"initiative_name": init_id},
        )

        assert response.status_code == 422
        assert "modo Demo não lê o conteúdo dos arquivos" in response.text

        fetch_response = client.post(
            "/generate",
            data={"initiative_name": init_id},
            headers={"X-Requested-With": "fetch"},
        )
        assert fetch_response.status_code == 422
        assert "modo Demo não lê" in fetch_response.json()["error"]

    def test_uploaded_file_content_reaches_prd_prompt(
        self, client, monkeypatch
    ):
        from pm_os.web.app import config_manager, job_repository

        class RecordingAIClient:
            def __init__(self):
                self.prompts = []

            def generate(self, prompt):
                self.prompts.append(prompt)
                if "Avalie a qualidade" in prompt or "Evaluate the quality" in prompt:
                    return '{"overall_score": 8, "sections": []}'
                return "# PRD contextual\n\nConteúdo fundamentado na pesquisa enviada."

        recording = RecordingAIClient()
        config_manager.set("ai_provider", "ollama")
        monkeypatch.setattr(
            "pm_os.web.app._build_ai_client",
            lambda provider_override="": recording,
        )
        init_id = _create_initiative(client, "Prompt upload", "INT-PROMPT-UPLOAD")
        unique_context = "CLIENTES-ALFA precisam reduzir o cadastro de 14 para 5 minutos."
        client.post(
            f"/initiative/{init_id}/upload",
            files={"docs": ("entrevistas.md", unique_context.encode("utf-8"))},
        )
        source_id = "SRC-" + hashlib.sha256(
            f"{init_id}/entrevistas.md".encode("utf-8")
        ).hexdigest()[:8].upper()

        response = client.post(
            "/generate",
            data={
                "initiative_name": init_id,
                "source_selection_enabled": "true",
                "selected_source_ids": source_id,
            },
            headers={"X-Requested-With": "fetch"},
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        task = None
        for _ in range(80):
            task = job_repository.get_for_scope(job_id, "test@pmstudio.app", "")
            if task and task["done"]:
                break
            time.sleep(0.05)

        assert task and task["done"] is True
        assert task["error"] is None
        assert unique_context in recording.prompts[0]


class TestGenerateAdditionalContext:
    """Additional context UX improvements on generate page."""

    def test_additional_context_hides_main(self, client, session_base):
        """The main selected initiative should be hidden from additional context."""
        _create_initiative(client, name="Alpha", init_id="INT-ALPHA")
        _create_initiative(client, name="Beta", init_id="INT-BETA")
        resp = client.get("/generate?initiative=INT-ALPHA")
        assert resp.status_code == 200
        # INT-BETA should be visible in the additional list (not hidden)
        assert "INT-BETA" in resp.text
        # The section should indicate "1 available" (only Beta remains)
        assert "1" in resp.text

    def test_additional_context_shows_doc_counts(self, client, session_base):
        """Checkboxes should show document counts or 'sem docs'."""
        _create_initiative(client, name="Alpha", init_id="INT-ALPHA")
        _create_initiative(client, name="Beta", init_id="INT-BETA")
        resp = client.get("/generate")
        assert resp.status_code == 200
        # Should have the additional context section with checkboxes
        assert 'type="checkbox"' in resp.text
        assert "gen-extra" in resp.text


class TestGenerationJobIsolation:
    def test_generation_job_is_persisted_through_completion(self, client):
        from pm_os.web.app import job_repository

        _create_initiative(client, name="Persistent", init_id="INT-PERSISTENT")
        response = client.post(
            "/generate",
            data={"initiative_name": "INT-PERSISTENT"},
            headers={"X-Requested-With": "fetch"},
        )
        job_id = response.json()["job_id"]

        task = None
        for _ in range(40):
            task = job_repository.get_for_scope(job_id, "test@pmstudio.app", "")
            if task and task["done"]:
                break
            time.sleep(0.05)

        assert task is not None
        assert task["done"] is True
        assert task["error"] is None
        assert task["result"]["initiative"] == "INT-PERSISTENT"
        assert task["result"]["prd"].startswith("# PRD demonstrativo")

    def test_status_only_returns_jobs_owned_by_current_scope(self, client):
        from pm_os.web.app import job_repository

        payload = {
            "steps": [],
            "step": 1,
            "message": "Private",
            "done": False,
            "error": None,
            "result": None,
        }
        job_repository.create("owned-job", "test@pmstudio.app", "", payload)
        job_repository.create("foreign-job", "other@pmstudio.app", "", payload)

        owned = client.get("/generate/status/owned-job")
        foreign = client.get("/generate/status/foreign-job")

        assert owned.status_code == 200
        assert owned.json()["message"] == "Private"
        assert foreign.status_code == 200
        assert foreign.json() == {"error": "not_found"}

    def test_result_only_returns_jobs_from_current_squad(self, client):
        from pm_os.web.app import job_repository

        payload = {
            "steps": [],
            "step": 4,
            "message": "",
            "done": True,
            "error": None,
            "result": {"prd": "Secret", "initiative": "INT-X"},
        }
        job_repository.create("other-squad-job", "test@pmstudio.app", "other", payload)

        response = client.get("/generate/result/other-squad-job?fragment=1")

        assert response.status_code == 200
        assert "Secret" not in response.text


class TestInitiativeCreationPage:
    """Initiative creation page UX improvements."""

    def test_new_initiative_page_shows_workspace(self, client):
        """Page should show 'em Pessoal' or current squad."""
        resp = client.get("/initiatives/new")
        assert resp.status_code == 200
        assert "Observa" in resp.text  # "Observações" label
        assert "Pessoal" in resp.text  # Workspace indicator

    def test_new_initiative_has_status_chips(self, client):
        """Status should be rendered as clickable chips."""
        resp = client.get("/initiatives/new")
        assert resp.status_code == 200
        assert 'type="radio"' in resp.text
        assert "status-chip" in resp.text

    def test_new_initiative_auto_generates_id(self, client):
        """JS must be present for auto-ID generation."""
        resp = client.get("/initiatives/new")
        assert resp.status_code == 200
        assert "auto-gerado" in resp.text or "document.getElementById('name')" in resp.text


class TestDashboardEmptyState:
    """Dashboard empty state and workspace selector."""

    def test_empty_state_has_workspace_selector(self, client):
        """Empty state dashboard should show workspace selector."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Espaço de trabalho:" in resp.text

    def test_empty_state_has_quickstart_button(self, client):
        """Empty state should have the quickstart button."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "/quickstart" in resp.text
        assert "Quickstart" in resp.text

    def test_empty_state_has_example_hint(self, client):
        """Empty state should show the example hint text."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "exemplo" in resp.text.lower() or "explorar" in resp.text.lower()

    def test_workspace_selector_shows_personal(self, client):
        """Workspace selector should show 'Pessoal' button."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "/workspace/personal" in resp.text

    def test_workspace_selector_shows_squads(self, client):
        """Workspace selector should show available squads."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "/workspace/default" in resp.text
        assert "Default" in resp.text

    def test_dashboard_exposes_recent_capabilities_and_version(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert 'href="/signals"' in response.text
        assert 'href="/decisions"' in response.text
        assert 'href="/config#plugins"' in response.text
        assert "PM Studio v0.2.0" in response.text


class TestGenerateLinks:
    """Navigation links pointing to generate page with initiative param."""

    def test_attention_panel_links_to_generate_with_initiative(self, client, session_base):
        """Detail page 'Gerar documentação' button should include ?initiative=."""
        init_id = _create_initiative(client, name="Old Initiative")
        resp = client.get(f"/initiative/{init_id}")
        assert resp.status_code == 200
        # The link should be present somewhere (attention panel or detail page generate button)
        assert "/generate?initiative=" in resp.text

    def test_detail_page_links_to_generate_with_initiative(self, client, session_base):
        """Initiative detail page 'Gerar documentação' should include ?initiative=."""
        init_id = _create_initiative(client)
        resp = client.get(f"/initiative/{init_id}")
        assert resp.status_code == 200
        assert f"/generate?initiative={init_id}" in resp.text

    def test_generate_link_on_detail_in_topbar(self, client, session_base):
        """The generate button should be in the topbar actions."""
        init_id = _create_initiative(client)
        resp = client.get(f"/initiative/{init_id}")
        assert resp.status_code == 200
        assert "Gerar requisitos" in resp.text or "Generate" in resp.text


class TestSquadCRUD:
    """Squad management CRUD."""

    def test_create_and_join_squad(self, client):
        """Create a squad via the API."""
        resp = client.post("/squad/create", data={
            "name": "test-squad",
            "display_name": "Test Squad",
            "password": "squadpass",
        }, follow_redirects=False)
        assert resp.status_code in (302, 303)
        # Verify squad exists in config
        import json
        cfg = json.loads((Path(os.environ["PM_OS_CONFIG_DIR"]) / "config.json").read_text())
        assert "test-squad" in cfg["squads"]
        assert cfg["squads"]["test-squad"]["display_name"] == "Test Squad"

    def test_squad_workspace_switch(self, client):
        """Switching to a squad workspace should work."""
        resp = client.get("/workspace/default", follow_redirects=False)
        assert resp.status_code in (302, 303)
        # Follow the redirect and verify dashboard loads
        resp2 = client.get("/", follow_redirects=False)
        assert resp2.status_code == 200

    def test_squad_workspace_personal(self, client):
        """Switching to personal workspace should work."""
        resp = client.get("/workspace/personal", follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_removed_member_loses_workspace_access_immediately(self, client):
        client.get("/workspace/default")
        client.post(
            "/product-docs/upload",
            files={"docs": ("squad-secret.md", b"# Squad secret")},
        )
        import pm_os.web.app as web_app

        squads = dict(web_app.config_manager.get("squads") or {})
        squads["default"]["members"] = ["other@example.com"]
        web_app.config_manager.set("squads", squads)

        response = client.get("/product-docs")

        assert "squad-secret.md" not in response.text

    def test_squad_identifier_rejects_path_syntax(self, client):
        response = client.post(
            "/squad/create",
            data={
                "name": "../../finance",
                "display_name": "Finance",
                "password": "squadpass",
            },
        )

        assert response.status_code == 200
        assert "letras minúsculas" in response.text
        import pm_os.web.app as web_app

        assert "../../finance" not in (web_app.config_manager.get("squads") or {})

    def test_creator_cannot_leave_or_remove_self(self, client):
        client.get("/workspace/default")
        leave_response = client.post("/squad/leave")
        assert leave_response.status_code == 200
        assert "criador não pode sair" in leave_response.text

        remove_response = client.post(
            "/squad/admin/default/remove-member",
            data={"member_email": "test@pmstudio.app"},
            follow_redirects=False,
        )

        assert remove_response.status_code == 302
        import pm_os.web.app as web_app

        assert "test@pmstudio.app" in (
            web_app.config_manager.get("squads")["default"]["members"]
        )

    def test_disbanded_squad_identifier_cannot_be_reused(self, client):
        response = client.post(
            "/squad/admin/default/disband",
            follow_redirects=False,
        )
        assert response.status_code == 302

        create_response = client.post(
            "/squad/create",
            data={
                "name": "default",
                "display_name": "Replacement",
                "password": "squadpass",
            },
        )

        assert create_response.status_code == 200
        import pm_os.web.app as web_app

        assert "default" not in (web_app.config_manager.get("squads") or {})
        assert "default" in web_app.config_manager.get("retired_squad_names")
