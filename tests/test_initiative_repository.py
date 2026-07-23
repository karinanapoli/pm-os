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
