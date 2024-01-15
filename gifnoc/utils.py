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
    def __init__(self, error):
        self._error = error

    def __getattr__(self, attr):
        raise self._error


def type_at_path(model, path):
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


def get_at_path(value, path):
    curr = value
    for p in path:
        if isinstance(curr, dict):
            curr = curr[p]
        else:
            curr = getattr(curr, p)
    return curr
