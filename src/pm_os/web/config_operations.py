"""Pure transactional mutations for account, integration, and squad config."""

from typing import Optional

from pm_os.web.account_tokens import prune_expired, token_matches


def rehash_user(config: dict, email: str, expected_hash: str, new_hash: str) -> bool:
    users = config.get("users") or {}
    if users.get(email) != expected_hash:
        return False
    users[email] = new_hash
    config["users"] = users
    return True


def reserve_registration(
    config: dict,
    email: str,
    pending_record: dict,
    now: float,
) -> bool:
    users = config.get("users") or {}
    pending = prune_expired(config.get("pending_registrations") or {}, now)
    if email in users or email in pending:
        return False
    pending[email] = pending_record
    config["pending_registrations"] = pending
    return True


def mark_pending_sent(
    config: dict,
    email: str,
    code_digest: str,
    sent_at: float,
) -> bool:
    pending = config.get("pending_registrations") or {}
    current = pending.get(email)
    if not current or current.get("code_digest") != code_digest:
        return False
    current["last_sent_at"] = sent_at
    config["pending_registrations"] = pending
    return True


def create_local_user(
    config: dict,
    email: str,
    password_hash: str,
    now: float,
) -> bool:
    users = config.get("users") or {}
    pending = prune_expired(config.get("pending_registrations") or {}, now)
    if email in users or email in pending:
        return False
    users[email] = password_hash
    config["users"] = users
    config["pending_registrations"] = pending
    config["onboarding_dismissed"] = False
    return True


def complete_verification(
    config: dict,
    email: str,
    code: str,
    secret: str,
    now: float,
    max_attempts: int,
) -> str:
    pending_registrations = config.get("pending_registrations") or {}
    pending = pending_registrations.get(email)
    if not pending or pending.get("expires_at", 0) < now:
        pending_registrations.pop(email, None)
        config["pending_registrations"] = pending_registrations
        return "expired"
    if not token_matches(
        pending.get("code_digest"),
        secret,
        "verify",
        email,
        code.strip(),
    ):
        pending["attempts"] = int(pending.get("attempts", 0)) + 1
        if pending["attempts"] >= max_attempts:
            pending_registrations.pop(email, None)
            status = "too_many"
        else:
            pending_registrations[email] = pending
            status = "invalid"
        config["pending_registrations"] = pending_registrations
        return status
    users = config.get("users") or {}
    users[email] = pending["password_hash"]
    pending_registrations.pop(email, None)
    config["users"] = users
    config["pending_registrations"] = pending_registrations
    config["onboarding_dismissed"] = False
    return "verified"


def reserve_verification_resend(
    config: dict,
    email: str,
    code_digest: str,
    now: float,
    expires_at: float,
    resend_seconds: int,
) -> str:
    pending_registrations = config.get("pending_registrations") or {}
    pending = pending_registrations.get(email)
    if not pending or pending.get("expires_at", 0) < now:
        pending_registrations.pop(email, None)
        config["pending_registrations"] = pending_registrations
        return "expired"
    if now - pending.get("last_sent_at", 0) < resend_seconds:
        return "wait"
    pending["code_digest"] = code_digest
    pending["expires_at"] = expires_at
    pending["attempts"] = 0
    pending_registrations[email] = pending
    config["pending_registrations"] = pending_registrations
    return "reserved"


def add_reset_token(
    config: dict,
    digest: str,
    record: dict,
    now: float,
) -> None:
    tokens = prune_expired(config.get("reset_tokens") or {}, now)
    tokens[digest] = record
    config["reset_tokens"] = tokens


def remove_reset_token(config: dict, token_key: str) -> bool:
    tokens = config.get("reset_tokens") or {}
    existed = token_key in tokens
    tokens.pop(token_key, None)
    config["reset_tokens"] = tokens
    return existed


def complete_password_reset(
    config: dict,
    email: str,
    stored_key: str,
    new_password_hash: str,
    now: float,
) -> bool:
    tokens = config.get("reset_tokens") or {}
    stored = tokens.get(stored_key)
    users = config.get("users") or {}
    if (
        not stored
        or stored.get("email") != email
        or stored.get("expires_at", 0) < now
        or email not in users
    ):
        return False
    users[email] = new_password_hash
    tokens.pop(stored_key, None)
    config["users"] = users
    config["reset_tokens"] = tokens
    return True


def delete_user(config: dict, email: str) -> bool:
    users = config.get("users") or {}
    existed = email in users
    users.pop(email, None)
    config["users"] = users
    return existed


def add_mcp_server(config: dict, server: dict) -> bool:
    servers = config.get("mcp_servers") or []
    if any(
        (
            server.get("id")
            and item.get("id") == server.get("id")
        )
        or (
            server.get("url")
            and item.get("url") == server.get("url")
        )
        for item in servers
    ):
        return False
    servers.append(server)
    config["mcp_servers"] = servers
    return True


def toggle_mcp_server(config: dict, target: str) -> Optional[tuple[str, str]]:
    servers = config.get("mcp_servers") or []
    for server in servers:
        if server.get("id") == target or server.get("url") == target:
            server["enabled"] = not server.get("enabled", True)
            config["mcp_servers"] = servers
            state = "enabled" if server["enabled"] else "disabled"
            return server["name"], state
    return None


def remove_mcp_server(config: dict, target: str) -> Optional[str]:
    servers = config.get("mcp_servers") or []
    removed = next((
        item.get("name", "MCP")
        for item in servers
        if item.get("id") == target or item.get("url") == target
    ), None)
    config["mcp_servers"] = [
        item
        for item in servers
        if item.get("id") != target and item.get("url") != target
    ]
    return removed


def update_mcp_capabilities(config: dict, url: str, capabilities: dict) -> bool:
    servers = config.get("mcp_servers") or []
    for server in servers:
        if server.get("url") == url:
            server["capabilities"] = capabilities
            config["mcp_servers"] = servers
            return True
    return False


def upsert_custom_provider(config: dict, provider: dict) -> None:
    providers = [
        item
        for item in (config.get("custom_providers") or [])
        if item["name"] != provider["name"]
    ]
    providers.append(provider)
    config["custom_providers"] = providers


def remove_custom_provider(config: dict, name: str) -> None:
    config["custom_providers"] = [
        provider
        for provider in (config.get("custom_providers") or [])
        if provider["name"] != name
    ]
    if config.get("ai_provider") == name:
        config["ai_provider"] = "ollama"


def create_squad(config: dict, squad_key: str, squad: dict) -> bool:
    squads = config.get("squads") or {}
    retired = config.get("retired_squad_names") or []
    if squad_key in squads or squad_key in retired:
        return False
    squads[squad_key] = squad
    config["squads"] = squads
    return True


def join_squad(
    config: dict,
    squad_key: str,
    user_email: str,
    expected_password_hash: str,
    replacement_hash: str,
) -> str:
    squads = config.get("squads") or {}
    squad = squads.get(squad_key)
    if not squad or squad.get("password_hash") != expected_password_hash:
        return "changed"
    if user_email in squad.get("members", []):
        return "member"
    squad["password_hash"] = replacement_hash
    squad["members"] = [*squad.get("members", []), user_email]
    config["squads"] = squads
    return "joined"


def leave_squad(config: dict, squad_key: str, user_email: str) -> str:
    squads = config.get("squads") or {}
    squad = squads.get(squad_key)
    if not squad or user_email not in squad.get("members", []):
        return "missing"
    if squad.get("created_by") == user_email:
        return "owner"
    squad["members"] = [
        member for member in squad["members"] if member != user_email
    ]
    config["squads"] = squads
    return "left"


def remove_squad_member(
    config: dict,
    squad_key: str,
    admin_email: str,
    member_email: str,
) -> bool:
    squads = config.get("squads") or {}
    squad = squads.get(squad_key)
    if not squad or squad.get("created_by") != admin_email:
        return False
    squad["members"] = [
        member
        for member in squad.get("members", [])
        if member != member_email
    ]
    config["squads"] = squads
    return True


def rename_squad(
    config: dict,
    squad_key: str,
    admin_email: str,
    display_name: str,
) -> bool:
    squads = config.get("squads") or {}
    squad = squads.get(squad_key)
    if not squad or squad.get("created_by") != admin_email:
        return False
    squad["display_name"] = display_name
    config["squads"] = squads
    return True


def disband_squad(config: dict, squad_key: str, admin_email: str) -> bool:
    squads = config.get("squads") or {}
    squad = squads.get(squad_key)
    if not squad or squad.get("created_by") != admin_email:
        return False
    del squads[squad_key]
    retired = config.get("retired_squad_names") or []
    if squad_key not in retired:
        retired.append(squad_key)
    config["squads"] = squads
    config["retired_squad_names"] = retired
    return True
