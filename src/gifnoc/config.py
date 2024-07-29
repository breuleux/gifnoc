from .proxy import Proxy as _Proxy


def __getattr__(key):
    return _Proxy(key)


# What did I do this for?
__path__ = None
