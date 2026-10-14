"""Inline SVG icon set for the web UI.

Icons are copied from Lucide v0.460.0 (https://lucide.dev), ISC License,
Copyright (c) Lucide Contributors 2022; portions Copyright (c) Cole Bemis
2013-2022 (Feather, MIT). Shapes are inlined so the UI keeps working offline.
"""

from markupsafe import Markup, escape

ICONS: dict[str, str] = {
    "layout-dashboard": '<rect width="7" height="9" x="3" y="3" rx="1"/> <rect width="7" height="5" x="14" y="3" rx="1"/> <rect width="7" height="9" x="14" y="12" rx="1"/> <rect width="7" height="5" x="3" y="16" rx="1"/>',
    "circle-plus": '<circle cx="12" cy="12" r="10"/> <path d="M8 12h8"/> <path d="M12 8v8"/>',
    "plus": '<path d="M5 12h14"/> <path d="M12 5v14"/>',
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/> <path d="M14 2v4a2 2 0 0 0 2 2h4"/> <path d="M10 9H8"/> <path d="M16 13H8"/> <path d="M16 17H8"/>',
    "message-circle-question": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/> <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/> <path d="M12 17h.01"/>',
    "archive": '<rect width="20" height="5" x="2" y="3" rx="1"/> <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/> <path d="M10 12h4"/>',
    "map": '<path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z"/> <path d="M15 5.764v15"/> <path d="M9 3.236v15"/>',
    "library": '<path d="m16 6 4 14"/> <path d="M12 6v14"/> <path d="M8 8v12"/> <path d="M4 4v16"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/> <circle cx="12" cy="12" r="3"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/> <circle cx="12" cy="7" r="4"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/> <circle cx="9" cy="7" r="4"/> <path d="M22 21v-2a4 4 0 0 0-3-3.87"/> <path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/> <path d="M20 3v4"/> <path d="M22 5h-4"/> <path d="M4 17v2"/> <path d="M5 18H3"/>',
    "plug": '<path d="M12 22v-5"/> <path d="M9 8V2"/> <path d="M15 8V2"/> <path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
    "pencil": '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/> <path d="m15 5 4 4"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/> <polyline points="7 10 12 15 17 10"/> <line x1="12" x2="12" y1="15" y2="3"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/> <path d="M14 2v4a2 2 0 0 0 2 2h4"/>',
    "list-todo": '<rect x="3" y="5" width="6" height="6" rx="1"/> <path d="m3 17 2 2 4-4"/> <path d="M13 6h8"/> <path d="M13 12h8"/> <path d="M13 18h8"/>',
    "target": '<circle cx="12" cy="12" r="10"/> <circle cx="12" cy="12" r="6"/> <circle cx="12" cy="12" r="2"/>',
    "sheet": '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/> <line x1="3" x2="21" y1="9" y2="9"/> <line x1="3" x2="21" y1="15" y2="15"/> <line x1="9" x2="9" y1="9" y2="21"/> <line x1="15" x2="15" y1="9" y2="21"/>',
    "workflow": '<rect width="8" height="8" x="3" y="3" rx="2"/> <path d="M7 11v4a2 2 0 0 0 2 2h4"/> <rect width="8" height="8" x="13" y="13" rx="2"/>',
    "files": '<path d="M20 7h-3a2 2 0 0 1-2-2V2"/> <path d="M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 2Z"/> <path d="M3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"/>',
    "lightbulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/> <path d="M9 18h6"/> <path d="M10 22h4"/>',
    "compass": '<path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z"/> <circle cx="12" cy="12" r="10"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/> <path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "puzzle": '<path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/>',
    "telescope": '<path d="m10.065 12.493-6.18 1.318a.934.934 0 0 1-1.108-.702l-.537-2.15a1.07 1.07 0 0 1 .691-1.265l13.504-4.44"/> <path d="m13.56 11.747 4.332-.924"/> <path d="m16 21-3.105-6.21"/> <path d="M16.485 5.94a2 2 0 0 1 1.455-2.425l1.09-.272a1 1 0 0 1 1.212.727l1.515 6.06a1 1 0 0 1-.727 1.213l-1.09.272a2 2 0 0 1-2.425-1.455z"/> <path d="m6.158 8.633 1.114 4.456"/> <path d="m8 21 3.105-6.21"/> <circle cx="12" cy="13" r="2"/>',
    "activity": '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/> <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/> <path d="M7 21h10"/> <path d="M12 3v18"/> <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/> <path d="m9 12 2 2 4-4"/>',
    "hourglass": '<path d="M5 22h14"/> <path d="M5 2h14"/> <path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/> <path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
    "x": '<path d="M18 6 6 18"/> <path d="m6 6 12 12"/>',
    "trash-2": '<path d="M3 6h18"/> <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/> <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/> <line x1="10" x2="10" y1="11" y2="17"/> <line x1="14" x2="14" y1="11" y2="17"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/> <path d="M3 3v5h5"/>',
    "package": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/> <path d="M12 22V12"/> <path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7"/> <path d="m7.5 4.27 9 5.15"/>',
    "menu": '<line x1="4" x2="20" y1="12" y2="12"/> <line x1="4" x2="20" y1="6" y2="6"/> <line x1="4" x2="20" y1="18" y2="18"/>',
    "trending-up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/> <polyline points="16 7 22 7 22 13"/>',
    "message-square": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/> <polyline points="17 8 12 3 7 8"/> <line x1="12" x2="12" y1="3" y2="15"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "milestone": '<path d="M12 13v8"/> <path d="M12 3v3"/> <path d="M4 6a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h13a2 2 0 0 0 1.152-.365l3.424-2.317a1 1 0 0 0 0-1.635l-3.424-2.318A2 2 0 0 0 17 6z"/>',
    "external-link": '<path d="M15 3h6v6"/> <path d="M10 14 21 3"/> <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/> <path d="m9 12 2 2 4-4"/>',
    "user-plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/> <circle cx="9" cy="7" r="4"/> <line x1="19" x2="19" y1="8" y2="14"/> <line x1="22" x2="16" y1="11" y2="11"/>',
    "log-in": '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/> <polyline points="10 17 15 12 10 7"/> <line x1="15" x2="3" y1="12" y2="12"/>',
}



def icon(name: str, size: int = 16, label: str = "", css_class: str = "") -> Markup:
    """Render an inline SVG icon. Decorative by default; pass ``label`` for icon-only controls."""
    body = ICONS.get(name)
    if body is None:
        return Markup("")
    a11y = f'role="img" aria-label="{escape(label)}"' if label else 'aria-hidden="true" focusable="false"'
    classes = f"icon icon-{name} {css_class}".strip()
    return Markup(
        f'<svg class="{classes}" xmlns="http://www.w3.org/2000/svg" width="{int(size)}" height="{int(size)}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" {a11y}>{body}</svg>'
    )
