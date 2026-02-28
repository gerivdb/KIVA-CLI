"""
Integration tests for EcosGateway
Tests CLI delegation, discovery, and health checks
"""
import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch
from tooling.ecos_cli.core.gateway import EcosGateway

@pytest.fixture
def gateway():
    """Create EcosGateway instance"""
    return EcosGateway()

@pytest.fixture
def mock_wal_manager():
    """Mock WAL Manager"""
    wal = Mock()
    wal.append_event = Mock()
    return wal

def test_delegation_map(gateway):
    """Test delegation map contains expected mappings"""
    assert gateway.DELEGATION_MAP["project"] == "kiva"
    assert gateway.DELEGATION_MAP["deploy"] == "kiva"
    assert gateway.DELEGATION_MAP["config"] == "kiva"
    assert gateway.DELEGATION_MAP["rollback"] == "kiva"
    
    # Future delegations
    assert gateway.DELEGATION_MAP["workflow"] == "fluence"
    assert gateway.DELEGATION_MAP["pattern"] == "brain"

def test_cli_discovery(gateway):
    """Test CLI executable discovery"""
    cli_paths = gateway.cli_paths
    
    assert isinstance(cli_paths, dict)
    assert "kiva" in cli_paths
    assert "brain" in cli_paths
    assert "fluence" in cli_paths
    assert "devtools" in cli_paths

def test_delegate_unknown_command(gateway):
    """Test delegation with unknown command"""
    result = gateway.delegate("nonexistent", ["arg1"])
    
    assert result["status"] == "UNKNOWN_COMMAND"
    assert "nonexistent" in result["command"]
    assert "available" in result

def test_delegate_cli_not_found(gateway):
    """Test delegation when CLI not found"""
    # Mock cli_paths to simulate missing CLI
    gateway.cli_paths["kiva"] = None
    
    result = gateway.delegate("project", ["init", "test"])
    
    assert result["status"] == "CLI_NOT_FOUND"
    assert result["target_cli"] == "kiva"

@patch('subprocess.run')
def test_delegate_successful_execution(mock_run, gateway, mock_wal_manager):
    """Test successful command delegation"""
    # Mock subprocess result
    mock_run.return_value = Mock(
        returncode=0,
        stdout='{"status": "SUCCESS"}',
        stderr=""
    )
    
    # Set valid CLI path
    gateway.cli_paths["kiva"] = Path("/usr/bin/kiva")
    gateway.wal_manager = mock_wal_manager
    
    result = gateway.delegate("project", ["init", "myapp"])
    
    assert result["status"] == "SUCCESS"
    assert result["target_cli"] == "kiva"
    assert result["command"] == "project"
    
    # Verify WAL logging
    mock_wal_manager.append_event.assert_called_once()

@patch('subprocess.run')
def test_delegate_failed_execution(mock_run, gateway):
    """Test failed command delegation"""
    mock_run.return_value = Mock(
        returncode=1,
        stdout="",
        stderr="Error: Invalid template"
    )
    
    gateway.cli_paths["kiva"] = Path("/usr/bin/kiva")
    
    result = gateway.delegate("project", ["init", "test", "--template", "invalid"])
    
    assert result["status"] == "FAILED"
    assert result["return_code"] == 1
    assert "stderr" in result

@patch('subprocess.run')
def test_delegate_timeout(mock_run, gateway):
    """Test command timeout"""
    import subprocess
    mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
    
    gateway.cli_paths["kiva"] = Path("/usr/bin/kiva")
    
    result = gateway.delegate("deploy", ["./project"], timeout=30)
    
    assert result["status"] == "TIMEOUT"
    assert result["timeout"] == 30

@patch('subprocess.run')
def test_delegate_python_script(mock_run, gateway):
    """Test delegation to Python script (.py)"""
    mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
    
    gateway.cli_paths["kiva"] = Path("/path/to/kiva.py")
    
    result = gateway.delegate("config", ["kiva.yaml"])
    
    # Verify Python interpreter used
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == sys.executable
    assert str(call_args[1]).endswith("kiva.py")

def test_health_check(gateway):
    """Test health check for all CLIs"""
    result = gateway.health_check()
    
    assert "timestamp" in result
    assert "cli_status" in result
    assert "total_available" in result
    
    # Check individual CLI statuses
    for cli_name in ["kiva", "brain", "fluence", "devtools"]:
        assert cli_name in result["cli_status"]
        status = result["cli_status"][cli_name]
        assert "status" in status
        assert "available" in status

@patch('subprocess.run')
def test_health_check_healthy_cli(mock_run, gateway):
    """Test health check with healthy CLI"""
    mock_run.return_value = Mock(
        returncode=0,
        stdout="kiva-cli version 1.0.0",
        stderr=""
    )
    
    gateway.cli_paths["kiva"] = Path("/usr/bin/kiva")
    
    result = gateway.health_check()
    
    kiva_status = result["cli_status"]["kiva"]
    assert kiva_status["status"] == "HEALTHY"
    assert kiva_status["available"] is True
    assert "version" in kiva_status

def test_integration_example():
    """Test integration example provided in docstring"""
    # Simulate ECOS CLI integration
    gateway = EcosGateway()
    
    # Check delegation map
    command = "project"
    assert command in gateway.DELEGATION_MAP
    target_cli = gateway.DELEGATION_MAP[command]
    assert target_cli == "kiva"
