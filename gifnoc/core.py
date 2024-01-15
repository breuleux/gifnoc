from argparse import ArgumentParser
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import os
import sys
from types import SimpleNamespace
from typing import Union
from apischema import deserialize

from gifnoc.utils import type_at_path
from ovld import ovld

from .acquire import acquire
from .merge import merge
from .parse import OptionsMap, parse_source
from .registry import global_model


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
    model = global_model()
    dct = parse_sources(model, *sources)
    rval = deserialize(model, dct)
    return Configuration(base=dct, built=rval)


@contextmanager
def overlay(*sources):
    current = active_configuration.get() or Configuration({}, None)
    new = load_sources(current.base, *sources)
    with new:
        yield new.built


@dataclass
class Info:
    argparser: ArgumentParser
    opt: str
    help: str | None


@ovld
def create_arg(model: bool, info: Info):
    info.argparser.add_argument(
        info.opt,
        action=argparse.BooleanOptionalAction,
        dest=info.opt,
        help=info.help,
    )


@ovld
def create_arg(model: Union[int, float, str], info: Info):
    info.argparser.add_argument(
        info.opt,
        type=info.type,
        dest=info.opt,
        help=info.help,
    )


@contextmanager
def gifnoc(
    envvar="APP_CONFIG",
    config_argument="--config",
    default_source=None,
    sources=[],
    option_map={},
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

        model = global_model()
        for opt, path in option_map.items():
            typ, hlp = type_at_path(model, path.split("."))
            create_arg[typ, Info](typ, Info(argparser=argparser, help=hlp, opt=opt))

        options = argparser.parse_args(argv or sys.argv[1:])
    else:
        options = SimpleNamespace(config=[])

    sources = [
        os.environ.get(envvar, None),
        os.environ,
        default_source,
        *sources,
        *(getattr(options, "$config") or []),
        OptionsMap(options=options, map=option_map),
    ]

    with load_sources(*sources) as cfg:
        yield cfg
