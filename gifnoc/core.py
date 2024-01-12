from argparse import ArgumentParser
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import os
import sys
from types import SimpleNamespace
from typing import TypedDict
from apischema import deserialize

from .acquire import acquire
from .merge import merge
from .parse import parse_source
from .registry import registry


@dataclass
class Configuration:
    base: dict
    built: object
    _token: object = None

    def __enter__(self):
        self._token = active_configuration.set(self)

    def __exit__(self, exct, excv, tb):
        active_configuration.reset(self._token)
        self._token = None


active_configuration = ContextVar("active_configuration", default=None)


def parse_sources(model, *sources):
    result = {}
    for src in sources:
        for ctx, dct in parse_source(src):
            result = merge(result, acquire(model, dct, ctx))
    return result


def get(key):
    cfg = active_configuration.get()
    if cfg is None:
        raise Exception("No configuration was loaded.")
    elif key not in cfg.built:
        raise Exception(f"No configuration was loaded for key '{key}'.")
    return cfg.built[key]


def load_sources(*sources):
    model = TypedDict(
        "GifnocTypedDict",
        {k: v.cls for k, v in registry.items()}  # type: ignore
    )
    dct = parse_sources(model, *sources)
    rval = deserialize(model, dct)
    return Configuration(base=dct, built=rval)


@contextmanager
def overlay(*sources):
    current = active_configuration.get() or Configuration({}, None)
    new = load_sources(current.base, *sources)
    with new:
        yield new.built


@contextmanager
def gifnoc(
    envvar="APP_CONFIG",
    config_argument="--config",
    default_source=None,
    sources=[],
    option_map={},  # TODO: implement
    argparser=None,
    parse_args=True,
    argv=[],
):
    if parse_args:
        if argparser is None:
            argparser = ArgumentParser()
        argparser.add_argument(
            config_argument,
            dest="$config",
            action="append",
            help="Configuration file(s) to load.",
        )
        options = argparser.parse_args(argv or sys.argv[1:])
    else:
        options = SimpleNamespace(config=[])

    sources = [
        os.environ.get(envvar, None),
        os.environ,
        default_source,
        *sources,
        *(getattr(options, "$config") or []),
    ]

    with load_sources(*sources) as cfg:
        yield cfg
