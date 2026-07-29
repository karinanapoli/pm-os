from pm_os.web.signal_source_service import SignalSourceService


def test_signal_source_is_scoped_and_generates_local_review_drafts(tmp_path):
    root = tmp_path / "sources"
    personal = SignalSourceService(str(root), squad_name="")
    squad = SignalSourceService(str(root), squad_name="growth")

    source = personal.save(
        "relatorio.md",
        b"# Pesquisa\n\nTres clientes abandonaram o cadastro na etapa fiscal.",
        created_by="pm@example.com",
    )
    stored = personal.get(source["id"])

    assert stored is not None
    assert squad.get(source["id"]) is None
    squad_source = squad.save(
        "relatorio.md",
        b"# Pesquisa\n\nTres clientes abandonaram o cadastro na etapa fiscal.",
    )
    assert squad_source["id"] != source["id"]
    assert personal.get(source["id"]) is not None
    text = personal.extract_text(stored)
    suggestions = personal.suggest(text, source["filename"])
    assert suggestions
    assert "clientes" in suggestions[0]["summary"].lower()
    assert suggestions[0]["source_type"] == "research"


def test_signal_source_parses_valid_ai_json(tmp_path):
    class Client:
        def generate(self, prompt):
            assert "relatorio.txt" in prompt
            return """```json
            [{"title":"Queda de ativação","summary":"A ativação caiu 12%.",
              "theme":"onboarding","strength":"strong","source_type":"metric"}]
            ```"""

    service = SignalSourceService(str(tmp_path / "sources"))
    suggestions = service.suggest(
        "A ativação caiu 12% no último mês.",
        "relatorio.txt",
        Client(),
    )

    assert suggestions == [{
        "title": "Queda de ativação",
        "summary": "A ativação caiu 12%.",
        "theme": "onboarding",
        "strength": "strong",
        "source_type": "metric",
    }]
