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


def render_safe_markdown(text: str) -> Markup:
    """Render Markdown while removing executable or unsafe HTML."""
    rendered = markdown.markdown(text or "", extensions=["fenced_code", "tables"])
    cleaned = nh3.clean(
        rendered,
        tags=_ALLOWED_TAGS,
        clean_content_tags={"script", "style"},
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_SCHEMES,
        link_rel="noopener noreferrer",
    )
    return Markup(cleaned)
