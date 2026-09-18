"""CNS system adapters: ghost_tools integration.

Used to re-export adapters in both forms (SystemModel-typed and string-typed
for different composers). With only GhostToolsAdapter now, this module simply
re-exports the core adapter and registration functions for backward compatibility.
"""

from __future__ import annotations

from .adapters import (
    GhostToolsAdapter,
    register_core_adapters as register_cns_adapters,
    register_core_translation_rules as register_cns_translation_rules,
)

__all__ = [
    "GhostToolsAdapter",
    "register_cns_adapters",
    "register_cns_translation_rules",
]
