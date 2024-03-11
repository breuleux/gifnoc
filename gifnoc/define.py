from typing import Optional, Type, TypeVar

from .config import _Proxy
from .registry import (
    map_environment_variables,
    register,
)

_T = TypeVar("_T")


def define(
    field: str, model: Type[_T], environ: Optional[dict] = None, default_factory=None
) -> _T:
    # The typing is a little bit of a lie since we're returning a _Proxy object,
    # but it works just the same.
    register(field, model, default_factory=default_factory)
    if environ:
        map_environment_variables(**{k: f"{field}.{v}" for k, v in environ.items()})
    return _Proxy(*field.split("."))
