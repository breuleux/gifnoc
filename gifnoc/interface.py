import os
import sys
from argparse import ArgumentParser
from contextlib import contextmanager
from types import SimpleNamespace

from . import registry as registry_module
from .arg import Command, add_arguments_to_parser, compile_command
from .parse import EnvironMap, OptionsMap
from .registry import Configuration, Registry, active_configuration
from .utils import ConfigurationError, get_at_path

global_registry = Registry()
registry_module.global_configuration = Configuration(sources=[], registry=global_registry)

register = global_registry.register
map_environment_variables = global_registry.map_environment_variables
define = global_registry.define
use = global_registry.use
load = global_registry.load
load_global = global_registry.load_global


def current_configuration():
    return active_configuration.get() or registry_module.global_configuration


@contextmanager
def overlay(*sources):
    """Overlay extra configuration.

    This acts as a context manager. The modified configuration is available
    inside the context manager and is popped off afterwards.

    Arguments:
        sources: Paths to configuration files or dicts.
    """
    current = current_configuration()
    with current.overlay(sources) as overlaid:
        yield overlaid


@contextmanager
def cli(
    envvar="GIFNOC_FILE",
    config_argument="--config",
    sources=[],
    registry=global_registry,
    options={},
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
            if isinstance(options, dict) or options is None:
                command = Command(mount="", options=options)
            elif isinstance(options, str):
                command = Command(mount=options, auto=True)
            elif not isinstance(options, Command):
                raise TypeError("options argument to cli() should be a dict or a Command")
            else:
                command = options

            command = compile_command(model, "", command)
            add_arguments_to_parser(argparser, command, registry)

            parsed = argparser.parse_args(sys.argv[1:] if argv is None else argv)
        else:
            parsed = SimpleNamespace(config=[])

        if environ_map is None:
            environ_map = registry.envmap

        envvars = [envvar] if isinstance(envvar, str) else envvar

        from_env = []
        for ev in envvars:
            if env_files := environ.get(ev, None):
                from_env.extend(env_files.split(","))

        sources = [
            *from_env,
            *sources,
            *(parsed.config or []),
            EnvironMap(environ=environ, map=environ_map),
            OptionsMap(options=parsed),
        ]

        container = Configuration(sources=sources, registry=registry)
        with container as cfg:
            if set_global:
                old_global = registry_module.global_configuration
                registry_module.global_configuration = container
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
                    container.options = options
                    yield container
                else:
                    yield container
            finally:
                if set_global:
                    registry_module.global_configuration = old_global

    except ConfigurationError as exc:
        if exit_on_error:
            exit(f"\u001b[1m\u001b[31mAn error occurred\u001b[0m\n{exc}")
        else:
            raise
