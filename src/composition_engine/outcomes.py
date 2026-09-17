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
from typing import Any, Dict, FrozenSet, Type


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
    model claimed and never promotes itself.
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
    """WIZZLE: where did the declared-but-unproduced state go?

    INTENTIONAL_REMOVAL is undocumented and unproduced. It is written down
    here because two branches already compare against it -- in
    `compose_library._canonicalize` and in the forensics translation rule,
    both mapping it to an approving outcome -- while no adapter in this
    repository ever returns it and no docstring lists it. Declaring it is
    not an endorsement: it makes a dead branch visible to the tools instead
    of leaving it as a literal nobody can grep for a definition of. Either
    something should produce it or those two branches should go.
    """

    REMOVED_FROM_LIBRARY = "removed_from_library"
    RELOCATED_TO_TESTS = "relocated_to_tests"
    REGRESSION = "regression"
    UNKNOWN = "unknown"
    INTENTIONAL_REMOVAL = "intentional_removal"


class InnovationOSDecision(str, Enum):
    """Innovation OS: what did governance decide?"""

    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    REJECTED = "rejected"
    BRANCHED = "branched"


# Keyed by SystemModel's value rather than by SystemModel itself, because
# SystemModel lives in compose_library, which imports this module. The
# string is the stable half of that enum and the indirection costs one
# lookup.
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
