from dataclasses import is_dataclass, fields
from pathlib import Path
from types import UnionType
from ovld import meta, ovld

from .parse import parse_file, Context, FileContext, EnvContext


def is_structure(cls):
    return issubclass(cls, dict) or issubclass(cls, list) or is_dataclass(cls)


@ovld
def _acquire(model: meta(is_dataclass), d: dict, context: Context):
    d = dict(d)
    for field in fields(model):
        if field.name in d:
            v = d[field.name]
            d[field.name] = acquire(field.type, v, context)
    return d


@ovld
def _acquire(model: str, s: str, context: FileContext):
    return s


@ovld
def _acquire(model: int, x: int, context: Context):
    return x


@ovld
def _acquire(model: float, x: float, context: Context):
    return x


@ovld
def _acquire(model: bool, x: bool, context: Context):
    return x


@ovld
def _acquire(model: list, xs: list, context: Context):
    (element_model,) = model.__args__
    return [acquire(element_model, x, context) for x in xs]


@ovld
def _acquire(model: dict, xs: dict, context: Context):
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
def _acquire(model: meta(is_structure), p: Path, context: FileContext):
    p = (context.path or ".") / Path(p)
    return acquire(model, parse_file(p), FileContext(path=p.parent))


@ovld
def _acquire(model: meta(is_structure), s: str, context: FileContext):
    return acquire(model, Path(s), context)


@ovld
def _acquire(model: bool, s: str, context: EnvContext):
    if s.strip().lower() in ("", "0", "false"):
        return False
    else:
        return True


@ovld
def _acquire(model: int, s: str, context: EnvContext):
    return int(s)


@ovld
def _acquire(model: float, s: str, context: EnvContext):
    return float(s)


@ovld
def _acquire(model: str, s: str, context: EnvContext):
    return s


@ovld
def _acquire(model: Path, s: str, context: FileContext):
    return str((context.path or ".") / s)


@ovld
def _acquire(model: object, obj: object, context: Context):
    return obj


def acquire(model, obj, context):
    if isinstance(model, UnionType):
        model, *_ = model.__args__
    method = _acquire[getattr(model, "__origin__", model), type(obj), type(context)]
    return method(model, obj, context)
