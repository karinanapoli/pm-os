from pm_os.infrastructure.cipher import decrypt, encrypt


def test_authenticated_encryption_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("PM_OS_CONFIG_DIR", str(tmp_path))
    encrypted = encrypt("secret-value")
    assert encrypted.startswith("fernet:")
    assert "secret-value" not in encrypted
    assert decrypt(encrypted) == "secret-value"


def test_authenticated_encryption_rejects_tampering(monkeypatch, tmp_path):
    monkeypatch.setenv("PM_OS_CONFIG_DIR", str(tmp_path))
    encrypted = encrypt("secret-value")
    replacement = "A" if encrypted[-1] != "A" else "B"
    tampered = encrypted[:-1] + replacement
    try:
        decrypt(tampered)
        assert False, "tampered value should not decrypt"
    except ValueError:
        pass
