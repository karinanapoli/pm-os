"""Web security middleware kept separate from routes and business workflows."""

from __future__ import annotations

import os
import re
import secrets
from typing import Callable
from urllib.parse import parse_qs

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

_CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_AUTH_PUBLIC_PATHS = frozenset(
    {"/login", "/register", "/verify", "/verify/resend", "/forgot", "/reset"}
)


class CSRFMiddleware:
    """Buffer state-changing bodies once and validate their CSRF token."""

    def __init__(self, app, error_message: Callable[[], str]):
        self.app = app
        self.error_message = error_message

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")

        if "session" in scope and "csrf_token" not in scope["session"]:
            scope["session"]["csrf_token"] = secrets.token_hex(32)

        if path.startswith("/static") or method in _CSRF_SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        if os.environ.get("PM_OS_ENV") == "test":
            await self.app(scope, receive, send)
            return

        chunks = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                chunks.append(message.get("body", b""))
                more_body = message.get("more_body", False)
        body_bytes = b"".join(chunks)

        token = scope.get("session", {}).get("csrf_token", "")
        headers = dict(scope.get("headers", []))
        header_token = headers.get(b"x-csrf-token", b"").decode("utf-8", errors="replace")
        provided_token = header_token or get_form_field(body_bytes, headers, "csrf_token")

        if not provided_token or not secrets.compare_digest(token, provided_token):
            response_body = self.error_message().encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [
                        (b"content-type", b"text/html; charset=utf-8"),
                        (b"content-length", str(len(response_body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": response_body})
            return

        delivered = False

        async def receive_wrapper():
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        await self.app(scope, receive_wrapper, send)


def get_form_field(body_bytes: bytes, headers: dict, field: str) -> str:
    """Extract one field without consuming an ASGI request body."""
    content_type = headers.get(b"content-type", b"").decode("utf-8", errors="replace")
    try:
        if "application/x-www-form-urlencoded" in content_type.lower():
            params = parse_qs(body_bytes.decode("utf-8", errors="replace"))
            return params.get(field, [""])[0]
        if "multipart/form-data" in content_type.lower():
            boundary_match = re.search(r'boundary="?([^";]+)', content_type, re.IGNORECASE)
            if not boundary_match:
                return ""
            boundary = boundary_match.group(1).encode()
            marker = b'name="' + field.encode() + b'"'
            for part in body_bytes.split(b"--" + boundary):
                if marker in part:
                    _, _, value = part.partition(b"\r\n\r\n")
                    return value.rsplit(b"\r\n", 1)[0].decode("utf-8", errors="replace")
    except (UnicodeError, ValueError):
        return ""
    return ""


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Apply browser security and no-cache headers to HTML responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce session authentication while preserving localhost quickstart."""

    def __init__(self, app, config_get: Callable):
        super().__init__(app)
        self.config_get = config_get

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static") or request.url.path in _AUTH_PUBLIC_PATHS:
            return await call_next(request)
        if self.config_get("auth_bypass_localhost", False):
            host = request.client.host if request.client else ""
            if host in ("127.0.0.1", "::1", "localhost"):
                users = self.config_get("users", {}) or {}
                if not request.session.get("user_email"):
                    request.session["user_email"] = next(iter(users), "local@localhost")
                    request.session["authenticated"] = True
                return await call_next(request)
        try:
            authenticated = request.session.get("authenticated")
            user_email = request.session.get("user_email")
        except (AssertionError, KeyError, RuntimeError):
            authenticated = False
            user_email = None
        users = self.config_get("users", {}) or {}
        if authenticated and user_email and user_email in users:
            return await call_next(request)
        destination = "/register" if not users else "/login"
        return RedirectResponse(url=destination, status_code=302)
