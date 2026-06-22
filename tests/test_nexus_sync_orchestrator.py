"""
Tests for NexusSyncOrchestrator (PRD-KIVA-006 + PRD-KIVA-007)

Covers:
- HAS_AUTOCHAIN guard and dynamic import
- run() baseline behavior
- run_chain() with fallback (KIVA-007 F2)
- run_chain() with mocked AutoChainManager (positive declarative path)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kiva_cli.core.nexus_sync_orchestrator import (
    NexusSyncOrchestrator,
    NexusSyncResult,
    HAS_AUTOCHAIN,
    AutoChainManager,
    _try_import_autochain,
)


class TestGuardAndDynamicImport:
    """KIVA-007 F1 — Guard behavior."""

    def test_has_auto_chain_false_by_default(self):
        """By default (no NEXUS), the guard must be False."""
        # The module-level constant is set at import time.
        # On a machine without NEXUS, it should be False.
        assert HAS_AUTOCHAIN is False
        assert AutoChainManager is None

    def test_try_import_autochain_no_nexus(self, tmp_path):
        """_try_import_autochain returns False and does not raise when NEXUS is absent."""
        fake_nexus = tmp_path / "L0-CANON" / "NEXUS"
        fake_nexus.mkdir(parents=True)

        result = _try_import_autochain(fake_nexus)
        assert result is False
        # Global state must remain unchanged
        assert HAS_AUTOCHAIN is False


class TestRunChainFallback:
    """KIVA-007 F2 — run_chain() fallback behavior."""

    def test_run_chain_falls_back_when_no_auto_chain(self, monkeypatch):
        """When HAS_AUTOCHAIN is False, run_chain must delegate to run()."""
        # Force the guard to False for this test
        monkeypatch.setattr(
            "kiva_cli.core.nexus_sync_orchestrator.HAS_AUTOCHAIN", False
        )
        monkeypatch.setattr(
            "kiva_cli.core.nexus_sync_orchestrator.AutoChainManager", None
        )

        orch = NexusSyncOrchestrator()

        # We cannot easily call the real NEXUS, so we patch run()
        fake_result = NexusSyncResult(
            success=True,
            dry_run=True,
            repo_filter="TEST",
            report_path=None,
            stdout="mocked",
        )

        with patch.object(orch, "run", return_value=fake_result) as mock_run:
            result = orch.run_chain(dry_run=True, repo_filter="TEST")

            mock_run.assert_called_once_with(dry_run=True, repo_filter="TEST")
            assert result is fake_result
            assert result.stdout == "mocked"

    def test_run_chain_falls_back_on_exception(self, monkeypatch):
        """If the declarative path raises, we must still fall back to run()."""
        # Simulate a working AutoChainManager that explodes on execute
        class ExplodingManager:
            def create_chain(self, *a, **k):
                pass

            def execute_chain(self, *a, **k):
                raise RuntimeError("Boom from NEXUS AutoChain")

        monkeypatch.setattr(
            "kiva_cli.core.nexus_sync_orchestrator.HAS_AUTOCHAIN", True
        )
        monkeypatch.setattr(
            "kiva_cli.core.nexus_sync_orchestrator.AutoChainManager",
            ExplodingManager,
        )

        orch = NexusSyncOrchestrator()

        fake_result = NexusSyncResult(
            success=True, dry_run=True, repo_filter=None, report_path=None
        )

        with patch.object(orch, "run", return_value=fake_result) as mock_run:
            result = orch.run_chain(dry_run=False)
            mock_run.assert_called_once()
            assert result is fake_result


class TestFindLatestReport:
    """Helper used by both run() and run_chain()."""

    def test_find_latest_report_no_nexus(self):
        orch = NexusSyncOrchestrator()
        assert orch._find_latest_report() is None

    def test_find_latest_report_with_reports(self, tmp_path, monkeypatch):
        """Should return the most recent reconciliation_*.md file."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        # Create two reports
        old = reports_dir / "reconciliation_2026-01-01.md"
        new = reports_dir / "reconciliation_2026-05-22.md"
        old.write_text("old")
        new.write_text("new")

        # Force a fake nexus_path
        orch = NexusSyncOrchestrator()
        monkeypatch.setattr(orch, "nexus_path", tmp_path)

        result = orch._find_latest_report()
        assert result == new


class TestRunChainPositivePath:
    """KIVA-007 F2 — Happy path when AutoChainManager is available (mocked)."""

    def test_run_chain_uses_declarative_engine(self, monkeypatch):
        """When HAS_AUTOCHAIN=True, run_chain must call create_chain + execute_chain."""
        mock_manager = MagicMock()
        mock_manager.execute_chain.return_value = True

        class FakeAutoChainManager:
            def __new__(cls):
                return mock_manager

        monkeypatch.setattr(
            "kiva_cli.core.nexus_sync_orchestrator.HAS_AUTOCHAIN", True
        )
        monkeypatch.setattr(
            "kiva_cli.core.nexus_sync_orchestrator.AutoChainManager",
            FakeAutoChainManager,
        )

        orch = NexusSyncOrchestrator()

        # Also patch _find_latest_report so we don't need a real NEXUS
        fake_report = Path("/tmp/fake-report.md")
        monkeypatch.setattr(orch, "_find_latest_report", lambda: fake_report)

        result = orch.run_chain(dry_run=True, repo_filter="FLUENCE")

        # Verify the declarative engine was used
        mock_manager.create_chain.assert_called_once()
        call_args = mock_manager.create_chain.call_args
        assert call_args.kwargs["chain_id"] == "nexus-sync"

        mock_manager.execute_chain.assert_called_once()
        assert result.success is True
        assert result.report_path == fake_report
