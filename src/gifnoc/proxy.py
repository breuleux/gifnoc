from serieux.features.partial import NOT_GIVEN


class MissingConfigurationError(Exception):
    pass


class Proxy:
    def __init__(self, registry, pth):
        self._context_var = registry.context_var
        self._registry = registry
        self._pth = pth
        self._cached_data = None
        self._cached = None

    def _obj(self):
        container = self._context_var.get() or self._registry.global_config
        if container is None:  # pragma: no cover
            raise MissingConfigurationError("No configuration was loaded.")
        root = cfg = container.data
        if cfg is self._cached_data:
            return self._cached
        try:
            for k in self._pth:
                if isinstance(cfg, dict):
                    cfg = cfg[k]
                elif isinstance(cfg, list):
                    cfg = cfg[int(k)]
                else:
                    cfg = getattr(cfg, k)
            self._cached_data = root
            self._cached = cfg
            return cfg
        except (KeyError, AttributeError):
            key = ".".join(self._pth)
            raise MissingConfigurationError(f"No configuration was found for key '{key}'.")

    def __str__(self):
        return f"Proxy for {self._obj()}"

    def __repr__(self):
        return f"Proxy({self._obj()!r})"

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        obj = self._obj()
        if obj is NOT_GIVEN:
            p = ".".join(self._pth)
            raise MissingConfigurationError(f"No configuration was found for '{p}'")
        return getattr(self._obj(), attr)

    def __eq__(self, other):
        return self._obj() == other

    def __ne__(self, other):  # pragma: no cover
        return self._obj() != other

    def __lt__(self, other):  # pragma: no cover
        return self._obj() < other

    def __le__(self, other):  # pragma: no cover
        return self._obj() <= other

    def __gt__(self, other):  # pragma: no cover
        return self._obj() > other

    def __ge__(self, other):  # pragma: no cover
        return self._obj() >= other

    def __hash__(self):  # pragma: no cover
        return hash(self._obj())

    def __len__(self):  # pragma: no cover
        return len(self._obj())

    def __getitem__(self, key):  # pragma: no cover
        return self._obj()[key]

    def __iter__(self):  # pragma: no cover
        return iter(self._obj())

    def __bool__(self):  # pragma: no cover
        return bool(self._obj())

    def __contains__(self, item):  # pragma: no cover
        return item in self._obj()

    def __add__(self, other):  # pragma: no cover
        return self._obj() + other

    def __sub__(self, other):  # pragma: no cover
        return self._obj() - other

    def __mul__(self, other):  # pragma: no cover
        return self._obj() * other

    def __truediv__(self, other):  # pragma: no cover
        return self._obj() / other

    def __floordiv__(self, other):  # pragma: no cover
        return self._obj() // other

    def __mod__(self, other):  # pragma: no cover
        return self._obj() % other

    def __pow__(self, other):  # pragma: no cover
        return self._obj() ** other

    def __radd__(self, other):  # pragma: no cover
        return other + self._obj()

    def __rsub__(self, other):  # pragma: no cover
        return other - self._obj()

    def __rmul__(self, other):  # pragma: no cover
        return other * self._obj()

    def __rtruediv__(self, other):  # pragma: no cover
        return other / self._obj()

    def __rfloordiv__(self, other):  # pragma: no cover
        return other // self._obj()

    def __rmod__(self, other):  # pragma: no cover
        return other % self._obj()

    def __rpow__(self, other):  # pragma: no cover
        return other ** self._obj()

    def __neg__(self):  # pragma: no cover
        return -self._obj()

    def __pos__(self):  # pragma: no cover
        return +self._obj()

    def __abs__(self):  # pragma: no cover
        return abs(self._obj())

    def __call__(self, *args, **kwargs):
        return self._obj()(*args, **kwargs)
