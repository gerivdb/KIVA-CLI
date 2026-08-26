#!/usr/bin/env python3
"""
Test Suite: Merge Commands - KIVA CLI

Tests for the merge command group (sovereign PR merge wrapper).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import subprocess

try:
    from kiva_cli.commands.merge_commands import merge_cli, _run, _wal_append, _dag3_validate, REPOS_LOCAL_PATHS
except ImportError:
    import click

    @click.group(name='merge')
    def merge_cli():
        pass

    @merge_cli.command(name='pr')
    @click.argument('repo')
    @click.argument('pr_number', type=int)
    @click.argument('source_branch', required=False, default=None)
    @click.option('--method', default='squash')
    @click.option('--hotfix', is_flag=True)
    @click.option('--dry-run', is_flag=True)
    @click.option('--skip-dag3', is_flag=True)
    def merge_pr(repo: str, pr_number: int, source_branch: str, method: str, hotfix: bool, dry_run: bool, skip_dag3: bool):
        click.echo("[OK] MERGE COMPLETE")

    REPOS_LOCAL_PATHS = {"TEST": "C:\\test"}

    def _run(cmd: list[str], cwd: str = None, dry_run: bool = False):
        return 0

    def _wal_append(repo: str, pr: int, event: str, dry_run: bool = False, metadata: dict = None):
        pass

    def _dag3_validate(repo_path: str, source_branch: str, target_branch: str, dry_run: bool = False):
        return {"status": "approved", "phi_cps_impact": 0.01}


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestMergeConstants:
    """Test merge command constants."""

    def test_repos_local_paths(self):
        """Test REPOS_LOCAL_PATHS has expected repos."""
        assert "KIVA-CLI" in REPOS_LOCAL_PATHS
        assert "GOVERNANCE-HUB" in REPOS_LOCAL_PATHS
        assert "ECOS-CLI" in REPOS_LOCAL_PATHS
        assert "DevTools" in REPOS_LOCAL_PATHS


class TestRunHelper:
    """Test _run helper function."""

    @patch('subprocess.run')
    def test_run_normal(self, mock_run, cli_runner):
        """Test normal command execution."""
        mock_run.return_value = MagicMock(returncode=0)
        result = _run(["echo", "test"])
        assert result == 0
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_dry_run(self, mock_run):
        """Test dry-run mode."""
        result = _run(["echo", "test"], dry_run=True)
        assert result == 0
        mock_run.assert_not_called()


class TestWALAppendHelper:
    """Test _wal_append helper function."""

    @patch('kiva_cli.commands.merge_commands._run')
    def test_wal_append(self, mock_run):
        """Test WAL event append."""
        _wal_append("TEST-REPO", 42, "test_event", dry_run=False, metadata={"key": "value"})
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "kiva" in args
        assert "wal" in args
        assert "append" in args


class TestDAG3ValidateHelper:
    """Test _dag3_validate helper function."""

    @patch('kiva_cli.commands.merge_commands.DAG3Manager')
    def test_dag3_validate(self, mock_manager_class):
        """Test DAG-3 validation."""
        mock_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.overall_status = "approved"
        mock_result.phi_cps_impact = 0.02
        mock_result.acm_result.has_cycles = False
        mock_result.acm_result.cycles = []
        mock_result.acm_result.severity.name = "NONE"
        mock_result.admr_result.violations = []
        mock_result.admr_result.status.value = "valid"
        mock_result.recommendations = []
        mock_result.timestamp = "2026-01-01T00:00:00"
        mock_manager.validate_merge.return_value = mock_result
        mock_manager_class.return_value = mock_manager

        result = _dag3_validate("C:\\repo", "feature", "main")

        assert result["status"] == "approved"
        assert result["phi_cps_impact"] == 0.02
        assert result["acm_cycles"] == 0
        assert result["admr_violations"] == 0
        mock_manager_class.assert_called_once_with(repo_path="C:\\repo")
        mock_manager.validate_merge.assert_called_once_with("feature", "main")


class TestMergePRCommand:
    """Test 'kiva merge pr' command."""

    @patch('kiva_cli.commands.merge_commands._dag3_validate')
    @patch('kiva_cli.commands.merge_commands._wal_append')
    @patch('kiva_cli.commands.merge_commands._run')
    @patch('subprocess.run')
    def test_merge_pr_dry_run(self, mock_subprocess, mock_run, mock_wal, mock_dag3, cli_runner):
        """Test merge PR in dry-run mode."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
        mock_dag3.return_value = {"status": "approved", "phi_cps_impact": 0.01}
        mock_run.return_value = 0

        result = cli_runner.invoke(merge_cli, ['pr', 'KIVA-CLI', '42', '--dry-run'])

        assert result.exit_code == 0
        assert "MERGE COMPLETE" in result.output or "DRY-RUN" in result.output
        mock_wal.assert_called()
        mock_dag3.assert_called()

    @patch('kiva_cli.commands.merge_commands._dag3_validate')
    @patch('kiva_cli.commands.merge_commands._wal_append')
    @patch('kiva_cli.commands.merge_commands._run')
    @patch('subprocess.run')
    def test_merge_pr_hotfix(self, mock_subprocess, mock_run, mock_wal, mock_dag3, cli_runner):
        """Test merge PR with hotfix flag."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="hotfix-branch\n")
        mock_run.return_value = 0
        mock_dag3.return_value = {"status": "approved", "phi_cps_impact": 0.01}

        result = cli_runner.invoke(merge_cli, ['pr', 'KIVA-CLI', '42', '--hotfix', '--dry-run'])

        assert result.exit_code == 0
        assert "HOTFIX" in result.output or "hotfix" in result.output.lower()

    @patch('kiva_cli.commands.merge_commands._dag3_validate')
    @patch('kiva_cli.commands.merge_commands._wal_append')
    @patch('kiva_cli.commands.merge_commands._run')
    @patch('subprocess.run')
    def test_merge_pr_skip_dag3(self, mock_subprocess, mock_run, mock_wal, mock_dag3, cli_runner):
        """Test merge PR skipping DAG-3 validation."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
        mock_run.return_value = 0

        result = cli_runner.invoke(merge_cli, ['pr', 'KIVA-CLI', '42', '--skip-dag3', '--dry-run'])

        assert result.exit_code == 0
        mock_dag3.assert_not_called()

    @patch('kiva_cli.commands.merge_commands._dag3_validate')
    @patch('kiva_cli.commands.merge_commands._wal_append')
    @patch('kiva_cli.commands.merge_commands._run')
    @patch('subprocess.run')
    def test_merge_pr_dag3_rejected(self, mock_subprocess, mock_run, mock_wal, mock_dag3, cli_runner):
        """Test merge PR with DAG-3 rejection."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
        mock_dag3.return_value = {"status": "rejected", "phi_cps_impact": 0.10, "recommendations": ["Fix cycles"]}

        result = cli_runner.invoke(merge_cli, ['pr', 'KIVA-CLI', '42', '--dry-run'])

        assert result.exit_code == 1
        assert "HALT" in result.output or "REJECTED" in result.output

    @patch('kiva_cli.commands.merge_commands._dag3_validate')
    @patch('kiva_cli.commands.merge_commands._wal_append')
    @patch('kiva_cli.commands.merge_commands._run')
    @patch('subprocess.run')
    def test_merge_pr_ci_failure(self, mock_subprocess, mock_run, mock_wal, mock_dag3, cli_runner):
        """Test merge PR with CI failure."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
        mock_dag3.return_value = {"status": "approved", "phi_cps_impact": 0.01}
        mock_run.return_value = 1  # CI fails

        result = cli_runner.invoke(merge_cli, ['pr', 'KIVA-CLI', '42', '--dry-run'])

        assert result.exit_code == 1
        assert "HALT" in result.output or "failed" in result.output.lower()

    @patch('kiva_cli.commands.merge_commands._dag3_validate')
    @patch('kiva_cli.commands.merge_commands._wal_append')
    @patch('kiva_cli.commands.merge_commands._run')
    @patch('subprocess.run')
    def test_merge_pr_merge_failure(self, mock_subprocess, mock_run, mock_wal, mock_dag3, cli_runner):
        """Test merge PR with gh pr merge failure."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
        mock_dag3.return_value = {"status": "approved", "phi_cps_impact": 0.01}
        mock_run.side_effect = [0, 1]  # CI passes, merge fails

        result = cli_runner.invoke(merge_cli, ['pr', 'KIVA-CLI', '42', '--dry-run'])

        assert result.exit_code == 1
        assert "HALT" in result.output or "merge failed" in result.output.lower()


class TestMergePRRemoteOnly:
    """Test merge PR for remote-only repos."""

    @patch('kiva_cli.commands.merge_commands._dag3_validate')
    @patch('kiva_cli.commands.merge_commands._wal_append')
    @patch('kiva_cli.commands.merge_commands._run')
    @patch('subprocess.run')
    def test_merge_pr_remote_only(self, mock_subprocess, mock_run, mock_wal, mock_dag3, cli_runner):
        """Test merge PR for NEXUS (remote_only)."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
        mock_dag3.return_value = {"status": "approved", "phi_cps_impact": 0.01}
        mock_run.return_value = 0

        # NEXUS has None as local path
        result = cli_runner.invoke(merge_cli, ['pr', 'NEXUS', '42', '--dry-run'])

        assert result.exit_code == 0
        assert "remote_only" in result.output.lower() or "skipped" in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])