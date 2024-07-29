import logging
from typing import Any, Union, get_origin

import apischema
from apischema import json_schema, settings
from apischema.schemas import Schema
from ovld import ovld

from .docstrings import get_attribute_docstrings
from .type_wrappers import wrapper_cache

logger = logging.getLogger(__name__)


NoneType = type(None)


@ovld
def _pull_defs(d: dict):
    results = {}
    if "$defs" in d:
        results.update(d.pop("$defs"))
    for k, v in d.items():
        results.update(_pull_defs(v))
    return results


@ovld
def _pull_defs(li: list):
    results = {}
    for x in li:
        results.update(_pull_defs(x))
    return results


@ovld
def _pull_defs(obj: object):
    return {}


def deserialization_schema(typ):
    for cls in wrapper_cache.values():
        cls.register_schemas()
    rval = json_schema.deserialization_schema(typ)
    defs = _pull_defs(rval)
    rval.setdefault("$defs", {}).update(defs)
    return rval


def serialization_schema(typ):
    # Should be the same?
    return deserialization_schema(typ)


def field_base_schema(tp: Any, name: str, alias: str) -> Union[Schema, NoneType]:
    title = alias.replace("_", " ").capitalize()
    tp = get_origin(tp) or tp  # tp can be generic

    try:
        docstrings = get_attribute_docstrings(tp)
    except Exception as exc:
        logger.error(str(exc), exc_info=exc)
        return apischema.schema(title=title)

    if doc := docstrings.get(name, None):
        return apischema.schema(title=title, description=doc)
    else:
        return apischema.schema(title=title)


settings.base_schema.field = field_base_schema
