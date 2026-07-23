from datetime import datetime

from pm_os.context_builder import ContextBuilder
from pm_os.domain.context_source import ContextSource
from pm_os.domain.initiative import Initiative


def test_build_with_documents(tmp_path):
    init_path = tmp_path / "INT-TEST"
    init_path.mkdir()
    ctx = init_path / "context"
    ctx.mkdir()
    (ctx / "doc1.md").write_text("# Document 1\n\nContent 1", encoding="utf-8")
    (ctx / "doc2.txt").write_text("Document 2 content", encoding="utf-8")

    initiative = Initiative(
        name="INT-TEST",
        path=init_path,
        documents=["# Document 1\n\nContent 1", "Document 2 content"],
    )

    builder = ContextBuilder()
    result = builder.build(initiative)

    assert "# Document 1" in result
    assert "Content 1" in result
    assert "Document 2 content" in result


def test_build_without_documents(tmp_path):
    init_path = tmp_path / "INT-EMPTY"
    init_path.mkdir()
    (init_path / "context").mkdir()

    initiative = Initiative(
        name="INT-EMPTY",
        path=init_path,
        documents=[],
    )

    builder = ContextBuilder()
    result = builder.build(initiative)
    assert result == ""


def test_build_with_traceable_sources(tmp_path):
    source = ContextSource(
        source_id="SRC-A1B2C3D4",
        name="discovery.md",
        content="Customers need a faster onboarding.",
        source_type="md",
        confidentiality="confidential",
        author="Product Team",
        modified_at=datetime(2026, 7, 23, 10, 30),
        size_bytes=35,
    )
    initiative = Initiative(
        name="INT-TRACEABLE",
        path=tmp_path,
        sources=[source],
    )

    result = ContextBuilder().build(initiative)

    assert 'id="SRC-A1B2C3D4"' in result
    assert 'confidentiality="confidential"' in result
    assert 'author="Product Team"' in result
    assert "Customers need a faster onboarding." in result
    assert '<<<END SOURCE id="SRC-A1B2C3D4">>>' in result
