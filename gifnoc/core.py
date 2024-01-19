from argparse import ArgumentParser
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from types import SimpleNamespace, UnionType
from typing import Union
from apischema import deserialize

from ovld import ovld

from .acquire import acquire
from .merge import merge
from .parse import EnvironMap, OptionsMap, parse_source
from .registry import envmap as default_environ_map, global_model
from .utils import get_at_path, type_at_path


@dataclass
class Configuration:
    base: dict
    built: object
    _token: object = None

    def __enter__(self):
        self._token = active_configuration.set(self)
        return self

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
    aliases: list


@ovld
def create_arg(model: bool, info: Info):
    info.argparser.add_argument(
        info.opt,
        *info.aliases,
        action=argparse.BooleanOptionalAction,
        dest=info.opt,
        help=info.help,
    )


@ovld
def create_arg(model: Union[int, float, str, Path], info: Info):  # noqa: F811
    info.argparser.add_argument(
        info.opt,
        *info.aliases,
        type=model,
        dest=info.opt,
        metavar=info.opt.strip("-").upper(),
        help=info.help,
    )


@contextmanager
def gifnoc(
    envvar="APP_CONFIG",
    config_argument="--config",
    sources=[],
    option_map={},
    environ_map=default_environ_map,
    environ=os.environ,
    argparser=None,
    parse_args=True,
    argv=None,
    write_back_environ=True,
):
    """Context manager to find/assemble configuration for the code within.

    All configuration and configuration files specified through environment
    variables, the command line, and the sources parameter will be merged
    together.

    Arguments:
        envvar: Name of the environment variable to use for the path to the
            configuration. (default: "APP_CONFIG")
        config_argument: Name of the command line argument used to specify
            one or more configuration files. (default: "--config")
        sources: A list of Path objects and/or dicts that will be merged into
            the final configuration.
        option_map: A map from command-line arguments to configuration paths,
            for example ``{"--port": "server.port"}`` will add a ``--port``
            command-line argument that will set ``gifnoc.config.server.port``.
        environ_map: A map from environment variables to configuration paths,
            for example ``{"SERVER_PORT": "server.port}`` will set
            ``gifnoc.config.server.port`` to the value of the ``$SERVER_PORT``
            environment variable. By default this is the global map in
            ``gifnoc.registry.envmap``, which most of the time is what you want,
            so there is usually no need to provide this argument.
        environ: The environment variables, by default ``os.environ``.
        argparser: The argument parser to add arguments to. If None, an
            argument parser will be created.
        parse_args: Whether to parse command-line arguments.
        argv: The list of command-line arguments.
        write_back_environ: If True, the mappings in ``environ_map`` will be used
            to write the configuration into ``environ``, for example if environ_map
            is ``{"SERVER_PORT": "server.port}``, we will set
            ``environ["SERVER_PORT"] = gifnoc.config.server.port`` after parsing
            the configuration. (default: True)
    """

    if parse_args:
        if argparser is None:
            argparser = ArgumentParser()
        if config_argument:
            argparser.add_argument(
                config_argument,
                dest="$config",
                metavar="CONFIG",
                action="append",
                help="Configuration file(s) to load.",
            )

        model = global_model()
        for opt, path in option_map.items():
            main, *aliases = opt.split(",")
            typ, hlp = type_at_path(model, path.split("."))
            if isinstance(typ, UnionType):
                typ = typ.__args__[0]
            create_arg[typ, Info](
                typ, Info(argparser=argparser, help=hlp, opt=main, aliases=aliases)
            )

        options = argparser.parse_args(sys.argv[1:] if argv is None else argv)
    else:
        options = SimpleNamespace(config=[])

    sources = [
        environ.get(envvar, None),
        *sources,
        *(getattr(options, "$config") or []),
        EnvironMap(environ=environ, map=environ_map),
        OptionsMap(options=options, map=option_map),
    ]

    with load_sources(*sources) as cfg:
        if write_back_environ:
            for envvar, pth in environ_map.items():
                value = get_at_path(cfg.built, pth)
                if isinstance(value, str):
                    environ[envvar] = value
                elif isinstance(value, bool):
                    environ[envvar] = str(int(value))
                else:
                    environ[envvar] = str(value)
        yield cfg
