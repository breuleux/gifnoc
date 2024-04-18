from pathlib import Path

from gifnoc.acquire import EnvContext, FileContext, acquire
from gifnoc.type_wrappers import Extensible

from .models import City, Member, Person

here = Path(__file__).parent


def test_acquire_file():
    acq = acquire(
        City,
        here / "objects" / "person-links.yaml",
        FileContext(path=None),
    )
    assert acq == {"people": [{"name": "Olivier", "age": 39}, {"name": "Sophie", "age": 31}]}


def test_acquire_environment():
    acq = acquire(Person, {"name": "bob", "age": "41", "fabulous": "1"}, EnvContext())
    assert acq == {"name": "bob", "age": 41, "fabulous": True}


def test_acquire_resolve():
    acq = acquire(Member, here / "objects" / "kevin.yaml", FileContext(path=None))
    assert acq == {
        "name": "kevin",
        "username": "kev",
        "home": str(here / "objects" / "wow"),
        "start": "2020-01-01",
    }


def test_acquire_passthrough():
    acq = acquire(Extensible[Member], here / "objects" / "kevin.yaml", FileContext(path=None))
    assert acq == {
        "name": "kevin",
        "username": "kev",
        "home": str(here / "objects" / "wow"),
        "start": "2020-01-01",
    }
