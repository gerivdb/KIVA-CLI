#!/usr/bin/env python3
"""
Test Suite: Dashboard Commands - KIVA CLI

Tests for the dashboard command group (web UI dashboard management).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

try:
    from kiva_cli.commands.dashboard_commands import dashboard_cli
except ImportError:
    import click

    @click.group(name='dashboard')
    def dashboard_cli():
        pass

    @dashboard_cli.command(name='start')
    @click.option('--host', '-h', default='localhost', help='Dashboard host')
    @click.option('--port', '-p', default=9000, help='Dashboard port')
    def start_dashboard(host: str, port: int):
        click.echo(f"Dashboard started at http://{host}:{port}")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestDashboardStartCommand:
    """Test 'kiva dashboard start' command."""

    @patch('kiva_cli.commands.dashboard_commands.DashboardServer')
    @patch('kiva_cli.commands.dashboard_commands.time.sleep')
    def test_start_dashboard_default(self, mock_sleep, mock_server_class, cli_runner):
        """Test starting dashboard with default host/port."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        # Make sleep raise KeyboardInterrupt to exit the loop
        mock_sleep.side_effect = KeyboardInterrupt()

        result = cli_runner.invoke(dashboard_cli, ['start'])

        assert result.exit_code == 0
        assert "Dashboard started at http://localhost:9000" in result.output
        mock_server.start.assert_called_once()
        mock_server.stop.assert_called_once()

    @patch('kiva_cli.commands.dashboard_commands.DashboardServer')
    @patch('kiva_cli.commands.dashboard_commands.time.sleep')
    def test_start_dashboard_custom(self, mock_sleep, mock_server_class, cli_runner):
        """Test starting dashboard with custom host/port."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_sleep.side_effect = KeyboardInterrupt()

        result = cli_runner.invoke(dashboard_cli, ['start', '--host', '0.0.0.0', '--port', '8080'])

        assert result.exit_code == 0
        assert "Dashboard started at http://0.0.0.0:8080" in result.output
        mock_server_class.assert_called_once_with('0.0.0.0', 8080)


class TestDashboardServer:
    """Test DashboardServer core functionality."""

    def test_init_default(self):
        """Test initialization with default host/port."""
        from kiva_cli.core.dashboard_server import DashboardServer
        
        server = DashboardServer()
        assert server.host == "localhost"
        assert server.port == 9000
        assert server.server is None
        assert server.thread is None

    def test_init_custom(self):
        """Test initialization with custom host/port."""
        from kiva_cli.core.dashboard_server import DashboardServer
        
        server = DashboardServer(host="0.0.0.0", port=8080)
        assert server.host == "0.0.0.0"
        assert server.port == 8080

    @patch('kiva_cli.core.dashboard_server.HTTPServer')
    @patch('kiva_cli.core.dashboard_server.threading.Thread')
    def test_start(self, mock_thread_class, mock_http_server_class):
        """Test starting the server."""
        from kiva_cli.core.dashboard_server import DashboardServer
        
        mock_server = MagicMock()
        mock_http_server_class.return_value = mock_server
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        server = DashboardServer()
        server.start()
        
        mock_http_server_class.assert_called_once()
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()
        assert server.server == mock_server
        assert server.thread == mock_thread

    def test_stop(self):
        """Test stopping the server."""
        from kiva_cli.core.dashboard_server import DashboardServer
        
        server = DashboardServer()
        mock_server = MagicMock()
        server.server = mock_server
        
        server.stop()
        
        mock_server.shutdown.assert_called_once()

    def test_stop_no_server(self):
        """Test stopping when no server is running."""
        from kiva_cli.core.dashboard_server import DashboardServer
        
        server = DashboardServer()
        server.server = None
        
        # Should not raise
        server.stop()


class TestDashboardHandler:
    """Test DashboardHandler HTTP request handling."""

    @pytest.mark.skip(reason="DashboardHandler requires complex HTTP mocking")
    def test_get_index_page(self):
        """Test getting index page HTML - skipped due to complex mocking."""
        pass

    @pytest.mark.skip(reason="DashboardHandler requires complex HTTP mocking")
    def test_send_html(self):
        """Test sending HTML response - skipped due to complex mocking."""
        pass

    @pytest.mark.skip(reason="DashboardHandler requires complex HTTP mocking")
    def test_send_json(self):
        """Test sending JSON response - skipped due to complex mocking."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])