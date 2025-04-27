import sys
import traceback

from serieux import SerieuxError

from .registry import Registry
from .version import version

global_registry = Registry()
define = global_registry.define
use = global_registry.use
overlay = global_registry.overlay
set_sources = global_registry.set_sources
add_overlay = global_registry.add_overlay
cli = global_registry.cli

set_sources("${envfile:GIFNOC_FILE}")


def custom_excepthook(exc_type, exc_value, exc_traceback):
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    if isinstance(exc_value, SerieuxError):
        tb = exc_value.__traceback__
        while tb.tb_next:
            spec = getattr(tb.tb_next.tb_frame.f_globals.get("__spec__", None), "name", None)
            if spec and (spec.startswith("gifnoc") or spec == "contextlib"):
                tb.tb_next = None
                break
            tb = tb.tb_next

        print(
            "============================= Configuration error ==============================",
            file=sys.stderr,
        )
        traceback.print_tb(tb)
        print("=" * 80, file=sys.stderr)
        exc_value.display()
        print("=" * 80, file=sys.stderr)


sys.excepthook = custom_excepthook


__all__ = [
    "global_registry",
    "cli",
    "define",
    "use",
    "overlay",
    "Registry",
    "set_sources",
    "add_overlay",
    "version",
]
