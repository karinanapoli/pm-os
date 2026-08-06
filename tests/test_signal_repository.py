from pm_os.repositories.signal_repository import SignalRepository


def test_signal_repository_creates_lists_and_links_by_scope(tmp_path):
    path = tmp_path / "signals"
    personal = SignalRepository(str(path), squad_name="")
    squad = SignalRepository(str(path), squad_name="growth")

    signal = personal.create(
        title="Falha no cadastro",
        summary="Três clientes abandonaram a mesma etapa.",
        source_type="customer_feedback",
        theme="onboarding",
        strength="strong",
        initiative_ids=["INT-ONBOARDING"],
        created_by="pm@example.com",
    )
    squad.create(
        title="Outro squad",
        summary="Este sinal não deve aparecer no espaço pessoal.",
        source_type="metric",
        theme="retenção",
        strength="medium",
    )

    assert personal.list() == [signal]
    assert personal.list("INT-ONBOARDING") == [signal]
    assert squad.get(signal.signal_id) is None

    updated = personal.update_links(signal.signal_id, ["INT-A", "INT-B", "INT-A"])
    assert updated is not None
    assert updated.initiative_ids == ["INT-A", "INT-B"]
    assert personal.get(signal.signal_id).initiative_ids == ["INT-A", "INT-B"]

    assert squad.delete(signal.signal_id) is False
    assert personal.delete(signal.signal_id) is True
    assert personal.get(signal.signal_id) is None
    assert personal.delete(signal.signal_id) is False


def test_signal_repository_rejects_invalid_values(tmp_path):
    repository = SignalRepository(str(tmp_path / "signals"))

    try:
        repository.create(
            title="",
            summary="Descrição",
            source_type="research",
            theme="",
            strength="medium",
        )
    except ValueError as exc:
        assert "obrigatórios" in str(exc)
    else:
        raise AssertionError("Expected invalid signal to be rejected")
