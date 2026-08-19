#!/usr/bin/env python3
"""
Test Suite: Cluster Commands - KIVA CLI

Tests for the cluster command group (multi-host cluster management).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import json

try:
    from kiva_cli.commands.cluster_commands import cluster_cli
except ImportError:
    import click

    @click.group(name='cluster')
    def cluster_cli():
        pass

    @cluster_cli.command(name='init')
    @click.argument('cluster_name')
    @click.option('--master-host', '-h', required=True)
    @click.option('--master-port', '-p', default=8080)
    def init_cluster(cluster_name: str, master_host: str, master_port: int):
        click.echo(f"Cluster '{cluster_name}' initialized with master at {master_host}:{master_port}")

    @cluster_cli.command(name='join')
    @click.argument('node_id')
    @click.option('--host', '-h', required=True)
    @click.option('--port', '-p', default=8080)
    @click.option('--role', default='worker')
    def join_cluster(node_id: str, host: str, port: int, role: str):
        click.echo(f"Node '{node_id}' joined the cluster.")

    @cluster_cli.command(name='leave')
    @click.argument('node_id')
    def leave_cluster(node_id: str):
        click.echo(f"Node '{node_id}' left the cluster.")

    @cluster_cli.command(name='list')
    def list_nodes():
        click.echo("Cluster Nodes (0)")

    @cluster_cli.command(name='status')
    def cluster_status():
        click.echo("Cluster Status")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_cluster_dir():
    """Create a temporary cluster directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cluster_dir = Path(tmpdir) / "cluster"
        cluster_dir.mkdir()
        yield str(cluster_dir)


class TestClusterInitCommand:
    """Test 'kiva cluster init' command."""

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_init_cluster(self, mock_manager_class, cli_runner):
        """Test cluster initialization."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, [
            'init', 'test-cluster',
            '--master-host', '192.168.1.100',
            '--master-port', '8080'
        ])

        assert result.exit_code == 0
        assert "test-cluster" in result.output
        assert "192.168.1.100" in result.output
        assert "8080" in result.output
        mock_manager.init_cluster.assert_called_once_with('test-cluster', '192.168.1.100', 8080)

    def test_init_cluster_missing_host(self, cli_runner):
        """Test init requires master-host."""
        result = cli_runner.invoke(cluster_cli, ['init', 'test-cluster'])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "--master-host" in result.output


class TestClusterJoinCommand:
    """Test 'kiva cluster join' command."""

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_join_success(self, mock_manager_class, cli_runner):
        """Test successful node join."""
        mock_manager = MagicMock()
        mock_manager.join_cluster.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, [
            'join', 'node-2',
            '--host', '192.168.1.101',
            '--port', '8080',
            '--role', 'worker'
        ])

        assert result.exit_code == 0
        assert "joined the cluster" in result.output
        mock_manager.join_cluster.assert_called_once_with('node-2', '192.168.1.101', 8080, 'worker')

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_join_already_exists(self, mock_manager_class, cli_runner):
        """Test joining existing node."""
        mock_manager = MagicMock()
        mock_manager.join_cluster.return_value = False
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, [
            'join', 'node-2',
            '--host', '192.168.1.101'
        ])

        assert result.exit_code == 0
        assert "already exists" in result.output

    def test_join_missing_host(self, cli_runner):
        """Test join requires host."""
        result = cli_runner.invoke(cluster_cli, ['join', 'node-2'])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "--host" in result.output


class TestClusterLeaveCommand:
    """Test 'kiva cluster leave' command."""

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_leave_success(self, mock_manager_class, cli_runner):
        """Test successful node leave."""
        mock_manager = MagicMock()
        mock_manager.leave_cluster.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, ['leave', 'node-2'])

        assert result.exit_code == 0
        assert "left the cluster" in result.output
        mock_manager.leave_cluster.assert_called_once_with('node-2')

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_leave_not_found(self, mock_manager_class, cli_runner):
        """Test leaving non-existent node."""
        mock_manager = MagicMock()
        mock_manager.leave_cluster.return_value = False
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, ['leave', 'nonexistent'])

        assert result.exit_code == 0
        assert "not found or is master" in result.output


class TestClusterListCommand:
    """Test 'kiva cluster list' command."""

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_list_empty(self, mock_manager_class, cli_runner):
        """Test listing empty cluster."""
        mock_manager = MagicMock()
        mock_manager.list_nodes.return_value = []
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, ['list'])

        assert result.exit_code == 0
        assert "Cluster Nodes (0)" in result.output

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_list_with_nodes(self, mock_manager_class, cli_runner):
        """Test listing cluster with nodes."""
        from kiva_cli.core.cluster_manager import ClusterNode
        
        mock_manager = MagicMock()
        node1 = ClusterNode({"id": "master", "host": "192.168.1.100", "port": 8080, "role": "master", "status": "active"})
        node2 = ClusterNode({"id": "node-1", "host": "192.168.1.101", "port": 8080, "role": "worker", "status": "active"})
        mock_manager.list_nodes.return_value = [node1, node2]
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, ['list'])

        assert result.exit_code == 0
        assert "Cluster Nodes (2)" in result.output
        assert "master" in result.output
        assert "node-1" in result.output


class TestClusterStatusCommand:
    """Test 'kiva cluster status' command."""

    @patch('kiva_cli.commands.cluster_commands.ClusterManager')
    def test_status(self, mock_manager_class, cli_runner):
        """Test cluster status check."""
        mock_manager = MagicMock()
        mock_manager.get_cluster_status.return_value = {
            'cluster_name': 'test-cluster',
            'total_nodes': 3,
            'active_nodes': 2
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(cluster_cli, ['status'])

        assert result.exit_code == 0
        assert "Cluster Status" in result.output
        assert "test-cluster" in result.output
        assert "Total Nodes: 3" in result.output
        assert "Active Nodes: 2" in result.output


class TestClusterManager:
    """Test ClusterManager core functionality."""

    def test_init_default_dir(self):
        """Test initialization with default directory."""
        from kiva_cli.core.cluster_manager import ClusterManager
        with patch('pathlib.Path.mkdir'):
            manager = ClusterManager()
            assert manager.cluster_dir is not None

    def test_init_custom_dir(self):
        """Test initialization with custom directory."""
        from kiva_cli.core.cluster_manager import ClusterManager
        with patch('pathlib.Path.mkdir'):
            manager = ClusterManager(cluster_dir="/custom/path")
            assert str(manager.cluster_dir).replace('\\', '/') == "/custom/path"

    def test_init_cluster(self, temp_cluster_dir):
        """Test cluster initialization."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        result = manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        
        assert result is True
        assert manager.cluster_name == "test-cluster"
        assert "master" in manager.nodes
        assert manager.nodes["master"].host == "192.168.1.100"
        assert manager.nodes["master"].port == 8080
        assert manager.nodes["master"].role == "master"

    def test_join_cluster(self, temp_cluster_dir):
        """Test joining node to cluster."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        
        result = manager.join_cluster("node-1", "192.168.1.101", 8080, "worker")
        assert result is True
        assert "node-1" in manager.nodes
        assert manager.nodes["node-1"].role == "worker"

    def test_join_existing_node(self, temp_cluster_dir):
        """Test joining existing node returns False."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        manager.join_cluster("node-1", "192.168.1.101", 8080, "worker")
        
        result = manager.join_cluster("node-1", "192.168.1.101", 8080, "worker")
        assert result is False

    def test_leave_cluster(self, temp_cluster_dir):
        """Test leaving cluster."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        manager.join_cluster("node-1", "192.168.1.101", 8080, "worker")
        
        result = manager.leave_cluster("node-1")
        assert result is True
        assert "node-1" not in manager.nodes

    def test_leave_master_node(self, temp_cluster_dir):
        """Test leaving master node returns False."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        
        result = manager.leave_cluster("master")
        assert result is False
        assert "master" in manager.nodes

    def test_leave_nonexistent_node(self, temp_cluster_dir):
        """Test leaving non-existent node returns False."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        
        result = manager.leave_cluster("nonexistent")
        assert result is False

    def test_list_nodes(self, temp_cluster_dir):
        """Test listing nodes."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        manager.join_cluster("node-1", "192.168.1.101", 8080, "worker")
        
        nodes = manager.list_nodes()
        assert len(nodes) == 2
        assert any(n.id == "master" for n in nodes)
        assert any(n.id == "node-1" for n in nodes)

    def test_get_cluster_status(self, temp_cluster_dir):
        """Test getting cluster status."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        manager = ClusterManager(cluster_dir=temp_cluster_dir)
        manager.init_cluster("test-cluster", "192.168.1.100", 8080)
        manager.join_cluster("node-1", "192.168.1.101", 8080, "worker")
        
        status = manager.get_cluster_status()
        assert status['cluster_name'] == "test-cluster"
        assert status['total_nodes'] == 2
        assert status['active_nodes'] == 2

    def test_persistence(self, temp_cluster_dir):
        """Test cluster state persistence."""
        from kiva_cli.core.cluster_manager import ClusterManager
        
        # First manager creates cluster
        manager1 = ClusterManager(cluster_dir=temp_cluster_dir)
        manager1.init_cluster("test-cluster", "192.168.1.100", 8080)
        manager1.join_cluster("node-1", "192.168.1.101", 8080, "worker")
        
        # Second manager loads cluster
        manager2 = ClusterManager(cluster_dir=temp_cluster_dir)
        assert manager2.cluster_name == "test-cluster"
        assert "master" in manager2.nodes
        assert "node-1" in manager2.nodes


class TestClusterNode:
    """Test ClusterNode data class."""

    def test_node_creation(self):
        """Test ClusterNode creation."""
        from kiva_cli.core.cluster_manager import ClusterNode
        
        node = ClusterNode({"id": "node-1", "host": "192.168.1.101", "port": 8080, "role": "worker", "status": "active"})
        
        assert node.id == "node-1"
        assert node.host == "192.168.1.101"
        assert node.port == 8080
        assert node.role == "worker"
        assert node.status == "active"

    def test_node_to_dict(self):
        """Test ClusterNode to_dict."""
        from kiva_cli.core.cluster_manager import ClusterNode
        
        node = ClusterNode({"id": "node-1", "host": "192.168.1.101", "port": 8080, "role": "worker", "status": "active"})
        data = node.to_dict()
        
        assert data['id'] == "node-1"
        assert data['host'] == "192.168.1.101"
        assert data['port'] == 8080
        assert data['role'] == "worker"
        assert data['status'] == "active"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])