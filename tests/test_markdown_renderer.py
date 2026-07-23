from pm_os.web.markdown_renderer import render_safe_markdown


def test_renders_expected_markdown():
    rendered = str(render_safe_markdown("# Title\n\n**Evidence**\n\n- One"))

    assert "<h1>Title</h1>" in rendered
    assert "<strong>Evidence</strong>" in rendered
    assert "<li>One</li>" in rendered


def test_removes_scripts_and_event_handlers():
    rendered = str(render_safe_markdown(
        '<script>alert("xss")</script>'
        '<img src="x" onerror="alert(1)">'
        '<p onclick="alert(2)">Safe text</p>'
    ))

    assert "<script" not in rendered
    assert "alert" not in rendered
    assert "<img" not in rendered
    assert "onclick" not in rendered
    assert "Safe text" in rendered


def test_removes_unsafe_link_schemes_and_protects_external_links():
    rendered = str(render_safe_markdown(
        "[unsafe](javascript:alert(1))\n\n[safe](https://example.com)"
    ))

    assert "javascript:" not in rendered
    assert 'href="https://example.com"' in rendered
    assert 'rel="noopener noreferrer"' in rendered


def test_keeps_fenced_code_as_text_not_executable_html():
    rendered = str(render_safe_markdown(
        "```html\n<script>alert('not executed')</script>\n```"
    ))

    assert "<pre><code" in rendered
    assert "&lt;script&gt;" in rendered
    assert "<script>" not in rendered
