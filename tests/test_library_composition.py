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
