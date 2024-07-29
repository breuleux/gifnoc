from .interface import current_configuration


class MissingConfigurationError(Exception):
    pass


class Proxy:
    def __init__(self, *pth):
        self._pth = pth
        self._cached_data = None
        self._cached = None

    def _obj(self):
        container = current_configuration()
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
            raise MissingConfigurationError(f"No configuration was loaded for key '{key}'.")

    def __str__(self):
        return f"Proxy for {self._obj()}"

    def __repr__(self):
        return f"Proxy({self._obj()!r})"

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        return getattr(self._obj(), attr)
