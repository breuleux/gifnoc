import json
from argparse import Namespace
from dataclasses import dataclass
from os import environ
from pathlib import Path

from ovld import ovld

from .utils import DELETE, MissingProxy

NoneType = type(None)
EnvironType = type(environ)


class NoParserError(Exception):
    """Exception to raise when no parser is found."""


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


@dataclass
class EnvironMap:
    """Environment variables associated with a map from varnames to configuration paths."""

    environ: EnvironType
    map: dict[str, str]


try:
    import yaml

    yaml.SafeLoader.add_constructor("!delete", lambda loader, node: DELETE)
except ImportError:  # pragma: no cover
    yaml = MissingProxy(
        ImportError("The yaml format is not available; install the pyyaml package")
    )


class JSONParser:
    def load(self, text):
        return json.loads(text)

    def dump(self, obj):
        return json.dumps(obj, indent=4)


class YAMLParser:
    def load(self, text):
        return yaml.safe_load(text)

    def dump(self, obj):
        return yaml.safe_dump(obj)


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
    if not file.exists():
        raise FileNotFoundError(
            f"Trying to read subconfiguration from file '{file}', but it does not exist."
        )
    if parser is None:
        sfx = file.suffix
        parser = extensions.get(sfx, None)
        if parser is None:
            raise NoParserError(f"No parser found for the {sfx} format")
    text = file.read_text()
    results = parser.load(text)
    return results if results is not None else {}


@ovld
def parse_source(source: (str, Path)):  # noqa: F811
    """Parse a source from the filesystem."""
    source = Path(source).expanduser()
    if source.is_dir():
        for entry in sorted(source.iterdir()):
            try:
                yield from parse_source(entry)
            except NoParserError:
                continue
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
    for pth, value in vars(source.options).items():
        if not pth.startswith("&") or value is None:
            continue
        pth = pth[1:].split(".")
        current = rval
        for part in pth[:-1]:
            current = current.setdefault(part, {})
        current[pth[-1]] = value
    yield (Context(), rval)
