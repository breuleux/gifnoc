import argparse
import os
from importlib import import_module

from apischema import serialize

from gifnoc.utils import get_at_path

from .core import use
from .parse import EnvironMap, extensions
from .registry import global_registry


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

    if options.ignore_env:
        from_env = []
    else:
        from_env = os.environ.get("GIFNOC_FILE", None)
        from_env = from_env.split(",") if from_env else []

    sources = [*from_env, *options.config]
    if not options.ignore_env:
        sources.append(EnvironMap(environ=os.environ, map=global_registry.envmap))

    if not sources:
        exit("Please provide at least one config source.")

    with use(*sources) as cfg:
        if options.command == "dump":
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
        else:
            exit(f"Unsupported command: {options.command}")


if __name__ == "__main__":
    main()
