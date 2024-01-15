from argparse import Namespace
from dataclasses import dataclass
import json
from pathlib import Path
from types import NoneType
from ovld import ovld
from os import environ

from .utils import DELETE, MissingProxy
from .registry import envmap


EnvironType = type(environ)


class Context:
    pass


class FileContext(Context):
    def __init__(self, path):
        self.path = path


class EnvContext(Context):
    pass


@dataclass
class OptionsMap:
    options: Namespace
    map: dict[str, str]


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
        yield (FileContext(path=source.parent), parse_file(source))


@ovld
def parse_source(source: Path):  # noqa: F811
    yield parse_file(source)


@ovld
def parse_source(source: dict):  # noqa: F811
    yield (Context(), source)


@ovld
def parse_source(source: NoneType):  # noqa: F811
    yield (Context(), {})


@ovld
def parse_source(source: EnvironType):  # noqa: F811
    rval = {}
    for k, pth in envmap.items():
        if k in source:
            current = rval
            for part in pth[:-1]:
                current = current.setdefault(part, {})
            value = source[k]
            current[pth[-1]] = value
    yield (EnvContext(), rval)


@ovld
def parse_source(source: OptionsMap):  # noqa: F811
    rval = {}
    for k, pth in source.map.items():
        if isinstance(pth, str):
            pth = pth.split(".")
        if k in source.options:
            current = rval
            for part in pth[:-1]:
                current = current.setdefault(part, {})
            value = getattr(source.options, k)
            if value is not None:
                current[pth[-1]] = value
    yield (Context(), rval)
