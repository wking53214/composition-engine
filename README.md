# composition-engine

Experimental **universal composer**: systems declare input/output outcome models; BFS routes compatible chains; translation rules only where models differ. Complementary research to the observe-perceive gate; **not a replacement** for the governed action chain.

## 1. Pipeline Position & Role

**EXPERIMENTAL ORCHESTRATION**, beside the gate, not in it. Does not admit, decide, conserve, execute, or custody.

## 2. Full System Scope & Architectural Depth

Real small engine (`src/composition_engine/core.py` ~330 lines):

- `SystemAdapter`: `system_name`, `input_models`, `output_model`, `invoke(subject, input_outcome) -> str`
- `UniversalComposer`: registry, compatibility graph, BFS `find_composition_path`, `compose()`
- `LibraryComposer` / `create_cns_composer()` wrap `CANONICAL_TABLE`
- CNS optional: `from cns.gate import GateOutcome, subject_digest, resolve` else local fallback (package renamed so it does not shadow `cns`)

**Only concrete adapter:** `GhostToolsAdapter`. `register_core_translation_rules` is `pass`. SWIZZLE/WIZZLE/Innovation OS named in comments — **no adapters**.

`CANONICAL_TABLE` polarity: CONFIRMED/CONFIRMED_BY_REVIEW → **TERMINAL_BREACH**; REJECTED/SUPPRESSED → PASS; REASONED → RETRY. Unrecognized → TERMINAL_BREACH.

`pyproject` `dependencies = []`. ~49 tests. CI exists. Python ≥ 3.11.

## 3. What It Does NOT Do / Non-Goals

Does not compose "67+ heterogeneous systems". Does not govern action or bind human authority. Does not replace CNS or observe-perceive.

## 4. Brutally Honest Current Status & Gaps

README scale claim is aspiration. Docs longer than the engine. CNS and ghost_tools are optional undeclared siblings; CI always hits fallbacks. Vocabulary miss → **warning on the trace, not raise**. Subject digest SHA-256 of `json.dumps(subject)` when CNS backend used. No `canonical_fields`.

## 5. Core Invariants & Guarantees

Unknown system / empty path → `ValueError`. Proven ghost_tools CONFIRMED is a breach in the canonical table (blocks), which is the adult part of the design.

## 6. Inputs, Outputs & Type Contracts

`GateOutcome`: `pass | retry | terminal_breach`. `GhostToolsStatus` / `Severity`. `CompositionStep{system_name, input_outcome, output_outcome, output_model, metadata, subject_hash}`.

## 7. Stack Integration Topology

```text
ghost_tools (opt adapter) → UniversalComposer → string outcomes
observe-perceive ✗ replacement
private CNS (opt)
```

**Safe to archive for live-path integrity**; keep only if you intend to grow adapters.

Apache-2.0.
