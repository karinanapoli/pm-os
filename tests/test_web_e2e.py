"""End-to-end tests for the web layer (FastAPI routes + templates).

Covers:
- All GET routes render successfully (200)
- All POST routes with valid data
- Security: path traversal in file uploads and deletions
- Security: unsanitized initiative ID
- Security: unsanitized archive restore name
- Template rendering with context variables
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient


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
    # Reset the config file to defaults before each test
    config_file = _session_base / ".pm_os" / "config.json"
    config_file.write_text(json.dumps({
        "model": "llama3.2:1b",
        "ollama_url": "http://localhost:11434",
        "lang": "pt-BR",
        "onboarding_dismissed": False,
        "mcp_servers": [],
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
    # Clean product-docs
    pd_ctx = _session_base / "workspace" / "product-docs" / "context"
    for f in list(pd_ctx.iterdir()):
        if f.is_file():
            f.unlink()
    links_file = _session_base / "workspace" / "product-docs" / "links.json"
    if links_file.exists():
        links_file.unlink()

    monkeypatch.chdir(_session_base)

    # Now import app — config_manager reads PM_OS_CONFIG_DIR at import time
    import importlib
    for mod in list(sys.modules.keys()):
        if mod.startswith("pm_os"):
            del sys.modules[mod]
    # Need to re-import config_manager to pick up new env
    import pm_os.web.config_manager
    importlib.reload(pm_os.web.config_manager)


import sys


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from pm_os.web.app import app as _app
    with TestClient(_app) as c:
        yield c


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

    def test_create_duplicate_id_returns_error(self, client):
        _create_initiative(client, init_id="INT-DUP")
        resp = client.post("/initiatives/new", data={
            "name": "Another",
            "id": "INT-DUP",
            "status": "discovery",
        })
        assert resp.status_code == 200
        assert b"j\xc3\xa1 existe" in resp.content or b"already exists" in resp.content

    def test_upload_context_doc(self, client, session_base):
        init_name = _create_initiative(client)
        resp = client.post(
            f"/initiative/{init_name}/upload",
            files={"docs": ("test.txt", b"Test content 123")},
        )
        assert resp.status_code == 200
        doc_path = session_base / "workspace" / "initiatives" / init_name / "context" / "test.txt"
        assert doc_path.exists()
        assert doc_path.read_text() == "Test content 123"

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
            files={"docs": ("guide.md", b"# Guide\n\nContent")},
        )
        assert resp.status_code == 200
        doc_path = session_base / "workspace" / "product-docs" / "context" / "guide.md"
        assert doc_path.exists()
        assert doc_path.read_text() == "# Guide\n\nContent"

    def test_add_link(self, client, session_base):
        resp = client.post("/product-docs/add-link", data={
            "title": "Google",
            "url": "https://google.com",
        })
        assert resp.status_code == 200
        links_file = session_base / "workspace" / "product-docs" / "links.json"
        assert links_file.exists()
        links = json.loads(links_file.read_text())
        assert any(l["title"] == "Google" and l["url"] == "https://google.com" for l in links)

    def test_delete_product_doc(self, client, session_base):
        doc_path = session_base / "workspace" / "product-docs" / "context" / "delete_me.md"
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
        links_file = session_base / "workspace" / "product-docs" / "links.json"
        links = json.loads(links_file.read_text())
        assert not any(l["url"] == "https://example.com/delete" for l in links)


# ═══════════════════════════════════════════
# 5. CONFIGURATION
# ═══════════════════════════════════════════

class TestConfiguration:
    def test_save_config(self, client, session_base):
        resp = client.post("/config", data={
            "model": "gemma4:e2b",
            "ollama_url": "http://localhost:11434",
            "lang": "en",
        })
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert cfg["model"] == "gemma4:e2b"
        assert cfg["lang"] == "en"

    def test_add_mcp_server(self, client, session_base):
        resp = client.post("/config/mcp/add", data={
            "name": "Test Server",
            "url": "http://localhost:9999/mcp",
        })
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert len(cfg["mcp_servers"]) == 1
        assert cfg["mcp_servers"][0]["name"] == "Test Server"

    def test_toggle_mcp_server(self, client, session_base):
        client.post("/config/mcp/add", data={
            "name": "Toggle Me",
            "url": "http://localhost:8888/mcp",
        })
        resp = client.post("/config/mcp/toggle", data={"url": "http://localhost:8888/mcp"})
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        server = next(s for s in cfg["mcp_servers"] if s["url"] == "http://localhost:8888/mcp")
        assert server["enabled"] is False

    def test_delete_mcp_server(self, client, session_base):
        client.post("/config/mcp/add", data={
            "name": "Delete Me",
            "url": "http://localhost:7777/mcp",
        })
        resp = client.post("/config/mcp/delete", data={"url": "http://localhost:7777/mcp"})
        assert resp.status_code == 200
        config_file = session_base / ".pm_os" / "config.json"
        cfg = json.loads(config_file.read_text())
        assert len(cfg["mcp_servers"]) == 0


# ═══════════════════════════════════════════
# 6. CONSULT / Q&A
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
# 7. ONBOARDING
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


# ═══════════════════════════════════════════
# 8. TEMPLATE CONTENT CHECKS
# ═══════════════════════════════════════════

class TestTemplateContent:
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
# 9. ERROR HANDLING
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
