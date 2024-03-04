from typing import Optional, Type, TypeVar

from . import config  # noqa: F401
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
    map_environment_variables,
    register,
)

_T = TypeVar("_T")


def define(field: str, model: Type[_T], environ: Optional[dict] = None) -> _T:
    # The typing is a little bit of a lie since we're returning a _Proxy object,
    # but it works just the same.
    register(field, model)
    if environ:
        map_environment_variables(**{k: f"{field}.{v}" for k, v in environ.items()})
    return getattr(config, field)
