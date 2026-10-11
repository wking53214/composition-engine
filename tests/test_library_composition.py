"""Tests for library-wide composition orchestrator.

Validates that SystemAdapter implementations work with LibraryComposer,
composition paths can be found and executed, and subject binding/convergence
work correctly across all systems.
"""

import pytest

from composition_engine.compose_library import LibraryComposer, SystemModel, SystemAdapter
from composition_engine.adapters import (
    register_core_adapters,
    register_core_translation_rules,
    GhostToolsAdapter,
)


class TestAdapterRegistration:
    """Verify adapters register correctly with LibraryComposer."""

    def test_ghost_tools_adapter_input_output_models(self):
        """ghost_tools accepts gate outcome, produces status."""
        adapter = GhostToolsAdapter()
        assert adapter.system_name == "ghost_tools"
        assert SystemModel.CNS_GATE_OUTCOME in adapter.input_models
        assert adapter.output_model == SystemModel.GHOST_TOOLS_STATUS


class TestLibraryComposerIntegration:
    """Verify LibraryComposer works with core adapters."""

    @pytest.fixture
    def composer(self):
        """Set up composer with core adapters and translation rules."""
        c = LibraryComposer()
        register_core_adapters(c)
        register_core_translation_rules(c)
        return c

    def test_find_path_circular(self, composer):
        """No circular paths from ghost_tools back to ghost_tools."""
        path = composer.find_composition_path("ghost_tools", "ghost_tools")
        # BFS will not find a cycle (no edge loops back)
        assert path is None or path == ["ghost_tools"]


class TestCompositionBuilder:
    """Verify fluent API for building compositions."""

    @pytest.fixture
    def composer(self):
        c = LibraryComposer()
        register_core_adapters(c)
        register_core_translation_rules(c)
        return c

    def test_builder_unknown_system_raises(self, composer):
        """Adding unknown system raises ValueError."""
        from composition_engine.compose_library import CompositionBuilder

        builder = CompositionBuilder(composer)
        with pytest.raises(ValueError, match="System not registered"):
            builder.add_system("nonexistent_system")


class _Emitter(SystemAdapter):
    """Emits a ghost_tools-style status. Accepts no input (a chain start)."""

    def __init__(self):
        super().__init__(system_name="emitter", input_models=set(),
                         output_model=SystemModel.GHOST_TOOLS_STATUS)

    def invoke(self, subject, input_outcome=None):
        return "confirmed"


class _StatusReader(SystemAdapter):
    """Accepts the same model the emitter produces: no translation needed."""

    def __init__(self):
        super().__init__(system_name="reader",
                         input_models={SystemModel.GHOST_TOOLS_STATUS},
                         output_model=SystemModel.GHOST_TOOLS_STATUS)

    def invoke(self, subject, input_outcome=None):
        return "confirmed"


class _GateReader(SystemAdapter):
    """Accepts only CNS gate outcomes: the emitter's status must be translated."""

    def __init__(self):
        super().__init__(system_name="gate",
                         input_models={SystemModel.CNS_GATE_OUTCOME},
                         output_model=SystemModel.CNS_GATE_OUTCOME)

    def invoke(self, subject, input_outcome=None):
        return "pass" if input_outcome == "pass" else "retry"


def _recording_composer(*adapters):
    """A composer whose translation rules record each time they fire."""
    composer = LibraryComposer()
    for adapter in adapters:
        composer.register_adapter(adapter)
    fired = []
    composer.register_translation(
        SystemModel.GHOST_TOOLS_STATUS, SystemModel.CNS_GATE_OUTCOME,
        lambda v: fired.append(v) or ("pass" if v == "confirmed" else "retry"),
    )
    return composer, fired


class TestComposerReuse:
    """A composer must be reusable: compose() may not consume adapter state.

    Regression: compose() called adapter.input_models.pop(), draining the
    adapter's standing declaration. The third multi-step compose on one
    instance raised KeyError('pop from an empty set'). Every other test class
    takes a fresh fixture, so none of them caught it.
    """

    def test_compose_is_repeatable_on_one_instance(self):
        composer, _ = _recording_composer(_Emitter(), _StatusReader())
        for cycle in range(1, 6):
            trace = composer.compose(["emitter", "reader"], {"s": 1}, cycle=cycle)
            assert len(trace.steps) == 2

    def test_compose_does_not_mutate_input_models(self):
        composer, _ = _recording_composer(_Emitter(), _StatusReader(), _GateReader())
        before = {n: set(a.input_models) for n, a in composer.adapters.items()}
        composer.compose(["emitter", "reader", "gate"], {"s": 1}, cycle=1)
        after = {n: set(a.input_models) for n, a in composer.adapters.items()}
        assert before == after


class TestBoundaryTranslation:
    """Registered translation rules must actually fire during compose().

    Regression: the rule was applied to the CURRENT adapter's output instead of
    the incoming outcome, and to_model came from an arbitrary set.pop() rather
    than being matched against from_model, so no registered rule ever fired.
    """

    def test_rule_fires_when_models_are_incompatible(self):
        composer, fired = _recording_composer(_Emitter(), _GateReader())
        trace = composer.compose(["emitter", "gate"], {"s": 1}, cycle=1)
        assert fired, "no translation rule fired at an incompatible boundary"
        assert trace.steps[1].input_outcome == "pass"

    def test_no_translation_when_models_already_compatible(self):
        composer, fired = _recording_composer(_Emitter(), _StatusReader())
        trace = composer.compose(["emitter", "reader"], {"s": 1}, cycle=1)
        assert not fired, f"translated unnecessarily: {fired}"
        assert trace.steps[1].input_outcome == trace.steps[0].output_outcome
