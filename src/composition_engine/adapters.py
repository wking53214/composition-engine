"""System adapters for SWIZZLE, ghost_tools, WIZZLE, and Innovation OS.

Each adapter declares its outcome model and implements the invoke interface
for the LibraryComposer to orchestrate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set

from .compose_library import SystemAdapter, SystemModel
from .outcomes import (
    GhostToolsSeverity,
    GhostToolsStatus,
    InnovationOSDecision,
    SwizzleVerdict,
    WizzleForensics,
)

# ghost_tools' own forensics analysis, imported when ghost_tools is
# installed alongside this repo -- same optional-dependency shape as
# cns_integration.py's HAS_CNS, and for the same reason: re-deriving
# forensics.py's git-history walk and mechanical.py's "is this member a
# production or a comparison" AST analysis independently, inside this repo,
# would recreate exactly the kind of drifting second copy the shared
# CANONICAL_TABLE exists to rule out. When it's not importable, WizzleAdapter
# says so and returns UNKNOWN rather than fabricating a verdict.
try:
    from ghost_buster.forensics import Provenance as GhostBusterProvenance
    from ghost_buster.forensics import provenance as ghost_buster_provenance
    from ghost_buster.mechanical import _analyse_sources as ghost_buster_analyse

    HAS_GHOST_TOOLS_FORENSICS = True
except ImportError:
    HAS_GHOST_TOOLS_FORENSICS = False


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


# Ordered most- to least-concerning: the statuses ghost_tools' own schema.py
# calls AUTHORITATIVE ("the statuses a deterministic decision may rest on")
# first, then the merely-claimed REASONED, then the two dispositions that
# close a finding out without denying it happened. Used to pick the single
# worst declared status among several findings -- the natural aggregate for
# an adapter whose output model represents one verdict, not a list.
#
# ghost_buster's own unreachable_declared_state detector flags CONFIRMED
# (MAJOR), CONFIRMED_BY_REVIEW and SUPPRESSED (MINOR) as unproduced despite
# GhostToolsAdapter.invoke() below genuinely returning each of them --
# proven, not asserted: see test_outcomes.py's
# TestGhostToolsAdapterThroughRealPipeline, which drives real findings
# through compose() and reads the real GateOutcome back. What the detector
# can see is attribute-access literals (`return GhostToolsStatus.X`); what
# this code does is `return status` for a `status` bound by iterating this
# tuple, which ghost_buster's own v1.7.6 fix deliberately excludes from
# counting as production (a module-level constant collection is a table to
# compare against, the exact fix that stopped AUTHORITATIVE = frozenset(...)
# in ghost_tools' own schema.py being misread as producing its members). The
# indirection here is one level further than that fix accounts for: not a
# value read back from data, a value read back from this table by a loop.
# Restructuring this into a branch-per-member cascade would make it visible
# to the detector at the cost of reintroducing exactly the kind of
# duplicated-branches shape this repository spent this same pass removing
# from _canonicalize. Left as a documented, test-proven exception instead.
_STATUS_CONCERN_ORDER = (
    GhostToolsStatus.CONFIRMED,
    GhostToolsStatus.CONFIRMED_BY_REVIEW,
    GhostToolsStatus.REASONED,
    GhostToolsStatus.REJECTED,
    GhostToolsStatus.SUPPRESSED,
)


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

        Independent of whatever SWIZZLE reported upstream: a real
        ghost_buster scan runs its own detectors against the subject, it
        does not consult SWIZZLE's verdict to decide what it found. (An
        earlier version of this placeholder derived CONFIRMED from
        SwizzleVerdict.ESCAPED, commented "SWIZZLE found a defect; ghost_tools
        confirms it" -- but per SWIZZLE's own README, ESCAPED means the
        opposite: "silence over a proven defect. A blind spot." Treating the
        scanner's own miss as its confirmation was incoherent on SWIZZLE's
        own terms, independent of anything about gate polarity.)

        In real execution this invokes ghost_buster.cli and aggregates the
        findings it returns. Here: if `subject` carries a `findings` list
        shaped like ghost_buster's own Finding output (each a dict with a
        "status" key), report the single most-concerning declared status
        among them. With no findings supplied -- the common case in this
        repo's own demos and tests, which pass a bare {"repo": ...} subject
        -- REASONED: an unverified claim is the only honest thing to report
        about a subject nobody has actually scanned.

        Args:
            subject: Code/repo to scan, optionally with a "findings" list
            input_outcome: Previous system's outcome (unused; see above)

        Returns:
            Status: one of CONFIRMED/REASONED/CONFIRMED_BY_REVIEW/REJECTED/SUPPRESSED
        """
        findings = subject.get("findings") if isinstance(subject, dict) else None
        if findings:
            present = {f.get("status") for f in findings if f.get("status")}
            for status in _STATUS_CONCERN_ORDER:
                if status.value in present:
                    return status
        return GhostToolsStatus.REASONED


class WizzleAdapter(SystemAdapter):
    """Adapter for WIZZLE: independent forensics verification.

    Not a re-run of SWIZZLE's own test: SWIZZLE plants a defect and checks
    whether ghost_tools finds it. WIZZLE checks a different question, one
    SWIZZLE's planted-defect testing never touches -- when ghost_tools
    reports that a declared enum member is unreachable, is that
    classification actually right, against the subject's real git history?
    See ghost_buster.forensics' module docstring for why a single snapshot
    can't answer that on its own.

    Produces WizzleForensics -- ghost_buster.forensics.Provenance, verbatim:
    NEVER_PRODUCED/REMOVED_FROM_LIBRARY/RELOCATED_TO_TESTS/UNKNOWN.
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
        """Independently check one enum member's real provenance.

        Real analysis, when both the inputs and ghost_tools itself are
        available: `subject` needs "repo_path", "enum" and "member" (which
        declared-but-unproduced member to check, in which repository --
        a different question than the {"repo", "commit"} shape the rest of
        this demo chain uses, because this is a genuinely different check,
        not a restatement of the ones before it in the chain). Runs
        ghost_buster's own provenance() walk over that repository's real
        commit history and returns its answer, unmodified.

        Otherwise: UNKNOWN. Not a guess dressed as one of the other three --
        ghost_tools' own forensics.py refuses to guess when history is
        unreadable, and WizzleAdapter refuses to guess when it cannot even
        ask the question, which is the honest thing to report whether the
        limitation is "ghost_tools isn't installed here" or "subject didn't
        say what to check".

        Args:
            subject: {"repo_path", "enum", "member"} to check, or anything
                else (UNKNOWN)
            input_outcome: ghost_tools Status from the prior step (not
                consulted -- provenance() answers from git history, not
                from what a sibling adapter concluded)

        Returns:
            Provenance: one of NEVER_PRODUCED/REMOVED_FROM_LIBRARY/
            RELOCATED_TO_TESTS/UNKNOWN
        """
        if not HAS_GHOST_TOOLS_FORENSICS or not isinstance(subject, dict):
            return WizzleForensics.UNKNOWN

        repo_path = subject.get("repo_path")
        enum_name = subject.get("enum")
        member_name = subject.get("member")
        if not (repo_path and enum_name and member_name):
            return WizzleForensics.UNKNOWN

        result: GhostBusterProvenance = ghost_buster_provenance(
            Path(repo_path), enum_name, member_name, analyse=ghost_buster_analyse
        )
        return WizzleForensics(result.value)


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

        GhostToolsStatus.CONFIRMED sits in the rejection bucket here, not
        the approval one: CANONICAL_TABLE's GHOST_TOOLS_STATUS row was
        corrected (see outcomes.py) to breach on a proven, deterministic
        finding -- the same finding this method used to read as "evidence
        supports approval". This is that same correction, made a second
        time in the one other place it was written down.

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
        elif input_outcome in (
            SwizzleVerdict.BANISHED,
            SwizzleVerdict.DISMISSED,
            GhostToolsStatus.REJECTED,
            GhostToolsStatus.SUPPRESSED,
        ):
            # Evidence supports approval: no defect found, or reviewed and
            # dismissed, or a known issue already accepted.
            return InnovationOSDecision.APPROVED
        elif input_outcome in (
            SwizzleVerdict.ESCAPED,
            SwizzleVerdict.CONJURED,
            GhostToolsStatus.CONFIRMED,
            GhostToolsStatus.CONFIRMED_BY_REVIEW,
        ):
            # Evidence supports rejection: a blind spot, a false positive on
            # a clean decoy, or a proven, established defect.
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
        # Same correction as InnovationOSAdapter.invoke() above, and for the
        # same reason: CONFIRMED/CONFIRMED_BY_REVIEW are the AUTHORITATIVE,
        # deterministically-established statuses and now breach; REJECTED
        # and SUPPRESSED both close a finding out without it blocking.
        if status in (GhostToolsStatus.REJECTED, GhostToolsStatus.SUPPRESSED):
            return InnovationOSDecision.APPROVED
        elif status in (GhostToolsStatus.CONFIRMED, GhostToolsStatus.CONFIRMED_BY_REVIEW):
            return InnovationOSDecision.REJECTED
        else:
            # REASONED, or anything undeclared: unverified, not yet decided.
            return InnovationOSDecision.BRANCHED

    composer.register_translation(
        SystemModel.GHOST_TOOLS_STATUS,
        SystemModel.INNOVATION_OS_DECISION,
        translate_status_to_decision,
    )

    # WIZZLE Forensics → Innovation OS Decision
    def translate_forensics_to_decision(forensics: str) -> str:
        if forensics == WizzleForensics.NEVER_PRODUCED:
            # An oversight, or a vocabulary written ahead of the behaviour --
            # not a regression. Matches CANONICAL_TABLE's WIZZLE_FORENSICS
            # row and ghost_buster's own MINOR calibration for this state.
            return InnovationOSDecision.APPROVED
        elif forensics in (WizzleForensics.REMOVED_FROM_LIBRARY, WizzleForensics.RELOCATED_TO_TESTS):
            # Both MAJOR in ghost_buster's own severity calibration: a real
            # regression, or the same regression with its evidence quieted
            # by moving into test code. Neither is a clean state.
            return InnovationOSDecision.REJECTED
        else:
            # UNKNOWN: history unreadable. Not a pass -- see CANONICAL_TABLE's
            # comment on why this fails closed instead.
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
