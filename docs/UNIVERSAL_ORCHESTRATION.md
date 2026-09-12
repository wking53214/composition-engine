# Universal Orchestration Architecture

## The Problem: Connecting N Heterogeneous Systems

You have N systems (67+), each with:
- Different outcome models (verdicts, statuses, decisions, findings)
- Different semantics (what "pass" means differs per system)
- Different composition needs (some systems compose, some run independently)

**Previous approaches:**

1. **Universal Translator** (HERALD-style)
   - Knows semantics of all N systems
   - Translates between all O(N²) model pairs
   - Complexity: O(N²) code, exponential mental load
   - Problem: Brittles as N grows; new systems require updating translator

2. **Hardcoded Pipelines**
   - System A → B → C → D
   - Routes hardcoded in orchestrator
   - Complexity: O(N) code but inflexible
   - Problem: Can't adapt routing; can't reuse systems in different contexts

3. **Imposing Common Language**
   - Force all systems to use same outcome model
   - Complexity: O(N) system modifications
   - Problem: Breaks existing systems; loses semantic richness

## The Composition Engine Solution: Pluggable Adapters + Graph Routing

**Architecture:**
```
┌────────────────────────────────────────────┐
│ UniversalComposer (system-agnostic)        │
├────────────────────────────────────────────┤
│                                             │
│ Adapter Registry    Compatibility Graph    │
│ ─────────────────   ─────────────────────  │
│ System A (→model_a) A→C (model_a→input_c) │
│ System B (→model_b) A→B (translated)      │
│ System C (→model_c) B→D (model_b→input_d) │
│ System D (→model_d) ...                    │
│                                             │
│ Translation Rules Registry                 │
│ ──────────────────────────────────────────│
│ (model_a, model_b) → translate_a_to_b()  │
│ (model_a, model_c) → translate_a_to_c()  │
│                                             │
└────────────────────────────────────────────┘
```

**Advantages:**
- ✅ Each system declares only its own interface (O(N) code)
- ✅ Translation rules only where needed (O(N) typical, O(N²) worst case)
- ✅ Automatic graph building (no hardcoding routes)
- ✅ Pluggable backends (CNS, custom semantics)
- ✅ No system modifications required
- ✅ Linear scaling to any N

## System Interface

Every system implements one interface:

```python
class SystemAdapter(ABC):
    system_name: str              # "my_system"
    input_models: Set[str]        # what models I accept
    output_model: str             # what model I produce
    
    def invoke(subject, input_outcome=None) -> str:
        # Execute system, return outcome
        pass
```

**That's it.** No semantics encoded in orchestrator.

## Outcome Models (Not Values)

Models are just **strings naming semantic categories**:

```python
# SWIZZLE system
output_model = "swizzle_verdict"
# Produces: "banished", "escaped", "misnamed", ...

# ghost_tools system
output_model = "ghost_tools_status"
# Produces: "confirmed", "reasoned", "rejected", ...

# Innovation OS system
output_model = "innovation_os_decision"
# Produces: "approved", "rejected", "branched", ...
```

Models don't constrain values—each system produces whatever outcomes make sense:

```python
def invoke(self, subject, input_outcome=None):
    result = analyze(subject)
    
    if result.is_safe:
        return "safe"           # YOUR outcome value
    else:
        return "unsafe"         # YOUR outcome value
```

## Automatic Graph Building

Composer observes which systems are compatible:

```python
# System A produces "model_x"
# System B accepts {"model_x", "model_y"}
# → Composer adds edge A→B (compatible!)

# System C produces "model_z"
# System D accepts {"model_x"}
# → Composer does NOT add edge C→D (incompatible)

# Path finding via BFS:
path = composer.find_composition_path("A", "B")  # → ["A", "B"]
```

**No hardcoding. No manual routing. Automatic discovery.**

## Translation Rules (On Demand)

Define only where boundaries need bridging:

```python
# System A produces "risk_score" (numeric: 0-100)
# System B accepts {"severity"} (enum: low/medium/high)

def translate_risk_to_severity(risk_score):
    score = int(risk_score)
    return "low" if score < 33 else "medium" if score < 67 else "high"

composer.register_translation(
    "risk_score",
    "severity",
    translate_risk_to_severity,
)

# Now A→B is compatible (via translation)
```

**Cost:** O(1) per translation rule + O(N) typical rules in library.

## Pluggable Backends

Core orchestrator is domain-agnostic. Backends provide:

### CNS Backend (Default)

```python
composer = create_cns_composer()  # Pre-configured

# Provides:
# - Subject binding: sha256 hash prevents verdict reuse
# - Canonicalization: Any model → PASS/RETRY/TERMINAL_BREACH
# - Convergence: RETRY = still exploring
```

### Custom Backend (Example)

```python
def my_digest(subject):
    return hash(subject)

def my_canonicalize(step):
    if step.output_model == "my_model":
        return {...}
    return step.output_outcome

def my_converge(steps):
    final = steps[-1].output_outcome
    return final != "exploring"

composer = UniversalComposer(
    subject_digest_fn=my_digest,
    canonicalize_fn=my_canonicalize,
    converge_fn=my_converge,
)
```

**Flexibility without complexity.**

## Scaling to 67+ Systems

### Phase 1: Adapter Creation (O(N))

```python
class Repo1Adapter(SystemAdapter):
    def __init__(self):
        super().__init__(
            system_name="repo_1",
            input_models={"model_a", "model_b"},
            output_model="repo_1_outcome",
        )
    
    def invoke(self, subject, input_outcome=None):
        return invoke_repo_1(subject, input_outcome)

# Repeat for all 67 repos
```

**Effort:** ~10-20 lines per adapter × 67 = ~700 lines total (if all different)

### Phase 2: Registration (O(1))

```python
composer = create_cns_composer()

# Register all adapters
for adapter in [Repo1Adapter(), Repo2Adapter(), ..., Repo67Adapter()]:
    composer.register_adapter(adapter)

# Composer auto-builds compatibility graph
```

### Phase 3: Translation Rules (O(N))

```python
# For each incompatible boundary, define translation rule
translation_rules = [
    ("repo_1_outcome", "repo_2_outcome", translate_1_to_2),
    ("repo_2_outcome", "repo_3_outcome", translate_2_to_3),
    # ... ~30-50 rules depending on outcome model diversity
]

for from_model, to_model, rule in translation_rules:
    composer.register_translation(from_model, to_model, rule)
```

**Estimate:** ~30-50 rules (most outcome models compatible or adjacent)

### Phase 4: Orchestration (O(log N))

```python
# Find path via BFS
path = composer.find_composition_path("repo_x", "repo_y")

# Execute composition
for cycle in range(1, 6):
    trace = composer.compose(path, subject, cycle=cycle)
    
    if trace.converged:
        print(f"Success in {cycle} cycles")
        break
    
    # Try alternative path on RETRY
    alt_path = composer.find_composition_path(path[0], path[-1])
    if alt_path != path:
        path = alt_path
```

## Comparison: Universal Translator vs Composition Engine

| Aspect | Universal Translator | Composition Engine |
|--------|----------------------|-------------------|
| **Translator Knowledge** | O(N²) mappings (all pairs) | O(N) rules (only boundaries) |
| **System Code** | O(N) (force common model) | O(N) (declare interface) |
| **Orchestrator Code** | O(N²) switch statements | O(N) (BFS graph) |
| **New System Added** | Update translator (scary) | Add adapter + register (safe) |
| **Mental Model** | Translator knows everything | Each system knows itself |
| **Scaling** | Exponential complexity | Linear complexity |

**Key Insight:** Composition Engine doesn't scale to N² complexity because it doesn't need to know all systems' semantics. Each system declares its own interface; orchestrator just routes based on compatibility.

## No Universal Semantics Needed

Traditional approaches fail because they try to encode universal semantics:

> "What does PASS mean across all systems?"
> 
> - SWIZZLE: "Test found no defects"
> - ghost_tools: "Scanner confirmed safe"
> - Innovation OS: "Approved for deployment"
> 
> Different systems, different meanings, same label.

**Composition Engine sidesteps this:**

1. Each system uses its native semantics (Verdict, Status, Decision)
2. Composer doesn't care what they mean
3. Translation rules encode meaning at specific boundaries only
4. Backends (like CNS) provide canonicalization if needed

**Result:** No universal semantics imposed. Diversity preserved. Composition still possible.

## Subject Binding Prevents Verdict Reuse

Every step includes subject hash:

```python
trace = composer.compose(path, subject, cycle=1)

# All steps carry same subject_hash
for step in trace.steps:
    assert step.subject_hash == sha256(subject)

# Different subject → different hash
trace2 = composer.compose(path, subject2, cycle=1)
assert trace.steps[0].subject_hash != trace2.steps[0].subject_hash
```

**Property:** Outcomes bind to content they judge. Can't forge or transfer verdicts.

## Convergence Enables Adaptive Routing

Composition traces report whether they converged:

```python
if trace.converged:
    # Final outcome deterministic (PASS or TERMINAL_BREACH)
    # All systems agree; stop
    return trace.overall_outcome
else:
    # Final outcome uncertain (RETRY)
    # Systems still exploring; try alternative path
    alt_path = find_alternative_path(path)
    trace = composer.compose(alt_path, subject, cycle+1)
```

**Enables:** Automatic multi-cycle loops with intelligent routing.

## Extensibility

### Add a New System

```python
# 1. Implement adapter
class NewSystemAdapter(SystemAdapter):
    # Define input/output models
    # Implement invoke()

# 2. Register
composer.register_adapter(NewSystemAdapter())

# 3. Define translations (if needed)
for from_model, to_model, rule in new_translations:
    composer.register_translation(from_model, to_model, rule)

# 4. Done! Graph auto-rebuilt; new system discoverable
```

### Add a New Backend

```python
# 1. Define functions
def my_digest(subject):
    pass

def my_canonicalize(step):
    pass

def my_converge(steps):
    pass

# 2. Create composer
composer = UniversalComposer(
    subject_digest_fn=my_digest,
    canonicalize_fn=my_canonicalize,
    converge_fn=my_converge,
)

# 3. Use it!
```

## Use Cases

### Governance Stack (CNS)

```python
# 67 systems → 1 unified governance interface
# No universal translator needed
# Each system maintains independence
# Composition enables collective intelligence
```

### Security Analysis Pipeline

```
Code → Scanner → Analyzer → Reporter → Dashboard
```

### Compliance Verification

```
Audit → Checker → Validator → Decision
```

### Research Workflows

```
Experiment A → Synthesizer → Experiment B → Analyzer
```

## Summary

**Composition Engine enables universal orchestration without requiring:**
- Universal translator (expensive O(N²) complexity)
- Imposing common language (breaks existing systems)
- Hardcoding routes (inflexible)
- Semantic omniscience (impossible to maintain)

**Instead, it provides:**
- Plugin interface (each system declares its interface)
- Automatic discovery (compatible systems found via graph)
- Targeted translation (only where boundaries differ)
- Linear complexity (O(N) adapters + O(N) rules)
- Extensible backends (CNS, custom semantics)

**Result:** Composition-based governance that scales to any ecosystem while preserving system independence and semantic diversity.
