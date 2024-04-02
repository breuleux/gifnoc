from dataclasses import MISSING, dataclass, field, fields, is_dataclass, make_dataclass
from functools import partial
from typing import Callable, Optional


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
                        field(
                            default_factory=get_default_factory(
                                built, cfg.default_factory
                            )
                        ),
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

    def register(self, path, cls=None, default_factory=None):
        def reg(hierarchy, path, key, cls):
            root, *rest = key.split(".", 1)
            rest = rest[0] if rest else None
            path = [*path, root]

            if root not in hierarchy.extras:
                hierarchy.extras[root] = RegisteredConfig(
                    path=".".join(path),
                    key=root,
                    cls=Root if rest else cls,
                    default_factory=default_factory,
                )

            if rest:
                reg(hierarchy.extras[root], path, rest, cls)
            else:
                self.version += 1

        if cls is None:
            return partial(reg, self.hierarchy, [], path)
        else:
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


global_registry = Registry()

register = global_registry.register
map_environment_variables = global_registry.map_environment_variables
