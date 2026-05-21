# kiva_cli/core/nexus_sync_orchestrator.py
"""
NEXUS Sync Governance Layer - KIVA-CLI (PRD-KIVA-006)

Orchestrator to invoke the NEXUS Sync Agent v2 (XECO-001)
from the KIVA-CLI CLI and CI uniformly.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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
    KIVA-CLI governance layer for the NEXUS Sync Agent v2.

    Locates the NEXUS checkout via the ECOS registry and executes
    the agent with the correct parameters.
    """

    DEFAULT_NEXUS_RELATIVE = "L0-CANON/NEXUS"
    DEFAULT_ECOS_ROOT = Path("D:/DO/WEB")

    def __init__(self, ecos_root: Optional[Path] = None):
        self.ecos_root = ecos_root or self.DEFAULT_ECOS_ROOT
        self.nexus_path: Optional[Path] = None
        self._resolve_nexus_path()

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

        # Find the generated report
        reports_dir = self.nexus_path / "reports"
        report_path = None
        if reports_dir.exists():
            reports = sorted(reports_dir.glob("reconciliation_*.md"))
            if reports:
                report_path = reports[-1]

        return NexusSyncResult(
            success=result.returncode == 0,
            dry_run=dry_run,
            repo_filter=repo_filter,
            report_path=report_path,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )
