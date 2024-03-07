from .core import current_configuration


class _Proxy:
    def __init__(self, *pth):
        self._pth = pth
        self._cached_built = None
        self._cached = None

    def __obj(self):
        container = current_configuration()
        if container is None:
            raise Exception("No configuration was loaded.")
        root = cfg = container.built
        if cfg is self._cached_built:
            return self._cached
        try:
            for k in self._pth:
                if isinstance(cfg, dict):
                    cfg = cfg[k]
                else:
                    nxt = getattr(cfg, k)
                    if nxt is None and (
                        factory := getattr(cfg, "__factories__", {}).get(k, None)
                    ):
                        nxt = factory()
                        setattr(cfg, k, nxt)
                    cfg = nxt
            if cfg is None:
                key = ".".join(self._pth)
                raise Exception(f"No configuration was loaded for key '{key}'.")
            self._cached_built = root
            self._cached = cfg
            return cfg
        except (KeyError, AttributeError):
            key = ".".join(self._pth)
            raise Exception(f"No configuration was loaded for key '{key}'.")

    def __str__(self):
        return f"Proxy for {self.__obj()}"

    def __repr__(self):
        return f"_Proxy({self.__obj()!r})"

    def __getattr__(self, attr):
        return getattr(self.__obj(), attr)


def __getattr__(key):
    return _Proxy(key)


__path__ = None
