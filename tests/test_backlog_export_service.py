import json

import pytest

from pm_os.web.backlog_export_service import BacklogExportService


BACKLOG = """## Iniciativa: Checkout

## Épico: Pagamentos

### História: Confirmar pagamento
**Épico pai**: Pagamentos
**Critérios de Aceite**
- Confirma em até dois segundos.

### História: Exibir erro
**Épico pai**: Pagamentos
- Mensagem orienta nova tentativa.
"""


def _approved_initiative(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "backlog.md").write_text(BACKLOG, encoding="utf-8")
    (artifacts / "specification.json").write_text(json.dumps({
        "artifacts": {"backlog": {"review_status": "approved"}},
    }), encoding="utf-8")


def test_prepares_confirms_and_audits_selected_export(tmp_path):
    _approved_initiative(tmp_path)
    service = BacklogExportService()
    items = service.items(BACKLOG)

    preview = service.prepare(
        tmp_path,
        initiative_name="Checkout",
        target="github",
        selected_ids=[items[0]["id"]],
        actor="pm@example.com",
    )

    assert preview["status"] == "prepared"
    assert preview["items"][0]["title"] == "Confirmar pagamento"
    assert preview["items"][0]["labels"] == ["backlog", "Pagamentos"]
    output = service.confirm(tmp_path, preview_id=preview["preview_id"], actor="pm@example.com")
    confirmed = json.loads(output.read_text(encoding="utf-8"))
    assert confirmed["status"] == "confirmed"
    audit = json.loads((tmp_path / "artifacts" / "backlog-export-audit.json").read_text())
    assert [event["event"] for event in audit] == ["prepared", "confirmed"]


def test_blocks_unapproved_empty_and_tampered_exports(tmp_path):
    _approved_initiative(tmp_path)
    service = BacklogExportService()
    with pytest.raises(ValueError, match="Select at least one"):
        service.prepare(
            tmp_path,
            initiative_name="Checkout",
            target="linear",
            selected_ids=[],
            actor="pm@example.com",
        )
    items = service.items(BACKLOG)
    preview = service.prepare(
        tmp_path,
        initiative_name="Checkout",
        target="plane",
        selected_ids=[items[0]["id"]],
        actor="pm@example.com",
    )
    with pytest.raises(ValueError, match="no longer valid"):
        service.confirm(tmp_path, preview_id="tampered", actor="pm@example.com")
