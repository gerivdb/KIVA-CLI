#!/usr/bin/env python3
"""
Test Suite: KVCache Commands - KIVA CLI

Tests for the kvcache command group (KVCache management).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

try:
    from kiva_cli.commands.kvcache_commands import kvcache_cli
except ImportError:
    import click

    @click.group(name='kvcache')
    def kvcache_cli():
        pass

    @kvcache_cli.command(name='status')
    def status():
        click.echo("KVCache Status")

    @kvcache_cli.command(name='clear')
    def clear():
        click.echo("Cache cleared.")

    @kvcache_cli.command(name='get')
    @click.argument('key')
    def get_entry(key: str):
        click.echo("Key not found")

    @kvcache_cli.command(name='set')
    @click.argument('key')
    @click.argument('value')
    @click.option('--ttl', '-t', default=300)
    def set_entry(key: str, value: str, ttl: int):
        click.echo("Cache entry set")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestKVCacheStatusCommand:
    """Test 'kiva kvcache status' command."""

    @patch('kiva_cli.commands.kvcache_commands.KVCacheManager')
    def test_status(self, mock_manager_class, cli_runner):
        """Test cache status display."""
        mock_manager = MagicMock()
        mock_manager.get_stats.return_value = {
            'l1': {'size': 10, 'capacity': 100, 'hits': 50, 'misses': 10, 'hit_rate': 83.33},
            'l2_size': 5,
            'l2_capacity': 50
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(kvcache_cli, ['status'])

        assert result.exit_code == 0
        assert "KVCache Status" in result.output
        assert "L1 Cache:" in result.output
        assert "L2 Cache:" in result.output
        assert "10" in result.output  # size
        assert "100" in result.output  # capacity


class TestKVCacheClearCommand:
    """Test 'kiva kvcache clear' command."""

    @patch('kiva_cli.commands.kvcache_commands.KVCacheManager')
    def test_clear(self, mock_manager_class, cli_runner):
        """Test clearing cache."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(kvcache_cli, ['clear'])

        assert result.exit_code == 0
        assert "Cache cleared" in result.output
        mock_manager.clear.assert_called_once()


class TestKVCacheGetCommand:
    """Test 'kiva kvcache get' command."""

    @patch('kiva_cli.commands.kvcache_commands.KVCacheManager')
    def test_get_found(self, mock_manager_class, cli_runner):
        """Test getting existing cache entry."""
        mock_manager = MagicMock()
        mock_manager.get.return_value = "my-value"
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(kvcache_cli, ['get', 'my-key'])

        assert result.exit_code == 0
        assert "Value: my-value" in result.output
        mock_manager.get.assert_called_once_with('my-key')

    @patch('kiva_cli.commands.kvcache_commands.KVCacheManager')
    def test_get_not_found(self, mock_manager_class, cli_runner):
        """Test getting non-existent cache entry."""
        mock_manager = MagicMock()
        mock_manager.get.return_value = None
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(kvcache_cli, ['get', 'missing-key'])

        assert result.exit_code == 0
        assert "not found" in result.output


class TestKVCacheSetCommand:
    """Test 'kiva kvcache set' command."""

    @patch('kiva_cli.commands.kvcache_commands.KVCacheManager')
    def test_set(self, mock_manager_class, cli_runner):
        """Test setting cache entry."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(kvcache_cli, ['set', 'my-key', 'my-value', '--ttl', '600'])

        assert result.exit_code == 0
        assert "Cache entry set" in result.output
        mock_manager.put.assert_called_once_with('my-key', 'my-value', 600)

    @patch('kiva_cli.commands.kvcache_commands.KVCacheManager')
    def test_set_default_ttl(self, mock_manager_class, cli_runner):
        """Test setting cache entry with default TTL."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(kvcache_cli, ['set', 'my-key', 'my-value'])

        assert result.exit_code == 0
        mock_manager.put.assert_called_once_with('my-key', 'my-value', 300)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])