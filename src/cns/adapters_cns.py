"""CNS system adapters: SWIZZLE, ghost_tools, WIZZLE, Innovation OS."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .core import SystemAdapter
from .cns_backend import create_cns_composer
from .outcomes import (
    GhostToolsSeverity,
    GhostToolsStatus,
    InnovationOSDecision,
    SwizzleVerdict,
    WizzleForensics,
)


class SwizzleAdapter(SystemAdapter):
    """Adapter for SWIZZLE: adversarial test framework.

    SWIZZLE plants defects and tests whether scanners find them.
    Produces Verdict outcomes: BANISHED/ESCAPED/MISNAMED/CONJURED/DISMISSED/UNSUMMONED
    """

    def __init__(self):
        super().__init__(
            system_name="swizzle",
            input_models={"cns_gate_outcome"},
            output_model="swizzle_verdict",
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Execute SWIZZLE test suite on subject."""
        if input_outcome == "retry":
            return SwizzleVerdict.BANISHED
        else:
            return SwizzleVerdict.ESCAPED


class GhostToolsAdapter(SystemAdapter):
    """Adapter for ghost_tools: code scanner and vulnerability finder."""

    def __init__(self):
        super().__init__(
            system_name="ghost_tools",
            input_models={"swizzle_verdict", "cns_gate_outcome"},
            output_model="ghost_tools_status",
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Scan subject for security findings."""
        if input_outcome == SwizzleVerdict.ESCAPED:
            return GhostToolsStatus.CONFIRMED
        else:
            return GhostToolsStatus.REASONED


class WizzleAdapter(SystemAdapter):
    """Adapter for WIZZLE: forensics edge-case test fixture.

    Tests ghost_tools's forensics layer for semantic correctness.
    """

    def __init__(self):
        super().__init__(
            system_name="wizzle",
            input_models={"ghost_tools_status"},
            output_model="wizzle_forensics",
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Verify forensics correctness against ghost_tools findings."""
        if input_outcome == GhostToolsStatus.CONFIRMED:
            return WizzleForensics.REMOVED_FROM_LIBRARY
        else:
            return WizzleForensics.UNKNOWN


class InnovationOSAdapter(SystemAdapter):
    """Adapter for Innovation OS: governed decision system.

    Takes input from SWIZZLE/ghost_tools/WIZZLE and produces a decision.
    """

    def __init__(self):
        super().__init__(
            system_name="innovation_os",
            input_models={
                "swizzle_verdict",
                "ghost_tools_status",
                "wizzle_forensics",
                "cns_gate_outcome",
            },
            output_model="innovation_os_decision",
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Produce governance decision based on input evidence."""
        if input_outcome is None:
            return InnovationOSDecision.PROPOSED
        elif input_outcome in (SwizzleVerdict.BANISHED, SwizzleVerdict.DISMISSED, GhostToolsStatus.CONFIRMED):
            return InnovationOSDecision.APPROVED
        elif input_outcome in (SwizzleVerdict.ESCAPED, SwizzleVerdict.CONJURED, GhostToolsStatus.REASONED):
            return InnovationOSDecision.REJECTED
        else:
            return InnovationOSDecision.BRANCHED


def register_cns_adapters(composer):
    """Register all CNS core adapters with a composer."""
    composer.register_adapter(SwizzleAdapter())
    composer.register_adapter(GhostToolsAdapter())
    composer.register_adapter(WizzleAdapter())
    composer.register_adapter(InnovationOSAdapter())


def register_cns_translation_rules(composer):
    """Register translation rules between CNS outcome models."""
    # Verdict → Decision
    def verdict_to_decision(verdict: str) -> str:
        if verdict in (SwizzleVerdict.BANISHED, SwizzleVerdict.DISMISSED):
            return InnovationOSDecision.APPROVED
        elif verdict in (SwizzleVerdict.ESCAPED, SwizzleVerdict.CONJURED, SwizzleVerdict.MISNAMED):
            return InnovationOSDecision.REJECTED
        else:
            return InnovationOSDecision.BRANCHED

    composer.register_translation(
        "swizzle_verdict",
        "innovation_os_decision",
        verdict_to_decision,
    )

    # Status → Decision
    def status_to_decision(status: str) -> str:
        if status == GhostToolsStatus.CONFIRMED:
            return InnovationOSDecision.APPROVED
        elif status == GhostToolsStatus.REASONED:
            return InnovationOSDecision.BRANCHED
        elif status == GhostToolsStatus.REJECTED:
            return InnovationOSDecision.REJECTED
        else:
            return InnovationOSDecision.BRANCHED

    composer.register_translation(
        "ghost_tools_status",
        "innovation_os_decision",
        status_to_decision,
    )

    # Forensics → Decision
    def forensics_to_decision(forensics: str) -> str:
        if forensics in (WizzleForensics.RELOCATED_TO_TESTS, WizzleForensics.INTENTIONAL_REMOVAL):
            return InnovationOSDecision.APPROVED
        elif forensics == WizzleForensics.REMOVED_FROM_LIBRARY:
            return InnovationOSDecision.REJECTED
        elif forensics == WizzleForensics.REGRESSION:
            return InnovationOSDecision.REJECTED
        else:
            return InnovationOSDecision.BRANCHED

    composer.register_translation(
        "wizzle_forensics",
        "innovation_os_decision",
        forensics_to_decision,
    )

    # Decision → Gate
    def decision_to_gate(decision: str) -> str:
        if decision == InnovationOSDecision.APPROVED:
            return "pass"
        elif decision == InnovationOSDecision.REJECTED:
            return "terminal_breach"
        else:
            return "retry"

    composer.register_translation(
        "innovation_os_decision",
        "cns_gate_outcome",
        decision_to_gate,
    )
