"""System adapters for SWIZZLE, ghost_tools, WIZZLE, and Innovation OS.

Each adapter declares its outcome model and implements the invoke interface
for the LibraryComposer to orchestrate.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from .compose_library import SystemAdapter, SystemModel
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
            input_models={SystemModel.CNS_GATE_OUTCOME},  # Can receive retry signals
            output_model=SystemModel.SWIZZLE_VERDICT,
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Execute SWIZZLE test suite on subject.

        Args:
            subject: Repo/commit to test
            input_outcome: Previous outcome if retesting after fix

        Returns:
            Verdict: one of BANISHED/ESCAPED/MISNAMED/CONJURED/DISMISSED/UNSUMMONED
        """
        # In real execution, this invokes SWIZZLE.run_warp() or run_all()
        # For now, placeholder showing the interface

        if input_outcome == "retry":
            # Retest after fix
            return SwizzleVerdict.BANISHED  # defect was fixed; no longer found
        else:
            # Initial test
            return SwizzleVerdict.ESCAPED  # defect found but not by our planted test


class GhostToolsAdapter(SystemAdapter):
    """Adapter for ghost_tools: code scanner and vulnerability finder.

    Scans for security findings with Status (CONFIRMED/REASONED/etc.)
    and Severity (CRITICAL/MAJOR/MINOR/INFORMATIONAL).

    Produces Status outcomes by default, but can also emit Severity as separate signal.
    """

    def __init__(self):
        super().__init__(
            system_name="ghost_tools",
            input_models={
                SystemModel.SWIZZLE_VERDICT,  # Can take SWIZZLE output
                SystemModel.CNS_GATE_OUTCOME,  # Can take gate signal
            },
            output_model=SystemModel.GHOST_TOOLS_STATUS,
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Scan subject for security findings.

        Args:
            subject: Code/repo to scan
            input_outcome: Previous verdict (e.g., "escaped" from SWIZZLE)

        Returns:
            Status: one of CONFIRMED/REASONED/CONFIRMED_BY_REVIEW/REJECTED/SUPPRESSED
        """
        # In real execution, this invokes ghost_buster.cli or mechanical scanner
        # For now, placeholder

        if input_outcome == SwizzleVerdict.ESCAPED:
            # SWIZZLE found a defect; ghost_tools confirms it
            return GhostToolsStatus.CONFIRMED
        else:
            # Independent scan
            return GhostToolsStatus.REASONED  # finding needs human review


class WizzleAdapter(SystemAdapter):
    """Adapter for WIZZLE: forensics edge-case test fixture.

    Tests ghost_tools's forensics layer for semantic correctness.
    Verifies that findings match intent, not just technical accuracy.

    Produces Provenance classifications: REMOVED_FROM_LIBRARY/RELOCATED_TO_TESTS/REGRESSION/UNKNOWN
    """

    def __init__(self):
        super().__init__(
            system_name="wizzle",
            input_models={SystemModel.GHOST_TOOLS_STATUS},
            output_model=SystemModel.WIZZLE_FORENSICS,
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Verify forensics correctness against ghost_tools findings.

        Args:
            subject: Code/repo to analyze
            input_outcome: ghost_tools Status (e.g., "confirmed")

        Returns:
            Provenance: one of REMOVED_FROM_LIBRARY/RELOCATED_TO_TESTS/REGRESSION/UNKNOWN
        """
        # In real execution, this runs WIZZLE's forensics test suite
        # Checking git history, commit messages, and semantic context
        # For now, placeholder

        if input_outcome == GhostToolsStatus.CONFIRMED:
            # Finding is confirmed; check if it's intentional or regression
            return WizzleForensics.REMOVED_FROM_LIBRARY  # member was intentionally removed from production
        else:
            return WizzleForensics.UNKNOWN  # need more context


class InnovationOSAdapter(SystemAdapter):
    """Adapter for Innovation OS: governed decision system.

    Takes input from SWIZZLE/ghost_tools/WIZZLE and produces a decision
    within the innovation lifecycle: PROPOSED/EVALUATED/APPROVED/REJECTED/BRANCHED
    """

    def __init__(self):
        super().__init__(
            system_name="innovation_os",
            input_models={
                SystemModel.SWIZZLE_VERDICT,
                SystemModel.GHOST_TOOLS_STATUS,
                SystemModel.GHOST_TOOLS_SEVERITY,
                SystemModel.WIZZLE_FORENSICS,
                SystemModel.CNS_GATE_OUTCOME,
            },
            output_model=SystemModel.INNOVATION_OS_DECISION,
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Produce governance decision based on input evidence.

        Args:
            subject: What we're deciding on
            input_outcome: Evidence from prior system (verdict/status/forensics)

        Returns:
            Decision: one of PROPOSED/EVALUATED/APPROVED/REJECTED/BRANCHED
        """
        # In real execution, this consults the Innovation OS decision model
        # applying governance rules to translate evidence into a decision
        # For now, show the translation pattern

        if input_outcome is None:
            # No prior evidence; propose for evaluation
            return InnovationOSDecision.PROPOSED
        elif input_outcome in (SwizzleVerdict.BANISHED, SwizzleVerdict.DISMISSED, GhostToolsStatus.CONFIRMED):
            # Evidence supports approval
            return InnovationOSDecision.APPROVED
        elif input_outcome in (SwizzleVerdict.ESCAPED, SwizzleVerdict.CONJURED, GhostToolsStatus.REASONED):
            # Evidence supports rejection or alternative path
            return InnovationOSDecision.REJECTED
        else:
            # Uncertain; need more information
            return InnovationOSDecision.BRANCHED


def register_core_adapters(composer: Any) -> None:
    """Register the four core system adapters with a LibraryComposer.

    Args:
        composer: LibraryComposer instance to register adapters on
    """
    composer.register_adapter(SwizzleAdapter())
    composer.register_adapter(GhostToolsAdapter())
    composer.register_adapter(WizzleAdapter())
    composer.register_adapter(InnovationOSAdapter())


def register_core_translation_rules(composer: Any) -> None:
    """Register translation rules between outcome models.

    Args:
        composer: LibraryComposer instance to register rules on
    """
    # SWIZZLE → Innovation OS
    def translate_verdict_to_decision(verdict: str) -> str:
        if verdict in (SwizzleVerdict.BANISHED, SwizzleVerdict.DISMISSED):
            return InnovationOSDecision.APPROVED
        elif verdict in (SwizzleVerdict.ESCAPED, SwizzleVerdict.CONJURED, SwizzleVerdict.MISNAMED):
            return InnovationOSDecision.REJECTED
        else:
            return InnovationOSDecision.BRANCHED

    composer.register_translation(
        SystemModel.SWIZZLE_VERDICT,
        SystemModel.INNOVATION_OS_DECISION,
        translate_verdict_to_decision,
    )

    # ghost_tools Status → Innovation OS Decision
    def translate_status_to_decision(status: str) -> str:
        if status == GhostToolsStatus.CONFIRMED:
            return InnovationOSDecision.APPROVED
        elif status == GhostToolsStatus.REASONED:
            return InnovationOSDecision.BRANCHED
        elif status == GhostToolsStatus.REJECTED:
            return InnovationOSDecision.REJECTED
        else:
            return InnovationOSDecision.BRANCHED

    composer.register_translation(
        SystemModel.GHOST_TOOLS_STATUS,
        SystemModel.INNOVATION_OS_DECISION,
        translate_status_to_decision,
    )

    # WIZZLE Forensics → Innovation OS Decision
    def translate_forensics_to_decision(forensics: str) -> str:
        if forensics in (WizzleForensics.RELOCATED_TO_TESTS, WizzleForensics.INTENTIONAL_REMOVAL):
            return InnovationOSDecision.APPROVED
        elif forensics == WizzleForensics.REMOVED_FROM_LIBRARY:
            return InnovationOSDecision.REJECTED
        elif forensics == WizzleForensics.REGRESSION:
            return InnovationOSDecision.REJECTED
        else:
            return InnovationOSDecision.BRANCHED

    composer.register_translation(
        SystemModel.WIZZLE_FORENSICS,
        SystemModel.INNOVATION_OS_DECISION,
        translate_forensics_to_decision,
    )

    # All → CNS Gate Outcome (canonical)
    def translate_decision_to_gate(decision: str) -> str:
        if decision == InnovationOSDecision.APPROVED:
            return "pass"
        elif decision == InnovationOSDecision.REJECTED:
            return "terminal_breach"
        else:
            return "retry"

    composer.register_translation(
        SystemModel.INNOVATION_OS_DECISION,
        SystemModel.CNS_GATE_OUTCOME,
        translate_decision_to_gate,
    )
