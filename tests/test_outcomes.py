"""Tests for the declared outcome vocabularies.

These exist because mutation analysis could not judge three of this
repository's four candidate tests: "no enum or literal collection in the
project defines these values; nothing to extend". The vocabularies are now
defined, so the values are mutable and the tests that check them can be
proven to check something.
"""

import pytest

from composition_engine.compose_library import LibraryComposer, SystemAdapter, SystemModel
from composition_engine.adapters import register_core_adapters, register_core_translation_rules
from composition_engine.outcomes import (
    GhostToolsStatus,
    InnovationOSDecision,
    SwizzleVerdict,
    WizzleForensics,
    is_declared,
    outcome_value,
    vocabulary_for,
)


class TestStringCompatibility:
    """The enums are str enums so that nothing downstream had to change."""

    def test_member_equals_its_string(self):
        assert SwizzleVerdict.BANISHED == "banished"
        assert GhostToolsStatus.CONFIRMED == "confirmed"
        assert InnovationOSDecision.APPROVED == "approved"

    def test_member_works_as_dict_key_by_value(self):
        assert {"banished": 1}[SwizzleVerdict.BANISHED] == 1

    def test_member_serialises_as_its_value(self):
        import json

        assert json.dumps({"o": SwizzleVerdict.BANISHED}) == '{"o": "banished"}'


class TestOutcomeValue:
    """str() on a str-Enum is a trap; outcome_value is the way past it."""

    def test_str_of_member_is_not_the_value(self):
        # Documenting the behaviour this helper exists for. If a future Python
        # changes it, this test fails and the helper can go.
        assert str(SwizzleVerdict.BANISHED) == "SwizzleVerdict.BANISHED"

    def test_outcome_value_is_the_value(self):
        assert outcome_value(SwizzleVerdict.BANISHED) == "banished"
        assert outcome_value(SystemModel.SWIZZLE_VERDICT) == "swizzle_verdict"

    def test_outcome_value_passes_plain_strings_through(self):
        assert outcome_value("banished") == "banished"


class TestVocabularies:
    def test_lookup_by_model_member_and_by_string_agree(self):
        assert vocabulary_for(SystemModel.SWIZZLE_VERDICT) == vocabulary_for(
            "swizzle_verdict"
        )

    def test_swizzle_vocabulary_is_the_documented_one(self):
        assert vocabulary_for(SystemModel.SWIZZLE_VERDICT) == {
            "banished",
            "escaped",
            "misnamed",
            "conjured",
            "dismissed",
            "unsummoned",
        }

    def test_canonical_model_declares_no_vocabulary_here(self):
        # CNS_GATE_OUTCOME belongs to GateOutcome, not to this module. Empty is
        # the honest answer, not an error.
        assert vocabulary_for(SystemModel.CNS_GATE_OUTCOME) == frozenset()

    def test_is_declared_accepts_members_and_strings(self):
        assert is_declared(SystemModel.SWIZZLE_VERDICT, SwizzleVerdict.BANISHED)
        assert is_declared("swizzle_verdict", "banished")

    def test_is_declared_rejects_a_typo(self):
        assert not is_declared(SystemModel.SWIZZLE_VERDICT, "banisheddd")

    def test_undeclared_model_vouches_for_nothing(self):
        assert not is_declared(SystemModel.CNS_GATE_OUTCOME, "pass")


class RogueAdapter(SystemAdapter):
    """Declares the SWIZZLE vocabulary and then answers outside it."""

    def __init__(self):
        super().__init__(
            system_name="rogue",
            input_models=set(),
            output_model=SystemModel.SWIZZLE_VERDICT,
        )

    def invoke(self, subject, input_outcome=None):
        return "banisheddd"


class TestComposeChecksVocabulary:
    def test_core_adapters_stay_inside_their_vocabularies(self):
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)
        trace = composer.compose(
            ["swizzle", "ghost_tools", "wizzle", "innovation_os"],
            {"repo": "x"},
            cycle=1,
        )
        assert all(s.metadata["outcome_declared"] is True for s in trace.steps)
        assert "[!]" not in trace.timeline()

    def test_an_outcome_outside_the_vocabulary_is_caught_and_printed(self):
        composer = LibraryComposer()
        composer.register_adapter(RogueAdapter())
        trace = composer.compose(["rogue"], {"repo": "x"}, cycle=1)
        assert trace.steps[0].metadata["outcome_declared"] is False
        assert "[!] not in this system's declared vocabulary" in trace.timeline()

    def test_a_model_with_no_vocabulary_records_none_not_false(self):
        # "nothing declared this" and "this is not declared" are different
        # statements and the trace keeps them apart.
        class Canonical(SystemAdapter):
            def __init__(self):
                super().__init__(
                    system_name="canonical",
                    input_models=set(),
                    output_model=SystemModel.CNS_GATE_OUTCOME,
                )

            def invoke(self, subject, input_outcome=None):
                return "pass"

        composer = LibraryComposer()
        composer.register_adapter(Canonical())
        trace = composer.compose(["canonical"], {"repo": "x"}, cycle=1)
        assert trace.steps[0].metadata["outcome_declared"] is None
        assert "[!]" not in trace.timeline()


class TestTimelineFormatting:
    def test_timeline_prints_values_not_member_names(self):
        # Converting the literals to enum members silently changed this text to
        # "SwizzleVerdict.ESCAPED" until outcome_value was applied. Nothing
        # else asserts on it.
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)
        trace = composer.compose(["swizzle", "ghost_tools"], {"repo": "x"}, cycle=1)
        timeline = trace.timeline()
        assert "escaped" in timeline
        assert "SwizzleVerdict" not in timeline


class TestCanonicalTable:
    """The table that replaced four near-identical branch cascades."""

    def _canon(self, outcome, model):
        from composition_engine.compose_library import CompositionStep, LibraryComposer

        step = CompositionStep(
            system_name="x", output_outcome=outcome, output_model=model
        )
        return LibraryComposer()._canonicalize(step)

    def test_every_model_has_an_entry(self):
        from composition_engine.compose_library import CANONICAL_TABLE

        assert set(CANONICAL_TABLE) == set(SystemModel)

    def test_known_values_map_as_before(self):
        from composition_engine.cns_integration import GateOutcome

        assert self._canon("banished", SystemModel.SWIZZLE_VERDICT) is GateOutcome.PASS
        assert (
            self._canon("escaped", SystemModel.SWIZZLE_VERDICT)
            is GateOutcome.TERMINAL_BREACH
        )
        assert (
            self._canon("approved", SystemModel.INNOVATION_OS_DECISION)
            is GateOutcome.PASS
        )
        assert (
            self._canon("critical", SystemModel.GHOST_TOOLS_SEVERITY)
            is GateOutcome.TERMINAL_BREACH
        )

    def test_unlisted_value_retries_for_a_system_vocabulary(self):
        from composition_engine.cns_integration import GateOutcome

        assert (
            self._canon("misnamed", SystemModel.SWIZZLE_VERDICT) is GateOutcome.RETRY
        )
        assert self._canon("nonsense", SystemModel.WIZZLE_FORENSICS) is GateOutcome.RETRY

    def test_unlisted_canonical_value_breaches_rather_than_retries(self):
        # The one asymmetry in the table, inherited from the cascade's silent
        # fall-through. A gate that cannot read its own vocabulary has failed,
        # it has not merely failed to decide yet. Asserted so that anyone
        # "tidying" the default into RETRY has to argue with a red test.
        from composition_engine.cns_integration import GateOutcome

        assert (
            self._canon("nonsense", SystemModel.CNS_GATE_OUTCOME)
            is GateOutcome.TERMINAL_BREACH
        )
        assert self._canon("pass", SystemModel.CNS_GATE_OUTCOME) is GateOutcome.PASS

    @pytest.mark.parametrize("model", list(SystemModel))
    def test_every_declared_word_lands_somewhere(self, model):
        # Not an assertion about which outcome; an assertion that canonicalising
        # a word the vocabulary declares never raises and never returns None.
        from composition_engine.cns_integration import GateOutcome

        for word in vocabulary_for(model):
            assert isinstance(self._canon(word, model), GateOutcome)
