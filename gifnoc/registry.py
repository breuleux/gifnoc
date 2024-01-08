from dataclasses import dataclass


registry = {}
envmap = {}
argmap = {}


@dataclass
class RegisteredConfig:
    key: str
    cls: type


def register(key, cls=None):
    def reg(cls):
        registry[key] = RegisteredConfig(
            key=key,
            cls=cls,
        )

    if cls is None:
        return reg
    else:
        return reg(cls)


def map_environment_variables(**mapping):
    for (
        envvar,
        path,
    ) in mapping.items():
        envmap[envvar] = path.split(".")


def map_command_line(mapping):
    for arg, path in mapping.items():
        argmap[arg] = path.split(".")
