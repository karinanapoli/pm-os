import json
import urllib.parse
from dataclasses import dataclass

from pm_os.web.mcp_oauth_service import MCPOAuthService


@dataclass
class Response:
    body: bytes


class FakeRequester:
    def __init__(self):
        self.calls = []

    def __call__(self, url, method="GET", headers=None, body=None, timeout=0):
        self.calls.append((url, method, body))
        if "oauth-protected-resource" in url:
            value = {"authorization_servers": ["https://auth.example.com"]}
        elif "oauth-authorization-server" in url:
            value = {
                "issuer": "https://auth.example.com",
                "authorization_endpoint": "https://auth.example.com/authorize",
                "token_endpoint": "https://auth.example.com/token",
                "registration_endpoint": "https://auth.example.com/register",
                "scopes_supported": ["read", "offline_access"],
            }
        elif url.endswith("/register"):
            value = {"client_id": "pm-studio-client"}
        elif url.endswith("/token"):
            form = urllib.parse.parse_qs(body.decode())
            if form["grant_type"] == ["refresh_token"]:
                value = {"access_token": "renewed", "expires_in": 7200}
            else:
                assert form["code_verifier"][0]
                value = {
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                }
        else:
            raise AssertionError(url)
        return Response(json.dumps(value).encode())


def connection():
    return {
        "id": "mcp-example",
        "name": "Example",
        "url": "https://mcp.example.com/mcp",
        "auth": {"type": "oauth"},
    }


def test_browser_flow_uses_discovery_pkce_and_exchanges_code():
    requester = FakeRequester()
    service = MCPOAuthService(requester=requester, now=lambda: 1000)

    started = service.begin(connection(), "http://127.0.0.1:8000/config/mcp/oauth/callback")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(started.authorization_url).query)

    assert query["code_challenge_method"] == ["S256"]
    assert query["resource"] == ["https://mcp.example.com/mcp"]
    target, auth = service.complete(started.state, "authorization-code")
    assert target == "mcp-example"
    assert auth["secret"] == "access"
    assert auth["refresh_token"] == "refresh"
    assert auth["expires_at"] == 4600


def test_refreshes_an_expired_oauth_token():
    requester = FakeRequester()
    service = MCPOAuthService(requester=requester, now=lambda: 5000)
    item = connection()
    item["auth"] = {
        "type": "oauth",
        "secret": "expired",
        "refresh_token": "refresh",
        "expires_at": 4000,
        "token_endpoint": "https://auth.example.com/token",
        "client_id": "pm-studio-client",
    }

    refreshed = service.refresh(item)

    assert refreshed["secret"] == "renewed"
    assert refreshed["refresh_token"] == "refresh"
    assert refreshed["expires_at"] == 12200


def test_technical_admin_can_use_a_preregistered_client_without_dynamic_registration():
    requester = FakeRequester()
    service = MCPOAuthService(requester=requester, now=lambda: 1000)
    item = connection()
    item["auth"].update({
        "client_id": "company-client",
        "client_secret": "company-secret",
    })

    started = service.begin(item, "http://127.0.0.1:8000/config/mcp/oauth/callback")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(started.authorization_url).query)

    assert query["client_id"] == ["company-client"]
    assert not any(url.endswith("/register") for url, _, _ in requester.calls)


def test_returning_user_with_a_valid_token_is_not_sent_through_refresh_again():
    requester = FakeRequester()
    service = MCPOAuthService(requester=requester, now=lambda: 5000)
    item = connection()
    item["auth"] = {
        "type": "oauth",
        "secret": "still-valid",
        "refresh_token": "refresh",
        "expires_at": 9000,
        "token_endpoint": "https://auth.example.com/token",
        "client_id": "pm-studio-client",
    }

    assert service.refresh(item) is None
    assert requester.calls == []
