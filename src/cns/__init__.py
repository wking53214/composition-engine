"""Composition Engine: Universal system orchestrator.

Core (system-agnostic):
- UniversalComposer: Orchestrates any systems
- SystemAdapter: Plugin interface for systems
- CompositionStep, CompositionTrace: Execution results

CNS Backend (optional):
- create_cns_composer: Pre-configured composer with CNS semantics
- GateOutcome: CNS canonical form (PASS/RETRY/TERMINAL_BREACH)
- subject_digest, cns_canonicalize, cns_converge: CNS functions

CNS Adapters (optional):
- SWIZZLE, ghost_tools, WIZZLE, Innovation OS adapters
- register_cns_adapters, register_cns_translation_rules
"""

from .core import (
    UniversalComposer,
    SystemAdapter,
    CompositionStep,
    CompositionTrace,
    CompositionBuilder,
)

from .cns_backend import (
    GateOutcome,
    subject_digest,
    cns_canonicalize,
    cns_converge,
    create_cns_composer,
)

from .adapters_cns import (
    SwizzleAdapter,
    GhostToolsAdapter,
    WizzleAdapter,
    InnovationOSAdapter,
    register_cns_adapters,
    register_cns_translation_rules,
)

__all__ = [
    # Core
    "UniversalComposer",
    "SystemAdapter",
    "CompositionStep",
    "CompositionTrace",
    "CompositionBuilder",
    # CNS Backend
    "GateOutcome",
    "subject_digest",
    "cns_canonicalize",
    "cns_converge",
    "create_cns_composer",
    # CNS Adapters
    "SwizzleAdapter",
    "GhostToolsAdapter",
    "WizzleAdapter",
    "InnovationOSAdapter",
    "register_cns_adapters",
    "register_cns_translation_rules",
]
