#!/usr/bin/env python3
"""
Test Suite: Entity Commands - KIVA CLI

Tests for the entity command group (entity path mapping utilities).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

try:
    from kiva_cli.commands.entity_commands import entity_cli
except ImportError:
    import click

    @click.group(name='entity')
    def entity_cli():
        pass

    @entity_cli.command(name='locate')
    @click.argument('citizen_id')
    @click.option('--repo', '-r', default=None)
    def locate_citizen(citizen_id: str, repo: str):
        click.echo(f"Local path: /path/to/{citizen_id}")

    @entity_cli.command(name='list')
    @click.option('--repo', '-r', default=None)
    def list_citizens(repo: str):
        click.echo("Citizens (0)")

    @entity_cli.command(name='sync')
    def sync_citizens():
        click.echo("Synced 0 citizens")

    @entity_cli.command(name='export')
    @click.option('--output', '-o', default=None)
    def export_registry(output: str):
        click.echo("{}")

@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestEntityLocateCommand:
    """Test 'kiva entity locate' command."""

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_locate_citizen_found(self, mock_mapper_class, cli_runner):
        """Test locating a citizen that exists."""
        mock_mapper = MagicMock()
        mock_mapper.locate_citizen.return_value = "/path/to/kiva-cli"
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['locate', 'kiva-cli'])

        assert result.exit_code == 0
        assert "Local path: /path/to/kiva-cli" in result.output
        mock_mapper.locate_citizen.assert_called_once_with('kiva-cli', None)

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_locate_citizen_with_repo(self, mock_mapper_class, cli_runner):
        """Test locating a citizen with repo filter."""
        mock_mapper = MagicMock()
        mock_mapper.locate_citizen.return_value = "/path/to/kiva-cli"
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['locate', 'kiva-cli', '--repo', 'KIVA-CLI'])

        assert result.exit_code == 0
        mock_mapper.locate_citizen.assert_called_once_with('kiva-cli', 'KIVA-CLI')

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_locate_citizen_not_found(self, mock_mapper_class, cli_runner):
        """Test locating a citizen that doesn't exist."""
        mock_mapper = MagicMock()
        mock_mapper.locate_citizen.return_value = None
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['locate', 'nonexistent'])

        assert result.exit_code == 0
        assert "No local path found for: nonexistent" in result.output


class TestEntityListCommand:
    """Test 'kiva entity list' command."""

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_list_citizens(self, mock_mapper_class, cli_runner):
        """Test listing citizens."""
        mock_citizen = MagicMock()
        mock_citizen.id = "kiva-cli"
        mock_citizen.slug = "kiva-cli"
        mock_citizen.role_type = "CLI"
        mock_citizen.tier = "L1-INFRA"
        mock_citizen.status = "ACTIVE"
        mock_citizen.repos_served = ["KIVA-CLI"]
        mock_citizen.local_paths = {"KIVA-CLI": "/path/to/kiva-cli"}

        mock_mapper = MagicMock()
        mock_mapper.list_citizens.return_value = [mock_citizen]
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['list'])

        assert result.exit_code == 0
        assert "Citizens (1)" in result.output
        assert "kiva-cli" in result.output
        assert "CLI" in result.output
        assert "L1-INFRA" in result.output
        assert "ACTIVE" in result.output

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_list_citizens_with_repo_filter(self, mock_mapper_class, cli_runner):
        """Test listing citizens with repo filter."""
        mock_mapper = MagicMock()
        mock_mapper.list_citizens.return_value = []
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['list', '--repo', 'KIVA-CLI'])

        assert result.exit_code == 0
        mock_mapper.list_citizens.assert_called_once_with('KIVA-CLI')

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_list_citizens_empty(self, mock_mapper_class, cli_runner):
        """Test listing citizens when none exist."""
        mock_mapper = MagicMock()
        mock_mapper.list_citizens.return_value = []
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['list'])

        assert result.exit_code == 0
        assert "Citizens (0)" in result.output


class TestEntitySyncCommand:
    """Test 'kiva entity sync' command."""

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_sync_citizens(self, mock_mapper_class, cli_runner):
        """Test syncing citizens."""
        mock_mapper = MagicMock()
        mock_mapper.sync_citizens.return_value = 5
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['sync'])

        assert result.exit_code == 0
        assert "Synced 5 citizens" in result.output
        mock_mapper.sync_citizens.assert_called_once()


class TestEntityExportCommand:
    """Test 'kiva entity export' command."""

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_export_registry_stdout(self, mock_mapper_class, cli_runner):
        """Test exporting registry to stdout."""
        mock_registry = {"citizens": [{"id": "kiva-cli", "slug": "kiva-cli"}]}
        mock_mapper = MagicMock()
        mock_mapper.export_registry.return_value = mock_registry
        mock_mapper_class.return_value = mock_mapper

        result = cli_runner.invoke(entity_cli, ['export'])

        assert result.exit_code == 0
        assert "kiva-cli" in result.output

    @patch('kiva_cli.commands.entity_commands.EntityPathMapper')
    def test_export_registry_to_file(self, mock_mapper_class, cli_runner):
        """Test exporting registry to file."""
        mock_registry = {"citizens": [{"id": "kiva-cli"}]}
        mock_mapper = MagicMock()
        mock_mapper.export_registry.return_value = mock_registry
        mock_mapper_class.return_value = mock_mapper

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "citizens.json"
            result = cli_runner.invoke(entity_cli, ['export', '-o', str(output_file)])

            assert result.exit_code == 0
            assert "Exported to:" in result.output
            assert output_file.exists()
            content = json.loads(output_file.read_text())
            assert content == mock_registry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])