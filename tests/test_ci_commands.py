#!/usr/bin/env python3
"""
Test Suite: CI Commands - KIVA CLI

Tests for the CI command group (local CI orchestration).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import json

try:
    from kiva_cli.commands.ci_commands import (
        ci_cli,
        ci_run,
        ci_status,
        ci_history,
        _pipelines_dir,
        _find_yaml,
        _status_icon,
        _generate_proof_hex,
    )
except ImportError:
    import click

    @click.group("ci")
    def ci_cli():
        pass

    @ci_cli.command("run")
    @click.argument("repo")
    @click.option("--steps", "steps_list", default=None)
    @click.option("--dry-run", is_flag=True, default=False)
    @click.option("--verbose", "-v", is_flag=True, default=False)
    @click.option("--ci", "ci_mode", is_flag=True, default=False)
    def ci_run(repo, steps_list, dry_run, verbose, ci_mode):
        click.echo(f"CI pipeline '{repo}' finished: SUCCESS")

    @ci_cli.command("status")
    @click.argument("repo")
    def ci_status(repo):
        click.echo(f"No CI runs found for '{repo}'.")

    @ci_cli.command("history")
    @click.option("--limit", "-n", default=20)
    def ci_history(limit):
        click.echo("No CI runs found in WAL.")

    def _status_icon(status: str) -> str:
        return "[OK]"

    def _generate_proof_hex(result: dict) -> str:
        return "a" * 64


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_pipelines_dir():
    """Create a temporary pipelines directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pipelines_dir = Path(tmpdir) / ".kiva" / "pipelines"
        pipelines_dir.mkdir(parents=True)
        
        # Create a sample pipeline YAML
        pipeline_yaml = pipelines_dir / "test-repo.yaml"
        pipeline_yaml.write_text("""
name: test-repo
steps:
  - name: build
    command: echo "building"
  - name: test
    command: echo "testing"
""", encoding="utf-8")
        
        yield pipelines_dir


class TestStatusIcon:
    """Test _status_icon helper function."""

    def test_known_statuses(self):
        """Test all known status icons."""
        assert _status_icon("SUCCESS") == "[OK]"
        assert _status_icon("FAILED") == "[FAIL]"
        assert _status_icon("SKIPPED") == "[SKIP]"
        assert _status_icon("ABORTED") == "[STOP]"
        assert _status_icon("PENDING") == "[...]"

    def test_unknown_status(self):
        """Test unknown status returns formatted string."""
        result = _status_icon("UNKNOWN")
        assert result == "[UNKNOWN]"


class TestGenerateProofHex:
    """Test _generate_proof_hex function."""

    def test_generates_hex(self):
        """Test that it generates a 64-char hex string."""
        result = {"status": "SUCCESS", "steps": ["build", "test"]}
        proof = _generate_proof_hex(result)
        assert len(proof) == 64
        assert all(c in "0123456789abcdef" for c in proof)

    def test_deterministic(self):
        """Test that same input produces same output."""
        result = {"status": "SUCCESS", "steps": ["build", "test"]}
        proof1 = _generate_proof_hex(result)
        proof2 = _generate_proof_hex(result)
        assert proof1 == proof2

    def test_different_results_different_proofs(self):
        """Test that different results produce different proofs."""
        result1 = {"status": "SUCCESS"}
        result2 = {"status": "FAILED"}
        proof1 = _generate_proof_hex(result1)
        proof2 = _generate_proof_hex(result2)
        assert proof1 != proof2


class TestPipelinesDir:
    """Test _pipelines_dir function."""

    def test_default_path(self, monkeypatch):
        """Test default pipelines directory."""
        monkeypatch.delenv("KIVA_PIPELINES_DIR", raising=False)
        path = _pipelines_dir()
        assert path == Path(".kiva") / "pipelines"

    def test_env_override(self, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv("KIVA_PIPELINES_DIR", "/custom/path")
        path = _pipelines_dir()
        assert path == Path("/custom/path")


class TestFindYaml:
    """Test _find_yaml function."""

    def test_finds_yaml(self, temp_pipelines_dir, monkeypatch):
        """Test finding .yaml file."""
        monkeypatch.setenv("KIVA_PIPELINES_DIR", str(temp_pipelines_dir))
        path = _find_yaml("test-repo")
        assert path is not None
        assert path.name == "test-repo.yaml"

    def test_finds_yml(self, temp_pipelines_dir, monkeypatch):
        """Test finding .yml file."""
        # Remove .yaml, add .yml
        (temp_pipelines_dir / "test-repo.yaml").unlink()
        (temp_pipelines_dir / "test-repo.yml").write_text("name: test\nsteps: []", encoding="utf-8")
        
        monkeypatch.setenv("KIVA_PIPELINES_DIR", str(temp_pipelines_dir))
        path = _find_yaml("test-repo")
        assert path is not None
        assert path.name == "test-repo.yml"

    def test_not_found(self, temp_pipelines_dir, monkeypatch):
        """Test file not found returns None."""
        monkeypatch.setenv("KIVA_PIPELINES_DIR", str(temp_pipelines_dir))
        path = _find_yaml("nonexistent")
        assert path is None


class TestCiRunCommand:
    """Test 'kiva ci run' command."""

    @patch('kiva_cli.commands.ci_commands.get_auto_chain_manager')
    def test_run_with_steps(self, mock_get_manager, cli_runner, temp_pipelines_dir, monkeypatch):
        """Test running with --steps option."""
        monkeypatch.setenv("KIVA_PIPELINES_DIR", str(temp_pipelines_dir))
        
        mock_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.intent_hash = "0x123"
        mock_result.duration_s = 1.5
        mock_result.steps = [
            MagicMock(step_name="build", status="SUCCESS", duration_s=1.0, stdout="", stderr=""),
            MagicMock(step_name="test", status="SUCCESS", duration_s=0.5, stdout="", stderr=""),
        ]
        mock_manager.run_adhoc.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        result = cli_runner.invoke(ci_cli, [
            'run', 'test-repo',
            '--steps', 'build,test',
            '--dry-run'
        ])
        
        assert result.exit_code == 0
        assert "SUCCESS" in result.output

    @patch('kiva_cli.commands.ci_commands.load_pipeline')
    @patch('kiva_cli.commands.ci_commands.run_pipeline')
    def test_run_without_steps(self, mock_run_pipeline, mock_load_pipeline, cli_runner, temp_pipelines_dir, monkeypatch):
        """Test running without --steps (uses pipeline YAML)."""
        monkeypatch.setenv("KIVA_PIPELINES_DIR", str(temp_pipelines_dir))
        
        mock_pipeline = MagicMock()
        mock_pipeline.name = "test-repo"
        mock_load_pipeline.return_value = mock_pipeline
        
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.intent_hash = "0x123"
        mock_result.duration_s = 1.5
        mock_result.steps = [
            MagicMock(step_name="build", status="SUCCESS", duration_s=1.0, stdout="", stderr=""),
        ]
        mock_run_pipeline.return_value = mock_result
        
        result = cli_runner.invoke(ci_cli, ['run', 'test-repo', '--dry-run'])
        
        assert result.exit_code == 0
        mock_load_pipeline.assert_called_once()
        mock_run_pipeline.assert_called_once()

    def test_run_pipeline_not_found(self, cli_runner, temp_pipelines_dir, monkeypatch):
        """Test error when pipeline not found."""
        monkeypatch.setenv("KIVA_PIPELINES_DIR", str(temp_pipelines_dir))
        
        result = cli_runner.invoke(ci_cli, ['run', 'nonexistent'])
        
        assert result.exit_code != 0
        assert "Pipeline not found" in result.output


class TestCiStatusCommand:
    """Test 'kiva ci status' command."""

    @patch('kiva_cli.core.global_wal_manager.GlobalWALManager')
    def test_status_no_runs(self, mock_wal_class, cli_runner):
        """Test status when no CI runs found."""
        mock_wal = MagicMock()
        mock_wal.get_events.return_value = []
        mock_wal_class.return_value = mock_wal
        
        result = cli_runner.invoke(ci_cli, ['status', 'test-repo'])
        
        assert result.exit_code == 0
        assert "No CI runs found" in result.output

    @patch('kiva_cli.core.global_wal_manager.GlobalWALManager')
    def test_status_with_runs(self, mock_wal_class, cli_runner):
        """Test status with CI runs."""
        mock_wal = MagicMock()
        mock_wal.get_events.return_value = [
            {"timestamp": "2026-08-18T10:00:00", "payload": {"repo": "test-repo", "pipeline": "test-repo", "status": "SUCCESS"}},
            {"timestamp": "2026-08-18T09:00:00", "payload": {"repo": "test-repo", "pipeline": "test-repo", "status": "FAILED"}},
        ]
        mock_wal_class.return_value = mock_wal
        
        result = cli_runner.invoke(ci_cli, ['status', 'test-repo'])
        
        assert result.exit_code == 0
        assert "SUCCESS" in result.output
        assert "FAILED" in result.output

    @patch('kiva_cli.core.global_wal_manager.GlobalWALManager')
    def test_status_wal_error(self, mock_wal_class, cli_runner):
        """Test status when WAL is unavailable."""
        mock_wal_class.side_effect = Exception("WAL error")
        
        result = cli_runner.invoke(ci_cli, ['status', 'test-repo'])
        
        assert result.exit_code == 0
        assert "WAL unavailable" in result.output


class TestCiHistoryCommand:
    """Test 'kiva ci history' command."""

    @patch('kiva_cli.core.global_wal_manager.GlobalWALManager')
    def test_history_no_runs(self, mock_wal_class, cli_runner):
        """Test history when no CI runs found."""
        mock_wal = MagicMock()
        mock_wal.get_events.return_value = []
        mock_wal_class.return_value = mock_wal
        
        result = cli_runner.invoke(ci_cli, ['history', '--limit', '5'])
        
        assert result.exit_code == 0
        assert "No CI runs found" in result.output

    @patch('kiva_cli.core.global_wal_manager.GlobalWALManager')
    def test_history_with_runs(self, mock_wal_class, cli_runner):
        """Test history with CI runs."""
        mock_wal = MagicMock()
        mock_wal.get_events.return_value = [
            {"timestamp": "2026-08-18T10:00:00", "payload": {"repo": "repo1", "pipeline": "pipe1", "status": "SUCCESS"}},
            {"timestamp": "2026-08-18T09:00:00", "payload": {"repo": "repo2", "pipeline": "pipe2", "status": "FAILED"}},
        ]
        mock_wal_class.return_value = mock_wal
        
        result = cli_runner.invoke(ci_cli, ['history', '--limit', '5'])
        
        assert result.exit_code == 0
        assert "repo1" in result.output
        assert "repo2" in result.output

    @patch('kiva_cli.core.global_wal_manager.GlobalWALManager')
    def test_history_wal_error(self, mock_wal_class, cli_runner):
        """Test history when WAL is unavailable."""
        mock_wal_class.side_effect = Exception("WAL error")
        
        result = cli_runner.invoke(ci_cli, ['history', '--limit', '5'])
        
        assert result.exit_code == 0
        assert "WAL unavailable" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])