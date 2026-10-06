"""OAuth 2.1 browser authorization for remote MCP connections."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
from dataclasses import dataclass
from typing import Callable, Optional

from pm_os.web.safe_http import request_public_url, validate_public_url


class MCPOAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class OAuthStart:
    authorization_url: str
    state: str


class MCPOAuthService:
    """Discover an MCP authorization server and run Authorization Code + PKCE."""

    def __init__(self, requester: Callable = request_public_url, now: Callable = time.time):
        self.requester = requester
        self.now = now
        self._pending: dict[str, dict] = {}

    def begin(self, connection: dict, redirect_uri: str) -> OAuthStart:
        metadata = self._discover(connection["url"])
        client = self._register_client(metadata, redirect_uri, connection.get("auth") or {})
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        scope = " ".join(metadata.get("scopes_supported") or [])
        params = {
            "response_type": "code",
            "client_id": client["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": connection["url"],
        }
        if scope:
            params["scope"] = scope
        self._pending[state] = {
            "connection_id": connection["id"],
            "redirect_uri": redirect_uri,
            "verifier": verifier,
            "token_endpoint": metadata["token_endpoint"],
            "issuer": metadata.get("issuer", ""),
            "client": client,
            "expires_at": self.now() + 600,
        }
        return OAuthStart(
            authorization_url=metadata["authorization_endpoint"] + "?" + urllib.parse.urlencode(params),
            state=state,
        )

    def complete(self, state: str, code: str, issuer: str = "") -> tuple[str, dict]:
        pending = self._pending.pop(state, None)
        if not pending or pending["expires_at"] < self.now():
            raise MCPOAuthError("A autorização expirou. Inicie a conexão novamente.")
        if not code:
            raise MCPOAuthError("O provedor não retornou o código de autorização.")
        if issuer and pending["issuer"] and issuer != pending["issuer"]:
            raise MCPOAuthError("O provedor de autorização retornou uma identidade inesperada.")
        client = pending["client"]
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": pending["redirect_uri"],
            "client_id": client["client_id"],
            "code_verifier": pending["verifier"],
        }
        if client.get("client_secret"):
            form["client_secret"] = client["client_secret"]
        tokens = self._post_form(pending["token_endpoint"], form)
        return pending["connection_id"], self._auth_record(tokens, pending)

    def refresh(self, connection: dict) -> Optional[dict]:
        auth = connection.get("auth") or {}
        if auth.get("type") != "oauth" or not auth.get("refresh_token"):
            return None
        if float(auth.get("expires_at") or 0) > self.now() + 60:
            return None
        form = {
            "grant_type": "refresh_token",
            "refresh_token": auth["refresh_token"],
            "client_id": auth.get("client_id", ""),
        }
        if auth.get("client_secret"):
            form["client_secret"] = auth["client_secret"]
        tokens = self._post_form(auth["token_endpoint"], form)
        merged = dict(auth)
        merged.update({
            "secret": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token") or auth["refresh_token"],
            "expires_at": self.now() + int(tokens.get("expires_in") or 3600),
        })
        return merged

    def _discover(self, resource_url: str) -> dict:
        parsed = urllib.parse.urlsplit(validate_public_url(resource_url, resolve_dns=False))
        origin = f"{parsed.scheme}://{parsed.netloc}"
        resource_candidates = [
            origin + "/.well-known/oauth-protected-resource" + parsed.path,
            origin + "/.well-known/oauth-protected-resource",
        ]
        resource = self._first_json(resource_candidates)
        auth_servers = resource.get("authorization_servers") or [origin]
        issuer = validate_public_url(str(auth_servers[0]), resolve_dns=False).rstrip("/")
        issuer_parts = urllib.parse.urlsplit(issuer)
        auth_candidates = [
            f"{issuer_parts.scheme}://{issuer_parts.netloc}/.well-known/oauth-authorization-server{issuer_parts.path}",
            issuer + "/.well-known/oauth-authorization-server",
        ]
        metadata = self._first_json(auth_candidates)
        for field in ("authorization_endpoint", "token_endpoint"):
            if not metadata.get(field):
                raise MCPOAuthError(f"O servidor OAuth não informou {field}.")
            metadata[field] = validate_public_url(metadata[field], resolve_dns=False)
        metadata.setdefault("issuer", issuer)
        return metadata

    def _register_client(self, metadata: dict, redirect_uri: str, auth: dict) -> dict:
        if auth.get("client_id"):
            return {
                "client_id": auth["client_id"],
                "client_secret": auth.get("client_secret", ""),
            }
        endpoint = metadata.get("registration_endpoint")
        if not endpoint:
            raise MCPOAuthError(
                "Este servidor não permite o cadastro automático do PM Studio. "
                "Solicite ao administrador do MCP um client_id compatível."
            )
        payload = {
            "client_name": "PM Studio",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "application_type": "web",
        }
        try:
            response = self.requester(
                validate_public_url(endpoint, resolve_dns=False),
                method="POST",
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                body=json.dumps(payload).encode("utf-8"),
                timeout=10,
            )
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            raise MCPOAuthError("Não foi possível cadastrar o PM Studio no provedor OAuth.") from exc
        try:
            result = self._decode(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MCPOAuthError("O cadastro OAuth retornou uma resposta inválida.") from exc
        if not result.get("client_id"):
            raise MCPOAuthError("O servidor OAuth não retornou um client_id.")
        return result

    def _post_form(self, url: str, form: dict) -> dict:
        try:
            response = self.requester(
                validate_public_url(url, resolve_dns=False),
                method="POST",
                headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                body=urllib.parse.urlencode(form).encode("utf-8"),
                timeout=10,
            )
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            raise MCPOAuthError("Não foi possível concluir a autorização OAuth.") from exc
        try:
            result = self._decode(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MCPOAuthError("O provedor OAuth retornou uma resposta inválida.") from exc
        if not result.get("access_token"):
            raise MCPOAuthError("O provedor não retornou um token de acesso.")
        return result

    def _first_json(self, urls: list[str]) -> dict:
        for url in dict.fromkeys(urls):
            try:
                response = self.requester(url, method="GET", headers={"Accept": "application/json"}, timeout=10)
                return self._decode(response.body)
            except (ValueError, urllib.error.HTTPError, json.JSONDecodeError):
                continue
        raise MCPOAuthError("Não foi possível descobrir a configuração OAuth deste MCP.")

    @staticmethod
    def _decode(body: bytes) -> dict:
        value = json.loads(body.decode("utf-8"))
        if not isinstance(value, dict):
            raise json.JSONDecodeError("object expected", "", 0)
        return value

    def _auth_record(self, tokens: dict, pending: dict) -> dict:
        client = pending["client"]
        return {
            "type": "oauth",
            "header": "",
            "secret": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": self.now() + int(tokens.get("expires_in") or 3600),
            "token_endpoint": pending["token_endpoint"],
            "issuer": pending["issuer"],
            "client_id": client["client_id"],
            "client_secret": client.get("client_secret", ""),
        }
