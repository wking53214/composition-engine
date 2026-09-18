"""Tests for the declared outcome vocabularies.

These exist because mutation analysis could not judge three of this
repository's four candidate tests: "no enum or literal collection in the
project defines these values; nothing to extend". The vocabularies are now
defined, so the values are mutable and the tests that check them can be
proven to check something.
"""

import pytest

from composition_engine.compose_library import LibraryComposer, SystemAdapter, SystemModel
from composition_engine.adapters import register_core_adapters, register_core_translation_rules, GhostToolsAdapter
from composition_engine.outcomes import (
    GhostToolsStatus,
    is_declared,
    outcome_value,
    vocabulary_for,
)


def _importable(module_name):
    """Check if a module is importable."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


class TestStringCompatibility:
    """The enums are str enums so that nothing downstream had to change."""

    def test_member_equals_its_string(self):
        assert GhostToolsStatus.CONFIRMED == "confirmed"

    def test_member_works_as_dict_key_by_value(self):
        assert {"confirmed": 1}[GhostToolsStatus.CONFIRMED] == 1

    def test_member_serialises_as_its_value(self):
        import json

        assert json.dumps({"o": GhostToolsStatus.CONFIRMED}) == '{"o": "confirmed"}'


class TestOutcomeValue:
    """str() on a str-Enum is a trap; outcome_value is the way past it."""

    def test_str_of_member_is_not_the_value(self):
        # Documenting the behaviour this helper exists for. If a future Python
        # changes it, this test fails and the helper can go.
        assert str(GhostToolsStatus.CONFIRMED) == "GhostToolsStatus.CONFIRMED"

    def test_outcome_value_is_the_value(self):
        assert outcome_value(GhostToolsStatus.CONFIRMED) == "confirmed"
        assert outcome_value(SystemModel.GHOST_TOOLS_STATUS) == "ghost_tools_status"

    def test_outcome_value_passes_plain_strings_through(self):
        assert outcome_value("confirmed") == "confirmed"


class TestVocabularies:
    def test_lookup_by_model_member_and_by_string_agree(self):
        assert vocabulary_for(SystemModel.GHOST_TOOLS_STATUS) == vocabulary_for(
            "ghost_tools_status"
        )

    def test_ghost_tools_vocabulary_is_the_documented_one(self):
        assert vocabulary_for(SystemModel.GHOST_TOOLS_STATUS) == {
            "confirmed",
            "reasoned",
            "confirmed_by_review",
            "rejected",
            "suppressed",
        }

    def test_canonical_model_declares_no_vocabulary_here(self):
        # CNS_GATE_OUTCOME belongs to GateOutcome, not to this module. Empty is
        # the honest answer, not an error.
        assert vocabulary_for(SystemModel.CNS_GATE_OUTCOME) == frozenset()

    def test_is_declared_accepts_members_and_strings(self):
        assert is_declared(SystemModel.GHOST_TOOLS_STATUS, GhostToolsStatus.CONFIRMED)
        assert is_declared("ghost_tools_status", "confirmed")

    def test_is_declared_rejects_a_typo(self):
        assert not is_declared(SystemModel.GHOST_TOOLS_STATUS, "confirmeddd")

    def test_undeclared_model_vouches_for_nothing(self):
        assert not is_declared(SystemModel.CNS_GATE_OUTCOME, "pass")


class RogueAdapter(SystemAdapter):
    """Declares the ghost_tools vocabulary and then answers outside it."""

    def __init__(self):
        super().__init__(
            system_name="rogue",
            input_models=set(),
            output_model=SystemModel.GHOST_TOOLS_STATUS,
        )

    def invoke(self, subject, input_outcome=None):
        return "confirmeddd"


class TestComposeChecksVocabulary:
    def test_core_adapters_stay_inside_their_vocabularies(self):
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)
        trace = composer.compose(
            ["ghost_tools"],
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
        # "GhostToolsStatus.REASONED" until outcome_value was applied. Nothing
        # else asserts on it.
        #
        # A bare {"repo": "x"} subject carries none of what GhostToolsAdapter's
        # real path needs (subject["repo_path"]), so it honestly reports REASONED.
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)
        trace = composer.compose(["ghost_tools"], {"repo": "x"}, cycle=1)
        timeline = trace.timeline()
        assert "reasoned" in timeline
        assert "GhostToolsStatus" not in timeline


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

        assert (
            self._canon("confirmed", SystemModel.GHOST_TOOLS_STATUS)
            is GateOutcome.TERMINAL_BREACH
        )
        assert (
            self._canon("critical", SystemModel.GHOST_TOOLS_SEVERITY)
            is GateOutcome.TERMINAL_BREACH
        )

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


class TestGhostToolsAdapterThroughRealPipeline:
    """The GHOST_TOOLS_STATUS gate polarity fix, proven through compose(),
    not by calling _canonicalize() with hand-picked literals.

    Every other test of CANONICAL_TABLE constructs a CompositionStep or calls
    _canonicalize directly -- correct for unit-testing the table in
    isolation, but it means the fix was never run through anything shaped
    like a real adapter: GhostToolsAdapter.invoke() could aggregate its
    findings backwards, or the vocabulary check could silently swallow a
    real value, and nothing here would have noticed. These tests register
    the actual adapter, call the actual compose(), and read the actual
    GateOutcome that comes out the other end -- the same path a real
    GhostToolsAdapter inherits unchanged.
    """

    @staticmethod
    def _run(findings):
        from composition_engine.adapters import GhostToolsAdapter

        composer = LibraryComposer()
        composer.register_adapter(GhostToolsAdapter())
        subject = {"repo": "some/repo"}
        if findings is not None:
            subject["findings"] = findings
        return composer.compose(["ghost_tools"], subject, cycle=1)

    def test_a_confirmed_critical_finding_breaches(self):
        trace = self._run([{"status": "confirmed", "severity": "critical"}])
        assert trace.steps[0].output_outcome is GhostToolsStatus.CONFIRMED
        assert trace.overall_outcome.value == "terminal_breach"

    def test_a_confirmed_by_review_finding_also_breaches(self):
        # Human-verified, not merely detector-proven -- still AUTHORITATIVE,
        # still breaches. Distinct code path from CONFIRMED in the adapter's
        # aggregation order; worth its own case.
        trace = self._run([{"status": "confirmed_by_review"}])
        assert trace.overall_outcome.value == "terminal_breach"

    def test_only_reasoned_findings_retries_not_breaches(self):
        # An unverified model claim. The pre-fix table breached on this;
        # the whole point of the fix is that an unproven claim doesn't get
        # the same treatment as a proven one.
        trace = self._run([{"status": "reasoned"}])
        assert trace.steps[0].output_outcome is GhostToolsStatus.REASONED
        assert trace.overall_outcome.value == "retry"

    def test_a_reviewed_and_dismissed_finding_passes(self):
        trace = self._run([{"status": "rejected"}])
        assert trace.overall_outcome.value == "pass"

    def test_a_suppressed_known_issue_passes(self):
        # Real, but accepted and waived -- not a live reason to block, even
        # though it was once confirmed.
        trace = self._run([{"status": "suppressed"}])
        assert trace.overall_outcome.value == "pass"

    def test_worst_finding_wins_when_several_are_present(self):
        # A REASONED hunch and a REJECTED dismissal alongside a real,
        # CONFIRMED defect -- the adapter has to report the most concerning
        # one, not the first, the last, or an average.
        trace = self._run(
            [
                {"status": "reasoned"},
                {"status": "rejected"},
                {"status": "confirmed"},
            ]
        )
        assert trace.steps[0].output_outcome is GhostToolsStatus.CONFIRMED
        assert trace.overall_outcome.value == "terminal_breach"

    def test_no_findings_supplied_is_a_cautious_retry_not_a_clean_pass(self):
        # No subject["findings"] at all -- the shape this repo's own demos
        # and the four-system tests below use. REASONED is the honest
        # report for a subject nobody scanned; the gate reads that as
        # unproven, not as clean.
        trace = self._run(None)
        assert trace.steps[0].output_outcome is GhostToolsStatus.REASONED
        assert trace.overall_outcome.value == "retry"

    def test_the_vocabulary_check_runs_for_real_too(self):
        # Every value GhostToolsAdapter can actually produce is declared --
        # proven by running it, not by asserting the vocabulary matches
        # itself.
        trace = self._run([{"status": "confirmed"}])
        assert trace.steps[0].metadata["outcome_declared"] is True
        assert "[!]" not in trace.timeline()


class TestGhostToolsAdapterRealScanPath:
    """GhostToolsAdapter's real path: an actual ghost_buster subprocess scan
    of a real repository, not a hand-built findings list.
    """

    @staticmethod
    def _run(subject):
        from composition_engine.adapters import GhostToolsAdapter

        composer = LibraryComposer()
        composer.register_adapter(GhostToolsAdapter())
        return composer.compose(["ghost_tools"], subject, cycle=1)

    def test_findings_list_wins_over_repo_path_when_both_given(self):
        # Cheap to check without a real scan: findings takes priority, per
        # the adapter's own docstring, so a caller who already has results
        # never pays for a redundant real scan.
        trace = self._run(
            {
                "repo_path": "/home/user/ghost_tools",
                "findings": [{"status": "rejected"}],
            }
        )
        assert trace.steps[0].output_outcome is GhostToolsStatus.REJECTED

    @pytest.mark.skipif(not _importable("ghost_buster"), reason="ghost_tools not installed alongside this checkout")
    def test_real_scan_of_composition_engine_itself_reports_a_declared_status(self):
        # composition-engine's own repository, scanned for real via
        # ghost_buster's actual CLI as a subprocess -- proof the real path
        # runs end to end, not a mock of what a scan would return.
        trace = self._run({"repo_path": "/home/user/composition-engine"})
        outcome = trace.steps[0].output_outcome
        assert outcome in set(GhostToolsStatus)
        assert trace.steps[0].metadata["outcome_declared"] is True

    def test_an_unreadable_repo_path_is_a_cautious_reasoned_not_a_crash(self):
        # No findings possible (nothing there to scan), no exception either
        # -- _run_ghost_buster_scan fails closed to None, which this adapter
        # reads the same as "no findings supplied".
        trace = self._run({"repo_path": "/no/such/path/at/all"})
        assert trace.steps[0].output_outcome is GhostToolsStatus.REASONED
