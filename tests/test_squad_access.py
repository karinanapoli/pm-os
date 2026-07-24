from pm_os.web.squad_access import authorized_squad, normalize_squad_key


def test_squad_key_normalizes_spaces_and_case():
    assert normalize_squad_key("Product Core") == "product-core"


def test_squad_key_rejects_paths_symbols_and_oversized_values():
    assert normalize_squad_key("../../finance") == ""
    assert normalize_squad_key("finance_team") == ""
    assert normalize_squad_key("-finance") == ""
    assert normalize_squad_key("a" * 51) == ""


def test_authorized_squad_requires_current_membership():
    squads = {"core": {"members": ["member@example.com"]}}

    assert authorized_squad("core", "member@example.com", squads) == "core"
    assert authorized_squad("core", "removed@example.com", squads) == ""
    assert authorized_squad("missing", "member@example.com", squads) == ""
