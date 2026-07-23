"""ASGI request-size protection applied before request body buffering."""

from __future__ import annotations

from typing import Optional

MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BODY_BYTES = 25 * 1024 * 1024


class _RequestTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Reject oversized declared or streamed request bodies with HTTP 413."""

    def __init__(self, app, max_bytes: int = MAX_REQUEST_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope.get("headers", []))
        if content_length is not None and content_length > self.max_bytes:
            await _send_too_large(send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestTooLarge:
            await _send_too_large(send)


def _content_length(headers: list[tuple[bytes, bytes]]) -> Optional[int]:
    for name, value in headers:
        if name.lower() == b"content-length":
            try:
                parsed = int(value)
            except ValueError:
                return None
            return parsed if parsed >= 0 else None
    return None


async def _send_too_large(send) -> None:
    body = b"Request body too large."
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
