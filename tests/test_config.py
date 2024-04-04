def test_config(org, registry, configs):
    from gifnoc.config import org as org2

    with registry.use(configs / "mila.yaml"):
        assert org.name == "mila"
        assert org2.name == "mila"
