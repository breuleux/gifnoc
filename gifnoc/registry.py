from dataclasses import dataclass


@dataclass
class RegisteredConfig:
    key: str
    cls: type


class Registry:
    def __init__(self):
        self.models = {}
        self.envmap = {}
        self.version = 0

    def register(self, key, cls=None):
        def reg(cls):
            self.models[key] = RegisteredConfig(
                key=key,
                cls=cls,
            )
            self.version += 1

        if cls is None:
            return reg
        else:
            return reg(cls)

    def model(self):
        return dataclass(
            type(
                "GifnocGlobalModel",
                (),
                {
                    "__annotations__": {k: v.cls for k, v in self.models.items()},
                    **{k: None for k, _ in self.models.items()},
                },
            )
        )

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
