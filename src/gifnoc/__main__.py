import argparse
import json
import os
import sys
from importlib import import_module

from apischema import serialize

from .interface import global_registry, use
from .parse import EnvironMap, extensions
from .schema import deserialization_schema
from .utils import get_at_path, type_at_path


def extract(options, sources):
    with use(*sources()) as cfg:
        data = cfg.data
        if options.SUBPATH:
            data = get_at_path(data, options.SUBPATH.split("."))
        return data


def command_dump(options, sources):
    data = extract(options, sources)
    ser = serialize(data)
    if options.format == "raw":
        print(ser)
    else:
        fmt = f".{options.format}"
        if fmt not in extensions:
            exit(f"Cannot dump to '{options.format}' format")
        else:
            print(extensions[fmt].dump(ser))


def command_check(options, sources):
    try:
        data = extract(options, sources)
    except AttributeError:
        print("nonexistent")
        exit(2)
    if data:
        print("true")
        exit(0)
    elif not data:
        print("false")
        exit(1)


def command_schema(options, sources):
    with use(*sources(require=False)) as cfg:
        cfg_type = type(cfg.data)
        if options.SUBPATH:
            cfg_type, _ = type_at_path(cfg_type, options.SUBPATH.split("."))
        schema = deserialization_schema(cfg_type)
        print(json.dumps(schema, indent=4))


def main(argv=None):
    sys.path.insert(0, os.path.abspath(os.curdir))

    parser = argparse.ArgumentParser(description="Do things with gifnoc configurations.")
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
    dump.add_argument("--format", "-f", help="Dump format", default="json")

    dump = subparsers.add_parser("check", help="Check configuration (true/false).")
    dump.add_argument("SUBPATH", help="Subpath to check", nargs="?", default=None)

    schema = subparsers.add_parser("schema", help="Dump JSON schema.")
    schema.add_argument("SUBPATH", help="Subpath to get a schema for", nargs="?", default=None)

    options = parser.parse_args(args=argv or sys.argv[1:])

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
