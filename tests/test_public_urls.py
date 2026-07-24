import pytest

from pm_os.web.public_urls import allowed_hosts_from_env, external_base_url


def test_allowed_hosts_use_safe_local_defaults():
    assert allowed_hosts_from_env("") == [
        "127.0.0.1",
        "localhost",
        "testserver",
    ]


def test_allowed_hosts_parse_explicit_deployment_hosts():
    assert allowed_hosts_from_env("pm.example.com, *.internal.example.com") == [
        "pm.example.com",
        "*.internal.example.com",
    ]


def test_external_base_url_prefers_explicit_configuration():
    assert (
        external_base_url(
            "http://localhost:8000/",
            "https://pm.example.com/product/",
            production=True,
        )
        == "https://pm.example.com/product"
    )


@pytest.mark.parametrize(
    "value",
    [
        "javascript:alert(1)",
        "https://user:password@pm.example.com",
        "https://pm.example.com?next=evil",
        "https://pm.example.com#fragment",
    ],
)
def test_external_base_url_rejects_unsafe_values(value):
    with pytest.raises(ValueError):
        external_base_url("http://localhost:8000/", value)


def test_external_base_url_requires_https_in_production():
    with pytest.raises(ValueError):
        external_base_url(
            "http://pm.example.com/",
            production=True,
        )
