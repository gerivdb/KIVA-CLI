#!/usr/bin/env python3
"""
Test Suite: Context Commands - KIVA CLI

Tests for the context command group (active repository context management).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import json

try:
    from kiva_cli.commands.context_commands import context_cli
except ImportError:
    import click

    @click.group(name='context')
    def context_cli():
        pass

    @context_cli.command(name='set')
    @click.argument('repo_name')
    def set_context(repo_name: str):
        click.echo(f"Active repository set to: {repo_name}")

    @context_cli.command(name='get')
    def get_context():
        click.echo("Active repo:    Not set")

    @context_cli.command(name='detect')
    def detect_context():
        click.echo("No repository detected.")

    @context_cli.command(name='list')
    def list_contexts():
        click.echo("Available Repositories")

    @context_cli.command(name='clear')
    def clear_context():
        click.echo("Context cleared.")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_context_dir():
    """Create a temporary context config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".kiva"
        config_dir.mkdir()
        yield str(config_dir / "context.json")


class TestContextSetCommand:
    """Test 'kiva context set' command."""

    @patch('kiva_cli.commands.context_commands.ContextManager')
    @patch('kiva_cli.commands.context_commands.PathResolver')
    def test_set_valid_repo(self, mock_resolver_class, mock_manager_class, cli_runner):
        """Test setting a valid repository context."""
        mock_resolver = MagicMock()
        mock_resolver.repos = {"DevTools": MagicMock(), "KIVA-CLI": MagicMock()}
        mock_resolver_class.return_value = mock_resolver

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['set', 'DevTools'])

        assert result.exit_code == 0
        assert "Active repository set to: DevTools" in result.output
        mock_manager.set_active_repo.assert_called_once_with('DevTools')

    @patch('kiva_cli.commands.context_commands.ContextManager')
    @patch('kiva_cli.commands.context_commands.PathResolver')
    def test_set_invalid_repo(self, mock_resolver_class, mock_manager_class, cli_runner):
        """Test setting an invalid repository context."""
        mock_resolver = MagicMock()
        mock_resolver.repos = {"DevTools": MagicMock()}
        mock_resolver_class.return_value = mock_resolver

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['set', 'InvalidRepo'])

        assert result.exit_code == 0
        assert "Unknown repository: InvalidRepo" in result.output
        assert "DevTools" in result.output
        mock_manager.set_active_repo.assert_not_called()


class TestContextGetCommand:
    """Test 'kiva context get' command."""

    @patch('kiva_cli.commands.context_commands.ContextManager')
    def test_get_context(self, mock_manager_class, cli_runner):
        """Test getting current context."""
        mock_manager = MagicMock()
        mock_manager.get_context_summary.return_value = {
            'active_repo': 'DevTools',
            'last_path': '/path/to/repo',
            'last_command': 'kiva deploy',
            'detected_repo': 'DevTools'
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['get'])

        assert result.exit_code == 0
        assert "Current Context" in result.output
        assert "DevTools" in result.output
        assert "/path/to/repo" in result.output
        assert "kiva deploy" in result.output

    @patch('kiva_cli.commands.context_commands.ContextManager')
    def test_get_empty_context(self, mock_manager_class, cli_runner):
        """Test getting empty context."""
        mock_manager = MagicMock()
        mock_manager.get_context_summary.return_value = {
            'active_repo': None,
            'last_path': None,
            'last_command': None,
            'detected_repo': None
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['get'])

        assert result.exit_code == 0
        assert "Not set" in result.output
        assert "None" in result.output


class TestContextDetectCommand:
    """Test 'kiva context detect' command."""

    @patch('kiva_cli.commands.context_commands.ContextManager')
    def test_detect_found(self, mock_manager_class, cli_runner):
        """Test detecting repository."""
        mock_manager = MagicMock()
        mock_manager.detect_current_repo.return_value = 'DevTools'
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['detect'])

        assert result.exit_code == 0
        assert "Detected repository: DevTools" in result.output

    @patch('kiva_cli.commands.context_commands.ContextManager')
    def test_detect_not_found(self, mock_manager_class, cli_runner):
        """Test detecting no repository."""
        mock_manager = MagicMock()
        mock_manager.detect_current_repo.return_value = None
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['detect'])

        assert result.exit_code == 0
        assert "No repository detected" in result.output


class TestContextListCommand:
    """Test 'kiva context list' command."""

    @patch('kiva_cli.commands.context_commands.ContextManager')
    @patch('kiva_cli.commands.context_commands.PathResolver')
    def test_list_contexts(self, mock_resolver_class, mock_manager_class, cli_runner):
        """Test listing available repositories."""
        mock_repo1 = MagicMock()
        mock_repo1.local_path = "/path/to/DevTools"
        mock_repo1.remote_url = "https://github.com/gerivdb/DevTools.git"

        mock_repo2 = MagicMock()
        mock_repo2.local_path = "/path/to/KIVA-CLI"
        mock_repo2.remote_url = "https://github.com/gerivdb/KIVA-CLI.git"

        mock_resolver = MagicMock()
        mock_resolver.repos = {"DevTools": mock_repo1, "KIVA-CLI": mock_repo2}
        mock_resolver_class.return_value = mock_resolver

        mock_manager = MagicMock()
        mock_manager.get_active_repo.return_value = "DevTools"
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['list'])

        assert result.exit_code == 0
        assert "Available Repositories" in result.output
        assert "DevTools" in result.output
        assert "KIVA-CLI" in result.output
        assert "(active)" in result.output
        assert "/path/to/DevTools" in result.output
        assert "github.com/gerivdb/DevTools" in result.output


class TestContextClearCommand:
    """Test 'kiva context clear' command."""

    @patch('kiva_cli.commands.context_commands.ContextManager')
    def test_clear_context(self, mock_manager_class, cli_runner):
        """Test clearing context."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(context_cli, ['clear'])

        assert result.exit_code == 0
        assert "Context cleared" in result.output
        mock_manager.clear_context.assert_called_once()


class TestContextManager:
    """Test ContextManager core functionality."""

    def test_init_default_config_path(self):
        """Test initialization with default config path."""
        from kiva_cli.core.context_manager import ContextManager
        with patch('pathlib.Path.exists', return_value=False):
            manager = ContextManager()
            assert manager.config_path is not None

    def test_init_custom_config_path(self):
        """Test initialization with custom config path."""
        from kiva_cli.core.context_manager import ContextManager
        with patch('pathlib.Path.exists', return_value=False):
            manager = ContextManager(config_path="/custom/path/context.json")
            assert manager.config_path == "/custom/path/context.json"

    def test_set_get_active_repo(self, temp_context_dir):
        """Test setting and getting active repo."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        manager.set_active_repo("DevTools")
        assert manager.get_active_repo() == "DevTools"

    def test_clear_context(self, temp_context_dir):
        """Test clearing context."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        manager.set_active_repo("DevTools")
        manager.clear_context()
        assert manager.get_active_repo() is None

    def test_set_get_last_path(self, temp_context_dir):
        """Test setting and getting last path."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        manager.set_last_path("/some/path")
        assert manager.get_last_path() == "/some/path"

    def test_set_get_last_command(self, temp_context_dir):
        """Test setting and getting last command."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        manager.set_last_command("kiva deploy")
        assert manager.get_last_command() == "kiva deploy"

    def test_persistence(self, temp_context_dir):
        """Test context persistence across instances."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager1 = ContextManager(config_path=temp_context_dir)
        manager1.set_active_repo("DevTools")
        manager1.set_last_path("/path")
        
        manager2 = ContextManager(config_path=temp_context_dir)
        assert manager2.get_active_repo() == "DevTools"
        assert manager2.get_last_path() == "/path"

    def test_load_existing_config(self, temp_context_dir):
        """Test loading existing config file."""
        from kiva_cli.core.context_manager import ContextManager
        
        # Create config file
        config = {"active_repo": "DevTools", "last_path": "/path", "last_command": "cmd"}
        Path(temp_context_dir).write_text(json.dumps(config))
        
        manager = ContextManager(config_path=temp_context_dir)
        assert manager.get_active_repo() == "DevTools"
        assert manager.get_last_path() == "/path"
        assert manager.get_last_command() == "cmd"

    @patch('subprocess.run')
    def test_detect_current_repo_git_success(self, mock_run, temp_context_dir):
        """Test detecting repo from git remote URL."""
        from kiva_cli.core.context_manager import ContextManager
        
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/DevTools\n"),
            MagicMock(returncode=0, stdout="https://github.com/gerivdb/DevTools.git\n"),
        ]
        
        manager = ContextManager(config_path=temp_context_dir)
        repo = manager.detect_current_repo()
        
        assert repo == "DevTools"

    @patch('subprocess.run')
    def test_detect_current_repo_git_fallback_dir_name(self, mock_run, temp_context_dir):
        """Test detecting repo from directory name when no remote."""
        from kiva_cli.core.context_manager import ContextManager
        
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/MyRepo\n"),
            MagicMock(returncode=1, stdout="", stderr=""),
        ]
        
        manager = ContextManager(config_path=temp_context_dir)
        repo = manager.detect_current_repo()
        
        assert repo == "MyRepo"

    @patch('subprocess.run')
    def test_detect_current_repo_git_failure(self, mock_run, temp_context_dir):
        """Test detecting repo fails gracefully."""
        from kiva_cli.core.context_manager import ContextManager
        
        mock_run.side_effect = FileNotFoundError("git not found")
        
        manager = ContextManager(config_path=temp_context_dir)
        repo = manager.detect_current_repo()
        
        assert repo is None

    def test_get_context_summary(self, temp_context_dir):
        """Test getting context summary."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        manager.set_active_repo("DevTools")
        
        with patch.object(manager, 'detect_current_repo', return_value="DevTools"):
            summary = manager.get_context_summary()
            assert summary['active_repo'] == "DevTools"
            assert summary['detected_repo'] == "DevTools"

    def test_resolve_path_with_context_absolute(self, temp_context_dir):
        """Test resolving absolute path."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        mock_resolver = MagicMock()
        
        result = manager.resolve_path_with_context("/absolute/path", mock_resolver)
        assert result == "/absolute/path"

    def test_resolve_path_with_context_relative(self, temp_context_dir):
        """Test resolving relative path with active repo."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        manager.set_active_repo("DevTools")
        
        mock_repo = MagicMock()
        mock_repo.local_path = Path("/base/DevTools")
        
        mock_resolver = MagicMock()
        mock_resolver.repos = {"DevTools": mock_repo}
        
        result = manager.resolve_path_with_context("relative/path", mock_resolver)
        assert result.replace('\\', '/') == "/base/DevTools/relative/path"

    def test_resolve_path_with_context_no_active_repo(self, temp_context_dir):
        """Test resolving relative path without active repo."""
        from kiva_cli.core.context_manager import ContextManager
        
        manager = ContextManager(config_path=temp_context_dir)
        mock_resolver = MagicMock()
        mock_resolver.repos = {}
        
        result = manager.resolve_path_with_context("relative/path", mock_resolver)
        assert result == "relative/path"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])