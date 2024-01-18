from .core import active_configuration


class _Proxy:
    def __init__(self, *pth):
        self._pth = pth

    def __obj(self):
        cfg = active_configuration.get()
        if cfg is None:
            raise Exception("No configuration was loaded.")
        try:
            cfg = cfg.built
            for k in self._pth:
                if isinstance(cfg, dict):
                    cfg = cfg[k]
                else:
                    cfg = getattr(cfg, k)
            return cfg
        except (KeyError, AttributeError):
            key = ".".join(self._pth)
            raise Exception(f"No configuration was loaded for key '{key}'.")

    def __getattr__(self, attr):
        return getattr(self.__obj(), attr)


def __getattr__(key):
    return _Proxy(key)


__path__ = None
