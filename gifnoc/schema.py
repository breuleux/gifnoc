import logging
from typing import Any, get_origin

from apischema import json_schema, schema, settings
from apischema.schemas import Schema

from .docstrings import get_attribute_docstrings
from .type_wrappers import TaggedSubclass

logger = logging.getLogger(__name__)


def deserialization_schema(typ):
    for cls in TaggedSubclass._cache.values():
        cls.register_schemas()
    return json_schema.deserialization_schema(typ)


def field_base_schema(tp: Any, name: str, alias: str) -> Schema | None:
    title = alias.replace("_", " ").capitalize()
    tp = get_origin(tp) or tp  # tp can be generic

    try:
        docstrings = get_attribute_docstrings(tp)
    except Exception as exc:
        logger.error(str(exc), exc_info=exc)
        return schema(title=title)

    if doc := docstrings.get(name, None):
        return schema(title=title, description=doc)
    else:
        return schema(title=title)


settings.base_schema.field = field_base_schema
