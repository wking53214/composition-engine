"""Tests for library-wide composition orchestrator.

Validates that SystemAdapter implementations work with LibraryComposer,
composition paths can be found and executed, and subject binding/convergence
work correctly across all systems.
"""

import pytest

from composition_engine.compose_library import LibraryComposer, SystemModel
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


class TestComposerReuse:
    """A composer must be reusable: compose() may not consume adapter state.

    Regression: compose() called adapter.input_models.pop(), draining the
    adapter's standing declaration. The third multi-step compose on one
    instance raised KeyError('pop from an empty set'). Every other test class
    takes a fresh fixture, so none of them caught it.
    """

    def test_compose_is_repeatable_on_one_instance(self):
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)
        for cycle in range(1, 6):
            trace = composer.compose(["swizzle", "ghost_tools"], {"s": 1}, cycle=cycle)
            assert len(trace.steps) == 2

    def test_compose_does_not_mutate_input_models(self):
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)
        before = {n: set(a.input_models) for n, a in composer.adapters.items()}
        composer.compose(["swizzle", "ghost_tools", "innovation_os"], {"s": 1}, cycle=1)
        after = {n: set(a.input_models) for n, a in composer.adapters.items()}
        assert before == after


class TestBoundaryTranslation:
    """Registered translation rules must actually fire during compose().

    Regression: the rule was applied to the CURRENT adapter's output instead of
    the incoming outcome, and to_model came from an arbitrary set.pop() rather
    than being matched against from_model, so no registered rule ever fired.
    """

    def test_rule_fires_when_models_are_incompatible(self):
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)

        fired = []
        for key, fn in list(composer.translation_rules.items()):
            def wrapped(value, _fn=fn, _key=key):
                fired.append(_key)
                return _fn(value)
            composer.translation_rules[key] = wrapped

        # innovation_os emits INNOVATION_OS_DECISION; swizzle accepts only
        # CNS_GATE_OUTCOME, so this boundary requires translation.
        trace = composer.compose(
            ["ghost_tools", "innovation_os", "swizzle"], {"s": 1}, cycle=1
        )
        assert fired, "no translation rule fired at an incompatible boundary"
        assert trace.steps[2].input_outcome != trace.steps[1].output_outcome

    def test_no_translation_when_models_already_compatible(self):
        composer = LibraryComposer()
        register_core_adapters(composer)
        register_core_translation_rules(composer)

        fired = []
        for key, fn in list(composer.translation_rules.items()):
            def wrapped(value, _fn=fn, _key=key):
                fired.append(_key)
                return _fn(value)
            composer.translation_rules[key] = wrapped

        # swizzle emits SWIZZLE_VERDICT, which ghost_tools already accepts.
        trace = composer.compose(["swizzle", "ghost_tools"], {"s": 1}, cycle=1)
        assert not fired, f"translated unnecessarily: {fired}"
        assert trace.steps[1].input_outcome == trace.steps[0].output_outcome
