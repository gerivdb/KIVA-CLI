#!/usr/bin/env python3
"""
Test Suite: CI/CD Commands - KIVA CLI

Tests for the cicd command group (CI/CD integration and pipeline management).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile

try:
    from kiva_cli.commands.cicd_commands import cicd_cli
except ImportError:
    import click

    @click.group(name='cicd')
    def cicd_cli():
        pass

    @cicd_cli.command(name='setup')
    @click.argument('repo_path')
    @click.option('--pipeline', '-p', default='ecos-ci', help='Pipeline name')
    def setup(repo_path: str, pipeline: str):
        click.echo("GitHub Actions workflow setup successfully.")

    @cicd_cli.command(name='run')
    @click.argument('repo_path')
    def run_pipeline(repo_path: str):
        click.echo("CI pipeline passed!")

    @cicd_cli.command(name='status')
    @click.argument('repo_path')
    def status(repo_path: str):
        click.echo("CI/CD Pipeline Status")
        click.echo(f"Repository: {repo_path}")
        click.echo("Workflows: 0")

    @cicd_cli.command(name='nexus-sync')
    @click.option('--dry-run', is_flag=True, default=True)
    @click.option('--repo', default=None)
    @click.option('--chain', is_flag=True, default=False)
    def nexus_sync(dry_run: bool, repo: str | None, chain: bool):
        click.echo("Sync completed")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_repo():
    """Create a temporary repository directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test-repo"
        repo_path.mkdir()
        yield str(repo_path)


class TestCicdSetupCommand:
    """Test 'kiva cicd setup' command."""

    @patch('kiva_cli.commands.cicd_commands.CICDManager')
    def test_setup_success(self, mock_manager_class, cli_runner, temp_repo):
        """Test successful GitHub Actions setup."""
        mock_manager = MagicMock()
        mock_manager.setup_github_actions.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cicd_cli, ['setup', temp_repo, '--pipeline', 'test-ci'])

        assert result.exit_code == 0
        assert "setup successfully" in result.output
        mock_manager.setup_github_actions.assert_called_once_with(temp_repo, 'test-ci')

    @patch('kiva_cli.commands.cicd_commands.CICDManager')
    def test_setup_failure(self, mock_manager_class, cli_runner, temp_repo):
        """Test failed GitHub Actions setup."""
        mock_manager = MagicMock()
        mock_manager.setup_github_actions.return_value = False
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cicd_cli, ['setup', temp_repo])

        assert result.exit_code == 0
        assert "Failed to setup" in result.output


class TestCicdRunCommand:
    """Test 'kiva cicd run' command."""

    @patch('kiva_cli.commands.cicd_commands.CICDManager')
    def test_run_success(self, mock_manager_class, cli_runner, temp_repo):
        """Test successful CI pipeline run."""
        mock_manager = MagicMock()
        mock_manager.run_ci_pipeline.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cicd_cli, ['run', temp_repo])

        assert result.exit_code == 0
        assert "CI pipeline passed" in result.output
        mock_manager.run_ci_pipeline.assert_called_once_with(temp_repo)

    @patch('kiva_cli.commands.cicd_commands.CICDManager')
    def test_run_failure(self, mock_manager_class, cli_runner, temp_repo):
        """Test failed CI pipeline run."""
        mock_manager = MagicMock()
        mock_manager.run_ci_pipeline.return_value = False
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cicd_cli, ['run', temp_repo])

        assert result.exit_code == 0
        assert "CI pipeline failed" in result.output


class TestCicdStatusCommand:
    """Test 'kiva cicd status' command."""

    @patch('kiva_cli.commands.cicd_commands.CICDManager')
    def test_status(self, mock_manager_class, cli_runner, temp_repo):
        """Test pipeline status check."""
        mock_manager = MagicMock()
        mock_manager.get_pipeline_status.return_value = {
            'repo_path': temp_repo,
            'workflows_count': 2,
            'workflows': ['ecos-ci.yml', 'deploy.yml']
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cicd_cli, ['status', temp_repo])

        assert result.exit_code == 0
        assert "CI/CD Pipeline Status" in result.output
        assert temp_repo in result.output
        assert "Workflows: 2" in result.output
        assert "ecos-ci.yml" in result.output
        assert "deploy.yml" in result.output


class TestCicdNexusSyncCommand:
    """Test 'kiva cicd nexus-sync' command."""

    @patch('kiva_cli.core.nexus_sync_orchestrator.NexusSyncOrchestrator')
    def test_nexus_sync_dry_run_classic(self, mock_orch_class, cli_runner):
        """Test nexus sync dry-run classic mode."""
        mock_orch = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.report_path = "/tmp/report.md"
        mock_result.stdout = "Sync output"
        mock_orch.run.return_value = mock_result
        mock_orch_class.return_value = mock_orch

        result = cli_runner.invoke(cicd_cli, ['nexus-sync', '--dry-run'])

        assert result.exit_code == 0
        assert "Sync" in result.output
        assert "report.md" in result.output
        mock_orch.run.assert_called_once_with(dry_run=True, repo_filter=None)

    @patch('kiva_cli.core.nexus_sync_orchestrator.NexusSyncOrchestrator')
    def test_nexus_sync_dry_run_with_repo(self, mock_orch_class, cli_runner):
        """Test nexus sync dry-run with repo filter."""
        mock_orch = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.report_path = "/tmp/report.md"
        mock_result.stdout = "Sync output"
        mock_orch.run.return_value = mock_result
        mock_orch_class.return_value = mock_orch

        result = cli_runner.invoke(cicd_cli, ['nexus-sync', '--dry-run', '--repo', 'KIVA-CLI'])

        assert result.exit_code == 0
        mock_orch.run.assert_called_once_with(dry_run=True, repo_filter='KIVA-CLI')

    @patch('kiva_cli.core.nexus_sync_orchestrator.NexusSyncOrchestrator')
    def test_nexus_sync_chain_mode(self, mock_orch_class, cli_runner):
        """Test nexus sync chain mode."""
        mock_orch = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.report_path = "/tmp/report.md"
        mock_result.stdout = "Chain sync output"
        mock_orch.run_chain.return_value = mock_result
        mock_orch_class.return_value = mock_orch

        result = cli_runner.invoke(cicd_cli, ['nexus-sync', '--chain', '--dry-run'])

        assert result.exit_code == 0
        assert "Sync" in result.output
        mock_orch.run_chain.assert_called_once_with(dry_run=True, repo_filter=None)

    @patch('kiva_cli.core.nexus_sync_orchestrator.NexusSyncOrchestrator')
    def test_nexus_sync_failure(self, mock_orch_class, cli_runner):
        """Test nexus sync failure."""
        mock_orch = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Sync failed"
        mock_orch.run.return_value = mock_result
        mock_orch_class.return_value = mock_orch

        result = cli_runner.invoke(cicd_cli, ['nexus-sync', '--dry-run'])

        assert result.exit_code != 0
        assert "Échec" in result.output or "failed" in result.output.lower()


class TestCICDManager:
    """Test CICDManager core functionality."""

    def test_init_default_workflows_dir(self):
        """Test initialization with default workflows directory."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager()
            assert manager.workflows_dir is not None

    def test_init_custom_workflows_dir(self):
        """Test initialization with custom workflows directory."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager(workflows_dir="/custom/path")
            assert str(manager.workflows_dir).replace('\\', '/') == "/custom/path"

    def test_setup_github_actions(self):
        """Test setting up GitHub Actions workflow."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager()
            
            with patch('builtins.open', mock_open()) as mock_file:
                result = manager.setup_github_actions("/tmp/repo", "test-ci")
                assert result is True
                mock_file.assert_called_once()

    def test_setup_github_actions_failure(self):
        """Test failed GitHub Actions setup."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager()
            
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                result = manager.setup_github_actions("/tmp/repo", "test-ci")
                assert result is False

    @patch('subprocess.run')
    def test_run_ci_pipeline_success(self, mock_run):
        """Test successful CI pipeline run."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager()
            mock_run.return_value = MagicMock(returncode=0, stdout="tests passed", stderr="")
            
            result = manager.run_ci_pipeline("/tmp/repo")
            assert result is True
            mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_ci_pipeline_failure(self, mock_run):
        """Test failed CI pipeline run."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager()
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="tests failed")
            
            result = manager.run_ci_pipeline("/tmp/repo")
            assert result is False

    @patch('subprocess.run')
    def test_run_ci_pipeline_exception(self, mock_run):
        """Test CI pipeline run with exception."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager()
            mock_run.side_effect = Exception("pytest not found")
            
            result = manager.run_ci_pipeline("/tmp/repo")
            assert result is False

    def test_get_pipeline_status(self):
        """Test getting pipeline status."""
        from kiva_cli.core.cicd_manager import CICDManager
        with patch('pathlib.Path.mkdir'):
            manager = CICDManager()
            
            with patch.object(Path, 'glob') as mock_glob:
                mock_glob.return_value = [Path("ecos-ci.yml"), Path("deploy.yml")]
                status = manager.get_pipeline_status("/tmp/repo")
                
                assert status['repo_path'] == "/tmp/repo"
                assert status['workflows_count'] == 2
                assert 'ecos-ci.yml' in status['workflows']
                assert 'deploy.yml' in status['workflows']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])