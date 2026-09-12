"""Check CNS integration status."""

from .cns_integration import get_cns_status


def check():
    """Print CNS integration status."""
    status = get_cns_status()

    print("CNS Integration Status")
    print("=" * 50)
    print(f"CNS Installed: {'✅ Yes' if status['has_cns'] else '❌ No (using fallback)'}")
    print(f"GateOutcome Source: {status['gate_outcome_source']}")
    print(f"subject_digest Source: {status['subject_digest_source']}")

    if status["has_cns"]:
        print("\n✅ Using authoritative CNS gate.py implementations")
        print("   - GateOutcome from cns.gate")
        print("   - subject_digest from cns.gate")
        print("   - Full CNS semantics enabled")
    else:
        print("\n⚠️  CNS not found; using local fallback implementations")
        print("   - GateOutcome: PASS/RETRY/TERMINAL_BREACH")
        print("   - subject_digest: SHA256 hash")
        print("\n   To use authoritative CNS implementations:")
        print("   1. Install CNS package or add as sibling repo")
        print("   2. Restart Python interpreter")


if __name__ == "__main__":
    check()
