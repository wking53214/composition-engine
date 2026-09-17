# Creating Custom Adapters

The UniversalComposer enables any system to participate in composition chains by implementing a `SystemAdapter`.

## Quick Start

### 1. Define Your Adapter

```python
from cns.core import SystemAdapter

class MySystemAdapter(SystemAdapter):
    def __init__(self):
        super().__init__(
            system_name="my_system",
            input_models={"model_a", "model_b"},  # what this accepts
            output_model="my_output_model",        # what this produces
        )
    
    def invoke(self, subject, input_outcome=None):
        # Execute your system
        result = my_system_logic(subject, input_outcome)
        return result  # Return outcome string
```

### 2. Register With Composer

```python
from cns.core import UniversalComposer

composer = UniversalComposer()
composer.register_adapter(MySystemAdapter())
```

### 3. Define Translation Rules (If Needed)

If your system's output model differs from systems you want to chain with:

```python
def translate_my_model_to_other(outcome: str) -> str:
    # Map your outcomes to compatible model
    mapping = {
        "my_outcome_a": "compatible_outcome_1",
        "my_outcome_b": "compatible_outcome_2",
    }
    return mapping.get(outcome, "unknown")

composer.register_translation(
    "my_output_model",
    "other_input_model",
    translate_my_model_to_other,
)
```

### 4. Compose and Execute

```python
subject = {"code": "...", "context": {...}}
path = ["my_system", "other_system"]
trace = composer.compose(path, subject, cycle=1)

print(trace.timeline())
```

## Architecture

### SystemAdapter Interface

Every adapter declares:

| Field | Purpose | Example |
|-------|---------|---------|
| `system_name` | Unique ID for routing | `"my_analyzer"` |
| `input_models` | Set of outcome models it accepts | `{"verdict", "finding"}` |
| `output_model` | Single outcome model it produces | `"decision"` |
| `invoke(subject, input_outcome)` | Execution method | Returns outcome string |

### Outcome Models

Models are just strings representing the semantics of outcomes:

```python
# Define your model names
input_models = {
    "security_verdict",     # boolean: safe/unsafe
    "compliance_status",    # enum: pass/warn/fail
}
output_model = "risk_score" # numeric: 0-100
```

Models don't have predefined values—you define the outcomes your system produces:

```python
def invoke(self, subject, input_outcome=None):
    if self.analyze(subject):
        return "high_risk"      # your outcome value
    else:
        return "low_risk"       # your outcome value
```

### Composition Path Finding

Systems are automatically connected if output models match input models:

```python
# Composer builds graph showing what can feed into what:
# system_a (produces "verdict")
#   ↓
# system_b (accepts "verdict") → compatible!

# Compatible chains are automatically discoverable:
path = composer.find_composition_path("system_a", "system_b")
# → ["system_a", "system_b"]
```

### Translation Rules

When systems have incompatible models, define translation rules:

```python
# system_a produces "risk_score" (numeric: 0-100)
# system_b accepts "severity" (enum: low/medium/high)

def translate_risk_to_severity(risk_score: str) -> str:
    score = int(risk_score)
    if score < 33:
        return "low"
    elif score < 67:
        return "medium"
    else:
        return "high"

composer.register_translation(
    "risk_score",
    "severity",
    translate_risk_to_severity,
)
```

## Customization

### Subject Binding

Bind outcomes to specific subjects so verdicts can't be reused:

```python
import hashlib
import json

def my_digest(subject):
    s = json.dumps(subject, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()

composer = UniversalComposer(subject_digest_fn=my_digest)
```

### Outcome Canonicalization

Convert final step outcome to a standard form:

```python
def my_canonicalize(step):
    if step.output_model == "my_model":
        # Map your outcomes to canonical form
        return {
            "high_risk": "needs_review",
            "low_risk": "approved",
        }.get(step.output_outcome, "unknown")
    return step.output_outcome

composer = UniversalComposer(canonicalize_fn=my_canonicalize)
```

### Convergence Detection

Define when composition has explored enough:

```python
def my_converge(steps):
    if not steps:
        return True
    
    # Converged if final step outcome is not "exploring"
    final_outcome = steps[-1].output_outcome
    return final_outcome != "exploring"

composer = UniversalComposer(converge_fn=my_converge)
```

## Example: Security Scanner System

```python
from cns.core import SystemAdapter, UniversalComposer

class SecurityScannerAdapter(SystemAdapter):
    """Scans code for security vulnerabilities."""
    
    def __init__(self):
        super().__init__(
            system_name="security_scanner",
            input_models={"code_artifact"},
            output_model="vulnerability_finding",
        )
    
    def invoke(self, subject, input_outcome=None):
        # subject = {"path": "...", "code": "..."}
        
        # Run your actual security scanner
        findings = scan_code(subject["code"])
        
        if len(findings) > 0:
            return "vulnerabilities_found"
        else:
            return "no_vulnerabilities"

class VulnerabilityReporterAdapter(SystemAdapter):
    """Converts findings to human-readable report."""
    
    def __init__(self):
        super().__init__(
            system_name="vulnerability_reporter",
            input_models={"vulnerability_finding"},
            output_model="report",
        )
    
    def invoke(self, subject, input_outcome=None):
        # input_outcome = "vulnerabilities_found" or "no_vulnerabilities"
        
        if input_outcome == "vulnerabilities_found":
            return "report_generated"
        else:
            return "no_report_needed"

# Use them together
composer = UniversalComposer()
composer.register_adapter(SecurityScannerAdapter())
composer.register_adapter(VulnerabilityReporterAdapter())

subject = {"path": "app.py", "code": "..."}
trace = composer.compose(
    ["security_scanner", "vulnerability_reporter"],
    subject,
    cycle=1
)

print(trace.timeline())
# Cycle 1: security_scanner → vulnerability_reporter
#   1. security_scanner → vulnerabilities_found
#   2. vulnerability_reporter ← vulnerabilities_found → report_generated
#   Final: report_generated
#   Converged: True
```

## Multi-Step Workflows

Chain many systems together:

```python
# Code → Security → Compliance → Report
path = [
    "code_extractor",
    "security_scanner",
    "compliance_checker",
    "report_generator",
]

trace = composer.compose(path, subject, cycle=1)

for step in trace.steps:
    print(f"{step.system_name}: {step.output_outcome}")
```

## Alternative Path Selection

Use convergence to route through alternatives:

```python
for cycle in range(1, 6):
    trace = composer.compose(path, subject, cycle=cycle)
    
    if trace.converged:
        print(f"Converged in cycle {cycle}")
        break
    
    # If not converged, try alternative path
    if cycle < 5:
        alt_path = composer.find_composition_path(
            start_system=path[0],
            end_system=path[-1],
        )
        if alt_path and alt_path != path:
            path = alt_path
            print(f"Trying alternative path: {path}")
```

## Testing Your Adapter

```python
import pytest
from cns.core import UniversalComposer

def test_my_adapter_accepts_correct_models():
    adapter = MySystemAdapter()
    assert "input_model_a" in adapter.input_models
    assert adapter.output_model == "my_output_model"

def test_my_adapter_produces_outcomes():
    adapter = MySystemAdapter()
    result = adapter.invoke({"test": "subject"})
    assert result in ["outcome_1", "outcome_2", ...]

def test_composition_with_my_adapter():
    composer = UniversalComposer()
    composer.register_adapter(MySystemAdapter())
    composer.register_adapter(OtherAdapter())
    
    trace = composer.compose(
        ["my_system", "other_system"],
        {"test": "subject"},
    )
    
    assert len(trace.steps) == 2
    assert trace.steps[0].system_name == "my_system"
    assert trace.steps[1].system_name == "other_system"
```

## Scaling to 67+ Systems

1. **Create one adapter per system** - Standardize on the SystemAdapter interface
2. **Define outcome models** for each system (string names, not enums)
3. **Register translation rules** between incompatible model pairs
4. **Build composition paths** using BFS (automatic via UniversalComposer)
5. **Execute multi-cycle loops** with alternative path selection on non-convergence

Example registration:

```python
composer = UniversalComposer()

# Register all 67 adapters
for adapter in [Repo1Adapter(), Repo2Adapter(), ..., Repo67Adapter()]:
    composer.register_adapter(adapter)

# Register translation rules (~30-50 depending on diversity)
for from_model, to_model, rule in translation_rules:
    composer.register_translation(from_model, to_model, rule)

# Now compose any systems together
path = composer.find_composition_path("repo_x", "repo_y")
trace = composer.compose(path, subject, cycle=1)
```

## No Universal Translator Required

UniversalComposer eliminates the need for a universal translator that knows all systems' semantics:

- Each system declares its interface (input_models, output_model)
- Composer automatically builds compatibility graph
- Translation rules are defined only where needed (at model boundaries)
- New systems added by implementing SystemAdapter + registering translations

Result: **Linear scaling** (N adapters + O(N²) translation rules) instead of **exponential** (universal translator knowing all N systems).
