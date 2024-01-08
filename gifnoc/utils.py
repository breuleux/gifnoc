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
