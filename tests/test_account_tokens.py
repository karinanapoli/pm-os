from pm_os.web.account_tokens import prune_expired, token_digest, token_matches


def test_token_digest_is_scoped_and_does_not_expose_raw_token():
    digest = token_digest("app-secret", "reset", "person@example.com", "raw-token")

    assert digest != "raw-token"
    assert len(digest) == 64
    assert digest != token_digest(
        "app-secret",
        "verify",
        "person@example.com",
        "raw-token",
    )
    assert digest != token_digest(
        "app-secret",
        "reset",
        "other@example.com",
        "raw-token",
    )


def test_token_match_uses_expected_scope():
    expected = token_digest("app-secret", "verify", "person@example.com", "123456")

    assert token_matches(
        expected,
        "app-secret",
        "verify",
        "person@example.com",
        "123456",
    )
    assert not token_matches(
        expected,
        "app-secret",
        "verify",
        "person@example.com",
        "654321",
    )
    assert not token_matches(None, "app-secret", "verify", "person@example.com", "123456")


def test_prune_expired_removes_invalid_and_old_records():
    records = {
        "active": {"expires_at": 101},
        "expired": {"expires_at": 99},
        "invalid": "not-a-record",
    }

    assert prune_expired(records, now=100) == {
        "active": {"expires_at": 101},
    }
