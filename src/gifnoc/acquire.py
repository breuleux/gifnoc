from dataclasses import fields
from pathlib import Path
from typing import Protocol, Union, runtime_checkable

from ovld import Dataclass, ovld

from .merge import merge
from .parse import Context, EnvContext, FileContext, parse_file, parse_source
from .utils import UnionTypes, convertible_from_string


@runtime_checkable
class PassthroughProtocol(Protocol):
    __passthrough__: object

    @classmethod
    def __subclasshook__(cls, subclass):
        return hasattr(subclass, "__passthrough__")


StructureType = Union[type[list], type[dict], type[Dataclass]]


@ovld
def acquire(model: type[Dataclass], d: dict, context: Context):
    d = dict(d)
    for field in fields(model):
        if field.name in d:
            v = d[field.name]
            d[field.name] = acquire(field.type, v, context)
    return d


@ovld
def acquire(model: type[str], s: str, context: FileContext):  # noqa: F811
    return s


@ovld
def acquire(model: type[int], x: int, context: Context):  # noqa: F811
    return x


@ovld
def acquire(model: type[float], x: float, context: Context):  # noqa: F811
    return x


@ovld
def acquire(model: type[bool], x: bool, context: Context):  # noqa: F811
    return x


@ovld
def acquire(model: type[list], xs: list, context: Context):  # noqa: F811
    (element_model,) = model.__args__
    return [acquire(element_model, x, context) for x in xs]


@ovld
def acquire(model: type[dict], xs: dict, context: Context):  # noqa: F811
    if hasattr(model, "__annotations__"):
        return {
            k: acquire(v_model, xs[k], context)
            for k, v_model in model.__annotations__.items()
            if k in xs
        }

    elif hasattr(model, "__args__"):
        key_model, element_model = model.__args__
        return {
            acquire(key_model, k, context): acquire(element_model, v, context)
            for k, v in xs.items()
        }

    else:
        return xs


@ovld
def acquire(model: StructureType, p: Path, context: FileContext):  # noqa: F811
    p = (context.path or ".") / Path(p)
    return acquire(model, parse_file(p), FileContext(path=p.parent))


@ovld
def acquire(model: StructureType, s: str, context: FileContext):  # noqa: F811
    if convertible_from_string(model):
        return s
    else:
        return acquire(model, Path(s), context)


@ovld
def acquire(  # noqa: F811
    model: type[PassthroughProtocol], x: object, context: Context
):
    return acquire(model.__passthrough__, x, context)


@ovld
def acquire(model: type[bool], s: str, context: EnvContext):  # noqa: F811
    if s.strip().lower() in ("", "0", "false"):
        return False
    else:
        return True


@ovld
def acquire(model: type[int], s: str, context: EnvContext):  # noqa: F811
    return int(s)


@ovld
def acquire(model: type[float], s: str, context: EnvContext):  # noqa: F811
    return float(s)


@ovld
def acquire(model: type[str], s: str, context: EnvContext):  # noqa: F811
    return s


@ovld
def acquire(model: type[Path], s: Union[str, Path], context: FileContext):  # noqa: F811
    return str(((context.path or ".") / s).resolve())


@ovld
def acquire(model: type[Path], obj: Path, context: Context):  # noqa: F811
    return str(obj)


@ovld
def acquire(model: type[object], obj: object, context: Context):  # noqa: F811
    return obj


@ovld
def acquire(model: UnionTypes, obj: object, context: Context):  # noqa: F811
    model, *_ = model.__args__
    return acquire(model, obj, context)


def parse_sources(model, *sources):
    result = {}
    for src in sources:
        for ctx, dct in parse_source(src):
            result = merge(result, acquire(model, dct, ctx))
    return result
