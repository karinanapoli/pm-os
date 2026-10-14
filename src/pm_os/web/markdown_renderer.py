import re

import markdown
import nh3
from markupsafe import Markup


_ALLOWED_TAGS = {
    "a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "li", "ol", "p", "pre", "strong",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "code": {"class"},
    "td": {"align"},
    "th": {"align"},
}
_ALLOWED_SCHEMES = {"http", "https", "mailto"}


_HEADING_TAG_RE = re.compile(r"<(/?)h([1-6])>")


def render_safe_markdown(text: str, heading_offset: int = 0) -> Markup:
    """Render Markdown while removing executable or unsafe HTML.

    ``heading_offset`` demotes headings (h1 -> h2 …) when the content is embedded
    in a page that already has its own h1.
    """
    rendered = markdown.markdown(text or "", extensions=["fenced_code", "tables"])
    cleaned = nh3.clean(
        rendered,
        tags=_ALLOWED_TAGS,
        clean_content_tags={"script", "style"},
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_SCHEMES,
        link_rel="noopener noreferrer",
    )
    if heading_offset:
        cleaned = _HEADING_TAG_RE.sub(
            lambda match: f"<{match.group(1)}h{min(6, int(match.group(2)) + heading_offset)}>",
            cleaned,
        )
    return Markup(cleaned)
