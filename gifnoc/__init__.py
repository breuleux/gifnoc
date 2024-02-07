from .core import (  # noqa: F401
    Configuration,
    active_configuration,
    current_configuration,
    get,
    gifnoc,
    is_loaded,
    load,
    load_global,
    overlay,
    use,
)
from .registry import (  # noqa: F401
    register,
    map_environment_variables,
)
from . import config  # noqa: F401


def define(field, model, environ=None):
    register(field, model)
    if environ:
        map_environment_variables(**{k: f"{field}.{v}" for k, v in environ.items()})
    return getattr(config, field)
