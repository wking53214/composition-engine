# Composition Engine

**Universal system orchestrator.** Compose any systems together without requiring a universal translator. Enable any system to declare its outcome model and participate in adaptive composition chains.

## Why Composition Engine?

**Problem**: Connecting 67+ heterogeneous systems with different outcome models requires either:
1. A universal translator that knows all systems' semantics (exponential complexity)
2. Manual routing and outcome mapping (maintenance nightmare)
3. A common language imposed on all systems (breaks existing ones)

**Solution**: Each system declares what it accepts and produces. Composer automatically:
- Builds compatibility graph from outcome model compatibility
- Routes outcomes through compatible chains via BFS
- Uses targeted translation rules only where models differ
- No universal translator needed—linear scaling to any number of systems

## Quick Start

### Universal (No Dependencies)

```python
from src.cns.core import UniversalComposer, SystemAdapter

# Define a system adapter
class MyAnalyzer(SystemAdapter):
    def __init__(self):
        super().__init__(
            system_name="my_analyzer",
            input_models={"code_artifact"},
            output_model="analysis_result",
        )
    
    def invoke(self, subject, input_outcome=None):
        return analyze(subject)

# Register and compose
composer = UniversalComposer()
composer.register_adapter(MyAnalyzer())

trace = composer.compose(["my_analyzer"], subject, cycle=1)
print(trace.timeline())
```

### With CNS Backend

```python
from src.cns.cns_backend import create_cns_composer
from src.cns.adapters_cns import register_cns_adapters, register_cns_translation_rules

# Create CNS-configured composer (with subject binding, canonicalization, convergence)
composer = create_cns_composer()
register_cns_adapters(composer)
register_cns_translation_rules(composer)

# Execute full 4-system circle
subject = {"repo": "innovation_os", "commit": "abc123"}
trace = composer.compose(
    ["swizzle", "ghost_tools", "wizzle", "innovation_os"],
    subject,
    cycle=1
)

print(f"Outcome: {trace.overall_outcome}")  # pass, retry, or terminal_breach
print(f"Converged: {trace.converged}")
```

## Architecture

### Core: UniversalComposer

System-agnostic foundation:
- Adapter registry (systems declare input/output models)
- Compatibility graph (auto-built from model compatibility)
- Path finding (BFS between any two systems)
- Composition execution (with optional subject binding, canonicalization, convergence detection)

```python
composer = UniversalComposer(
    subject_digest_fn=my_digest,          # Optional: hash subjects
    canonicalize_fn=my_canonicalize,      # Optional: normalize outcomes
    converge_fn=my_converge,              # Optional: detect convergence
)
```

### Backend: CNS

CNS-specific backend providing:
- Subject binding via sha256 digest (outcomes bind to specific content)
- Outcome canonicalization (any model → PASS/RETRY/TERMINAL_BREACH)
- Convergence detection (RETRY = still exploring)

```python
composer = create_cns_composer()  # Pre-configured with CNS semantics
```

### Adapters: Any Systems

Four reference implementations:
- **SwizzleAdapter**: Adversarial test framework (Verdict → BANISHED/ESCAPED/...)
- **GhostToolsAdapter**: Code scanner (Status → CONFIRMED/REASONED/...)
- **WizzleAdapter**: Forensics validator (Provenance → REMOVED_FROM_LIBRARY/...)
- **InnovationOSAdapter**: Decision system (Decision → APPROVED/REJECTED/...)

## Concepts

### SystemAdapter

Every system implements:

```python
class MySystemAdapter(SystemAdapter):
    system_name: str                    # "my_system"
    input_models: Set[str]              # {"model_a", "model_b"}
    output_model: str                   # "my_model"
    
    def invoke(self, subject, input_outcome=None) -> str:
        # Execute system, return outcome string
        pass
```

### Outcome Models

String identifiers for outcome semantics (no predefined values):

```python
# Define your model names
input_models = {"verdict", "severity"}
output_model = "decision"

# Define your outcomes
def invoke(self, subject, input_outcome=None):
    return "approved"   # your outcome
```

### Composition Path

Sequence of systems connected by compatible outcome models:

```python
# If system_a.output_model in system_b.input_models: compatible!
path = composer.find_composition_path("system_a", "system_b")
trace = composer.compose(path, subject, cycle=1)
```

### Translation Rules

Map between incompatible models:

```python
def translate_verdict_to_decision(verdict):
    return {"safe": "approved", "unsafe": "rejected"}[verdict]

composer.register_translation("verdict", "decision", translate_verdict_to_decision)
```

## Files

| Path | Purpose |
|------|---------|
| `src/cns/core.py` | Universal orchestrator (system-agnostic) |
| `src/cns/cns_backend.py` | CNS outcomes, subject binding, convergence |
| `src/cns/adapters_cns.py` | SWIZZLE, ghost_tools, WIZZLE, Innovation OS |
| `tests/test_library_composition.py` | 21 comprehensive tests |
| `docs/LIBRARY_COMPOSITION_GUIDE.md` | Complete guide (universality, scaling) |
| `docs/CREATING_CUSTOM_ADAPTERS.md` | How to create adapters for any system |

## Usage Patterns

### Single System

```python
composer.register_adapter(MyAdapter())
trace = composer.compose(["my_system"], subject, cycle=1)
```

### Two Systems

```python
composer.register_adapter(SystemA())
composer.register_adapter(SystemB())

# Automatic: finds that A→B is compatible
path = composer.find_composition_path("system_a", "system_b")
trace = composer.compose(path, subject, cycle=1)
```

### Multi-System with Translation

```python
composer.register_adapter(SystemA())  # output: "model_a"
composer.register_adapter(SystemB())  # input: {"model_b"}

# Register translation A → B
composer.register_translation("model_a", "model_b", translate_a_to_b)

# Now A→B is compatible
path = composer.find_composition_path("system_a", "system_b")
```

### Multi-Cycle with Alternative Routing

```python
for cycle in range(1, 6):
    trace = composer.compose(path, subject, cycle=cycle)
    
    if trace.converged:
        break
    
    # Try alternative path on RETRY
    alt_path = composer.find_composition_path(path[0], path[-1])
    if alt_path != path:
        path = alt_path
```

## Subject Binding

Every step includes cryptographic digest, preventing outcome reuse:

```python
trace = composer.compose(path, subject, cycle=1)

# All steps carry same subject_hash
assert trace.steps[0].subject_hash == trace.steps[1].subject_hash
```

## Convergence

Compositions converge when final outcome is deterministic:

```python
if trace.converged:
    print(f"Converged: {trace.overall_outcome}")
else:
    print("Still exploring; try alternative path")
```

## Testing

```bash
cd /home/user/composition-engine
python -m pytest tests/test_library_composition.py -v
```

All 21 tests passing:
- ✅ Adapter registration
- ✅ Compatibility graph building
- ✅ Path finding (BFS)
- ✅ Composition execution
- ✅ Subject binding
- ✅ Convergence detection
- ✅ Translation rules
- ✅ Fluent API

## Scaling to Any Number of Systems

1. Create adapters for each system (implement `SystemAdapter`)
2. Register adapters with composer
3. Define translation rules for incompatible model pairs
4. Execute compositions (automatic graph building + path finding)

Complexity:
- N adapters: O(N) lines of code
- Translation rules: O(N²) worst case, ~O(N) typical
- No universal translator needed

## Documentation

- **[LIBRARY_COMPOSITION_GUIDE.md](docs/LIBRARY_COMPOSITION_GUIDE.md)** - Architecture, concepts, usage, scaling to 67+ repos
- **[CREATING_CUSTOM_ADAPTERS.md](docs/CREATING_CUSTOM_ADAPTERS.md)** - How to build adapters for any system

## Key Insight

**No universal translator required.** Instead:
1. Each system declares its interface (input_models, output_model)
2. Composer builds graph from these declarations
3. Translation rules defined only at boundaries where models differ
4. Linear scaling to any number of systems

Result: **Composition-based governance** that scales to entire ecosystems without requiring semantic omniscience.

---

**Generated with Claude Code**  
https://claude.ai/code/session_011fXR86oBM3gwTschX3x8gw
