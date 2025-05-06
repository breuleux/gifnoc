import pytest

from gifnoc.proxy import MissingConfigurationError, Proxy


def test_proxy(org, registry, configs):
    def px(*pth):
        return Proxy(registry, pth)

    with registry.use(configs / "mila.yaml"):
        assert px("org").name == "mila"
        assert px("org", "machines", "1").name == "turbo02"
        assert px("org", "passwords", "breuleuo")._obj() == "password123"

        with pytest.raises(MissingConfigurationError):
            px("x").name

        with pytest.raises(MissingConfigurationError):
            px("org.x").name

        assert str(px("org")).startswith("Proxy for Organization")
        assert repr(px("org")).startswith("Proxy(Organization")

    with pytest.raises(MissingConfigurationError):
        px("org").name

    assert px("org").__module__ == "gifnoc.proxy"
    assert not hasattr(px("org"), "__xyz__")

    with registry.use(configs / "mila.yaml"):
        assert px("org")() == "milamila"
