from dataclasses import dataclass
from typing import TypedDict


@dataclass
class RegisteredConfig:
    key: str
    cls: type


class Registry:
    def __init__(self):
        self.models = {}
        self.envmap = {}

    def register(self, key, cls=None):
        def reg(cls):
            self.models[key] = RegisteredConfig(
                key=key,
                cls=cls,
            )

        if cls is None:
            return reg
        else:
            return reg(cls)

    def model(self):
        return TypedDict(
            "GifnocGlobalModel", {k: v.cls for k, v in self.models.items()}  # type: ignore
        )

    def map_environment_variables(self, **mapping):
        for (
            envvar,
            path,
        ) in mapping.items():
            self.envmap[envvar] = path.split(".")


global_registry = Registry()

register = global_registry.register
global_model = global_registry.model
map_environment_variables = global_registry.map_environment_variables
global_environ_map = global_registry.envmap
