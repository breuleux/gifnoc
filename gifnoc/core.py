import argparse
import os
import sys
from argparse import ArgumentParser
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, fields
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Union

from apischema import ValidationError, deserialize
from ovld import ovld

from .acquire import acquire
from .merge import merge
from .parse import EnvironMap, OptionsMap, parse_source
from .registry import global_registry
from .utils import ConfigurationError, UnionTypes, get_at_path, type_at_path


class Configuration:
    """Hold configuration base dict and built configuration.

    Configuration objects act as context managers, setting the
    ``gifnoc.active_configuration`` context variable. All code that
    runs from within the ``with`` block will thus have access to that
    specific configuration through ``gifnoc.config``.

    Attributes:
        sources: The data sources used to populate the configuration.
        registry: The registry to use for the data model.
        base: The configuration serialized as a dictionary.
        built: The deserialized configuration object, with the proper
            types.
    """

    def __init__(self, sources, registry):
        self.sources = sources
        self.registry = registry
        self.base = None
        self._built = None
        self._model = None
        self.version = None

    def build(self):
        self._model = model = self.registry.model()
        dct = parse_sources(model, *self.sources)
        dct = {f.name: dct[f.name] for f in fields(model) if f.name in dct}
        try:
            self._built = deserialize(model, dct, pass_through=lambda x: x is not Any)
        except ValidationError as exc:
            raise ConfigurationError(exc.errors) from None
        self.base = dct
        self.version = self.registry.version

    @property
    def built(self):
        if not self._built or self.registry.version > self.version:
            self.build()
        return self._built

    def overlay(self, sources):
        return Configuration([*self.sources, *sources], self.registry)

    def __enter__(self):
        self._token = active_configuration.set(self)
        built = self.built
        for f in fields(self._model):
            value = getattr(built, f.name, None)
            if hasattr(value, "__enter__"):
                value.__enter__()
        return built

    def __exit__(self, exct, excv, tb):
        active_configuration.reset(self._token)
        built = self.built
        for f in fields(self._model):
            value = getattr(built, f.name, None)
            if hasattr(value, "__exit__"):
                value.__exit__(exct, excv, tb)
        self._token = None


empty_configuration = Configuration(sources=[], registry=global_registry)
global_configuration = empty_configuration
active_configuration = ContextVar("active_configuration", default=empty_configuration)


def current_configuration():
    return active_configuration.get() or global_configuration


def parse_sources(model, *sources):
    result = {}
    for src in sources:
        for ctx, dct in parse_source(src):
            result = merge(result, acquire(model, dct, ctx))
    return result


def is_loaded():
    return current_configuration() is not None


def get(key):
    cfg = current_configuration()
    if cfg is None:
        raise Exception("No configuration was loaded.")
    elif not getattr(cfg.built, key, None):
        raise Exception(f"No configuration was loaded for key '{key}'.")
    return getattr(cfg.built, key)


@contextmanager
def overlay(*sources, registry=global_registry):
    """Overlay extra configuration.

    This acts as a context manager. The modified configuration is available
    inside the context manager and is popped off afterwards.

    Arguments:
        sources: Paths to configuration files or dicts.
        registry: Model registry to use. Defaults to the global registry.
    """
    current = current_configuration() or Configuration(registry=registry, sources=[])
    with current.overlay(sources) as overlaid:
        yield overlaid


@contextmanager
def use(*sources, registry=global_registry):
    """Use a configuration."""
    with Configuration(sources, registry) as cfg:
        yield cfg


def load(*sources, registry=global_registry):
    container = Configuration(sources=sources, registry=registry)
    return container.built


def load_global(*sources, registry=global_registry):
    global global_configuration

    container = Configuration(sources=sources, registry=registry)
    container.__enter__()
    global_configuration = container
    return container.built


@dataclass
class Info:
    """Holds information for the create_arg function."""

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
def cli(
    envvar="GIFNOC_FILE",
    config_argument="--config",
    sources=[],
    registry=global_registry,
    option_map={},
    environ_map=None,
    environ=os.environ,
    argparser=None,
    parse_args=True,
    argv=None,
    write_back_environ=True,
    set_global=True,
    exit_on_error=None,
):
    """Context manager to find/assemble configuration for the code within.

    All configuration and configuration files specified through environment
    variables, the command line, and the sources parameter will be merged
    together.

    Arguments:
        envvar: Name of the environment variable to use for the path to the
            configuration. (default: "GIFNOC_FILE")
        config_argument: Name of the command line argument used to specify
            one or more configuration files. (default: "--config")
        sources: A list of Path objects and/or dicts that will be merged into
            the final configuration.
        registry: Which model registry to use. Defaults to the global registry
            in ``gifnoc.registry.global_registry``.
        option_map: A map from command-line arguments to configuration paths,
            for example ``{"--port": "server.port"}`` will add a ``--port``
            command-line argument that will set ``gifnoc.config.server.port``.
        environ_map: A map from environment variables to configuration paths,
            for example ``{"SERVER_PORT": "server.port}`` will set
            ``gifnoc.config.server.port`` to the value of the ``$SERVER_PORT``
            environment variable. By default this is the environment map in
            the registry used.
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
    global global_configuration

    try:
        if parse_args:
            if exit_on_error is None:
                exit_on_error = True
            if argparser is None:
                argparser = ArgumentParser()
            if config_argument:
                argparser.add_argument(
                    config_argument,
                    dest="config",
                    metavar="CONFIG",
                    action="append",
                    help="Configuration file(s) to load.",
                )

            model = registry.model()
            for opt, path in option_map.items():
                main, *aliases = opt.split(",")
                typ, hlp = type_at_path(model, path.split("."))
                if isinstance(typ, UnionTypes):
                    typ = typ.__args__[0]
                create_arg[typ, Info](
                    typ, Info(argparser=argparser, help=hlp, opt=main, aliases=aliases)
                )

            options = argparser.parse_args(sys.argv[1:] if argv is None else argv)
        else:
            options = SimpleNamespace(config=[])

        if environ_map is None:
            environ_map = registry.envmap

        from_env = environ.get(envvar, None)
        from_env = from_env.split(",") if from_env else []

        sources = [
            *from_env,
            *sources,
            *(options.config or []),
            EnvironMap(environ=environ, map=environ_map),
            OptionsMap(options=options, map=option_map),
        ]

        container = Configuration(sources=sources, registry=registry)
        with container as cfg:
            if set_global:
                old_global = global_configuration
                global_configuration = container
            try:
                if write_back_environ:
                    for envvar, pth in environ_map.items():
                        value = get_at_path(cfg, pth)
                        if isinstance(value, str):
                            environ[envvar] = value
                        elif isinstance(value, bool):
                            environ[envvar] = str(int(value))
                        else:
                            environ[envvar] = str(value)
                if parse_args:
                    yield cfg, options
                else:
                    yield cfg
            finally:
                if set_global:
                    global_configuration = old_global

    except ConfigurationError as exc:
        if exit_on_error:
            exit(f"\u001b[1m\u001b[31mAn error occurred\u001b[0m\n{exc}")
        else:
            raise
