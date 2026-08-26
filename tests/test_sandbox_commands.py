#!/usr/bin/env python3
"""
Test Suite: Sandbox Commands - KIVA CLI

Tests for the sandbox command group (OpenSandbox secure execution).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

try:
    from kiva_cli.commands.sandbox_commands import sandbox_cli
except ImportError:
    import click

    @click.group(name='sandbox')
    def sandbox_cli():
        pass

    @sandbox_cli.command(name='exec')
    @click.argument('script_path')
    @click.option('--timeout', '-t', default=60)
    def exec_script(script_path: str, timeout: int):
        click.echo("Sandbox Execution")

    @sandbox_cli.command(name='cmd')
    @click.argument('command')
    @click.option('--args', '-a', multiple=True)
    @click.option('--timeout', '-t', default=30)
    def exec_command(command: str, args: tuple, timeout: int):
        click.echo("Sandbox Command")

    @sandbox_cli.command(name='status')
    def sandbox_status():
        click.echo("OpenSandbox Status")

    @sandbox_cli.command(name='clean')
    def sandbox_clean():
        click.echo("Sandbox cleaned up.")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestSandboxExecCommand:
    """Test 'kiva sandbox exec' command."""

    @patch('kiva_cli.commands.sandbox_commands.OpenSandboxManager')
    def test_exec_script_success(self, mock_manager_class, cli_runner):
        """Test executing a script successfully."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.exit_code = 0
        mock_result.stdout = "Hello World"
        mock_result.stderr = ""

        mock_manager = MagicMock()
        mock_manager.execute_script.return_value = mock_result
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(sandbox_cli, ['exec', 'C:\\scripts\\test.ps1', '--timeout', '60'])

        assert result.exit_code == 0
        assert "Sandbox Execution" in result.output
        assert "Success: Yes" in result.output
        assert "Exit Code: 0" in result.output
        assert "Hello World" in result.output
        mock_manager.execute_script.assert_called_once_with('C:\\scripts\\test.ps1', 60)

    @patch('kiva_cli.commands.sandbox_commands.OpenSandboxManager')
    def test_exec_script_failure(self, mock_manager_class, cli_runner):
        """Test executing a script that fails."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.exit_code = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: script failed"

        mock_manager = MagicMock()
        mock_manager.execute_script.return_value = mock_result
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(sandbox_cli, ['exec', 'C:\\scripts\\bad.ps1'])

        assert result.exit_code == 0
        assert "Success: No" in result.output
        assert "Error: script failed" in result.output


class TestSandboxCmdCommand:
    """Test 'kiva sandbox cmd' command."""

    @patch('kiva_cli.commands.sandbox_commands.OpenSandboxManager')
    def test_exec_command(self, mock_manager_class, cli_runner):
        """Test executing a command."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.exit_code = 0
        mock_result.stdout = "Python 3.12.7"
        mock_result.stderr = ""

        mock_manager = MagicMock()
        mock_manager.execute_command.return_value = mock_result
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(sandbox_cli, ['cmd', 'python', '--args', '--version'])

        assert result.exit_code == 0
        assert "Sandbox Command" in result.output
        assert "Success: Yes" in result.output
        mock_manager.execute_command.assert_called_once_with('python', ['--version'], 30)


class TestSandboxStatusCommand:
    """Test 'kiva sandbox status' command."""

    @patch('kiva_cli.commands.sandbox_commands.OpenSandboxManager')
    def test_status(self, mock_manager_class, cli_runner):
        """Test sandbox status."""
        mock_manager = MagicMock()
        mock_manager.get_stats.return_value = {
            'sandbox_dir': 'C:\\Temp\\sandbox',
            'executions': 42
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(sandbox_cli, ['status'])

        assert result.exit_code == 0
        assert "OpenSandbox Status" in result.output
        assert "Sandbox Dir:" in result.output
        assert "Executions: 42" in result.output


class TestSandboxCleanCommand:
    """Test 'kiva sandbox clean' command."""

    @patch('kiva_cli.commands.sandbox_commands.OpenSandboxManager')
    def test_clean(self, mock_manager_class, cli_runner):
        """Test sandbox cleanup."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(sandbox_cli, ['clean'])

        assert result.exit_code == 0
        assert "Sandbox cleaned up" in result.output
        mock_manager.cleanup.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])