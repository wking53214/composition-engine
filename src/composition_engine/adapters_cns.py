"""CNS system adapters: SWIZZLE, ghost_tools, WIZZLE, Innovation OS.

Used to be a second, hand-copied implementation of every class and function
in adapters.py -- typed on plain strings instead of SystemModel, for use
with cns_backend.py's create_cns_composer() instead of compose_library.py's
LibraryComposer. ghost_buster flagged the two invoke() methods as
near-duplicate functions without knowing why there were two; the answer is
that SystemModel's members are a str Enum, so they already equal, hash and
compare identically to the plain strings this module re-declared them as --
"cns_gate_outcome" == SystemModel.CNS_GATE_OUTCOME is True, and so is every
lookup that depends on it. There was never a reason for two copies: this
module now just re-exports adapters.py's classes and functions under their
CNS-flavored names, and register_cns_adapters()/register_cns_translation_rules()
wire the exact same adapters onto whichever composer they're handed, string-
typed or SystemModel-typed track alike.
"""

from __future__ import annotations

from .adapters import (
    GhostToolsAdapter,
    InnovationOSAdapter,
    SwizzleAdapter,
    WizzleAdapter,
    register_core_adapters as register_cns_adapters,
    register_core_translation_rules as register_cns_translation_rules,
)

__all__ = [
    "SwizzleAdapter",
    "GhostToolsAdapter",
    "WizzleAdapter",
    "InnovationOSAdapter",
    "register_cns_adapters",
    "register_cns_translation_rules",
]
