import importlib
from typing import TYPE_CHECKING, Annotated, Type, TypeVar

from apischema import ValidationError, deserialize, deserializer, serialize, serializer
from apischema.conversions import Conversion

T = TypeVar("T")


class _TaggedSubclass:
    _cache = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        if item not in TaggedSubclass._cache:
            typ = type(
                f"TaggedSubclass[{item.__name__}]",
                (TaggedSubclass,),
                {"__passthrough__": item},
            )
            TaggedSubclass._cache[item] = typ
            deserializer(Conversion(typ._deserialize, source=dict, target=typ))
        return TaggedSubclass._cache[item]

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
