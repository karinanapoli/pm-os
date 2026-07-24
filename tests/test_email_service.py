from pm_os.web import email_service


def _config(port: object = "587") -> dict:
    return {
        "smtp_host": "smtp.example.com",
        "smtp_port": port,
        "smtp_user": "mailer@example.com",
        "smtp_password": "secret",
        "smtp_from_email": "hello@example.com",
        "smtp_from_name": "PM Studio",
    }


class _FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout, **kwargs):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.kwargs = kwargs
        self.tls_context = None
        self.credentials = None
        self.message = None
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def starttls(self, *, context):
        self.tls_context = context

    def login(self, user, password):
        self.credentials = (user, password)

    def send_message(self, message):
        self.message = message


def test_smtp_configuration_requires_valid_host_user_and_port():
    assert email_service.is_smtp_configured(_config())
    assert not email_service.is_smtp_configured(_config("invalid"))
    assert not email_service.is_smtp_configured(_config("70000"))
    assert not email_service.is_smtp_configured({**_config(), "smtp_host": ""})
    assert not email_service.is_smtp_configured({**_config(), "smtp_user": ""})


def test_verification_email_uses_starttls_with_verified_context(monkeypatch):
    _FakeSMTP.instances.clear()
    tls_context = object()
    monkeypatch.setattr(email_service.ssl, "create_default_context", lambda: tls_context)
    monkeypatch.setattr(email_service.smtplib, "SMTP", _FakeSMTP)

    assert email_service.send_verification_email(
        _config(), "person@example.com", "123456"
    )

    smtp = _FakeSMTP.instances[-1]
    assert (smtp.host, smtp.port, smtp.timeout) == (
        "smtp.example.com",
        587,
        15,
    )
    assert smtp.tls_context is tls_context
    assert smtp.credentials == ("mailer@example.com", "secret")
    assert smtp.message["To"] == "person@example.com"
    assert smtp.message["From"] == "PM Studio <hello@example.com>"
    assert "123456" in smtp.message.get_payload(decode=True).decode()


def test_password_reset_email_uses_implicit_tls_on_port_465(monkeypatch):
    _FakeSMTP.instances.clear()
    tls_context = object()
    monkeypatch.setattr(email_service.ssl, "create_default_context", lambda: tls_context)
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", _FakeSMTP)

    assert email_service.send_password_reset_email(
        _config("465"),
        "person@example.com",
        "https://pm.example/reset?token=secret",
    )

    smtp = _FakeSMTP.instances[-1]
    assert smtp.port == 465
    assert smtp.kwargs["context"] is tls_context
    assert smtp.tls_context is None
    assert "https://pm.example/reset?token=secret" in (
        smtp.message.get_payload(decode=True).decode()
    )


def test_email_rejects_header_injection_before_connecting(monkeypatch):
    def unexpected_connection(*_args, **_kwargs):
        raise AssertionError("SMTP connection should not be opened")

    monkeypatch.setattr(email_service.smtplib, "SMTP", unexpected_connection)

    assert not email_service.send_verification_email(
        _config(), "person@example.com\nBcc: attacker@example.com", "123456"
    )


def test_email_returns_false_when_delivery_fails(monkeypatch):
    class FailingSMTP:
        def __init__(self, *_args, **_kwargs):
            raise OSError("connection refused")

    monkeypatch.setattr(email_service.smtplib, "SMTP", FailingSMTP)

    assert not email_service.send_verification_email(
        _config(), "person@example.com", "123456"
    )
