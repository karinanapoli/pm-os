from pathlib import Path
from pm_os.context_builder import ContextBuilder
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
