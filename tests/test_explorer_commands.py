#!/usr/bin/env python3
"""
Test Suite: Explorer Commands - KIVA CLI

Tests for the explorer command group (Windows Explorer integration).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import sys

try:
    from kiva_cli.commands.explorer_commands import explorer_cli, _open_explorer, _copy_to_clipboard
except ImportError:
    import click

    @click.group(name='explorer')
    def explorer_cli():
        pass

    @explorer_cli.command(name='open')
    @click.argument('path', default='.')
    def open_explorer(path: str):
        click.echo(f"Opened Explorer at: {path}")

    @explorer_cli.command(name='select')
    @click.argument('file_path')
    def select_file(file_path: str):
        click.echo(f"Selected file in Explorer: {file_path}")

    @explorer_cli.command(name='copy-path')
    @click.argument('path', default='.')
    @click.option('--remote', '-r', is_flag=True)
    def copy_path(path: str, remote: bool):
        click.echo(f"Copied to clipboard: {path}")

    @explorer_cli.command(name='convert')
    @click.argument('path')
    @click.option('--to', '-t', 'target_format', default='auto')
    def convert_and_copy(path: str, target_format: str):
        click.echo(f"Converted and copied: {path}")

    def _open_explorer(path: str):
        return True

    def _copy_to_clipboard(text: str):
        return True


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestOpenExplorerHelper:
    """Test _open_explorer helper function."""

    @patch('sys.platform', 'win32')
    @patch('os.startfile')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=False)
    def test_open_explorer_directory(self, mock_is_file, mock_exists, mock_startfile):
        """Test opening a directory in Explorer."""
        result = _open_explorer("C:\\DevTools")
        assert result is True
        mock_startfile.assert_called_once()

    @patch('sys.platform', 'linux')
    def test_open_explorer_non_windows(self):
        """Test that non-Windows returns False."""
        result = _open_explorer("/path")
        assert result is False

    @patch('sys.platform', 'win32')
    @patch('pathlib.Path.exists', return_value=False)
    def test_open_explorer_not_exists(self, mock_exists):
        """Test opening non-existent path."""
        result = _open_explorer("C:\\NonExistent")
        assert result is False


class TestCopyToClipboardHelper:
    """Test _copy_to_clipboard helper function."""

    @patch('sys.platform', 'win32')
    @patch('subprocess.run')
    def test_copy_to_clipboard_success(self, mock_run):
        """Test successful clipboard copy."""
        mock_run.return_value = MagicMock(returncode=0)
        result = _copy_to_clipboard("test text")
        assert result is True
        mock_run.assert_called_once()

    @patch('sys.platform', 'linux')
    def test_copy_to_clipboard_non_windows(self):
        """Test that non-Windows returns False."""
        result = _copy_to_clipboard("test")
        assert result is False

    @patch('sys.platform', 'win32')
    @patch('subprocess.run')
    def test_copy_to_clipboard_failure(self, mock_run):
        """Test clipboard copy failure."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "clip")
        result = _copy_to_clipboard("test")
        assert result is False


class TestExplorerOpenCommand:
    """Test 'kiva explorer open' command."""

    @patch('kiva_cli.commands.explorer_commands._open_explorer')
    def test_open_explorer_default_path(self, mock_open, cli_runner):
        """Test open with default path."""
        mock_open.return_value = True
        result = cli_runner.invoke(explorer_cli, ['open'])
        assert result.exit_code == 0
        assert "Opened Explorer at: ." in result.output
        mock_open.assert_called_once_with('.')

    @patch('kiva_cli.commands.explorer_commands._open_explorer')
    def test_open_explorer_custom_path(self, mock_open, cli_runner):
        """Test open with custom path."""
        mock_open.return_value = True
        result = cli_runner.invoke(explorer_cli, ['open', 'C:\\DevTools\\bin'])
        assert result.exit_code == 0
        assert "Opened Explorer at: C:\\DevTools\\bin" in result.output
        mock_open.assert_called_once_with('C:\\DevTools\\bin')


class TestExplorerSelectCommand:
    """Test 'kiva explorer select' command."""

    @patch('kiva_cli.commands.explorer_commands._open_explorer')
    def test_select_file(self, mock_open, cli_runner):
        """Test selecting a file."""
        mock_open.return_value = True
        result = cli_runner.invoke(explorer_cli, ['select', 'C:\\file.txt'])
        assert result.exit_code == 0
        assert "Selected file in Explorer: C:\\file.txt" in result.output


class TestExplorerCopyPathCommand:
    """Test 'kiva explorer copy-path' command."""

    @patch('kiva_cli.core.path_resolver.PathResolver')
    @patch('kiva_cli.commands.explorer_commands._copy_to_clipboard')
    def test_copy_path_local(self, mock_copy, mock_resolver_class, cli_runner):
        """Test copying local path."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = {'local': 'C:\\DevTools', 'remote': None}
        mock_resolver_class.return_value = mock_resolver
        mock_copy.return_value = True

        result = cli_runner.invoke(explorer_cli, ['copy-path'])
        assert result.exit_code == 0
        assert "Copied to clipboard:" in result.output

    @patch('kiva_cli.core.path_resolver.PathResolver')
    @patch('kiva_cli.commands.explorer_commands._copy_to_clipboard')
    def test_copy_path_remote(self, mock_copy, mock_resolver_class, cli_runner):
        """Test copying remote path."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = {'local': 'C:\\DevTools', 'remote': 'gerivdb/DevTools'}
        mock_resolver_class.return_value = mock_resolver
        mock_copy.return_value = True

        result = cli_runner.invoke(explorer_cli, ['copy-path', '--remote'])
        assert result.exit_code == 0
        assert "gerivdb/DevTools" in result.output


class TestExplorerConvertCommand:
    """Test 'kiva explorer convert' command."""

    @patch('kiva_cli.core.path_resolver.PathResolver')
    @patch('kiva_cli.commands.explorer_commands._copy_to_clipboard')
    def test_convert_and_copy(self, mock_copy, mock_resolver_class, cli_runner):
        """Test converting and copying path."""
        mock_resolver = MagicMock()
        mock_resolver.convert_path.return_value = 'gerivdb/DevTools'
        mock_resolver_class.return_value = mock_resolver
        mock_copy.return_value = True

        result = cli_runner.invoke(explorer_cli, ['convert', 'C:\\DevTools'])
        assert result.exit_code == 0
        assert "Converted and copied:" in result.output

    @patch('kiva_cli.core.path_resolver.PathResolver')
    def test_convert_same_path(self, mock_resolver_class, cli_runner):
        """Test when conversion returns same path."""
        mock_resolver = MagicMock()
        mock_resolver.convert_path.return_value = 'C:\\DevTools'
        mock_resolver_class.return_value = mock_resolver

        result = cli_runner.invoke(explorer_cli, ['convert', 'C:\\DevTools'])
        assert result.exit_code == 0
        assert "Could not convert" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])