from dataclasses import dataclass

from .models import Point


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


def test_context(registry):
    sentinel = [-1]

    @dataclass
    class Fudge:
        deliciousness: int

        def __enter__(self):
            sentinel[0] = self.deliciousness

        def __exit__(self, ext, exv, tb):
            sentinel[0] = -1

    registry.define(field="fudge", model=Fudge)

    assert sentinel[0] == -1
    with registry.use({"fudge": {"deliciousness": 666}}):
        assert sentinel[0] == 666
    assert sentinel[0] == -1


def test_register_deep(registry, configs):
    p1 = registry.define(
        field="points.one",
        model=Point,
    )
    p2 = registry.define(
        field="points.two",
        model=Point,
    )
    with registry.use(configs / "some-points.yaml"):
        assert p1.x == 1
        assert p1.y == 2
        assert p2.x == 10
        assert p2.y == 20


def test_register_deep_incomplete(registry, configs):
    p2 = registry.define(
        field="points.two",
        model=Point,
    )
    with registry.use(configs / "some-points.yaml"):
        assert p2.x == 10
        assert p2.y == 20
