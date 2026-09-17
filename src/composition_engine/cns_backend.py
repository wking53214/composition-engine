"""CNS-specific backend for UniversalComposer.

Uses authoritative CNS infrastructure when available:
- GateOutcome from cns.gate (PASS/RETRY/TERMINAL_BREACH)
- subject_digest from cns.gate (cryptographic binding)
- resolve from cns.gate (outcome cascade)

Falls back to local implementations if CNS not installed.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .core import CompositionStep, UniversalComposer
from .cns_integration import GateOutcome, subject_digest, HAS_CNS, get_cns_status
from .outcomes import CANONICAL_TABLE


def cns_canonicalize(step: CompositionStep) -> str:
    """Convert any outcome to CNS canonical form.

    Maps system outcomes to PASS/RETRY/TERMINAL_BREACH based on model type,
    via the same CANONICAL_TABLE compose_library.py's LibraryComposer uses --
    not a second hand-written cascade. The two used to be independent copies
    of the same five branches; this one drifted a full row short (no
    ghost_tools_severity branch at all, so anything in that model silently
    fell through to terminal_breach) and nothing caught it, because nothing
    here had test coverage and nothing tied the two copies together. Sharing
    one table is what makes that class of drift structurally impossible
    rather than merely unlikely.

    CANONICAL_TABLE is keyed by SystemModel enum members and by the *Verdict
    /*Status/*Decision enum members within each model's row, but every one
    of those is a str Enum, and a str Enum hashes and compares equal to its
    plain string value -- so this function's plain-string model and outcome
    (this composer track never imports SystemModel or the vocabulary enums)
    look themselves up in the same dict compose_library.py's SystemModel-
    typed calls do, with no conversion at either end. Returns a plain
    string, matching every existing caller (cns_converge compares the
    result against "retry" as a string): GateOutcome.value, never the bare
    enum member -- str() on a str-Enum member prints "GateOutcome.PASS",
    not "pass".
    """
    outcome = step.output_outcome or "unknown"
    model = step.output_model

    mapping, default = CANONICAL_TABLE.get(model, ({}, GateOutcome.TERMINAL_BREACH))
    return mapping.get(outcome, default).value


def cns_converge(steps: List[CompositionStep]) -> bool:
    """Check if composition converged in CNS terms.

    Converged when final outcome is deterministic (not RETRY).
    """
    if not steps:
        return True

    final = cns_canonicalize(steps[-1])
    return final != "retry"


def create_cns_composer() -> UniversalComposer:
    """Factory for CNS-configured UniversalComposer.

    Returns a composer with:
    - Subject binding via sha256 digest
    - CNS outcome canonicalization
    - Convergence detection (RETRY = exploring)
    """
    return UniversalComposer(
        subject_digest_fn=subject_digest,
        canonicalize_fn=cns_canonicalize,
        converge_fn=cns_converge,
    )
