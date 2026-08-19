#!/usr/bin/env python3
"""
Test Suite: Autoscale Commands - KIVA CLI

Tests for the autoscale command group (scaling policies).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import json
import tempfile
import os
from pathlib import Path

try:
    from kiva_cli.commands.autoscale_commands import autoscale_cli
except ImportError:
    import click

    @click.group(name='autoscale')
    def autoscale_cli():
        pass

    @autoscale_cli.command(name='create')
    @click.argument('name')
    @click.option('--service', '-s', required=True, help='Target service')
    @click.option('--min', default=1, help='Min instances')
    @click.option('--max', default=10, help='Max instances')
    @click.option('--cpu-threshold', default=80, help='CPU threshold %')
    @click.option('--memory-threshold', default=85, help='Memory threshold %')
    def create_policy(name: str, service: str, min: int, max: int, cpu_threshold: int, memory_threshold: int):
        click.echo(f"Policy '{name}' created for {service}")

    @autoscale_cli.command(name='list')
    def list_policies():
        click.echo("Scaling Policies (0)")

    @autoscale_cli.command(name='delete')
    @click.argument('name')
    def delete_policy(name: str):
        click.echo(f"Policy '{name}' deleted.")

    @autoscale_cli.command(name='evaluate')
    @click.argument('name')
    @click.option('--cpu', default=50, help='Current CPU %')
    @click.option('--memory', default=50, help='Current Memory %')
    @click.option('--instances', default=1, help='Current instances')
    def evaluate_policy(name: str, cpu: int, memory: int, instances: int):
        click.echo(f"Policy Evaluation: {name}")
        click.echo(f"Action: none")
        click.echo(f"Reason: Policy not found")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_policies_file():
    """Create a temporary policies file for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kiva_autoscale_test_"))
    policies_file = temp_dir / "policies.json"
    policies_file.write_text(json.dumps({"policies": {}}), encoding="utf-8")
    yield str(policies_file)
    # Cleanup
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestAutoscaleCreateCommand:
    """Test 'kiva autoscale create' command."""

    def test_create_policy_basic(self, cli_runner, temp_policies_file):
        """Test creating a basic scaling policy."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, [
                'create', 'test-policy',
                '--service', 'api',
                '--min', '2',
                '--max', '20',
                '--cpu-threshold', '75',
                '--memory-threshold', '80'
            ])
            
            assert result.exit_code == 0
            assert "created for api" in result.output
            mock_mgr.create_policy.assert_called_once_with(
                'test-policy', 'api', 2, 20, 75, 80
            )

    def test_create_policy_defaults(self, cli_runner, temp_policies_file):
        """Test creating a policy with default values."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, [
                'create', 'default-policy',
                '--service', 'worker'
            ])
            
            assert result.exit_code == 0
            mock_mgr.create_policy.assert_called_once_with(
                'default-policy', 'worker', 1, 10, 80, 85
            )

    def test_create_policy_missing_service(self, cli_runner):
        """Test that --service is required."""
        result = cli_runner.invoke(autoscale_cli, ['create', 'no-service'])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "--service" in result.output


class TestAutoscaleListCommand:
    """Test 'kiva autoscale list' command."""

    def test_list_empty(self, cli_runner, temp_policies_file):
        """Test listing policies when none exist."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr.list_policies.return_value = []
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, ['list'])
            
            assert result.exit_code == 0
            assert "Scaling Policies (0)" in result.output

    def test_list_with_policies(self, cli_runner, temp_policies_file):
        """Test listing policies when some exist."""
        from kiva_cli.core.autoscaling_manager import ScalingPolicy
        
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            policy1 = ScalingPolicy({
                "name": "policy1",
                "service": "api",
                "min_instances": 1,
                "max_instances": 10,
                "cpu_threshold": 80,
                "memory_threshold": 85
            })
            policy2 = ScalingPolicy({
                "name": "policy2",
                "service": "worker",
                "min_instances": 2,
                "max_instances": 5,
                "cpu_threshold": 70,
                "memory_threshold": 75
            })
            mock_mgr.list_policies.return_value = [policy1, policy2]
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, ['list'])
            
            assert result.exit_code == 0
            assert "policy1" in result.output
            assert "policy2" in result.output
            assert "api" in result.output
            assert "worker" in result.output


class TestAutoscaleDeleteCommand:
    """Test 'kiva autoscale delete' command."""

    def test_delete_existing_policy(self, cli_runner, temp_policies_file):
        """Test deleting an existing policy."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr.delete_policy.return_value = True
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, ['delete', 'test-policy'])
            
            assert result.exit_code == 0
            assert "deleted" in result.output.lower()
            mock_mgr.delete_policy.assert_called_once_with('test-policy')

    def test_delete_nonexistent_policy(self, cli_runner, temp_policies_file):
        """Test deleting a non-existent policy."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr.delete_policy.return_value = False
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, ['delete', 'nonexistent'])
            
            assert result.exit_code == 0
            assert "not found" in result.output.lower()


class TestAutoscaleEvaluateCommand:
    """Test 'kiva autoscale evaluate' command."""

    def test_evaluate_nonexistent_policy(self, cli_runner, temp_policies_file):
        """Test evaluating a non-existent policy."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr.evaluate_policy.return_value = {
                "action": "none",
                "reason": "Policy not found"
            }
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, [
                'evaluate', 'nonexistent',
                '--cpu', '90',
                '--memory', '90',
                '--instances', '1'
            ])
            
            assert result.exit_code == 0
            assert "Policy not found" in result.output

    def test_evaluate_scale_up(self, cli_runner, temp_policies_file):
        """Test evaluating a policy that triggers scale up."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr.evaluate_policy.return_value = {
                "action": "scale_up",
                "current_instances": 1,
                "new_instances": 2,
                "reason": "CPU: 90%, Memory: 90% exceeded thresholds"
            }
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, [
                'evaluate', 'test-policy',
                '--cpu', '90',
                '--memory', '90',
                '--instances', '1'
            ])
            
            assert result.exit_code == 0
            assert "scale_up" in result.output
            assert "2" in result.output

    def test_evaluate_scale_down(self, cli_runner, temp_policies_file):
        """Test evaluating a policy that triggers scale down."""
        with patch('kiva_cli.commands.autoscale_commands.AutoScalingManager') as mock_mgr_class:
            mock_mgr = MagicMock()
            mock_mgr.evaluate_policy.return_value = {
                "action": "scale_down",
                "current_instances": 4,
                "new_instances": 2,
                "reason": "CPU: 20%, Memory: 20% below thresholds"
            }
            mock_mgr_class.return_value = mock_mgr
            
            result = cli_runner.invoke(autoscale_cli, [
                'evaluate', 'test-policy',
                '--cpu', '20',
                '--memory', '20',
                '--instances', '4'
            ])
            
            assert result.exit_code == 0
            assert "scale_down" in result.output
            assert "2" in result.output


class TestAutoscaleManager:
    """Test AutoScalingManager core functionality."""

    def test_create_and_list_policy(self, temp_policies_file):
        """Test creating and listing a policy through the manager."""
        from kiva_cli.core.autoscaling_manager import AutoScalingManager
        
        mgr = AutoScalingManager(policies_path=temp_policies_file)
        mgr.create_policy("test-policy", "api", 2, 20, 75, 80)
        
        policies = mgr.list_policies()
        assert len(policies) == 1
        assert policies[0].name == "test-policy"
        assert policies[0].service == "api"
        assert policies[0].min_instances == 2
        assert policies[0].max_instances == 20

    def test_delete_policy(self, temp_policies_file):
        """Test deleting a policy through the manager."""
        from kiva_cli.core.autoscaling_manager import AutoScalingManager
        
        mgr = AutoScalingManager(policies_path=temp_policies_file)
        mgr.create_policy("test-policy", "api", 1, 10, 80, 85)
        assert len(mgr.list_policies()) == 1
        
        result = mgr.delete_policy("test-policy")
        assert result is True
        assert len(mgr.list_policies()) == 0
        
        # Deleting again should return False
        result = mgr.delete_policy("test-policy")
        assert result is False

    def test_evaluate_policy_scale_up(self, temp_policies_file):
        """Test policy evaluation for scale up."""
        from kiva_cli.core.autoscaling_manager import AutoScalingManager
        
        mgr = AutoScalingManager(policies_path=temp_policies_file)
        mgr.create_policy("test-policy", "api", 1, 10, 80, 85)
        
        result = mgr.evaluate_policy("test-policy", 90, 90, 1)
        assert result["action"] == "scale_up"
        assert result["new_instances"] == 2

    def test_evaluate_policy_scale_down(self, temp_policies_file):
        """Test policy evaluation for scale down."""
        from kiva_cli.core.autoscaling_manager import AutoScalingManager
        import time
        
        mgr = AutoScalingManager(policies_path=temp_policies_file)
        mgr.create_policy("test-policy", "api", 1, 10, 80, 85)
        
        # Scale down directly without prior scale up (to avoid cooldown)
        result = mgr.evaluate_policy("test-policy", 20, 20, 2)
        assert result["action"] == "scale_down"
        assert result["new_instances"] == 1

    def test_evaluate_policy_cooldown(self, temp_policies_file):
        """Test policy evaluation respects cooldown."""
        from kiva_cli.core.autoscaling_manager import AutoScalingManager
        import time
        
        mgr = AutoScalingManager(policies_path=temp_policies_file)
        mgr.create_policy("test-policy", "api", 1, 10, 80, 85)
        
        # Scale up
        mgr.evaluate_policy("test-policy", 90, 90, 1)
        
        # Immediately try to scale up again - should be in cooldown
        result = mgr.evaluate_policy("test-policy", 95, 95, 2)
        assert result["action"] == "none"
        assert "Cooldown" in result["reason"]

    def test_evaluate_nonexistent_policy(self, temp_policies_file):
        """Test evaluating a non-existent policy."""
        from kiva_cli.core.autoscaling_manager import AutoScalingManager
        
        mgr = AutoScalingManager(policies_path=temp_policies_file)
        result = mgr.evaluate_policy("nonexistent", 90, 90, 1)
        assert result["action"] == "none"
        assert "Policy not found" in result["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])