import json
from pathlib import Path
from types import NoneType
from ovld import ovld
from os import environ

from .utils import DELETE, MissingProxy
from .registry import envmap


EnvironType = type(environ)


class FromEnviron(dict):
    def __init__(self, value):
        super().__init__()
        self.value = value


try:
    import yaml

    yaml.SafeLoader.add_constructor("!delete", lambda loader, node: DELETE)
except ImportError:
    yaml = MissingProxy(
        ImportError("The yaml format is not available; install the pyyaml package")
    )


class JSONParser:
    def load(self, text):
        return json.loads(text)


class YAMLParser:
    def load(self, text):
        return yaml.safe_load(text)


extensions = {
    ".json": JSONParser(),
    ".yaml": YAMLParser(),
    ".yml": YAMLParser(),
}


def parse_file(file):
    sfx = file.suffix
    parser = extensions.get(sfx, None)
    if parser is None:
        raise Exception(f"No parser found for the {sfx} format")
    text = file.read_text()
    return parser.load(text)


@ovld
def parse_source(source: (str, Path)):  # noqa: F811
    source = Path(source)
    if source.is_dir():
        for entry in source.iterdir():
            yield from parse_source(entry)
    else:
        yield parse_file(source)


@ovld
def parse_source(source: Path):  # noqa: F811
    yield parse_file(source)


@ovld
def parse_source(source: dict):  # noqa: F811
    yield source


@ovld
def parse_source(source: NoneType):  # noqa: F811
    yield {}


@ovld
def parse_source(source: EnvironType):  # noqa: F811
    rval = {}
    for k, pth in envmap.items():
        if k in source:
            current = rval
            for part in pth[:-1]:
                current = current.setdefault(part, {})
            value = source[k]
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass
            current[pth[-1]] = value
    yield rval
