"""Generic composition orchestrator for entire library.

Discovers systems across 67 repos, builds composition graphs,
and routes outcomes through compatible chains without universal translation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from abc import ABC, abstractmethod

from .cns_integration import GateOutcome, subject_digest
from .outcomes import (
    GhostToolsSeverity,
    GhostToolsStatus,
    InnovationOSDecision,
    SwizzleVerdict,
    WizzleForensics,
    is_declared,
    outcome_value,
    vocabulary_for,
)


class SystemModel(str, Enum):
    """Outcome model signatures across library."""
    SWIZZLE_VERDICT = "swizzle_verdict"  # BANISHED/ESCAPED/MISNAMED/CONJURED/DISMISSED/UNSUMMONED
    GHOST_TOOLS_STATUS = "ghost_tools_status"  # CONFIRMED/REASONED/CONFIRMED_BY_REVIEW/REJECTED/SUPPRESSED
    GHOST_TOOLS_SEVERITY = "ghost_tools_severity"  # CRITICAL/MAJOR/MINOR/INFORMATIONAL
    WIZZLE_FORENSICS = "wizzle_forensics"  # REMOVED_FROM_LIBRARY/RELOCATED_TO_TESTS/REGRESSION/UNKNOWN
    INNOVATION_OS_DECISION = "innovation_os_decision"  # PROPOSED/EVALUATED/APPROVED/REJECTED/BRANCHED
    CNS_GATE_OUTCOME = "cns_gate_outcome"  # PASS/RETRY/TERMINAL_BREACH (canonical)


@dataclass
class SystemAdapter(ABC):
    """Base adapter for any system in the library.

    Each repo that wants to participate in composition provides an adapter
    that declares its input/output models and execution interface.
    """

    system_name: str
    input_models: Set[SystemModel]  # what this system accepts
    output_model: SystemModel  # what this system produces

    @abstractmethod
    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Execute this system and return outcome as string.

        Args:
            subject: What we're judging
            input_outcome: Previous system's outcome (if this is not first in chain)

        Returns:
            Outcome string in this system's native format
        """
        pass


@dataclass
class CompositionLink:
    """One edge in composition graph: system A outputs to system B."""

    from_system: str
    to_system: str
    translation_rule: Optional[Callable[[str], str]] = None  # None = direct passthrough


@dataclass(frozen=True)
class CompositionStep:
    """One system's execution in the composition."""

    system_name: str
    input_outcome: Optional[str] = None
    output_outcome: Optional[str] = None
    output_model: SystemModel = SystemModel.CNS_GATE_OUTCOME
    metadata: Dict[str, Any] = field(default_factory=dict)
    subject_hash: Optional[str] = None


@dataclass(frozen=True)
class CompositionTrace:
    """Full execution trace through library systems."""

    steps: List[CompositionStep]
    overall_outcome: GateOutcome
    composition_path: List[str]  # system names in order
    cycle: int = 1
    converged: bool = False

    def timeline(self) -> str:
        """Human-readable timeline."""
        lines = [f"Cycle {self.cycle}: {' → '.join(self.composition_path)}"]
        for i, step in enumerate(self.steps, 1):
            # outcome_value, not the bare member: f-string formatting of a
            # str-Enum prints "SwizzleVerdict.ESCAPED" where this timeline has
            # always printed "escaped". Nothing asserts on this text, so the
            # change would have shipped silently.
            inp = f" ← {outcome_value(step.input_outcome)}" if step.input_outcome else ""
            out = f" → {outcome_value(step.output_outcome)}" if step.output_outcome else ""
            # Marked in the timeline rather than only in metadata, because a
            # flag nobody prints is indistinguishable from a check nobody ran.
            flag = (
                "  [!] not in this system's declared vocabulary"
                if step.metadata.get("outcome_declared") is False
                else ""
            )
            lines.append(f"  {i}. {step.system_name}{inp}{out}{flag}")
        lines.append(f"  Final: {self.overall_outcome.value}")
        return "\n".join(lines)


# How each system's words become the canonical gate outcome.
#
# This was four near-identical branch cascades inside `_canonicalize`, one per
# outcome model, each mapping a handful of values and falling through to a
# default. ghost_buster read it as one statement repeated four times in one
# function (ghost-0f0192120c82, MAJOR) and it was right: the branches were the
# same operation written out once per model, which is what a table is for.
#
# Each entry is (mapping, default). The default is the outcome for a value the
# mapping does not list, and it is NOT uniform: an unrecognised canonical
# outcome is a TERMINAL_BREACH, because a gate that cannot read its own
# vocabulary has failed rather than merely not-yet-decided, while every other
# model treats an unlisted value as RETRY. That asymmetry was already in the
# cascade, as CNS_GATE_OUTCOME's silent fall-through past the end of its own
# branch to the function's final return, where it read as an oversight. It is
# preserved here deliberately and written down.
CANONICAL_TABLE: Dict[SystemModel, Tuple[Dict[str, GateOutcome], GateOutcome]] = {
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
            SwizzleVerdict.BANISHED: GateOutcome.PASS,
            SwizzleVerdict.DISMISSED: GateOutcome.PASS,
            SwizzleVerdict.ESCAPED: GateOutcome.TERMINAL_BREACH,
            SwizzleVerdict.CONJURED: GateOutcome.TERMINAL_BREACH,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.GHOST_TOOLS_STATUS: (
        {
            GhostToolsStatus.CONFIRMED: GateOutcome.PASS,
            GhostToolsStatus.REASONED: GateOutcome.TERMINAL_BREACH,
            GhostToolsStatus.REJECTED: GateOutcome.TERMINAL_BREACH,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.GHOST_TOOLS_SEVERITY: (
        {
            GhostToolsSeverity.CRITICAL: GateOutcome.TERMINAL_BREACH,
            GhostToolsSeverity.MAJOR: GateOutcome.TERMINAL_BREACH,
            GhostToolsSeverity.MINOR: GateOutcome.PASS,
            GhostToolsSeverity.INFORMATIONAL: GateOutcome.PASS,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.WIZZLE_FORENSICS: (
        {
            WizzleForensics.RELOCATED_TO_TESTS: GateOutcome.PASS,
            WizzleForensics.INTENTIONAL_REMOVAL: GateOutcome.PASS,
            WizzleForensics.REMOVED_FROM_LIBRARY: GateOutcome.TERMINAL_BREACH,
            WizzleForensics.REGRESSION: GateOutcome.TERMINAL_BREACH,
        },
        GateOutcome.RETRY,
    ),
    SystemModel.INNOVATION_OS_DECISION: (
        {
            InnovationOSDecision.APPROVED: GateOutcome.PASS,
            InnovationOSDecision.REJECTED: GateOutcome.TERMINAL_BREACH,
        },
        GateOutcome.RETRY,
    ),
}


class LibraryComposer:
    """Orchestrates composition across entire library.

    - Discovers systems and their outcome models
    - Builds compatibility graphs
    - Routes outcomes through compatible chains
    - Translates only where models differ
    """

    def __init__(self):
        self.adapters: Dict[str, SystemAdapter] = {}
        self.translation_rules: Dict[Tuple[SystemModel, SystemModel], Callable[[str], str]] = {}
        self._build_compatibility_graph()

    def register_adapter(self, adapter: SystemAdapter) -> None:
        """Register a system adapter from the library."""
        self.adapters[adapter.system_name] = adapter
        self._build_compatibility_graph()  # Rebuild graph after each registration

    def register_translation(
        self,
        from_model: SystemModel,
        to_model: SystemModel,
        rule: Callable[[str], str],
    ) -> None:
        """Register translation rule between two outcome models."""
        self.translation_rules[(from_model, to_model)] = rule

    def _build_compatibility_graph(self) -> None:
        """Build graph of which systems can feed into which."""
        self.graph: Dict[str, Set[str]] = {
            name: set() for name in self.adapters.keys()
        }

        for from_name, from_adapter in self.adapters.items():
            for to_name, to_adapter in self.adapters.items():
                if from_name == to_name:
                    continue
                # Can from_adapter → to_adapter?
                if from_adapter.output_model in to_adapter.input_models:
                    self.graph[from_name].add(to_name)

    def find_composition_path(
        self,
        start_system: str,
        end_system: str,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        """Find shortest composition path from start to end system.

        Returns list of system names in order, or None if no path exists.
        """
        if start_system not in self.adapters or end_system not in self.adapters:
            return None

        visited = {start_system}
        queue = [(start_system, [start_system])]

        while queue:
            current, path = queue.pop(0)
            if current == end_system:
                return path
            if len(path) >= max_depth:
                continue

            for neighbor in self.graph.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def compose(
        self,
        composition_path: List[str],
        subject: Dict[str, Any],
        cycle: int = 1,
    ) -> CompositionTrace:
        """Execute composition along specified path.

        Args:
            composition_path: List of system names to chain
            subject: What we're judging
            cycle: Which cycle this is

        Returns:
            Full trace of execution
        """
        if not composition_path:
            raise ValueError("Empty composition path")

        for system_name in composition_path:
            if system_name not in self.adapters:
                raise ValueError(f"Unknown system: {system_name}")

        steps: List[CompositionStep] = []
        subject_hash = subject_digest(subject)
        previous_outcome = None

        for system_name in composition_path:
            adapter = self.adapters[system_name]

            # Translate the INCOMING outcome into a model this adapter accepts,
            # before invoking it. Selection is non-destructive and deterministic:
            # adapter.input_models is the adapter's standing declaration and must
            # not be consumed, and a set's iteration order is not stable.
            incoming = previous_outcome
            if incoming is not None and steps:
                from_model = steps[-1].output_model
                if from_model not in adapter.input_models:
                    for to_model in sorted(adapter.input_models, key=str):
                        if (from_model, to_model) in self.translation_rules:
                            incoming = self._translate(incoming, from_model, to_model)
                            break

            # Invoke system
            outcome = adapter.invoke(subject, input_outcome=incoming)

            declared = self._check_vocabulary(adapter.output_model, outcome)

            step = CompositionStep(
                system_name=system_name,
                input_outcome=incoming,
                output_outcome=outcome,
                output_model=adapter.output_model,
                subject_hash=subject_hash,
                metadata={"outcome_declared": declared},
            )
            steps.append(step)
            previous_outcome = outcome

        # Canonicalize final outcome
        final_outcome = self._canonicalize(steps[-1])
        converged = self._check_convergence(steps)

        return CompositionTrace(
            steps=steps,
            overall_outcome=final_outcome,
            composition_path=composition_path,
            cycle=cycle,
            converged=converged,
        )

    @staticmethod
    def _check_vocabulary(model: SystemModel, outcome: str) -> Optional[bool]:
        """Is this outcome one of the words its system declared?

        None, not False, when the model has no vocabulary to check against:
        CNS_GATE_OUTCOME is canonical and owned by GateOutcome, and "nothing
        declared this" is a different statement from "this is not declared".

        Recorded rather than raised. A composition that reached a
        wrong-vocabulary outcome still has a trace worth reading, and an
        exception here would destroy the step that produced it along with
        every step before it.
        """
        if not vocabulary_for(model):
            return None
        return is_declared(model, outcome)

    def _translate(
        self,
        outcome: str,
        from_model: SystemModel,
        to_model: SystemModel,
    ) -> str:
        """Translate outcome between models using registered rules."""
        rule = self.translation_rules.get((from_model, to_model))
        if rule:
            return rule(outcome)
        # Fallback: no translation registered
        return outcome

    def _canonicalize(self, final_step: CompositionStep) -> GateOutcome:
        """Convert final outcome to canonical GateOutcome."""
        outcome = final_step.output_outcome or "unknown"
        model = final_step.output_model

        mapping, default = CANONICAL_TABLE.get(
            model, ({}, GateOutcome.TERMINAL_BREACH)
        )
        return mapping.get(outcome, default)

    def _check_convergence(self, steps: List[CompositionStep]) -> bool:
        """Did composition converge to a decision?"""
        if len(steps) < 2:
            return True
        # Convergence: final outcome is PASS or TERMINAL_BREACH (not RETRY)
        final = self._canonicalize(steps[-1])
        return final != GateOutcome.RETRY


class CompositionBuilder:
    """Fluent API for building complex compositions."""

    def __init__(self, composer: LibraryComposer):
        self.composer = composer
        self.path: List[str] = []

    def add_system(self, system_name: str) -> CompositionBuilder:
        """Add system to composition path."""
        if system_name in self.composer.adapters:
            self.path.append(system_name)
        else:
            raise ValueError(f"System not registered: {system_name}")
        return self

    def build(self) -> List[str]:
        """Return the composition path."""
        return self.path

    def execute(
        self,
        subject: Dict[str, Any],
        cycle: int = 1,
    ) -> CompositionTrace:
        """Execute the composition."""
        return self.composer.compose(self.path, subject, cycle)
