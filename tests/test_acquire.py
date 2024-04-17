from pathlib import Path

from gifnoc.acquire import EnvContext, FileContext, acquire

from .models import City, Person


def test_acquire_file():
    acq = acquire(
        City,
        Path(__file__).parent / "objects" / "person-links.yaml",
        FileContext(path=None),
    )
    assert acq == {"people": [{"name": "Olivier", "age": 39}, {"name": "Sophie", "age": 31}]}


def test_acquire_environment():
    acq = acquire(Person, {"name": "bob", "age": "41", "fabulous": "1"}, EnvContext())
    assert acq == {"name": "bob", "age": 41, "fabulous": True}
