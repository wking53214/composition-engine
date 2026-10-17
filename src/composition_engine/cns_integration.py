"""Integration with actual CNS gate infrastructure.

When CNS is available (installed or as sibling repo), use its authoritative
implementations of:
- GateOutcome (enum: PASS/RETRY/TERMINAL_BREACH)
- subject_digest (cryptographic binding)
- resolve (cascade of outcomes)

Fallback to local implementations if CNS is unavailable.
"""

from __future__ import annotations

import sys
from typing import Any, Dict

# Try to import from actual CNS repo
try:
    from cns.gate import GateOutcome as CNSGateOutcome
    from cns.gate import subject_digest as cns_subject_digest
    from cns.gate import resolve as cns_resolve
    from cns.gate import GateResult

    HAS_CNS = True
    GateOutcome = CNSGateOutcome
    subject_digest = cns_subject_digest

except ImportError:
    # Fallback: use local implementations
    HAS_CNS = False

    from collections.abc import Mapping, Sequence
    from enum import Enum
    import hashlib

    class GateOutcome(str, Enum):
        """Canonical outcomes (from CNS gate.py)."""
        PASS = "pass"
        RETRY = "retry"
        TERMINAL_BREACH = "terminal_breach"

    def _canonical(value: Any) -> str:
        """Length-prefixed rendering of restricted content, as cns.gate._canonical.

        Not JSON: a digest bound without CNS must equal the one CNS computes, or
        no verdict made here verifies there. Proven by cns_composition.fallback_parity
        and contracts/digest-vectors.json in the CNS repository.
        """
        if value is None:
            return "n:"
        if isinstance(value, bool):  # before int: True is not 1
            return "b:1" if value else "b:0"
        if isinstance(value, int):
            return f"i:{value}:"
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                raise TypeError("cannot bind a verdict to NaN or an infinity")
            if value == 0.0:
                value = 0.0  # collapses -0.0
            return f"f:{value!r}:"
        if isinstance(value, str):
            return f"s:{len(value)}:{value}"  # length in code points, not bytes
        if isinstance(value, Mapping):
            keys = sorted(str(k) for k in value.keys())  # code point order
            if len(set(keys)) != len(keys):
                raise TypeError("mapping keys collide once stringified")
            return f"d:{len(keys)}:" + "".join(_canonical(k) + _canonical(value[k]) for k in keys)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return f"l:{len(value)}:" + "".join(_canonical(v) for v in value)
        raise TypeError(f"cannot bind a verdict to {type(value).__name__}")

    def subject_digest(subject: Dict[str, Any]) -> str:
        """SHA-256 of the canonical encoding; identical to cns.gate.subject_digest."""
        return hashlib.sha256(_canonical(subject).encode("utf-8")).hexdigest()

    # Fallback resolve (simple cascade: breach > retry > pass)
    def cns_resolve(results):
        """Cascade: any TERMINAL_BREACH wins, then RETRY, then PASS."""
        outcomes = list(results)
        if not outcomes:
            return GateOutcome.PASS

        # Check for terminal breaches first
        for outcome in outcomes:
            if outcome == GateOutcome.TERMINAL_BREACH or outcome == "terminal_breach":
                return GateOutcome.TERMINAL_BREACH

        # Then retries
        for outcome in outcomes:
            if outcome == GateOutcome.RETRY or outcome == "retry":
                return GateOutcome.RETRY

        # Finally pass
        return GateOutcome.PASS


def get_cns_status():
    """Report whether CNS is available and which implementations are in use."""
    status = {
        "has_cns": HAS_CNS,
        "gate_outcome_source": "cns.gate" if HAS_CNS else "local_fallback",
        "subject_digest_source": "cns.gate" if HAS_CNS else "local_fallback",
    }
    return status
