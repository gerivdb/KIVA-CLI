# kiva_cli/core/nexus_sync_orchestrator.py
"""
NEXUS Sync Governance Layer - KIVA-CLI (PRD-KIVA-006 / PRD-KIVA-007)

Orchestrator to invoke the NEXUS Sync Agent v2 (XECO-001)
from the KIVA-CLI CLI and CI uniformly.

Execution modes:
- KIVA-006 (default): safe subprocess.run fallback (always works)
- KIVA-007: dynamic import of NEXUS AutoChainManager when local checkout present (HAS_AUTOCHAIN guard)
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# =============================================================================
# KIVA-007 F1 — Dynamic cross-repo import guard for NEXUS AutoChainManager
# =============================================================================
# Populated only when a sibling NEXUS checkout with entities/auto_chain_manager.py
# is resolvable and importable. Allows CLI/CI to choose between direct Python
# chaining (declarative) and the proven subprocess fallback.

HAS_AUTOCHAIN: bool = False
AutoChainManager = None  # type: ignore[assignment]


def _try_import_autochain(nexus_path: Optional[Path]) -> bool:
    """
    KIVA-007 F1 — Attempt dynamic import of AutoChainManager from NEXUS.

    - Safe: never raises, any failure → stays in fallback mode.
    - Clean: sys.path is restored in finally (no global pollution).
    - CI-friendly: when NEXUS is absent (runners), HAS_AUTOCHAIN remains False.
    """
    global HAS_AUTOCHAIN, AutoChainManager

    if not nexus_path or not nexus_path.exists():
        return False

    original_sys_path = list(sys.path)
    try:
        sys.path.insert(0, str(nexus_path))
        # NEXUS ships the real declarative engine (PRD-XECO-001)
        from entities.auto_chain_manager import AutoChainManager as _ACM  # type: ignore

        AutoChainManager = _ACM
        HAS_AUTOCHAIN = True
        return True

    except Exception:
        # ImportError / missing file / syntax / runtime → graceful degradation
        return False

    finally:
        sys.path[:] = original_sys_path


@dataclass
class NexusSyncResult:
    success: bool
    dry_run: bool
    repo_filter: Optional[str]
    report_path: Optional[Path]
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class NexusSyncOrchestrator:
    """
    KIVA-CLI governance layer for the NEXUS Sync Agent v2 (PRD-KIVA-006/007).

    Supports two execution strategies:
    - run()          : classic subprocess invocation (KIVA-006, always safe)
    - run_chain()    : declarative execution via NEXUS AutoChainManager when
                       HAS_AUTOCHAIN is True (KIVA-007). Automatic fallback
                       to run() otherwise.
    """

    DEFAULT_NEXUS_RELATIVE = "L0-CANON/NEXUS"
    DEFAULT_ECOS_ROOT = Path("D:/DO/WEB")

    def __init__(self, ecos_root: Optional[Path] = None):
        self.ecos_root = ecos_root or self.DEFAULT_ECOS_ROOT
        self.nexus_path: Optional[Path] = None
        self._resolve_nexus_path()

        # KIVA-007 F1: try to bring in the declarative AutoChain engine from NEXUS
        if self.nexus_path:
            _try_import_autochain(self.nexus_path)

    def _resolve_nexus_path(self) -> None:
        """Try to find the local path of the NEXUS repo."""
        # Priority 1: via ECOS-CLI registry if present
        registry_path = self.ecos_root / "TOOLS/ECOS-CLI/registry/repos.json"
        if registry_path.exists():
            try:
                data = json.loads(registry_path.read_text(encoding="utf-8"))
                nexus_entry = data.get("repos", {}).get("NEXUS", {})
                local = nexus_entry.get("local_path") or nexus_entry.get("path")
                if local:
                    self.nexus_path = Path(local)
                    return
            except Exception:
                pass

        # Fallback: standard path
        candidate = self.ecos_root / self.DEFAULT_NEXUS_RELATIVE
        if candidate.exists():
            self.nexus_path = candidate

    def run(
        self,
        dry_run: bool = True,
        repo_filter: Optional[str] = None,
    ) -> NexusSyncResult:
        """Execute the NEXUS Sync Agent v2."""
        if not self.nexus_path or not self.nexus_path.exists():
            return NexusSyncResult(
                success=False,
                dry_run=dry_run,
                repo_filter=repo_filter,
                report_path=None,
                stderr=(
                    "NEXUS checkout not found. "
                    "Check the ECOS registry or the default path."
                ),
            )

        sync_script = self.nexus_path / "tools" / "sync_agent_v2.py"
        if not sync_script.exists():
            return NexusSyncResult(
                success=False,
                dry_run=dry_run,
                repo_filter=repo_filter,
                report_path=None,
                stderr=f"Script not found: {sync_script}",
            )

        cmd = ["python", str(sync_script), "reconcile"]
        if dry_run:
            cmd.append("--dry-run")
        if repo_filter:
            cmd += ["--repo", repo_filter]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.nexus_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except Exception as exc:
            return NexusSyncResult(
                success=False,
                dry_run=dry_run,
                repo_filter=repo_filter,
                report_path=None,
                stderr=str(exc),
            )

        # Find the generated report (delegated to helper for KIVA-007 reuse)
        report_path = self._find_latest_report()

        return NexusSyncResult(
            success=result.returncode == 0,
            dry_run=dry_run,
            repo_filter=repo_filter,
            report_path=report_path,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    # -------------------------------------------------------------------------
    # KIVA-007 F2 — Declarative chain execution via NEXUS AutoChainManager
    # -------------------------------------------------------------------------

    def _find_latest_report(self) -> Optional[Path]:
        """Return the most recent reconciliation_*.md report, if any."""
        if not self.nexus_path or not self.nexus_path.exists():
            return None
        reports_dir = self.nexus_path / "reports"
        if reports_dir.exists():
            reports = sorted(reports_dir.glob("reconciliation_*.md"))
            if reports:
                return reports[-1]
        return None

    def run_chain(
        self,
        dry_run: bool = True,
        repo_filter: Optional[str] = None,
    ) -> NexusSyncResult:
        """
        KIVA-007 F2: Execute the nexus-sync governance chain using the
        declarative AutoChainManager from NEXUS when available.

        Falls back transparently to the classic subprocess-based run()
        when:
          - HAS_AUTOCHAIN is False (NEXUS not present or import failed)
          - The declarative engine raises for any reason (API drift, etc.)

        This guarantees that `kiva cicd nexus-sync --chain` never breaks
        the existing KIVA-006 behavior.
        """
        # Guard: no declarative engine → immediate safe fallback
        if not HAS_AUTOCHAIN or AutoChainManager is None:
            return self.run(dry_run=dry_run, repo_filter=repo_filter)

        try:
            manager = AutoChainManager()

            # Declarative definition of the "nexus-sync" chain (PRD-KIVA-007)
            manager.create_chain(
                chain_id="nexus-sync",
                name="NEXUS Sync Governance",
                steps=[
                    {"name": "resolve", "type": "tool", "target": "resolve_nexus_path"},
                    {"name": "reconcile", "type": "tool", "target": "run_reconcile"},
                    {"name": "report", "type": "tool", "target": "generate_report"},
                ],
                error_handling="stop_on_error",
            )

            # Execute with context (orchestrator passed for potential callbacks)
            success = manager.execute_chain(
                "nexus-sync",
                context={
                    "dry_run": dry_run,
                    "repo_filter": repo_filter,
                    "orchestrator": self,
                },
            )

            return NexusSyncResult(
                success=bool(success),
                dry_run=dry_run,
                repo_filter=repo_filter,
                report_path=self._find_latest_report(),
            )

        except Exception:
            # Any problem with the NEXUS declarative engine → fallback
            # (protects against future changes in AutoChainManager API)
            return self.run(dry_run=dry_run, repo_filter=repo_filter)
