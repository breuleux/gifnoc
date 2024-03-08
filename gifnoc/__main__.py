import argparse
import json
import os
from importlib import import_module

from apischema import serialize

from .core import use
from .parse import EnvironMap, extensions
from .registry import global_registry
from .schema import deserialization_schema
from .utils import get_at_path, type_at_path


def command_dump(options, sources):
    with use(*sources()) as cfg:
        if options.SUBPATH:
            cfg = get_at_path(cfg, options.SUBPATH.split("."))
        ser = serialize(cfg)
        if options.format == "raw":
            print(ser)
        else:
            fmt = f".{options.format}"
            if fmt not in extensions:
                exit(f"Cannot dump to '{options.format}' format")
            else:
                print(extensions[fmt].dump(ser))


def command_schema(options, sources):
    with use(*sources(require=False)) as cfg:
        cfg_type = type(cfg)
        if options.SUBPATH:
            cfg_type, _ = type_at_path(cfg_type, options.SUBPATH.split("."))
        schema = deserialization_schema(cfg_type)
        print(json.dumps(schema, indent=4))


def main():
    parser = argparse.ArgumentParser(
        description="Do things with gifnoc configurations."
    )
    parser.add_argument(
        "--module",
        "-m",
        action="append",
        help="Module(s) with the configuration definition(s)",
        default=[],
    )
    parser.add_argument(
        "--config",
        "-c",
        dest="config",
        metavar="CONFIG",
        action="append",
        default=[],
        help="Configuration file(s) to load.",
    )
    parser.add_argument(
        "--ignore-env",
        action="store_true",
        help="Ignore mappings from environment variables.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    dump = subparsers.add_parser("dump", help="Dump configuration.")
    dump.add_argument("SUBPATH", help="Subpath to dump", nargs="?", default=None)
    dump.add_argument("--format", "-f", help="Dump format", default="raw")

    schema = subparsers.add_parser("schema", help="Dump JSON schema.")
    schema.add_argument(
        "SUBPATH", help="Subpath to get a schema for", nargs="?", default=None
    )

    options = parser.parse_args()

    from_env = os.environ.get("GIFNOC_MODULE", None)
    from_env = from_env.split(",") if from_env else []

    modules = [*from_env, *options.module]

    if not modules:
        exit(
            "You must specify at least one module to source models with,"
            " either with -m, --module or $GIFNOC_MODULE."
        )

    for modpath in modules:
        import_module(modpath)

    def build_sources(require=True):
        if options.ignore_env:
            from_env = []
        else:
            from_env = os.environ.get("GIFNOC_FILE", None)
            from_env = from_env.split(",") if from_env else []

        sources = [*from_env, *options.config]
        if not options.ignore_env:
            sources.append(EnvironMap(environ=os.environ, map=global_registry.envmap))

        if not sources and require:
            exit("Please provide at least one config source.")

        return sources

    command = globals()[f"command_{options.command}"]
    command(options, build_sources)


if __name__ == "__main__":
    main()
