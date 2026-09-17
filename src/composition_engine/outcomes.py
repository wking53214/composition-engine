"""The outcome vocabularies, written down.

Every system in a composition chain answers in its own words: SWIZZLE
returns a verdict, ghost_tools returns a status, WIZZLE returns a
provenance classification, Innovation OS returns a decision. Those
vocabularies were previously documented in three places that could not
check each other -- a trailing comment on each `SystemModel` member, a
docstring on each adapter's `invoke`, and the string literals in the
branches themselves -- and defined in none.

Nothing enforced them, so nothing could catch a typo, a value that no
system produces, or a branch comparing against a word that is not in the
vocabulary at all. Mutation analysis said so first: of four candidate
tests, three could not be judged because "no enum or literal collection in
the project defines these values; nothing to extend". A vocabulary the
project does not define is a vocabulary no test can be proven to check.

These are `str` enums, the same shape as `GateOutcome` in
`cns_integration.py`, so `SwizzleVerdict.BANISHED == "banished"` remains
true and every existing caller, comparison and serialisation keeps working
unchanged. This module adds a place to look; it takes nothing away.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, FrozenSet, Tuple, Type

from .cns_integration import GateOutcome


def outcome_value(x: Any) -> str:
    """The string a member stands for, not the name Python prints for it.

    `str()` on a `str`-Enum member returns "SwizzleVerdict.BANISHED", because
    `Enum.__str__` wins over `str.__str__`. Only `enum.StrEnum` behaves the
    other way, and this module cannot use it while 3.11 is the floor. Equality
    is unaffected -- `SwizzleVerdict.BANISHED == "banished"` is True -- which
    is exactly why the mistake survives a casual test: it only bites code that
    formats or dict-keys a member instead of comparing it, and both of the
    lookups below do.
    """
    return x.value if isinstance(x, Enum) else str(x)


class SwizzleVerdict(str, Enum):
    """SWIZZLE: did the planted defect get caught?"""

    BANISHED = "banished"
    ESCAPED = "escaped"
    MISNAMED = "misnamed"
    CONJURED = "conjured"
    DISMISSED = "dismissed"
    UNSUMMONED = "unsummoned"


class GhostToolsStatus(str, Enum):
    """ghost_tools: how well established is the finding?

    CONFIRMED is what a deterministic check proved; REASONED is what a
    model claimed and never promotes itself. ghost_tools' own schema.py
    groups CONFIRMED, CONFIRMED_BY_REVIEW and SUPPRESSED as AUTHORITATIVE --
    "the statuses a deterministic decision may rest on" -- and excludes
    REASONED (unverified) and REJECTED (decided not real) from that set.
    CANONICAL_TABLE's GHOST_TOOLS_STATUS row is built on that same split;
    see the comment there.
    """

    CONFIRMED = "confirmed"
    REASONED = "reasoned"
    CONFIRMED_BY_REVIEW = "confirmed_by_review"
    REJECTED = "rejected"
    SUPPRESSED = "suppressed"


class GhostToolsSeverity(str, Enum):
    """ghost_tools: how much does the finding weigh?"""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFORMATIONAL = "informational"


class WizzleForensics(str, Enum):
    """WIZZLE: why is a declared enum member not produced?

    This is ghost_tools' own `ghost_buster.forensics.Provenance`, member for
    member and value for value -- not a vocabulary invented for this repo.
    An earlier version of this enum had five members (REMOVED_FROM_LIBRARY,
    RELOCATED_TO_TESTS, REGRESSION, UNKNOWN, INTENTIONAL_REMOVAL) that were
    never checked against the real detector: it turned out to have four,
    NEVER_PRODUCED was missing entirely, and REGRESSION and
    INTENTIONAL_REMOVAL don't exist there at all. REMOVED_FROM_LIBRARY
    carried both meanings at once -- one adapter's own comment called it
    "intentionally removed" while a separate, unused member spelled
    INTENTIONAL_REMOVAL sat in the canonical table mapped to the opposite
    outcome. That was never a real distinction to preserve; it was the
    absence of one, on record as far back as the adapter that produced it.

    This is what WIZZLE checks that SWIZZLE's planted-defect testing does
    not: not "did the scanner find what I planted", but "when the scanner
    says a state is unreachable, is that classification right, against real
    git history". A member nobody ever wired up and a member something
    stopped producing look identical in a single snapshot and mean very
    different things -- see forensics.py's own module docstring for why
    that distinction needs history to draw at all, and RELOCATED_TO_TESTS
    for its sharpest case: production that moved from library code into a
    test in the same commit, which makes the state no more reachable while
    making the evidence of that quieter.

    Every member but UNKNOWN arrives from data, never as a literal return in
    this codebase: WizzleAdapter builds one from ghost_buster's real
    provenance() result (`WizzleForensics(result.value)`, a non-literal
    constructor call, exactly the shape ghost_tools' own
    _reachable_from_data is written to recognise), not by naming a member
    directly. Same pattern as GhostToolsStatus.CONFIRMED_BY_REVIEW: declared
    so a value read back from real data has somewhere correct to land, not
    dead weight to prune.
    """

    #: No commit reachable from HEAD ever produced it. An oversight, or a
    #: vocabulary written ahead of the behaviour it names.
    NEVER_PRODUCED = "never_produced"
    #: Library code produced it once; a commit removed that production and
    #: left the declaration standing.
    REMOVED_FROM_LIBRARY = "removed_from_library"
    #: Production moved from library code into test code in the same
    #: commit. The declaration's evidence got quieter, not more true.
    RELOCATED_TO_TESTS = "relocated_to_tests"
    #: The history could not be read -- git missing, a shallow checkout, the
    #: search over budget. Not a synonym for NEVER_PRODUCED.
    UNKNOWN = "unknown"


class InnovationOSDecision(str, Enum):
    """Innovation OS: what did governance decide?

    EVALUATED has no real Innovation OS repository to check against --
    unlike every other unproduced member in this module, this one is not
    confirmed to be either a live word in a real system or dead. Unverified,
    not unreachable; don't delete it on the strength of an absence that
    might just be this checkout's, not the vocabulary's.
    """

    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    REJECTED = "rejected"
    BRANCHED = "branched"


class SystemModel(str, Enum):
    """Outcome model signatures across the library.

    Was declared in compose_library.py, next to the LibraryComposer that
    used to be its only reader. It moved here, next to CANONICAL_TABLE and
    the vocabularies both depend on, once cns_backend.py needed to read the
    same table under the same model names: one place either file's
    canonicalizer imports from, instead of two files hand-copying values
    that already drifted apart once (cns_backend.py's cns_canonicalize had
    no ghost_tools_severity branch at all, and silently mis-canonicalized
    anything in that model to a breach -- ghost-buster's own
    intra_function_duplicate_block finding on this file, applied literally).
    """

    SWIZZLE_VERDICT = "swizzle_verdict"  # BANISHED/ESCAPED/MISNAMED/CONJURED/DISMISSED/UNSUMMONED
    GHOST_TOOLS_STATUS = "ghost_tools_status"  # CONFIRMED/REASONED/CONFIRMED_BY_REVIEW/REJECTED/SUPPRESSED
    GHOST_TOOLS_SEVERITY = "ghost_tools_severity"  # CRITICAL/MAJOR/MINOR/INFORMATIONAL
    WIZZLE_FORENSICS = "wizzle_forensics"  # NEVER_PRODUCED/REMOVED_FROM_LIBRARY/RELOCATED_TO_TESTS/UNKNOWN
    INNOVATION_OS_DECISION = "innovation_os_decision"  # PROPOSED/EVALUATED/APPROVED/REJECTED/BRANCHED
    CNS_GATE_OUTCOME = "cns_gate_outcome"  # PASS/RETRY/TERMINAL_BREACH (canonical)


# How each system's words become the canonical gate outcome.
#
# This was four near-identical branch cascades inside compose_library.py's
# `_canonicalize`, one per outcome model, each mapping a handful of values
# and falling through to a default; ghost_buster read it as one statement
# repeated four times in one function (ghost-0f0192120c82, MAJOR) and it was
# right. It was ALSO, independently, a second near-identical cascade inside
# cns_backend.py's `cns_canonicalize` -- the same operation, hand-copied,
# with no shared source, which is how that copy went a full model (
# ghost_tools_severity) short without anyone noticing. Both canonicalizers
# read this one table now.
#
# Each entry is (mapping, default). The default is the outcome for a value
# the mapping does not list, and it is NOT uniform: an unrecognised
# canonical outcome is a TERMINAL_BREACH, because a gate that cannot read
# its own vocabulary has failed rather than merely not-yet-decided, while
# every other model treats an unlisted value as RETRY. That asymmetry was
# already in the original cascade, as CNS_GATE_OUTCOME's silent fall-through
# past the end of its own branch to the function's final return, where it
# read as an oversight. It is preserved here deliberately and written down.
#
# GHOST_TOOLS_STATUS's polarity, corrected: a red team across four
# independent lenses could not sustain the previous mapping (CONFIRMED ->
# PASS, REJECTED -> TERMINAL_BREACH). The sharpest of the four found the
# literal adapter code reaching CONFIRMED exactly on the branch SWIZZLE's
# own README defines as the scanner's silence over a proven defect -- not a
# different framing of the same evidence, a mix-up of "the scanner missed
# it" with "the scanner confirmed it". This table now follows ghost_tools'
# own AUTHORITATIVE split (see GhostToolsStatus's docstring): the statuses a
# deterministic decision may rest on -- CONFIRMED, CONFIRMED_BY_REVIEW --
# are the ones that breach the gate, because a proven, human-verified defect
# is what TERMINAL_BREACH exists to name. REJECTED (reviewed, not real) and
# SUPPRESSED (real, but accepted and waived) both pass: neither is a live
# reason to block. REASONED -- an unverified model claim, "never promotes
# itself" per ghost_tools' own principle -- retries: not proven, not yet
# decided, exactly what RETRY already means everywhere else in this table.
#
# WIZZLE_FORENSICS, redesigned around ghost_buster.forensics.Provenance
# rather than an invented vocabulary (see WizzleForensics' docstring for the
# full account). Its own author's severity calibration
# (ghost_buster/mechanical.py's _HISTORY_SEVERITY) rates NEVER_PRODUCED and
# UNKNOWN both MINOR and REMOVED_FROM_LIBRARY/RELOCATED_TO_TESTS both MAJOR;
# this table follows that MAJOR/MINOR split for what breaches, with one
# deliberate departure. UNKNOWN gets RETRY here, not PASS: ghost_tools'
# second principle is "fail closed... a criterion the scan could not assess
# counts against the patient", and UNKNOWN is exactly that criterion --
# unreadable history is not evidence of a clean one, whatever weight the
# resulting finding is calibrated at once it's raised.
CANONICAL_TABLE: Dict["SystemModel", Tuple[Dict[str, GateOutcome], GateOutcome]] = {
    SystemModel.CNS_GATE_OUTCOME: (
        {
            GateOutcome.PASS.value: GateOutcome.PASS,
            GateOutcome.TERMINAL_BREACH.value: GateOutcome.TERMINAL_BREACH,
            GateOutcome.RETRY.value: GateOutcome.RETRY,
        },
        GateOutcome.TERMINAL_BREACH,
    ),
    SystemModel.SWIZZLE_VERDICT: (
        {
            "banished": GateOutcome.PASS,
            "dismissed": GateOutcome.PASS,
            "escaped": GateOutcome.TERMINAL_BREACH,
            "conjured": GateOutcome.TERMINAL_BREACH,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.GHOST_TOOLS_STATUS: (
        {
            "confirmed": GateOutcome.TERMINAL_BREACH,
            "confirmed_by_review": GateOutcome.TERMINAL_BREACH,
            "rejected": GateOutcome.PASS,
            "suppressed": GateOutcome.PASS,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.GHOST_TOOLS_SEVERITY: (
        {
            "critical": GateOutcome.TERMINAL_BREACH,
            "major": GateOutcome.TERMINAL_BREACH,
            "minor": GateOutcome.PASS,
            "informational": GateOutcome.PASS,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.WIZZLE_FORENSICS: (
        {
            "never_produced": GateOutcome.PASS,
            "removed_from_library": GateOutcome.TERMINAL_BREACH,
            "relocated_to_tests": GateOutcome.TERMINAL_BREACH,
            "unknown": GateOutcome.RETRY,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.INNOVATION_OS_DECISION: (
        {
            "approved": GateOutcome.PASS,
            "rejected": GateOutcome.TERMINAL_BREACH,
        },
        GateOutcome.RETRY,
    ),
}


# Keyed by SystemModel's value rather than by SystemModel itself, so a
# caller with just the string (as every adapter's output_model comparison
# already works with, since these are str enums) can look itself up without
# importing the enum too.
VOCABULARIES: Dict[str, Type[Enum]] = {
    "swizzle_verdict": SwizzleVerdict,
    "ghost_tools_status": GhostToolsStatus,
    "ghost_tools_severity": GhostToolsSeverity,
    "wizzle_forensics": WizzleForensics,
    "innovation_os_decision": InnovationOSDecision,
}


def vocabulary_for(model: str) -> FrozenSet[str]:
    """Every legal outcome for one outcome model.

    An unknown model returns the empty set rather than raising: CNS_GATE_OUTCOME
    is canonical and owned by `GateOutcome`, and a caller asking about a model
    with no vocabulary here should get "nothing declared", which is the truth,
    not an exception.
    """
    vocab = VOCABULARIES.get(outcome_value(model))
    if vocab is None:
        return frozenset()
    return frozenset(member.value for member in vocab)


def is_declared(model: str, outcome: str) -> bool:
    """Is this outcome in the model's vocabulary?

    False for a model with no declared vocabulary, because an undeclared
    vocabulary cannot vouch for anything. Callers that want "unknown models
    pass" should check `vocabulary_for(model)` for emptiness first and say so
    at the call site.
    """
    return outcome_value(outcome) in vocabulary_for(model)
