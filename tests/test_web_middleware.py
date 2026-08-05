import asyncio

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from pm_os.web.middleware import CSRFMiddleware, NoCacheMiddleware, get_form_field


def test_get_form_field_reads_urlencoded_and_multipart_tokens():
    urlencoded_headers = {b"content-type": b"application/x-www-form-urlencoded"}
    assert get_form_field(b"name=PM+Studio&csrf_token=abc123", urlencoded_headers, "csrf_token") == "abc123"

    multipart_headers = {b"content-type": b'multipart/form-data; boundary="boundary"'}
    multipart_body = (
        b"--boundary\r\n"
        b'Content-Disposition: form-data; name="csrf_token"\r\n\r\n'
        b"secure-token\r\n"
        b"--boundary--\r\n"
    )
    assert get_form_field(multipart_body, multipart_headers, "csrf_token") == "secure-token"


def test_csrf_middleware_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("PM_OS_ENV", "production")
    sent = []
    called = False

    async def inner(scope, receive, send):
        nonlocal called
        called = True

    async def receive():
        return {"type": "http.request", "body": b"csrf_token=wrong", "more_body": False}

    async def send(message):
        sent.append(message)

    middleware = CSRFMiddleware(inner, error_message=lambda: "Invalid token")
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/config",
        "session": {"csrf_token": "correct"},
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
    }

    asyncio.run(middleware(scope, receive, send))

    assert called is False
    assert sent[0]["status"] == 403
    assert sent[1]["body"] == b"Invalid token"


def test_csrf_middleware_passes_valid_body_to_application(monkeypatch):
    monkeypatch.setenv("PM_OS_ENV", "production")
    received_body = b""
    sent = []

    async def inner(scope, receive, send):
        nonlocal received_body
        message = await receive()
        received_body = message["body"]
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        return {"type": "http.request", "body": b"csrf_token=correct&name=PM", "more_body": False}

    async def send(message):
        sent.append(message)

    middleware = CSRFMiddleware(inner, error_message=lambda: "Invalid token")
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/config",
        "session": {"csrf_token": "correct"},
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
    }

    asyncio.run(middleware(scope, receive, send))

    assert received_body == b"csrf_token=correct&name=PM"
    assert sent[0]["status"] == 204


def test_security_headers_apply_to_html_and_downloads(monkeypatch):
    monkeypatch.setenv("PM_OS_ENV", "production")

    async def html_response(_request):
        return HTMLResponse("ok")

    async def download_response(_request):
        return Response(b"content", media_type="text/markdown")

    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("localhost", 443),
    }
    request = Request(scope)

    html = asyncio.run(NoCacheMiddleware(html_response).dispatch(request, html_response))
    download = asyncio.run(NoCacheMiddleware(download_response).dispatch(request, download_response))

    for response in (html, download):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
        assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
        assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "Content-Security-Policy" in html.headers
    assert "Content-Security-Policy" not in download.headers
