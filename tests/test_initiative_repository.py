from pm_os.repositories.initiative_repository import InitiativeRepository


def test_repository_loads_source_metadata_and_stable_id(tmp_path):
    initiative_dir = tmp_path / "INT-ONBOARDING"
    context_dir = initiative_dir / "context"
    context_dir.mkdir(parents=True)
    (context_dir / "discovery.md").write_text("Interview evidence", encoding="utf-8")
    (context_dir / ".sources.yaml").write_text(
        "sources:\n"
        "  discovery.md:\n"
        "    author: Research Team\n"
        "    confidentiality: confidential\n",
        encoding="utf-8",
    )

    repository = InitiativeRepository(str(tmp_path))
    first = repository.list_initiatives()[0]
    second = repository.list_initiatives()[0]

    assert first.document_count == 1
    assert first.sources[0].source_id.startswith("SRC-")
    assert first.sources[0].source_id == second.sources[0].source_id
    assert first.sources[0].author == "Research Team"
    assert first.sources[0].confidentiality == "confidential"
    assert first.estimated_tokens > 0


def test_repository_defaults_invalid_confidentiality_to_internal(tmp_path):
    context_dir = tmp_path / "INT-SAFE" / "context"
    context_dir.mkdir(parents=True)
    (context_dir / "notes.txt").write_text("Notes", encoding="utf-8")
    (context_dir / ".sources.yaml").write_text(
        "sources:\n  notes.txt:\n    confidentiality: secret-ish\n",
        encoding="utf-8",
    )

    initiative = InitiativeRepository(str(tmp_path)).list_initiatives()[0]

    assert initiative.sources[0].confidentiality == "internal"


def test_repository_summary_keeps_metadata_without_reading_content(tmp_path, monkeypatch):
    context_dir = tmp_path / "INT-LIGHT" / "context"
    context_dir.mkdir(parents=True)
    (context_dir / "research.md").write_text("Evidence for the product", encoding="utf-8")
    (context_dir / "report.pdf").write_bytes(b"%PDF placeholder")

    monkeypatch.setattr(
        "pm_os.repositories.initiative_repository.extract_pdf_text",
        lambda path: (_ for _ in ()).throw(AssertionError("PDF extraction should be lazy")),
    )

    repository = InitiativeRepository(str(tmp_path))
    summary = repository.list_initiatives(load_content=False)[0]

    assert summary.document_count == 2
    assert summary.documents == []
    assert all(source.content == "" for source in summary.sources)
    assert summary.context_char_count > 0
    assert summary.estimated_tokens > 0


def test_repository_get_loads_only_requested_initiative(tmp_path):
    for name, content in (("INT-A", "Alpha"), ("INT-B", "Beta")):
        context_dir = tmp_path / name / "context"
        context_dir.mkdir(parents=True)
        (context_dir / "notes.md").write_text(content, encoding="utf-8")
    (tmp_path / "INT-A" / "context" / "notes.md").write_bytes(b"\xff")

    repository = InitiativeRepository(str(tmp_path))
    initiative = repository.get("INT-B")

    assert initiative is not None
    assert initiative.name == "INT-B"
    assert initiative.documents == ["Beta"]
    assert repository.get("../INT-B") is None
