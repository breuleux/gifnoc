import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._time import time  # noqa: F401

else:

    def __getattr__(item):
        module = importlib.import_module(f"{__name__}._{item}")
        return getattr(module, item)
