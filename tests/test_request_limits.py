import asyncio

from pm_os.web.request_limits import RequestBodyLimitMiddleware


def _scope(content_length=None):
    headers = []
    if content_length is not None:
        headers.append((b"content-length", str(content_length).encode("ascii")))
    return {"type": "http", "method": "POST", "path": "/upload", "headers": headers}


async def _run_middleware(scope, messages, max_bytes=10):
    sent = []
    called = False

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    async def inner(app_scope, app_receive, app_send):
        nonlocal called
        called = True
        while True:
            message = await app_receive()
            if not message.get("more_body", False):
                break
        await app_send({"type": "http.response.start", "status": 204, "headers": []})
        await app_send({"type": "http.response.body", "body": b""})

    middleware = RequestBodyLimitMiddleware(inner, max_bytes=max_bytes)
    await middleware(scope, receive, send)
    return called, sent


def test_rejects_declared_oversized_body_before_calling_app():
    called, sent = asyncio.run(
        _run_middleware(
            _scope(content_length=11),
            [{"type": "http.request", "body": b"", "more_body": False}],
        )
    )
    assert called is False
    assert sent[0]["status"] == 413


def test_rejects_chunked_body_when_stream_crosses_limit():
    called, sent = asyncio.run(
        _run_middleware(
            _scope(),
            [
                {"type": "http.request", "body": b"123456", "more_body": True},
                {"type": "http.request", "body": b"78901", "more_body": False},
            ],
        )
    )
    assert called is True
    assert sent[0]["status"] == 413


def test_allows_body_at_exact_limit():
    called, sent = asyncio.run(
        _run_middleware(
            _scope(content_length=10),
            [{"type": "http.request", "body": b"1234567890", "more_body": False}],
        )
    )
    assert called is True
    assert sent[0]["status"] == 204
