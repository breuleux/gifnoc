from dataclasses import fields, is_dataclass

from apischema.conversions.converters import default_deserialization
from apischema.conversions.utils import converter_types
from ovld.types import UnionTypes

from .docstrings import get_attribute_docstrings


class ConfigurationError(Exception):
    def __init__(self, errors, is_definition_problem=False):
        self.errors = errors
        self.is_definition_problem = is_definition_problem

    def __str__(self):
        if self.is_definition_problem:
            lines = ["Errors were found in the definition of the configuration:"]
        else:
            lines = ["Errors were found in the configuration:"]
        for err in self.errors:
            loc = ".".join(map(str, err["loc"]))
            message = err["err"]
            lines.append(f"* At \u001b[1m\u001b[33m{loc}\u001b[0m: {message}")
        return "\n".join(lines)


class Named:
    """A named object.
    This class can be used to construct objects with a name that will be used
    for the string representation.
    """

    def __init__(self, name):
        """Construct a named object.
        Arguments:
            name: The name of this object.
        """
        self.name = name

    def __repr__(self):
        """Return the object's name."""
        return self.name


# Use in a merge to indicate that a key should be deleted
DELETE = Named("DELETE")


class MissingProxy:
    """Substitute for a missing import that errors out only on getattr."""

    def __init__(self, error):
        self._error = error

    def __getattr__(self, attr):
        raise self._error


def type_at_path(model, path, allow_union=True):
    """Get the type at a given path from the given configuration model.

    Argument:
        model: The configuration model (the type of configuration objects).
        path: Dot-separated fields, e.g. ``server.port``, in which case the
            return value would be the type of ``cfg.server.port``.
    """
    omodel = model
    opath = path
    for entry in path:
        model = getattr(model, "__passthrough__", model)

        doc = None
        origin = getattr(model, "__origin__", model)
        if issubclass(origin, dict):
            if hasattr(model, "__args__"):
                ktype, vtype = model.__args__
                assert ktype is str
                model = vtype
            elif hasattr(model, "__annotations__"):
                model = model.__annotations__[entry]
            else:
                model = object

        elif is_dataclass(model):
            docs = get_attribute_docstrings(model)
            flds = fields(model)
            for fld in flds:
                if fld.name == entry:
                    model = fld.type
                    doc = docs.get(entry, None)
                    break
            else:
                raise TypeError(
                    f"Cannot resolve type at `{opath}` from `{omodel}`, blocked at type `{model.__qualname__}`"
                )

        else:
            raise TypeError(
                f"Cannot resolve type at `{opath}` from `{omodel}`, blocked at type `{model.__qualname__}` (`{model.__qualname__}` is not a dataclass)"
            )

    if not allow_union and isinstance(model, UnionTypes):
        model = model.__args__[0]

    return model, doc


def get_at_path(cfg, path):
    """Get the value at a given path from the given config.

    The fields in ``path`` should be dot-separated and will be extracted from the
    configuration using getitem if a dict, getattr otherwise.

    Argument:
        cfg: The configuration object.
        path: Dot-separated fields, e.g. ``server.port``, in which case the
            return value would be ``cfg.server.port``.
    """
    curr = cfg
    for p in path:
        if isinstance(curr, dict):
            curr = curr[p]
        elif isinstance(curr, (list, tuple)):
            curr = curr[int(p)]
        else:
            curr = getattr(curr, p)
    return curr


def convertible_from_string(typ):
    return any(converter_types(ds, target=typ)[0] is str for ds in default_deserialization(typ))
