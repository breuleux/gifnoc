import importlib
from collections import deque
from typing import TYPE_CHECKING, Annotated, Any, Type, TypeVar

from apischema import (
    ValidationError,
    deserialize,
    deserializer,
    schema,
    serialize,
    serializer,
)
from apischema.conversions import Conversion
from apischema.json_schema import deserialization_schema

T = TypeVar("T")


class _TaggedSubclass:
    _cache = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        if item not in TaggedSubclass._cache:
            typ = type(
                f"TaggedSubclass[{item.__name__}]",
                (TaggedSubclass,),
                {"__passthrough__": item, "__wrapper__": _TaggedSubclass},
            )
            TaggedSubclass._cache[item] = typ
            deserializer(
                Conversion(typ._deserialize, source=dict[str, Any], target=typ)
            )
            typ.register_schemas()

        return TaggedSubclass._cache[item]

    @classmethod
    def register_schemas(cls):
        base = cls.__passthrough__
        possibilities = []
        base_mod = base.__module__
        queue = deque([base])
        while queue:
            sc = queue.popleft()
            queue.extend(sc.__subclasses__())
            sc_mod = sc.__module__
            sc_name = sc.__name__
            sch = dict(deserialization_schema(sc))
            sch.pop("$schema", None)
            sch.setdefault("properties", {})["class"] = {
                "title": "Class",
                "description": "Reference to the class to instantiate",
                "enum": [sc_name if sc_mod == base_mod else f"{sc_mod}:{sc_name}"],
            }
            possibilities.append(sch)
            if sc is not base:
                sch.setdefault("required", []).append("class")
        if len(possibilities) == 1:
            schema(extra=possibilities[0])(cls)
        else:
            schema(extra={"oneOf": possibilities})(cls)

    @classmethod
    def _deserialize(cls, data: dict):
        base = cls.__passthrough__

        data = {**data}
        cls_name = data.pop("class", None)

        if cls_name is None:
            actual_class = base
        else:
            if (ncolon := cls_name.count(":")) == 0:
                mod_name = base.__module__
                symbol = cls_name
            elif ncolon == 1:
                mod_name, symbol = cls_name.split(":")
            else:
                raise ValidationError(f"Bad format for class reference: {cls_name}")
            try:
                mod = importlib.import_module(mod_name)
                actual_class = getattr(mod, symbol)
            except (ModuleNotFoundError, AttributeError) as exc:
                raise ValidationError(str(exc))
        if not issubclass(actual_class, base):
            raise ValidationError(f"'{cls_name}' is not a '{base.__name__}' subclass")
        return deserialize(actual_class, data)


if TYPE_CHECKING:
    # Lets us pretend that TaggedSubclass[T] is T
    TaggedSubclass = Annotated[T, None]

else:
    TaggedSubclass = _TaggedSubclass


@serializer
def _serialize(x: TaggedSubclass) -> dict:
    qn = type(x).__qualname__
    assert "." not in qn, "Only top-level symbols can be serialized"
    mod = type(x).__module__
    return {
        "class": f"{mod}:{qn}",
        **serialize(x),
    }
