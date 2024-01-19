from argparse import Namespace
from dataclasses import dataclass
import json
from pathlib import Path
from types import NoneType
from ovld import ovld
from os import environ

from .utils import DELETE, MissingProxy


EnvironType = type(environ)


class Context:
    """Context of a configuration source."""


class FileContext(Context):
    """Context: source was parsed from a file."""

    def __init__(self, path):
        self.path = path


class EnvContext(Context):
    """Context: source is environment variables mapped through registry.envmap."""


@dataclass
class OptionsMap:
    """Command-line options associated with a map from options to configuration paths."""

    options: Namespace
    map: dict[str, str]


@dataclass
class EnvironMap:
    """Environment variables associated with a map from varnames to configuration paths."""

    environ: EnvironType
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


def parse_file(file, parser=None):
    """Parse a file with the right parser depending on the suffix.

    Arguments:
        file: The file to parse.
        parser: The parser to use (default: based on file suffix)
    """
    if parser is None:
        sfx = file.suffix
        parser = extensions.get(sfx, None)
        if parser is None:
            raise Exception(f"No parser found for the {sfx} format")
    text = file.read_text()
    return parser.load(text)


@ovld
def parse_source(source: (str, Path)):  # noqa: F811
    """Parse a source from the filesystem."""
    source = Path(source)
    if source.is_dir():
        for entry in source.iterdir():
            yield from parse_source(entry)
    else:
        yield (FileContext(path=source.parent), parse_file(source))


@ovld
def parse_source(source: dict):  # noqa: F811
    """Parse a source that's already a dict."""
    yield (Context(), source)


@ovld
def parse_source(source: NoneType):  # noqa: F811
    """Parse None as a source (returns an empty dictionary)."""
    yield (Context(), {})


@ovld
def parse_source(source: EnvironMap):  # noqa: F811
    """Parse environment variables based on a map."""
    rval = {}
    for k, pth in source.map.items():
        if k in source.environ:
            current = rval
            for part in pth[:-1]:
                current = current.setdefault(part, {})
            value = source.environ[k]
            current[pth[-1]] = value
    yield (EnvContext(), rval)


@ovld
def parse_source(source: OptionsMap):  # noqa: F811
    """Parse command-line options based on a map."""
    rval = {}
    for k, pth in source.map.items():
        k, *_ = k.split(",")
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
