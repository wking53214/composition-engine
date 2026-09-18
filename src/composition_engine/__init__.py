"""Composition Engine: Universal system orchestrator.

Core (system-agnostic):
- UniversalComposer: Orchestrates any systems
- SystemAdapter: Plugin interface for systems
- CompositionStep, CompositionTrace: Execution results

CNS Backend (optional):
- create_cns_composer: Pre-configured composer with CNS semantics
- GateOutcome: CNS canonical form (PASS/RETRY/TERMINAL_BREACH)
- subject_digest, cns_canonicalize, cns_converge: CNS functions

System Adapters:
- GhostToolsAdapter: Code scanner
- register_core_adapters, register_core_translation_rules

Outcome vocabularies:
- GhostToolsStatus, GhostToolsSeverity: what each system is allowed to answer
- vocabulary_for, is_declared, outcome_value: read and check those vocabularies
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

from .cns_integration import (
    HAS_CNS,
    get_cns_status,
)

from .outcomes import (
    GhostToolsStatus,
    GhostToolsSeverity,
    SystemModel,
    CANONICAL_TABLE,
    vocabulary_for,
    is_declared,
    outcome_value,
)

from .adapters import (
    GhostToolsAdapter,
    register_core_adapters,
    register_core_translation_rules,
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
    # CNS Integration
    "HAS_CNS",
    "get_cns_status",
    # System Adapters
    "GhostToolsAdapter",
    "register_core_adapters",
    "register_core_translation_rules",
    # Outcome vocabularies
    "GhostToolsStatus",
    "GhostToolsSeverity",
    "SystemModel",
    "CANONICAL_TABLE",
    "vocabulary_for",
    "is_declared",
    "outcome_value",
]
