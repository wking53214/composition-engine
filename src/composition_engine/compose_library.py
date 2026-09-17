"""CNS-flavored composition orchestrator, typed on SystemModel.

Used to duplicate UniversalComposer's engine wholesale: its own adapter
registry, compatibility graph, BFS path-finding, translation-rule lookup and
compose() loop, hand-copied here the day before core.py's generic version
existed (commit a852214) and never migrated onto it once core.py did
(f9eedef, the same day). ghost_buster flagged the result as near-duplicate
functions (find_composition_path, _translate, CompositionBuilder's three
methods, and SystemAdapter.invoke's signature) without knowing why they
were there; the answer was an unmigrated refactor, not a second product
track -- README.md's two Quick Start examples both already route through
UniversalComposer (bare, or via create_cns_composer()), and neither
mentions LibraryComposer.

LibraryComposer now IS a UniversalComposer, configured with the CNS-specific
functions its constructor already accepts as hooks: CANONICAL_TABLE for
canonicalize_fn, subject_digest for subject_digest_fn, and a vocabulary
check for step_hook_fn -- the one thing UniversalComposer's engine didn't
already do generically. Everything mechanical is inherited, not
re-implemented.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .core import (
    CompositionBuilder,
    CompositionStep,
    CompositionTrace,
    SystemAdapter,
    UniversalComposer,
)
from .cns_integration import GateOutcome, subject_digest
from .outcomes import (
    CANONICAL_TABLE,
    SystemModel,
    is_declared,
    vocabulary_for,
)

__all__ = [
    "SystemModel",
    "SystemAdapter",
    "CompositionStep",
    "CompositionTrace",
    "CompositionBuilder",
    "CANONICAL_TABLE",
    "LibraryComposer",
]


class LibraryComposer(UniversalComposer):
    """UniversalComposer, pre-configured with this library's CNS semantics.

    - canonicalize_fn: CANONICAL_TABLE, shared with cns_backend.py's
      cns_canonicalize rather than hand-copied a second time.
    - converge_fn: RETRY means still exploring, same rule CANONICAL_TABLE's
      outcomes already encode.
    - step_hook_fn: flags an outcome that isn't in its own model's declared
      vocabulary. None (not False) when the model declares no vocabulary at
      all -- CNS_GATE_OUTCOME is canonical and owned by GateOutcome, and
      "nothing declared this" is a different statement from "this is not
      declared". Recorded rather than raised: a composition that reached a
      wrong-vocabulary outcome still has a trace worth reading, and an
      exception here would destroy the step that produced it along with
      every step before it.
    """

    def __init__(self) -> None:
        super().__init__(
            subject_digest_fn=subject_digest,
            canonicalize_fn=self._canonicalize,
            converge_fn=self._check_convergence,
            step_hook_fn=self._vocabulary_hook,
        )

    @staticmethod
    def _vocabulary_hook(adapter: SystemAdapter, outcome: Any) -> Dict[str, Any]:
        model = adapter.output_model
        if not vocabulary_for(model):
            return {"outcome_declared": None}
        declared = is_declared(model, outcome)
        metadata: Dict[str, Any] = {"outcome_declared": declared}
        if not declared:
            metadata["warning"] = "not in this system's declared vocabulary"
        return metadata

    @staticmethod
    def _canonicalize(final_step: CompositionStep) -> GateOutcome:
        """Convert final outcome to canonical GateOutcome, via CANONICAL_TABLE."""
        outcome = final_step.output_outcome or "unknown"
        model = final_step.output_model

        mapping, default = CANONICAL_TABLE.get(
            model, ({}, GateOutcome.TERMINAL_BREACH)
        )
        return mapping.get(outcome, default)

    def _check_convergence(self, steps) -> bool:
        """Did composition converge to a decision?"""
        if len(steps) < 2:
            return True
        # Convergence: final outcome is PASS or TERMINAL_BREACH (not RETRY)
        final = self._canonicalize(steps[-1])
        return final != GateOutcome.RETRY
