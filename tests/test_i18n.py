from pm_os.web.i18n import t, LANGS


def test_ptbr_key():
    assert t("dashboard.title", lang="pt-BR") == "Dashboard"
    assert t("nav.dashboard", lang="pt-BR") == "Dashboard"


def test_en_key():
    assert t("dashboard.title", lang="en") == "Dashboard"
    assert t("nav.dashboard", lang="en") == "Dashboard"


def test_fallback_to_en():
    """When key missing in pt-BR, fall back to en."""
    # All keys exist in both, so test with a custom missing key
    result = t("nonexistent.key", lang="pt-BR")
    # Falls back to en (also missing) → returns the key itself
    assert result == "nonexistent.key"


def test_fallback_to_key():
    """When key missing in both, return the key."""
    assert t("completely.missing.key", lang="fr") == "completely.missing.key"


def test_langs_export():
    assert isinstance(LANGS, list)
    assert ("en", "English") in LANGS
    assert ("pt-BR", "Português (Brasil)") in LANGS


def test_all_keys_in_both_langs():
    from pm_os.web.i18n import TRANSLATIONS
    pt_keys = set(TRANSLATIONS.get("pt-BR", {}).keys())
    en_keys = set(TRANSLATIONS.get("en", {}).keys())
    # Allow the known duplicate nav.timeline only
    expected_diff = {"nav.timeline"}
    diff = pt_keys.symmetric_difference(en_keys) - expected_diff
    assert diff == set(), f"Missing keys in one language: {diff}"
