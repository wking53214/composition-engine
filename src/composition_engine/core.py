"""Universal composition orchestrator core.

System-agnostic foundation for composing any systems with pluggable
outcome models, canonicalization, and subject binding.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class SystemAdapter(ABC):
    """Base adapter for any system.

    Each system declares what outcome models it accepts and produces,
    implementing the invoke() interface for execution.
    """

    system_name: str
    input_models: Set[str]  # outcome model names this system accepts
    output_model: str  # outcome model name this system produces

    @abstractmethod
    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Execute this system and return outcome as string.

        Args:
            subject: What we're analyzing/judging/processing
            input_outcome: Previous system's outcome (if chained)

        Returns:
            Outcome string in this system's native format
        """
        pass


@dataclass(frozen=True)
class CompositionStep:
    """One system's execution in a composition."""

    system_name: str
    input_outcome: Optional[str] = None
    output_outcome: Optional[str] = None
    output_model: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    subject_hash: Optional[str] = None


def _plain(x: Any) -> Any:
    """The value a possibly-Enum outcome stands for, without importing Enum.

    core.py has no CNS/domain dependency and never will, so it can't import
    outcomes.py's `outcome_value` (same str-Enum trap: `str()` on a str-Enum
    member prints "ClassName.MEMBER", not the value). Duck-typed on
    `.value` instead, which every stdlib Enum has and a plain string does
    not -- generic Python, not domain knowledge.
    """
    return getattr(x, "value", x)


@dataclass(frozen=True)
class CompositionTrace:
    """Full execution trace through systems."""

    steps: List[CompositionStep]
    overall_outcome: Optional[Any]
    composition_path: List[str]
    cycle: int = 1
    converged: bool = False

    def timeline(self) -> str:
        """Human-readable timeline."""
        lines = [f"Cycle {self.cycle}: {' → '.join(self.composition_path)}"]
        for i, step in enumerate(self.steps, 1):
            inp = f" ← {_plain(step.input_outcome)}" if step.input_outcome else ""
            out = f" → {_plain(step.output_outcome)}" if step.output_outcome else ""
            # A generic warning slot, not a vocabulary check -- core.py
            # doesn't know what a vocabulary is. A composer flavor that does
            # (LibraryComposer, via its step_hook_fn) sets step.metadata
            # ["warning"] and it surfaces here; core.py just prints it if
            # present, same as it prints any other step.
            warning = step.metadata.get("warning")
            flag = f"  [!] {warning}" if warning else ""
            lines.append(f"  {i}. {step.system_name}{inp}{out}{flag}")
        if self.overall_outcome:
            lines.append(f"  Final: {_plain(self.overall_outcome)}")
        lines.append(f"  Converged: {self.converged}")
        return "\n".join(lines)


class UniversalComposer:
    """Generic orchestration engine for any systems.

    - Discovers systems via adapter registry (system-agnostic)
    - Builds compatibility graphs from outcome model compatibility
    - Routes outcomes through compatible chains via BFS
    - Uses targeted translation rules at model boundaries
    - Supports pluggable subject binding and canonicalization
    """

    def __init__(
        self,
        subject_digest_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
        canonicalize_fn: Optional[Callable[[CompositionStep], str]] = None,
        converge_fn: Optional[Callable[[List[CompositionStep]], bool]] = None,
        step_hook_fn: Optional[Callable[[SystemAdapter, Any], Dict[str, Any]]] = None,
    ):
        """Initialize composer with optional customization functions.

        Args:
            subject_digest_fn: Function to hash subjects. Default: None (no binding)
            canonicalize_fn: Function to convert final step to canonical outcome.
                Default: None (use final step outcome as-is)
            converge_fn: Function to check if composition converged.
                Default: None (always converged)
            step_hook_fn: Called with (adapter, outcome) right after each
                adapter is invoked, before its CompositionStep is built.
                Returns a metadata dict merged into that step. Default: None
                (no extra metadata). core.py never calls this for anything
                domain-specific -- it exists so a composer flavor built on
                top of UniversalComposer (see compose_library.LibraryComposer)
                can attach its own per-step checks (a vocabulary check, say)
                without UniversalComposer knowing what one is. The one thing
                it's contracted to produce, if anything: a "warning" key
                whose value CompositionTrace.timeline() will print.
        """
        self.adapters: Dict[str, SystemAdapter] = {}
        self.translation_rules: Dict[Tuple[str, str], Callable[[str], str]] = {}

        self.subject_digest_fn = subject_digest_fn or (lambda s: None)
        self.canonicalize_fn = canonicalize_fn or (lambda step: step.output_outcome)
        self.converge_fn = converge_fn or (lambda steps: True)
        self.step_hook_fn = step_hook_fn

        self.graph: Dict[str, Set[str]] = {}

    def register_adapter(self, adapter: SystemAdapter) -> None:
        """Register a system adapter."""
        self.adapters[adapter.system_name] = adapter
        self._build_compatibility_graph()

    def register_translation(
        self,
        from_model: str,
        to_model: str,
        rule: Callable[[str], str],
    ) -> None:
        """Register translation rule between outcome models."""
        self.translation_rules[(from_model, to_model)] = rule

    def _build_compatibility_graph(self) -> None:
        """Build graph of which systems can feed into which."""
        self.graph = {name: set() for name in self.adapters.keys()}

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
        """Find shortest composition path between systems via BFS.

        Args:
            start_system: Starting system name
            end_system: Target system name
            max_depth: Maximum path length

        Returns:
            List of system names in order, or None if no path exists
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
            subject: What we're analyzing
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
        subject_hash = self.subject_digest_fn(subject)
        previous_outcome = None

        for system_name in composition_path:
            adapter = self.adapters[system_name]

            # Translate the INCOMING outcome into a model this adapter accepts,
            # before invoking it. Non-destructive and deterministic: input_models
            # is a standing declaration, and set order is not stable.
            incoming = previous_outcome
            if incoming is not None and steps:
                from_model = steps[-1].output_model
                if from_model not in adapter.input_models:
                    for to_model in sorted(adapter.input_models, key=str):
                        rule = self.translation_rules.get((from_model, to_model))
                        if rule:
                            incoming = rule(incoming)
                            break

            # Invoke system
            outcome = adapter.invoke(subject, input_outcome=incoming)

            extra_metadata = self.step_hook_fn(adapter, outcome) if self.step_hook_fn else {}

            step = CompositionStep(
                system_name=system_name,
                input_outcome=incoming,
                output_outcome=outcome,
                output_model=adapter.output_model,
                subject_hash=subject_hash,
                metadata=extra_metadata,
            )
            steps.append(step)
            previous_outcome = outcome

        # Canonicalize final outcome
        final_outcome = self.canonicalize_fn(steps[-1]) if steps else None
        converged = self.converge_fn(steps)

        return CompositionTrace(
            steps=steps,
            overall_outcome=final_outcome,
            composition_path=composition_path,
            cycle=cycle,
            converged=converged,
        )

    def _translate(
        self,
        outcome: str,
        from_model: str,
        to_model: str,
    ) -> str:
        """Translate outcome between models using registered rules."""
        rule = self.translation_rules.get((from_model, to_model))
        if rule:
            return rule(outcome)
        return outcome


class CompositionBuilder:
    """Fluent API for building complex compositions."""

    def __init__(self, composer: UniversalComposer):
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
