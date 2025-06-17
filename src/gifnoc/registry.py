import os
import random
import string
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, fields, make_dataclass
from pathlib import Path
from typing import Optional, TypeVar

from serieux import (
    DottedNotation,
    Environment,
    FromFileExtra,
    Lazy,
    Serieux,
    Sources,
    WorkingDirectory,
    parse_cli,
)
from serieux.features.dotted import unflatten
from serieux.features.partial import NOT_GIVEN

from .proxy import Proxy

_T = TypeVar("_T")


deserialize = (Serieux + FromFileExtra + DottedNotation)().deserialize


class Configuration:
    """Hold configuration base dict and built configuration.

    Configuration objects act as context managers, setting a context variable
    pointing to the current configuration. All code that
    runs from within the ``with`` block will thus have access to that
    specific configuration through the return value of ``gifnoc.define``.

    Attributes:
        sources: The data sources used to populate the configuration.
        registry: The registry to use for the data model.
        data: The deserialized configuration object, with the proper
            types.
    """

    def __init__(self, sources, registry):
        self.sources = sources
        self.registry = registry
        self._data = None
        self._model = None
        self.version = None

    def refresh(self):
        self._model = model = self.registry.model()
        defaults = unflatten(self.registry.defaults)
        self._data = deserialize(
            model,
            Sources(defaults, *self.sources),
            Environment() + WorkingDirectory(directory=Path(os.getcwd())),
        )
        self.version = self.registry.version

    @property
    def data(self):
        if not self._data or self.registry.version > self.version:
            self.refresh()
        return self._data

    @property
    def model(self):
        if not self._model or self.registry.version > self.version:  # pragma: no cover
            self.refresh()
        return self._model

    def overlay(self, sources):
        return Configuration([*self.sources, *sources], self.registry)

    def __enter__(self):
        try:
            self._token = self.registry.context_var.set(self)
            data = self.data
            for f in fields(self._model):
                if hasattr(f.type, "__enter__"):
                    getattr(data, f.name).__enter__()
            return data
        except Exception:
            self.registry.context_var.reset(self._token)
            self._token = None
            raise

    def __exit__(self, exct, excv, tb):
        self.registry.context_var.reset(self._token)
        data = self.data
        for f in fields(self._model):
            if hasattr(f.type, "__exit__"):
                getattr(data, f.name).__exit__(exct, excv, tb)
        self._token = None


@dataclass
class RegisteredConfig:
    path: str
    key: str
    cls: type
    extras: dict[str, "RegisteredConfig"] = field(default_factory=dict)

    def build(self):
        if not self.extras:
            dc = self.cls
        else:
            dc = make_dataclass(
                cls_name=self.path or "GIFNOC_ROOT",
                bases=(self.cls,),
                fields=[
                    (name, cfg.build(), field(default=NOT_GIVEN))
                    for name, cfg in self.extras.items()
                ],
            )
        return dc


@dataclass
class Root:
    pass


class Registry:
    def __init__(self, context_var=None):
        self.hierarchy = RegisteredConfig(path="", key=None, cls=Root)
        self.context_var = context_var or ContextVar("active_configuration", default=None)
        self.global_config = None
        self.defaults = {}
        self.version = 0

    def register(self, path, cls):
        def reg(hierarchy, path, key, cls):
            root, *rest = key.split(".", 1)
            rest = rest[0] if rest else None
            path = [*path, root]

            if root not in hierarchy.extras:
                hierarchy.extras[root] = RegisteredConfig(
                    path=".".join(path),
                    key=root,
                    cls=Root if rest else cls,
                )

            if rest:
                reg(hierarchy.extras[root], path, rest, cls)
            else:
                self.version += 1

        return reg(self.hierarchy, [], path, cls)

    def model(self):
        return self.hierarchy.build()

    def current(self):
        container = self.context_var.get() or self.global_config
        return container

    @contextmanager
    def overlay(self, *sources):
        """Use a configuration."""
        existing = self.context_var.get()
        with existing.overlay(sources) as container:
            yield container

    @contextmanager
    def use(self, *sources):
        """Use a configuration."""
        container = Configuration(sources, self)
        with container:
            yield container

    def set_sources(self, *sources):
        container = Configuration(sources, self)
        self.global_config = container
        container.__enter__()

    def add_overlay(self, *sources):
        existing = self.context_var.get()
        if not existing:
            self.set_sources(*sources)
        else:
            container = existing.overlay(sources)
            self.global_config = container
            container.__enter__()

    def define(
        self,
        field: str,
        model: type[_T],
        defaults: Optional[dict] = NOT_GIVEN,
        lazy: bool = False,
    ) -> _T:
        # The typing is a little bit of a lie since we're returning a Proxy object,
        # but it works just the same.
        if lazy:
            model = Lazy[model]
        if defaults is not NOT_GIVEN:
            self.defaults[field] = defaults
        self.register(field, model)
        return Proxy(self, field.split("."))

    def cli(
        self,
        type: Optional[type[_T]] = None,
        *,
        field=None,
        mapping=None,
        argv=None,
        description=None,
        config_argument=True,
    ) -> _T:
        if mapping is None:
            mapping = {}

        if field is None:
            field = "_cli_" + "".join(random.choices(string.ascii_lowercase, k=8))

        mangled_mapping = {}

        if type is not None:
            mangled_mapping[field] = {"auto": True}

        if config_argument:
            mangled_mapping[""] = {
                "option": "--config",
                "required": False,
                "help": "Path to a configuration file",
            }

        for k, v in mapping.items():
            k = k.lstrip(".")
            mangled_mapping[k] = v

        if type is not None:
            rval = self.define(field=field, model=type)
        else:
            rval = None

        overlay = parse_cli(
            root_type=self.model(),
            mapping=mangled_mapping,
            argv=argv,
            description=description or (type and type.__doc__) or "",
        )
        self.add_overlay(overlay)
        return rval
