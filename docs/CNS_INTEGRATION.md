# CNS Integration: Running Through the CNS Vein

The composition engine is wired directly into CNS infrastructure and uses authoritative implementations from `cns.gate`.

## Architecture

```
┌─────────────────────────────────────────────┐
│ composition-engine                          │
├─────────────────────────────────────────────┤
│                                              │
│ cns_integration.py (bridge)                 │
│  ├─ Try: import from cns.gate               │
│  └─ Fallback: local implementations         │
│                 ↓                            │
│ cns_backend.py (CNS-configured)             │
│  ├─ GateOutcome (from cns.gate)             │
│  ├─ subject_digest (from cns.gate)          │
│  └─ create_cns_composer()                   │
│                                              │
│ core.py (orchestration)                     │
│  └─ Uses backend via pluggable functions   │
│                                              │
└──────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────┐
│ cns (authoritative)                          │
├──────────────────────────────────────────────┤
│                                              │
│ gate.py                                      │
│ ├─ GateOutcome enum (PASS/RETRY/BREACH)    │
│ ├─ subject_digest(content) → sha256        │
│ ├─ resolve(results) → cascade              │
│ └─ GateResult (binding)                    │
│                                              │
└──────────────────────────────────────────────┘
```

## How It Works

### 1. Integration Layer (cns_integration.py)

```python
# Attempts to import from authoritative CNS
try:
    from cns.gate import GateOutcome, subject_digest, resolve
    HAS_CNS = True
except ImportError:
    # Fallback implementations
    HAS_CNS = False
```

**Status**: When CNS is available (same machine or PYTHONPATH), composition engine automatically uses it.

### 2. CNS Backend (cns_backend.py)

```python
from .cns_integration import GateOutcome, subject_digest, HAS_CNS

# Backend now uses real CNS implementations
composer = UniversalComposer(
    subject_digest_fn=subject_digest,  # from cns.gate
    canonicalize_fn=cns_canonicalize,
    converge_fn=cns_converge,
)
```

**Result**: All subject binding uses the authoritative CNS cryptographic digest.

### 3. Verify Integration

```python
from cns import get_cns_status

status = get_cns_status()
print(f"Has CNS: {status['has_cns']}")
print(f"GateOutcome Source: {status['gate_outcome_source']}")
print(f"subject_digest Source: {status['subject_digest_source']}")
```

Example output (when CNS is available):
```
Has CNS: True
GateOutcome Source: cns.gate
subject_digest Source: cns.gate
```

## CNS Semantics in Action

### GateOutcome Cascade

CNS gate.py implements outcome cascade semantics:

```python
# Any TERMINAL_BREACH in results → TERMINAL_BREACH
# Otherwise any RETRY → RETRY
# Otherwise → PASS

resolve([PASS, RETRY, PASS])  # → RETRY
resolve([PASS, TERMINAL_BREACH, RETRY])  # → TERMINAL_BREACH
resolve([PASS, PASS, PASS])  # → PASS
```

Composition engine inherits this via `cns_converge()`:

```python
def cns_converge(steps):
    """RETRY = still exploring"""
    final = cns_canonicalize(steps[-1])
    return final != "retry"
```

### Subject Binding

Every composition step includes cryptographic binding to the subject:

```python
trace = composer.compose(path, subject, cycle=1)

# Subject hash from cns.gate.subject_digest
for step in trace.steps:
    print(f"{step.system_name}: hash={step.subject_hash}")

# Same subject → same hash (verdict can't be transferred)
# Different subject → different hash (outcome bound to content)
```

**Implementation**: CNS's `subject_digest()` computes SHA256 of `json.dumps(subject, sort_keys=True)`.

### Outcome Canonicalization

When composition ends with any model, `cns_canonicalize()` maps to CNS canonical form:

```python
# SWIZZLE verdict → PASS/RETRY/TERMINAL_BREACH
if model == "swizzle_verdict":
    if outcome in ("banished", "dismissed"):
        return "pass"
    elif outcome in ("escaped", "conjured"):
        return "terminal_breach"
    else:
        return "retry"

# ghost_tools status → PASS/RETRY/TERMINAL_BREACH
if model == "ghost_tools_status":
    if outcome == "confirmed":
        return "pass"
    elif outcome in ("reasoned", "rejected"):
        return "terminal_breach"
    else:
        return "retry"
```

**Property**: All system outcomes ultimately map to CNS gate outcomes (PASS/RETRY/TERMINAL_BREACH).

## Using Composition Engine with CNS

### Setup

```python
import sys
sys.path.insert(0, '/path/to/CNS')
sys.path.insert(0, '/path/to/composition-engine/src')

from cns import (
    create_cns_composer,
    register_cns_adapters,
    register_cns_translation_rules,
    get_cns_status,
)

# Verify integration
print(get_cns_status())
```

### Execute with CNS Semantics

```python
# Create composer (pre-configured with CNS infrastructure)
composer = create_cns_composer()

# Register systems
register_cns_adapters(composer)
register_cns_translation_rules(composer)

# Compose
subject = {"repo": "innovation_os", "commit": "abc123"}
trace = composer.compose(
    ["swizzle", "ghost_tools", "wizzle", "innovation_os"],
    subject,
    cycle=1,
)

# Results are CNS-canonical
print(f"Outcome: {trace.overall_outcome}")  # GateOutcome.PASS, .RETRY, or .TERMINAL_BREACH
print(f"Subject bound to: {trace.steps[0].subject_hash}")  # Cryptographic binding
print(f"Converged: {trace.converged}")  # RETRY means still exploring
```

## Without CNS (Standalone)

Composition engine works standalone if CNS is not available:

```python
# No CNS required
from composition_engine.src.cns import UniversalComposer

composer = UniversalComposer()
# ... register adapters, execute compositions ...
```

Falls back to local implementations:
- GateOutcome: Simple enum
- subject_digest: SHA256 (same as CNS)
- Convergence: Simple RETRY check

**Use case**: Integrate composition engine into other systems without requiring CNS dependency.

## Running Through the CNS Vein

When both CNS and composition-engine are available:

1. **Data flows** through composition engine orchestration
2. **Subject binding** enforces via CNS cryptographic digest
3. **Outcomes** cascade per CNS gate semantics
4. **Convergence** detected per CNS rules (RETRY = exploring)
5. **Canonicalization** maps to CNS gate outcomes

**Result**: Composition engine is not just compatible with CNS—it's an extension of CNS governance infrastructure, running natively on CNS foundations.

## Extending with Custom Backends

You can also create backends that use other integrity/convergence systems:

```python
# Example: Custom backend with different semantics
def my_subject_binding(subject):
    return base64.b64encode(str(subject).encode()).decode()

def my_canonicalize(step):
    return {...}

def my_converge(steps):
    return {...}

composer = UniversalComposer(
    subject_digest_fn=my_subject_binding,
    canonicalize_fn=my_canonicalize,
    converge_fn=my_converge,
)
```

**But for CNS use cases**: Use `create_cns_composer()` to get authoritative CNS semantics.

## Status Check in Code

```python
from cns import HAS_CNS, get_cns_status

if HAS_CNS:
    print("✅ Running via CNS vein")
else:
    print("⚠️ CNS not found; using fallback")

status = get_cns_status()
for key, value in status.items():
    print(f"  {key}: {value}")
```

## Summary

Composition engine **transparently integrates with CNS**:
- Detects authoritative CNS when available
- Falls back gracefully if not
- Exposes integration status at runtime
- Uses real CNS semantics for subject binding and canonicalization
- Can run standalone if needed

**Net result**: Universal orchestration engine that's deeply rooted in CNS infrastructure when CNS is present, yet completely independent when needed.
