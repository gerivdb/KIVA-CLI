#!/usr/bin/env python3
"""
Test Suite: Service Commands - KIVA CLI

Tests for the service command group (service discovery and management).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

try:
    from kiva_cli.commands.service_commands import service_cli
except ImportError:
    import click

    @click.group(name='service')
    def service_cli():
        pass

    @service_cli.command(name='register')
    @click.argument('name')
    @click.option('--host', '-h', default='localhost')
    @click.option('--port', '-p', required=True, type=int)
    @click.option('--protocol', default='http')
    def register(name: str, host: str, port: int, protocol: str):
        click.echo("Service registered")

    @service_cli.command(name='discover')
    @click.argument('name')
    def discover(name: str):
        click.echo("Service discovered")

    @service_cli.command(name='list')
    def list_services():
        click.echo("Registered Services")

    @service_cli.command(name='deregister')
    @click.argument('name')
    def deregister(name: str):
        click.echo("Service deregistered")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestServiceRegisterCommand:
    """Test 'kiva service register' command."""

    @patch('kiva_cli.commands.service_commands.ServiceDiscovery')
    def test_register_success(self, mock_sd_class, cli_runner):
        """Test registering a service successfully."""
        mock_sd = MagicMock()
        mock_sd.register_service.return_value = True
        mock_sd_class.return_value = mock_sd

        result = cli_runner.invoke(service_cli, ['register', 'my-api', '--port', '8080'])

        assert result.exit_code == 0
        assert "registered at localhost:8080" in result.output
        mock_sd.register_service.assert_called_once_with('my-api', 'localhost', 8080, 'http')

    @patch('kiva_cli.commands.service_commands.ServiceDiscovery')
    def test_register_failure(self, mock_sd_class, cli_runner):
        """Test registering a service failure."""
        mock_sd = MagicMock()
        mock_sd.register_service.return_value = False
        mock_sd_class.return_value = mock_sd

        result = cli_runner.invoke(service_cli, ['register', 'my-api', '--port', '8080'])

        assert result.exit_code == 0
        assert "Failed to register" in result.output


class TestServiceDiscoverCommand:
    """Test 'kiva service discover' command."""

    @patch('kiva_cli.commands.service_commands.ServiceDiscovery')
    def test_discover_found(self, mock_sd_class, cli_runner):
        """Test discovering an existing service."""
        mock_service = MagicMock()
        mock_service.get_url.return_value = "http://localhost:8080"
        mock_service.status = "healthy"
        mock_service.last_heartbeat = "2026-01-01T00:00:00"

        mock_sd = MagicMock()
        mock_sd.discover_service.return_value = mock_service
        mock_sd_class.return_value = mock_sd

        result = cli_runner.invoke(service_cli, ['discover', 'my-api'])

        assert result.exit_code == 0
        assert "Service: my-api" in result.output
        assert "http://localhost:8080" in result.output
        assert "healthy" in result.output

    @patch('kiva_cli.commands.service_commands.ServiceDiscovery')
    def test_discover_not_found(self, mock_sd_class, cli_runner):
        """Test discovering non-existent service."""
        mock_sd = MagicMock()
        mock_sd.discover_service.return_value = None
        mock_sd_class.return_value = mock_sd

        result = cli_runner.invoke(service_cli, ['discover', 'nonexistent'])

        assert result.exit_code == 0
        assert "not found" in result.output


class TestServiceListCommand:
    """Test 'kiva service list' command."""

    @patch('kiva_cli.commands.service_commands.ServiceDiscovery')
    def test_list_services(self, mock_sd_class, cli_runner):
        """Test listing services."""
        mock_service1 = MagicMock()
        mock_service1.name = "api-1"
        mock_service1.get_url.return_value = "http://localhost:8080"
        mock_service1.status = "healthy"

        mock_service2 = MagicMock()
        mock_service2.name = "api-2"
        mock_service2.get_url.return_value = "http://localhost:8081"
        mock_service2.status = "unhealthy"

        mock_sd = MagicMock()
        mock_sd.list_services.return_value = [mock_service1, mock_service2]
        mock_sd_class.return_value = mock_sd

        result = cli_runner.invoke(service_cli, ['list'])

        assert result.exit_code == 0
        assert "Registered Services (2)" in result.output
        assert "api-1" in result.output
        assert "api-2" in result.output


class TestServiceDeregisterCommand:
    """Test 'kiva service deregister' command."""

    @patch('kiva_cli.commands.service_commands.ServiceDiscovery')
    def test_deregister_success(self, mock_sd_class, cli_runner):
        """Test deregistering a service."""
        mock_sd = MagicMock()
        mock_sd.deregister_service.return_value = True
        mock_sd_class.return_value = mock_sd

        result = cli_runner.invoke(service_cli, ['deregister', 'my-api'])

        assert result.exit_code == 0
        assert "deregistered" in result.output
        mock_sd.deregister_service.assert_called_once_with('my-api')

    @patch('kiva_cli.commands.service_commands.ServiceDiscovery')
    def test_deregister_not_found(self, mock_sd_class, cli_runner):
        """Test deregistering non-existent service."""
        mock_sd = MagicMock()
        mock_sd.deregister_service.return_value = False
        mock_sd_class.return_value = mock_sd

        result = cli_runner.invoke(service_cli, ['deregister', 'nonexistent'])

        assert result.exit_code == 0
        assert "not found" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])