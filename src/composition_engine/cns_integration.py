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

    from enum import Enum
    import hashlib
    import json

    class GateOutcome(str, Enum):
        """Canonical outcomes (from CNS gate.py)."""
        PASS = "pass"
        RETRY = "retry"
        TERMINAL_BREACH = "terminal_breach"

    def subject_digest(subject: Dict[str, Any]) -> str:
        """Cryptographic hash of subject (from CNS gate.py)."""
        subject_json = json.dumps(subject, sort_keys=True)
        return hashlib.sha256(subject_json.encode()).hexdigest()

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
