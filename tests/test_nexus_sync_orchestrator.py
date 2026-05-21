"""Unit tests for NexusSyncOrchestrator (PRD-KIVA-006 F1)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kiva_cli.core.nexus_sync_orchestrator import NexusSyncOrchestrator, NexusSyncResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_nexus(tmp_path: Path) -> Path:
    """Create a minimal fake NEXUS checkout."""
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "sync_agent_v2.py").write_text("# fake agent", encoding="utf-8")
    (tmp_path / "reports").mkdir()
    return tmp_path


@pytest.fixture()
def tmp_ecos_root(tmp_path: Path, tmp_nexus: Path) -> Path:
    """Create a fake ECOS root with a registry pointing to tmp_nexus."""
    registry_dir = tmp_path / "TOOLS/ECOS-CLI/registry"
    registry_dir.mkdir(parents=True)
    registry = {
        "repos": {
            "NEXUS": {"local_path": str(tmp_nexus)}
        }
    }
    (registry_dir / "repos.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

class TestNexusPathResolution:
    def test_resolves_via_registry(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        assert orch.nexus_path == tmp_nexus

    def test_fallback_to_default_path(self, tmp_path: Path, tmp_nexus: Path):
        """No registry — fallback uses DEFAULT_NEXUS_RELATIVE."""
        ecos_root = tmp_path / "ecos_root"
        ecos_root.mkdir()
        nexus_default = ecos_root / NexusSyncOrchestrator.DEFAULT_NEXUS_RELATIVE
        nexus_default.mkdir(parents=True)
        orch = NexusSyncOrchestrator(ecos_root=ecos_root)
        assert orch.nexus_path == nexus_default

    def test_nexus_path_none_when_missing(self, tmp_path: Path):
        """Neither registry nor default path exists."""
        orch = NexusSyncOrchestrator(ecos_root=tmp_path)
        assert orch.nexus_path is None


# ---------------------------------------------------------------------------
# run() — NEXUS absent
# ---------------------------------------------------------------------------

class TestRunNexusAbsent:
    def test_returns_failure_when_nexus_missing(self, tmp_path: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_path)
        result = orch.run(dry_run=True)
        assert result.success is False
        assert result.report_path is None
        assert "not found" in result.stderr.lower() or "introuvable" in result.stderr.lower()

    def test_returns_failure_when_script_missing(self, tmp_path: Path):
        nexus = tmp_path / "NEXUS"
        nexus.mkdir()
        (nexus / "tools").mkdir()
        # sync_agent_v2.py intentionally NOT created
        orch = NexusSyncOrchestrator.__new__(NexusSyncOrchestrator)
        orch.ecos_root = tmp_path
        orch.nexus_path = nexus
        result = orch.run(dry_run=True)
        assert result.success is False
        assert "sync_agent_v2.py" in result.stderr or "not found" in result.stderr.lower()


# ---------------------------------------------------------------------------
# run() — dry-run nominal
# ---------------------------------------------------------------------------

class TestRunDryRun:
    def test_dry_run_flag_in_command(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("kiva_cli.core.nexus_sync_orchestrator.subprocess.run", return_value=mock_result) as mock_run:
            orch.run(dry_run=True)
            cmd = mock_run.call_args[0][0]
            assert "--dry-run" in cmd

    def test_no_dry_run_flag_when_false(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("kiva_cli.core.nexus_sync_orchestrator.subprocess.run", return_value=mock_result) as mock_run:
            orch.run(dry_run=False)
            cmd = mock_run.call_args[0][0]
            assert "--dry-run" not in cmd

    def test_repo_filter_in_command(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("kiva_cli.core.nexus_sync_orchestrator.subprocess.run", return_value=mock_result) as mock_run:
            orch.run(dry_run=True, repo_filter="KIVA-CLI")
            cmd = mock_run.call_args[0][0]
            assert "--repo" in cmd
            assert "KIVA-CLI" in cmd

    def test_success_result_structure(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        mock_result = MagicMock(returncode=0, stdout="synced", stderr="")
        with patch("kiva_cli.core.nexus_sync_orchestrator.subprocess.run", return_value=mock_result):
            result = orch.run(dry_run=True)
        assert isinstance(result, NexusSyncResult)
        assert result.success is True
        assert result.dry_run is True
        assert result.stdout == "synced"

    def test_failure_result_on_nonzero_returncode(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        mock_result = MagicMock(returncode=1, stdout="", stderr="error")
        with patch("kiva_cli.core.nexus_sync_orchestrator.subprocess.run", return_value=mock_result):
            result = orch.run(dry_run=True)
        assert result.success is False
        assert result.returncode == 1


# ---------------------------------------------------------------------------
# run() — report detection
# ---------------------------------------------------------------------------

class TestReportDetection:
    def test_detects_latest_report(self, tmp_ecos_root: Path, tmp_nexus: Path):
        reports_dir = tmp_nexus / "reports"
        (reports_dir / "reconciliation_20260521_220000.md").write_text("old", encoding="utf-8")
        (reports_dir / "reconciliation_20260521_230000.md").write_text("new", encoding="utf-8")
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("kiva_cli.core.nexus_sync_orchestrator.subprocess.run", return_value=mock_result):
            result = orch.run(dry_run=True)
        assert result.report_path is not None
        assert "230000" in result.report_path.name

    def test_report_path_none_when_no_reports(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("kiva_cli.core.nexus_sync_orchestrator.subprocess.run", return_value=mock_result):
            result = orch.run(dry_run=True)
        assert result.report_path is None

    def test_handles_subprocess_exception(self, tmp_ecos_root: Path, tmp_nexus: Path):
        orch = NexusSyncOrchestrator(ecos_root=tmp_ecos_root)
        with patch(
            "kiva_cli.core.nexus_sync_orchestrator.subprocess.run",
            side_effect=TimeoutError("timeout")
        ):
            result = orch.run(dry_run=True)
        assert result.success is False
        assert "timeout" in result.stderr.lower()
