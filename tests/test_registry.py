def test_use(org, registry, configs):
    with registry.use(configs / "mila.yaml"):
        assert org.name == "mila"


def test_refresh(org, registry, configs):
    dct = {"org": {"name": "google"}}
    with registry.use(configs / "mila.yaml", dct) as cfg:
        assert org.name == "google"
        dct["org"]["name"] = "microsoft"
        assert org.name == "google"
        cfg.refresh()
        assert org.name == "microsoft"
