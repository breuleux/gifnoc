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

    def __call__(self, *args, **kwargs):
        return self._obj()(*args, **kwargs)
