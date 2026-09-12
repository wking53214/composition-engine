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


def cns_canonicalize(step: CompositionStep) -> str:
    """Convert any outcome to CNS canonical form.

    Maps system outcomes to PASS/RETRY/TERMINAL_BREACH based on model type.
    Uses authoritative CNS gate.py semantics when available.
    """
    outcome = step.output_outcome or "unknown"
    model = step.output_model

    # Already canonical (handle both string and enum forms)
    if model == "cns_gate_outcome":
        outcome_lower = str(outcome).lower()
        if outcome_lower in ("pass", "retry", "terminal_breach"):
            return outcome_lower
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
