"""CNS-specific backend for UniversalComposer.

Provides CNS outcome canonicalization (PASS/RETRY/TERMINAL_BREACH),
subject binding via cryptographic digest, and convergence detection.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict, List

from .core import CompositionStep, UniversalComposer


class GateOutcome(str, Enum):
    """CNS canonical outcomes."""
    PASS = "pass"
    RETRY = "retry"
    TERMINAL_BREACH = "terminal_breach"


def subject_digest(subject: Dict[str, Any]) -> str:
    """Cryptographic hash of subject for binding."""
    subject_json = json.dumps(subject, sort_keys=True)
    return hashlib.sha256(subject_json.encode()).hexdigest()


def cns_canonicalize(step: CompositionStep) -> str:
    """Convert any outcome to CNS canonical form.

    Maps system outcomes to PASS/RETRY/TERMINAL_BREACH based on model type.
    """
    outcome = step.output_outcome or "unknown"
    model = step.output_model

    # Already canonical
    if model == "cns_gate_outcome":
        if outcome in ("pass", "retry", "terminal_breach"):
            return outcome
        return "terminal_breach"

    # SWIZZLE verdicts
    if model == "swizzle_verdict":
        if outcome in ("banished", "dismissed"):
            return "pass"
        elif outcome in ("escaped", "conjured"):
            return "terminal_breach"
        else:
            return "retry"

    # ghost_tools status
    if model == "ghost_tools_status":
        if outcome == "confirmed":
            return "pass"
        elif outcome in ("reasoned", "rejected"):
            return "terminal_breach"
        else:
            return "retry"

    # WIZZLE forensics
    if model == "wizzle_forensics":
        if outcome in ("relocated_to_tests", "intentional_removal"):
            return "pass"
        elif outcome in ("removed_from_library", "regression"):
            return "terminal_breach"
        else:
            return "retry"

    # Innovation OS decisions
    if model == "innovation_os_decision":
        if outcome == "approved":
            return "pass"
        elif outcome == "rejected":
            return "terminal_breach"
        else:
            return "retry"

    # Fallback
    return "terminal_breach"


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
