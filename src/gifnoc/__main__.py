import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import yaml
from serieux import CommandLineArguments, TaggedUnion, deserialize, schema, serialize
from serieux.model import field_at

from gifnoc import add_overlay, global_registry


def value_at(data, path):
    for part in path.split("."):
        if isinstance(data, Sequence):
            data = data[int(part)]
        elif isinstance(data, Mapping):  # pragma: no cover
            data = data[part]
        else:
            data = getattr(data, part)
    return data


def model_at(model, path):
    model = field_at(model, path)
    if model is None:  # pragma: no cover
        sys.exit(f"No model found at {path!r}")
    return model.type


@dataclass
class Dump:
    """Dump configuration."""

    # Attribute path to follow in the structure
    # [positional]
    subpath: str = None

    # Dump format
    # [alias: -f]
    format: str = "yaml"

    def __call__(self):
        container = global_registry.current()
        data = container.data
        model = container.model

        if self.subpath:
            model = model_at(model, self.subpath)
            data = value_at(data, self.subpath)

        serialized = serialize(model, data)
        if self.format == "raw":  # pragma: no cover
            dmp = str(serialized)
        elif self.format == "yaml":
            dmp = yaml.safe_dump(serialized)
        elif self.format == "json":
            dmp = json.dumps(serialized, indent=4)
        else:  # pragma: no cover
            sys.exit(f"Unsupported dump format: {format}")
        print(dmp)


@dataclass
class Check:
    """Check configuration (true/false)."""

    # Attribute path to follow in the structure
    # [positional]
    subpath: str = None

    def __call__(self):
        container = global_registry.current()
        data = container.data

        try:
            data = value_at(data, self.subpath)
        except AttributeError:
            print("nonexistent")
            exit(2)

        if data:
            print("true")
            exit(0)
        elif not data:
            print("false")
            exit(1)


@dataclass
class Schema:
    """Dump JSON schema."""

    # [positional]
    subpath: str = None

    def __call__(self):
        container = global_registry.current()
        model = container._model
        if self.subpath:
            model = model_at(model, self.subpath)
        sch = schema(model).compile()
        print(json.dumps(sch, indent=4))


@dataclass
class GifnocCommand:
    """Do things with gifnoc configurations."""

    command: TaggedUnion[Dump, Check, Schema]

    # Module(s) with the configuration definition(s)
    # [alias: -m]
    # [action: append]
    module: list[str]

    # Configuration file(s) to load.
    # [alias: -c]
    config: Path = None

    def __call__(self):
        sys.path.insert(0, str(Path.cwd()))

        from_env = os.environ.get("GIFNOC_MODULE", None)
        from_env = from_env.split(",") if from_env else []

        modules = [*from_env, *self.module]

        for mod in modules:
            importlib.import_module(mod)

        if self.config:
            add_overlay(self.config)
        else:
            add_overlay({})
            pass
        self.command()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    cmd = deserialize(
        GifnocCommand,
        CommandLineArguments(arguments=argv),
    )
    cmd()


if __name__ == "__main__":  # pragma: no cover
    main()
