"""CNS system adapters: SWIZZLE, ghost_tools, WIZZLE, Innovation OS."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .core import SystemAdapter
from .cns_backend import create_cns_composer


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
            return "banished"
        else:
            return "escaped"


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
        if input_outcome == "escaped":
            return "confirmed"
        else:
            return "reasoned"


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
        if input_outcome == "confirmed":
            return "removed_from_library"
        else:
            return "unknown"


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
            return "proposed"
        elif input_outcome in ("banished", "dismissed", "confirmed"):
            return "approved"
        elif input_outcome in ("escaped", "conjured", "reasoned"):
            return "rejected"
        else:
            return "branched"


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
        if verdict in ("banished", "dismissed"):
            return "approved"
        elif verdict in ("escaped", "conjured", "misnamed"):
            return "rejected"
        else:
            return "branched"

    composer.register_translation(
        "swizzle_verdict",
        "innovation_os_decision",
        verdict_to_decision,
    )

    # Status → Decision
    def status_to_decision(status: str) -> str:
        if status == "confirmed":
            return "approved"
        elif status == "reasoned":
            return "branched"
        elif status == "rejected":
            return "rejected"
        else:
            return "branched"

    composer.register_translation(
        "ghost_tools_status",
        "innovation_os_decision",
        status_to_decision,
    )

    # Forensics → Decision
    def forensics_to_decision(forensics: str) -> str:
        if forensics in ("relocated_to_tests", "intentional_removal"):
            return "approved"
        elif forensics == "removed_from_library":
            return "rejected"
        elif forensics == "regression":
            return "rejected"
        else:
            return "branched"

    composer.register_translation(
        "wizzle_forensics",
        "innovation_os_decision",
        forensics_to_decision,
    )

    # Decision → Gate
    def decision_to_gate(decision: str) -> str:
        if decision == "approved":
            return "pass"
        elif decision == "rejected":
            return "terminal_breach"
        else:
            return "retry"

    composer.register_translation(
        "innovation_os_decision",
        "cns_gate_outcome",
        decision_to_gate,
    )
