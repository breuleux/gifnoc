from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import MISSING, dataclass, field, fields, is_dataclass, make_dataclass
from typing import Any, Callable, Optional, Type, TypeVar

from apischema import ValidationError, deserialize

from .acquire import parse_sources
from .type_wrappers import Extensible
from .utils import ConfigurationError

_T = TypeVar("_T")


active_configuration = ContextVar("active_configuration", default=None)
global_configuration = None


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
        data: The deserialized configuration object, with the proper
            types.
    """

    def __init__(self, sources, registry):
        self.sources = sources
        self.registry = registry
        self.base = None
        self._data = None
        self._model = None
        self.version = None

    def refresh(self):
        self._model = model = self.registry.model()
        dct = parse_sources(model, *self.sources)
        dct = {f.name: dct[f.name] for f in fields(model) if f.name in dct}
        try:
            self._data = deserialize(model, dct, pass_through=lambda x: x is not Any)
        except ValidationError as exc:
            raise ConfigurationError(exc.errors) from None
        self.base = dct
        self.version = self.registry.version

    @property
    def data(self):
        if not self._data or self.registry.version > self.version:
            self.refresh()
        return self._data

    def overlay(self, sources):
        return Configuration([*self.sources, *sources], self.registry)

    def __enter__(self):
        try:
            self._token = active_configuration.set(self)
            data = self.data
            for f in fields(self._model):
                value = getattr(data, f.name, None)
                if hasattr(value, "__enter__"):
                    value.__enter__()
            return data
        except Exception:
            active_configuration.reset(self._token)
            self._token = None
            raise

    def __exit__(self, exct, excv, tb):
        active_configuration.reset(self._token)
        data = self.data
        for f in fields(self._model):
            value = getattr(data, f.name, None)
            if hasattr(value, "__exit__"):
                value.__exit__(exct, excv, tb)
        self._token = None


def get_default_factory(cls, default_factory=None):
    cls = getattr(cls, "__passthrough__", cls)
    if default_factory is None and is_dataclass(cls):
        if all(
            field.default is not MISSING or field.default_factory is not MISSING
            for field in fields(cls)
        ):
            default_factory = cls
        return default_factory or (lambda: None)


@dataclass
class RegisteredConfig:
    path: str
    key: str
    cls: type
    wrapper: Optional[type] = None
    default_factory: Optional[Callable[[], object]] = None
    extras: dict[str, "RegisteredConfig"] = field(default_factory=dict)

    def __post_init__(self):
        if hasattr(self.cls, "__passthrough__"):
            self.wrapper = self.cls.__wrapper__
            self.cls = self.cls.__passthrough__

    def build(self):
        if not self.extras:
            dc = self.cls
        else:
            dc = make_dataclass(
                cls_name=self.path,
                bases=(self.cls,),
                fields=[
                    (
                        name,
                        built := cfg.build(),
                        field(default_factory=get_default_factory(built, cfg.default_factory)),
                    )
                    for name, cfg in self.extras.items()
                ],
            )
        if self.wrapper:
            dc = self.wrapper[dc]
        return dc


@dataclass
class Root:
    pass


class Registry:
    def __init__(self):
        self.hierarchy = RegisteredConfig(
            path="",
            key=None,
            cls=Root,
        )
        self.envmap = {}
        self.version = 0

    def register(self, path, cls, default_factory=None):
        def reg(hierarchy, path, key, cls):
            root, *rest = key.split(".", 1)
            rest = rest[0] if rest else None
            path = [*path, root]

            if root not in hierarchy.extras:
                hierarchy.extras[root] = RegisteredConfig(
                    path=".".join(path),
                    key=root,
                    cls=Extensible[Root] if rest else cls,
                    default_factory=default_factory,
                )

            if rest:
                reg(hierarchy.extras[root], path, rest, cls)
            else:
                self.version += 1

        return reg(self.hierarchy, [], path, cls)

    def model(self):
        return self.hierarchy.build()

    def map_environment_variables(self, **mapping):
        for (
            envvar,
            path,
        ) in mapping.items():
            self.envmap[envvar] = path.split(".")
        self.version += 1

    @contextmanager
    def use(self, *sources):
        """Use a configuration."""
        container = Configuration(sources, self)
        with container:
            yield container

    def load(self, *sources):
        container = Configuration(sources=sources, registry=self)
        return container

    def load_global(self, *sources):
        global global_configuration

        container = Configuration(sources=sources, registry=self)
        container.__enter__()
        global_configuration = container
        return container

    def define(
        self,
        field: str,
        model: Type[_T],
        environ: Optional[dict] = None,
        default_factory=None,
    ) -> _T:
        from .config import _Proxy

        # The typing is a little bit of a lie since we're returning a _Proxy object,
        # but it works just the same.
        self.register(field, model, default_factory=default_factory)
        if environ:
            self.map_environment_variables(**{k: f"{field}.{v}" for k, v in environ.items()})
        return _Proxy(*field.split("."))
