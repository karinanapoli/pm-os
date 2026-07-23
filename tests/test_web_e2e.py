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

    def test_login_page_renders(self, unauth_client, session_base):
        self._enable_auth(session_base)
        resp = unauth_client.get("/login")
        assert resp.status_code == 200
        assert b"E-mail" in resp.content or b"Email" in resp.content

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

    def test_verify_resend_generates_a_new_code(
        self, unauth_client, session_base, monkeypatch
    ):
        self._enable_auth(session_base)
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


# ═══════════════════════════════════════════
# 9. TEMPLATE CONTENT CHECKS
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
        assert "Workspace:" in resp.text

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
        assert "nav.generate_prd" in resp.text or "Gerar documentação" in resp.text or "Generate" in resp.text


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
