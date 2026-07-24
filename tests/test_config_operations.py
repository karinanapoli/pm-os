from pm_os.web import config_operations as operations
from pm_os.web.account_tokens import token_digest


def test_registration_lifecycle_activates_user():
    secret = "app-secret"
    code = "123456"
    email = "person@example.com"
    config = {
        "users": {},
        "pending_registrations": {},
        "onboarding_dismissed": True,
    }
    record = {
        "password_hash": "password-hash",
        "code_digest": token_digest(secret, "verify", email, code),
        "expires_at": 200,
        "attempts": 0,
        "last_sent_at": 0,
    }

    assert operations.reserve_registration(config, email, record, now=100)
    assert not operations.reserve_registration(config, email, record, now=100)
    assert operations.mark_pending_sent(config, email, record["code_digest"], 110)
    assert (
        operations.complete_verification(
            config,
            email,
            code,
            secret,
            now=120,
            max_attempts=5,
        )
        == "verified"
    )
    assert config["users"][email] == "password-hash"
    assert email not in config["pending_registrations"]
    assert config["onboarding_dismissed"] is False


def test_verification_tracks_invalid_and_expired_codes():
    secret = "app-secret"
    email = "person@example.com"
    digest = token_digest(secret, "verify", email, "123456")
    config = {
        "users": {},
        "pending_registrations": {
            email: {
                "password_hash": "hash",
                "code_digest": digest,
                "expires_at": 200,
                "attempts": 0,
            }
        },
    }

    assert operations.complete_verification(
        config, email, "wrong", secret, 100, 2
    ) == "invalid"
    assert operations.complete_verification(
        config, email, "wrong", secret, 100, 2
    ) == "too_many"
    assert operations.complete_verification(
        config, email, "123456", secret, 100, 2
    ) == "expired"


def test_password_reset_updates_password_and_consumes_token():
    config = {
        "users": {"person@example.com": "old-hash"},
        "reset_tokens": {
            "digest": {"email": "person@example.com", "expires_at": 200}
        },
    }

    assert operations.complete_password_reset(
        config,
        "person@example.com",
        "digest",
        "new-hash",
        now=100,
    )
    assert config["users"]["person@example.com"] == "new-hash"
    assert config["reset_tokens"] == {}
    assert not operations.complete_password_reset(
        config,
        "person@example.com",
        "digest",
        "another-hash",
        now=100,
    )


def test_mcp_operations_preserve_unrelated_servers():
    config = {"mcp_servers": []}
    first = {"name": "One", "url": "https://one.example", "enabled": True}
    second = {"name": "Two", "url": "https://two.example", "enabled": True}

    assert operations.add_mcp_server(config, first)
    assert operations.add_mcp_server(config, second)
    assert not operations.add_mcp_server(config, first)
    assert operations.toggle_mcp_server(
        config, first["url"]
    ) == ("One", "disabled")
    assert operations.remove_mcp_server(config, first["url"]) == "One"
    assert config["mcp_servers"] == [second]


def test_provider_operations_reset_deleted_selection():
    config = {"custom_providers": [], "ai_provider": "custom"}
    provider = {
        "name": "custom",
        "model": "model",
        "api_key": "key",
        "base_url": "https://ai.example",
    }

    operations.upsert_custom_provider(config, provider)
    operations.upsert_custom_provider(config, {**provider, "model": "new-model"})
    assert len(config["custom_providers"]) == 1
    assert config["custom_providers"][0]["model"] == "new-model"

    operations.remove_custom_provider(config, "custom")

    assert config["custom_providers"] == []
    assert config["ai_provider"] == "ollama"


def test_squad_membership_lifecycle():
    config = {"squads": {}, "retired_squad_names": []}
    squad = {
        "password_hash": "old-hash",
        "members": ["owner@example.com"],
        "created_by": "owner@example.com",
    }

    assert operations.create_squad(config, "core", squad)
    assert not operations.create_squad(config, "core", squad)
    assert operations.join_squad(
        config,
        "core",
        "member@example.com",
        "old-hash",
        "new-hash",
    ) == "joined"
    assert operations.leave_squad(
        config, "core", "member@example.com"
    ) == "left"
    assert operations.leave_squad(
        config, "core", "owner@example.com"
    ) == "owner"
    assert operations.rename_squad(
        config, "core", "owner@example.com", "Core Team"
    )
    assert operations.disband_squad(config, "core", "owner@example.com")
    assert "core" not in config["squads"]
    assert "core" in config["retired_squad_names"]
