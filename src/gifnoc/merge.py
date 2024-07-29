"""Utilities to merge dictionaries and other data structures."""

from typing import Union

from ovld import ovld

from .utils import DELETE

###########
# cleanup #
###########


@ovld
def cleanup(value: object):
    """Clean up work structures and values."""
    return value


@ovld
def cleanup(d: dict):  # noqa: F811
    return type(d)({k: cleanup(v) for k, v in d.items() if v is not DELETE})


@ovld
def cleanup(xs: Union[tuple, list, set, frozenset]):  # noqa: F811
    return type(xs)(cleanup(x) for x in xs)


#########
# merge #
#########


@ovld
def merge(d1: dict, d2):  # noqa: F811
    rval = type(d1)()
    for k, v in d1.items():
        if k in d2:
            v2 = d2[k]
            if v2 is DELETE:
                pass
            else:
                rval[k] = merge(v, v2)
        else:
            rval[k] = v
    for k, v in d2.items():
        if k not in d1:
            rval[k] = cleanup(v)
    return rval


@ovld
def merge(l1: list, l2: list):  # noqa: F811
    return l2


@ovld
def merge(l1: list, d: dict):  # noqa: F811
    if "append" in d:
        return l1 + d["append"]
    else:
        raise TypeError("Cannot merge list and dict unless dict has 'append' key")


@ovld
def merge(a: object, b):  # noqa: F811
    if hasattr(a, "__merge__"):
        return a.__merge__(b)
    else:
        return cleanup(b)
