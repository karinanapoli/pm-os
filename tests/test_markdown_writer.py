from pm_os.writers.markdown_writer import MarkdownWriter


def test_markdown_writer_creates_file(tmp_path):
    writer = MarkdownWriter()

    output_path = tmp_path / "PRD.md"

    written_path = writer.write(
        content="# Test PRD",
        output_path=str(output_path),
    )

    assert written_path.exists()
    assert written_path.read_text(encoding="utf-8") == "# Test PRD"