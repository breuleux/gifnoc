from .registry import Registry
from .version import version

global_registry = Registry()
define = global_registry.define
proxy = global_registry.proxy
get = global_registry.get
use = global_registry.use
overlay = global_registry.overlay
set_sources = global_registry.set_sources
add_overlay = global_registry.add_overlay
cli = global_registry.cli

set_sources("${envfile:GIFNOC_FILE}")


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
