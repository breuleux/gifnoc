from dataclasses import fields, is_dataclass

from .docstrings import get_attribute_docstrings


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


def type_at_path(model, path):
    """Get the type at a given path from the given configuration model.

    Argument:
        model: The configuration model (the type of configuration objects).
        path: Dot-separated fields, e.g. ``server.port``, in which case the
            return value would be the type of ``cfg.server.port``.
    """
    omodel = model
    opath = path
    for entry in path:
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
                raise TypeError(f"Cannot resolve type at `{opath}` from `{omodel}`")

        else:
            raise TypeError(f"Cannot resolve type at `{opath}` from `{omodel}`")

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
        else:
            curr = getattr(curr, p)
    return curr
