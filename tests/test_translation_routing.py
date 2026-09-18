"""Red-team tests for translation-aware routing.

These tests verify that the composition engine can find paths through
systems with incompatible outcome models IF translation rules exist.

This addresses the core architectural claim: "compose any systems together"
"""

import pytest

from composition_engine.core import UniversalComposer, SystemAdapter, CompositionTrace


class SensorAdapter(SystemAdapter):
    """Produces raw sensor detection: 'detected' or 'none'."""

    def __init__(self):
        super().__init__(
            system_name="sensor",
            input_models=set(),
            output_model="detection",
        )

    def invoke(self, subject, input_outcome=None):
        return "detected" if subject.get("signal", False) else "none"


class ClassifierAdapter(SystemAdapter):
    """Accepts threat_level, produces classification.

    Deliberately uses different input model than sensor output.
    """

    def __init__(self):
        super().__init__(
            system_name="classifier",
            input_models={"threat_level"},
            output_model="classification",
        )

    def invoke(self, subject, input_outcome=None):
        level = input_outcome or "none"
        if level == "critical":
            return "category_a"
        elif level == "moderate":
            return "category_b"
        else:
            return "category_c"


class DeciderAdapter(SystemAdapter):
    """Accepts classification, produces decision.

    This adapter accepts classification (matching classifier output).
    """

    def __init__(self):
        super().__init__(
            system_name="decider",
            input_models={"classification"},
            output_model="decision",
        )

    def invoke(self, subject, input_outcome=None):
        if input_outcome == "category_a":
            return "block"
        elif input_outcome == "category_b":
            return "review"
        else:
            return "allow"


def translate_detection_to_threat(detection):
    """Bridge raw detection to threat assessment."""
    return "critical" if detection == "detected" else "none"


class TestTranslationRoutingDiscovery:
    """Verify that paths requiring translation are discovered."""

    def test_direct_path_without_translation(self):
        """Sensor→Classifier is NOT directly compatible (no translation)."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        # Without translation rule, no path should exist
        path = composer.find_composition_path("sensor", "classifier")
        assert path is None, "Should not find path without translation rule"

    def test_path_discovered_after_translation_registered(self):
        """After registering translation, path becomes discoverable."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        # Register translation rule
        composer.register_translation(
            "detection",
            "threat_level",
            translate_detection_to_threat,
        )

        # Now path should be discovered
        path = composer.find_composition_path("sensor", "classifier")
        assert path is not None, "Path should exist after translation registered"
        assert path == ["sensor", "classifier"]

    def test_three_system_chain_with_translation(self):
        """Multi-system path with translation in middle."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())
        composer.register_adapter(DeciderAdapter())

        # Register only the first translation
        # (classifier→decider is direct, no translation needed)
        composer.register_translation(
            "detection",
            "threat_level",
            translate_detection_to_threat,
        )

        # Path should go sensor→classifier→decider
        path = composer.find_composition_path("sensor", "decider")
        assert path is not None
        assert path == ["sensor", "classifier", "decider"]

    def test_translation_rule_determinism(self):
        """Translation rule selection is deterministic."""
        composer = UniversalComposer()

        # Adapter that accepts multiple models
        class MultiInputAdapter(SystemAdapter):
            def __init__(self):
                super().__init__(
                    system_name="multi",
                    input_models={"model_a", "model_b"},
                    output_model="output",
                )

            def invoke(self, subject, input_outcome=None):
                return "out"

        composer.register_adapter(SensorAdapter())
        composer.register_adapter(MultiInputAdapter())

        # Register TWO possible translations
        composer.register_translation(
            "detection",
            "model_a",
            lambda x: f"model_a({x})",
        )
        composer.register_translation(
            "detection",
            "model_b",
            lambda x: f"model_b({x})",
        )

        # Run multiple times - should always select same model
        for _ in range(5):
            trace = composer.compose(["sensor", "multi"], {"signal": True}, cycle=1)
            # sorted(['model_a', 'model_b']) → ['model_a', 'model_b']
            # Should pick model_a (first in sorted order)
            assert trace.steps[1].input_outcome == "model_a(detected)"


class TestTranslationExecution:
    """Verify translation actually executes during composition."""

    def test_translation_applied_during_compose(self):
        """Translation rule is applied when outcome crosses model boundary."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        composer.register_translation(
            "detection",
            "threat_level",
            translate_detection_to_threat,
        )

        # Compose with signal=True (should be "detected")
        trace = composer.compose(["sensor", "classifier"], {"signal": True}, cycle=1)

        assert len(trace.steps) == 2
        assert trace.steps[0].output_outcome == "detected"
        # After translation: "detected" → "critical"
        assert trace.steps[1].input_outcome == "critical"
        # Classifier maps critical → category_a
        assert trace.steps[1].output_outcome == "category_a"

    def test_translation_with_signal_false(self):
        """Translation with false signal."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        composer.register_translation(
            "detection",
            "threat_level",
            translate_detection_to_threat,
        )

        trace = composer.compose(["sensor", "classifier"], {"signal": False}, cycle=1)

        assert trace.steps[0].output_outcome == "none"
        # After translation: "none" → "none"
        assert trace.steps[1].input_outcome == "none"
        # Classifier maps none → category_c
        assert trace.steps[1].output_outcome == "category_c"


class TestTranslationAbsence:
    """Verify behavior when translation is missing but needed."""

    def test_missing_translation_breaks_path_finding(self):
        """No edge created if translation doesn't exist."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        # DON'T register translation
        path = composer.find_composition_path("sensor", "classifier")
        assert path is None

    def test_missing_translation_passes_outcome_unchanged(self):
        """When translation missing, outcome passes through unchanged.

        This is graceful degradation: the adapter receives the untranslated
        outcome and must handle it. It may fail, or it may work depending on
        whether the adapter accepts the raw value.
        """
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        # Don't register translation, but force composition
        trace = composer.compose(["sensor", "classifier"], {"signal": True}, cycle=1)

        # Outcome passes through untranslated
        assert trace.steps[0].output_outcome == "detected"
        assert trace.steps[1].input_outcome == "detected"  # Not translated
        # ClassifierAdapter falls back to else clause (threat_level != "critical"/"moderate")
        assert trace.steps[1].output_outcome == "category_c"


class TestGraphConsistency:
    """Verify graph is built and maintained correctly."""

    def test_graph_initially_empty_for_incompatible_systems(self):
        """New adapters with incompatible models have no edge."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        # No edge should exist
        assert "classifier" not in composer.graph.get("sensor", set())

    def test_graph_edge_added_after_translation_registration(self):
        """Graph is updated when translation registered."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        # Before: no edge
        assert "classifier" not in composer.graph.get("sensor", set())

        # Register translation
        composer.register_translation(
            "detection",
            "threat_level",
            translate_detection_to_threat,
        )

        # After: edge exists
        assert "classifier" in composer.graph.get("sensor", set())

    def test_graph_bidirectional_not_implied(self):
        """Translation from A→B doesn't create B→A."""
        composer = UniversalComposer()
        composer.register_adapter(SensorAdapter())
        composer.register_adapter(ClassifierAdapter())

        composer.register_translation(
            "detection",
            "threat_level",
            translate_detection_to_threat,
        )

        # sensor→classifier should exist
        assert "classifier" in composer.graph.get("sensor", set())

        # But classifier→sensor should NOT
        assert "sensor" not in composer.graph.get("classifier", set())
