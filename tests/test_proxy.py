import pytest

from gifnoc.proxy import MissingConfigurationError, Proxy


def test_proxy(org, registry, configs):
    with registry.use(configs / "mila.yaml"):
        assert Proxy("org").name == "mila"
        assert Proxy("org", "machines", "1").name == "turbo02"
        assert Proxy("org", "passwords", "breuleuo")._obj() == "password123"

        with pytest.raises(MissingConfigurationError):
            Proxy("x").name

        with pytest.raises(MissingConfigurationError):
            Proxy("org.x").name

        assert str(Proxy("org")).startswith("Proxy for Organization")
        assert repr(Proxy("org")).startswith("Proxy(Organization")

    with pytest.raises(MissingConfigurationError):
        Proxy("org").name

    assert Proxy("org").__module__ == "gifnoc.proxy"
    assert not hasattr(Proxy("org"), "__xyz__")
