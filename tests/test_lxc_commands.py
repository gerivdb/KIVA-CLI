#!/usr/bin/env python3
"""
Test Suite: LXC Commands - KIVA CLI

Tests for the lxc command group (LXC/LXD container management).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

try:
    from kiva_cli.commands.lxc_commands import lxc_cli
except ImportError:
    import click

    @click.group(name='lxc')
    def lxc_cli():
        pass

    @lxc_cli.command(name='create')
    @click.argument('name')
    @click.option('--image', '-i', default='ubuntu:22.04')
    @click.option('--cpu', default=2)
    @click.option('--memory', default='4GB')
    @click.option('--storage', default='20GB')
    def create_container(name: str, image: str, cpu: int, memory: str, storage: str):
        click.echo(f"Container '{name}' created")

    @lxc_cli.command(name='start')
    @click.argument('name')
    def start_container(name: str):
        click.echo(f"Container '{name}' started")

    @lxc_cli.command(name='stop')
    @click.argument('name')
    def stop_container(name: str):
        click.echo(f"Container '{name}' stopped")

    @lxc_cli.command(name='delete')
    @click.argument('name')
    def delete_container(name: str):
        click.echo(f"Container '{name}' deleted")

    @lxc_cli.command(name='list')
    def list_containers():
        click.echo("LXC Containers (0)")

    @lxc_cli.command(name='status')
    @click.argument('name', required=False)
    def container_status(name: str):
        click.echo("LXC Overview")

    @lxc_cli.command(name='exec')
    @click.argument('name')
    @click.argument('command')
    @click.option('--user', '-u', default='root')
    def exec_container(name: str, command: str, user: str):
        click.echo("Exec")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestLXCCreateCommand:
    """Test 'kiva lxc create' command."""

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_create_container_success(self, mock_manager_class, cli_runner):
        """Test creating a container successfully."""
        mock_manager = MagicMock()
        mock_manager.create_container.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['create', 'my-container', '--image', 'ubuntu:22.04'])

        assert result.exit_code == 0
        assert "created with image ubuntu:22.04" in result.output
        mock_manager.create_container.assert_called_once_with('my-container', 'ubuntu:22.04', 2, '4GB', '20GB')

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_create_container_exists(self, mock_manager_class, cli_runner):
        """Test creating a container that already exists."""
        mock_manager = MagicMock()
        mock_manager.create_container.return_value = False
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['create', 'my-container'])

        assert result.exit_code == 0
        assert "already exists" in result.output

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_create_container_custom_options(self, mock_manager_class, cli_runner):
        """Test creating a container with custom options."""
        mock_manager = MagicMock()
        mock_manager.create_container.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, [
            'create', 'custom-container',
            '--image', 'debian:11',
            '--cpu', '4',
            '--memory', '8GB',
            '--storage', '50GB'
        ])

        assert result.exit_code == 0
        mock_manager.create_container.assert_called_once_with('custom-container', 'debian:11', 4, '8GB', '50GB')


class TestLXCStartCommand:
    """Test 'kiva lxc start' command."""

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_start_container_success(self, mock_manager_class, cli_runner):
        """Test starting a container."""
        mock_manager = MagicMock()
        mock_manager.start_container.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['start', 'my-container'])

        assert result.exit_code == 0
        assert "started" in result.output
        mock_manager.start_container.assert_called_once_with('my-container')

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_start_container_not_found(self, mock_manager_class, cli_runner):
        """Test starting non-existent container."""
        mock_manager = MagicMock()
        mock_manager.start_container.return_value = False
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['start', 'nonexistent'])

        assert result.exit_code == 0
        assert "not found" in result.output


class TestLXCStopCommand:
    """Test 'kiva lxc stop' command."""

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_stop_container_success(self, mock_manager_class, cli_runner):
        """Test stopping a container."""
        mock_manager = MagicMock()
        mock_manager.stop_container.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['stop', 'my-container'])

        assert result.exit_code == 0
        assert "stopped" in result.output
        mock_manager.stop_container.assert_called_once_with('my-container')


class TestLXCDeleteCommand:
    """Test 'kiva lxc delete' command."""

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_delete_container_success(self, mock_manager_class, cli_runner):
        """Test deleting a container."""
        mock_manager = MagicMock()
        mock_manager.delete_container.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['delete', 'my-container'])

        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_manager.delete_container.assert_called_once_with('my-container')


class TestLXCListCommand:
    """Test 'kiva lxc list' command."""

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_list_containers(self, mock_manager_class, cli_runner):
        """Test listing containers."""
        mock_container1 = MagicMock()
        mock_container1.name = "container1"
        mock_container1.image = "ubuntu:22.04"
        mock_container1.status = "running"
        mock_container1.ip_address = "10.0.0.1"
        mock_container1.cpu = 2
        mock_container1.memory = "4GB"
        mock_container1.storage = "20GB"

        mock_container2 = MagicMock()
        mock_container2.name = "container2"
        mock_container2.image = "debian:11"
        mock_container2.status = "stopped"
        mock_container2.ip_address = None
        mock_container2.cpu = 1
        mock_container2.memory = "2GB"
        mock_container2.storage = "10GB"

        mock_manager = MagicMock()
        mock_manager.list_containers.return_value = [mock_container1, mock_container2]
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['list'])

        assert result.exit_code == 0
        assert "LXC Containers (2)" in result.output
        assert "container1" in result.output
        assert "container2" in result.output
        assert "running" in result.output
        assert "stopped" in result.output


class TestLXCStatusCommand:
    """Test 'kiva lxc status' command."""

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_status_specific_container(self, mock_manager_class, cli_runner):
        """Test checking status of specific container."""
        mock_container = MagicMock()
        mock_container.image = "ubuntu:22.04"
        mock_container.status = "running"
        mock_container.cpu = 2
        mock_container.memory = "4GB"
        mock_container.storage = "20GB"
        mock_container.ip_address = "10.0.0.1"

        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = mock_container
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['status', 'my-container'])

        assert result.exit_code == 0
        assert "Container: my-container" in result.output
        assert "ubuntu:22.04" in result.output
        assert "running" in result.output

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_status_not_found(self, mock_manager_class, cli_runner):
        """Test status for non-existent container."""
        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = None
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['status', 'nonexistent'])

        assert result.exit_code == 0
        assert "not found" in result.output

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_status_all_containers(self, mock_manager_class, cli_runner):
        """Test status overview for all containers."""
        mock_manager = MagicMock()
        mock_manager.get_all_status.return_value = {
            'total_containers': 3,
            'running_containers': 2,
            'stopped_containers': 1
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['status'])

        assert result.exit_code == 0
        assert "LXC Overview" in result.output
        assert "Total: 3" in result.output
        assert "Running: 2" in result.output
        assert "Stopped: 1" in result.output


class TestLXCExecCommand:
    """Test 'kiva lxc exec' command."""

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_exec_container_not_found(self, mock_manager_class, cli_runner):
        """Test executing in non-existent container."""
        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = None
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['exec', 'nonexistent', 'echo hello'])

        assert result.exit_code == 0
        assert "not found" in result.output

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    def test_exec_container_not_running(self, mock_manager_class, cli_runner):
        """Test executing in stopped container."""
        mock_container = MagicMock()
        mock_container.status = "stopped"

        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = mock_container
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(lxc_cli, ['exec', 'stopped-container', 'echo hello'])

        assert result.exit_code == 0
        assert "not running" in result.output

    @patch('kiva_cli.commands.lxc_commands.LXCManager')
    @patch('subprocess.run')
    def test_exec_atomic_container(self, mock_subprocess, mock_manager_class, cli_runner):
        """Test executing in atomic-container (WSL)."""
        mock_container = MagicMock()
        mock_container.status = "running"

        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = mock_container
        mock_manager_class.return_value = mock_manager

        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="hello\n",
            stderr=""
        )

        result = cli_runner.invoke(lxc_cli, ['exec', 'atomic-container', 'echo hello'])

        assert result.exit_code == 0
        assert "hello" in result.output
        assert "successfully" in result.output
        mock_subprocess.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])