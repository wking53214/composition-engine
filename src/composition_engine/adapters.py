"""System adapter for ghost_tools (code scanner).

Each adapter declares its outcome model and implements the invoke interface
for the LibraryComposer to orchestrate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .compose_library import SystemAdapter, SystemModel
from .outcomes import GhostToolsStatus

# ghost_buster's own CLI, invoked as a subprocess rather than imported: its
# scan pipeline (ghost_buster/pipeline.py's gather()) takes a full argparse
# Namespace as its argument, built from ~30 flags this repo has no business
# reconstructing and keeping in sync with. The CLI, not that internal
# function, is ghost_buster's stable public contract.
try:
    import ghost_buster
    HAS_GHOST_TOOLS_CLI = True
except ImportError:
    HAS_GHOST_TOOLS_CLI = False


# Ordered most- to least-concerning: the statuses ghost_tools' own schema.py
# calls AUTHORITATIVE ("the statuses a deterministic decision may rest on")
# first, then the merely-claimed REASONED, then the two dispositions that
# close a finding out without denying it happened. Used to pick the single
# worst declared status among several findings -- the natural aggregate for
# an adapter whose output model represents one verdict, not a list.
_STATUS_CONCERN_ORDER = (
    GhostToolsStatus.CONFIRMED,
    GhostToolsStatus.CONFIRMED_BY_REVIEW,
    GhostToolsStatus.REASONED,
    GhostToolsStatus.REJECTED,
    GhostToolsStatus.SUPPRESSED,
)

_GHOST_BUSTER_SCAN_TIMEOUT_SECONDS = 120


def _run_ghost_buster_scan(repo_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Run ghost_buster's real CLI against a repo and return its findings.

    --json for machine output; --no-secrets/--no-tests/--no-branches/
    --no-ledger keep this fast and non-interactive (--tests would need
    --trust consent recorded first, and --secrets needs gitleaks installed
    separately -- neither is this adapter's call to make on a caller's
    behalf); --single-repo skips the cross-repository-seam prompt, since
    an adapter call has no terminal to ask it at.

    ghost-buster's own exit code is 1 whenever it found anything to report,
    which is the normal case, not a failure -- only a genuine crash, a
    timeout, or output that isn't the JSON it promised counts as this scan
    not having run. Returns None for those, which the caller treats the
    same as "no findings supplied": an honest REASONED, not a fabricated
    CONFIRMED or a raised exception the rest of the composition wouldn't
    survive.
    """
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "ghost_buster.cli", str(repo_path),
                "--json", "--no-secrets", "--no-tests", "--no-branches",
                "--no-ledger", "--single-repo",
            ],
            capture_output=True, text=True,
            timeout=_GHOST_BUSTER_SCAN_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return findings if isinstance(findings, list) else None


class GhostToolsAdapter(SystemAdapter):
    """Adapter for ghost_tools: code scanner and vulnerability finder.

    Scans for security findings with Status (CONFIRMED/REASONED/etc.)
    and Severity (CRITICAL/MAJOR/MINOR/INFORMATIONAL).

    Produces Status outcomes by default, but can also emit Severity as separate signal.
    """

    def __init__(self):
        super().__init__(
            system_name="ghost_tools",
            input_models={SystemModel.CNS_GATE_OUTCOME},
            output_model=SystemModel.GHOST_TOOLS_STATUS,
        )

    def invoke(
        self,
        subject: Dict[str, Any],
        input_outcome: Optional[str] = None,
    ) -> str:
        """Scan subject for security findings.

        In real execution this invokes ghost_buster.cli and aggregates the
        findings it returns. Here: if `subject` carries a `findings` list
        shaped like ghost_buster's own Finding output (each a dict with a
        "status" key), report the single most-concerning declared status
        among them. With no findings supplied -- the common case in this
        repo's own demos and tests, which pass a bare {"repo": ...} subject
        -- REASONED: an unverified claim is the only honest thing to report
        about a subject nobody has actually scanned.

        Args:
            subject: Code/repo to scan. Either a "findings" list already
                shaped like ghost_buster's own output (each a dict with a
                "status" key -- for tests and callers who already have
                results), or a "repo_path" to scan for real via ghost_buster's
                CLI. "findings" wins if both are given.
            input_outcome: Previous system's outcome (unused)

        Returns:
            Status: one of CONFIRMED/REASONED/CONFIRMED_BY_REVIEW/REJECTED/SUPPRESSED
        """
        if not isinstance(subject, dict):
            return GhostToolsStatus.REASONED

        findings = subject.get("findings")
        if findings is None and subject.get("repo_path") and HAS_GHOST_TOOLS_CLI:
            findings = _run_ghost_buster_scan(Path(subject["repo_path"]))

        if findings:
            present = {f.get("status") for f in findings if f.get("status")}
            for status in _STATUS_CONCERN_ORDER:
                if status.value in present:
                    return status
        return GhostToolsStatus.REASONED


def register_core_adapters(composer: Any) -> None:
    """Register the core system adapters with a LibraryComposer.

    Currently only GhostToolsAdapter is registered. It provides
    security scanning capabilities via ghost_tools.

    Args:
        composer: LibraryComposer instance to register adapters on
    """
    composer.register_adapter(GhostToolsAdapter())


def register_core_translation_rules(composer: Any) -> None:
    """Register translation rules between outcome models.

    Currently no translation rules are needed with only GhostTools
    and CNS Gate outcomes in the composition.

    Args:
        composer: LibraryComposer instance to register rules on
    """
    pass
