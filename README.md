# composition-engine (retired)

This repository is retired. Its job, deciding what a set of systems together allow, is done by CNS:

- `cns_composition.super_gate.SuperGate` is the one control point. It is built from repository gates, refuses a gate at an end its repository does not declare, treats a gate with no candidate as a TERMINAL_BREACH, and says `allowed` only for a complete, all-PASS decision in which every verdict records what it judged.
- `cns_composition.gate_chain` and `cns_composition.compose_library` hold the chain runner and the composer. Unlike the composer here, they resolve every verdict, so a breach in the middle of a path is not lost when the last gate passes.

CNS: https://github.com/wking53214/CNS

## Why it was retired

- It read only the last step's outcome.
- Its one adapter (ghost_tools) and its vocabulary table had CNS-side equivalents, and no repository imported it.
- Its table mapped a confirmed ghost_tools finding to a breach, the opposite of CNS and ghost_tools, so one finding could get opposite verdicts depending on which of them judged it.

## The source

The code stays in this repository's git history. The last commit that contains it is `0501d20` (its fallback digest is byte-identical to `cns.gate.subject_digest` on CNS's 24 published vectors).

Apache-2.0.
