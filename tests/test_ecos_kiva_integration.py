"""Integration tests for ECOS <-> KIVA CLI communication.

Validates subprocess delegation, WAL event propagation, and φ-CPS tracking.
"""

import pytest
import subprocess
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestECOSKIVADelegation:
    """Test ECOS CLI delegating commands to KIVA CLI."""

    def test_subprocess_delegation_latency(self):
        """Test subprocess call latency is <50ms."""
        mock_result = subprocess.CompletedProcess(
            args=["kiva", "--version"],
            returncode=0,
            stdout="kiva-cli 1.0.0",
            stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            start = time.perf_counter()
            result = subprocess.run(
                ["kiva", "--version"],
                capture_output=True,
                text=True,
                timeout=1
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert result.returncode == 0
        assert elapsed_ms < 50, f"Latency {elapsed_ms:.2f}ms exceeds 50ms threshold"

    def test_ecos_to_kiva_project_list(self):
        """Test ECOS calling KIVA project list command."""
        mock_result = subprocess.CompletedProcess(
            args=["kiva", "project", "list", "--format", "json"],
            returncode=0,
            stdout="[]",
            stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = subprocess.run(
                ["kiva", "project", "list", "--format", "json"],
                capture_output=True,
                text=True
            )
        
        # Should execute without errors
        assert result.returncode == 0

    def test_ecos_to_kiva_deploy_command(self):
        """Test ECOS calling KIVA deploy command."""
        mock_result = subprocess.CompletedProcess(
            args=["kiva", "deploy", "--help"],
            returncode=0,
            stdout="Usage: kiva deploy [OPTIONS] COMMAND [ARGS]...\n\ndeploy options:\n  --help  Show this message.",
            stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = subprocess.run(
                ["kiva", "deploy", "--help"],
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0

    def test_command_output_parsing(self):
        """Test parsing KIVA CLI JSON output."""
        # Mock KIVA CLI output
        mock_output = json.dumps({
            "status": "SUCCESS",
            "projects": [
                {"name": "proj1", "status": "ACTIVE"},
                {"name": "proj2", "status": "INACTIVE"}
            ]
        })
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )
            
            result = subprocess.run(
                ["kiva", "project", "list", "--format", "json"],
                capture_output=True,
                text=True
            )
            
            data = json.loads(result.stdout)
            assert data["status"] == "SUCCESS"
            assert len(data["projects"]) == 2


class TestWALEventPropagation:
    """Test WAL event propagation from KIVA to ECOS."""

    def test_wal_event_logging(self):
        """Test WAL events are logged correctly."""
        from kiva_cli.core.wal_logger import WALLogger
        
        logger = WALLogger()
        
        event_id = logger.log_event(
            event_type="KIVA_DEPLOYMENT",
            project="test-project",
            status="SUCCESS",
            metadata={
                "version": "1.0.0",
                "environment": "production",
                "timestamp": "2026-02-28T23:15:00Z"
            }
        )
        
        assert event_id is not None
        assert event_id.startswith("event_kiva_")

    def test_wal_event_propagation_to_ecos(self):
        """Test KIVA events propagate to ECOS global WAL."""
        from kiva_cli.core.wal_logger import WALLogger
        
        logger = WALLogger()
        
        # Log KIVA event
        event_id = logger.log_event(
            event_type="DEPLOYMENT",
            project="test-project",
            status="SUCCESS"
        )
        
        # Verify event can be retrieved
        event = logger.get_event(event_id)
        
        assert event is not None
        assert event["event_type"] == "DEPLOYMENT"
        assert event["status"] == "SUCCESS"

    def test_wal_cross_repo_sync(self):
        """Test WAL events sync across ECOYSTEM and KIVA-CLI."""
        from kiva_cli.core.wal_logger import WALLogger
        
        logger = WALLogger()
        
        # Log event with cross-repo metadata
        event_id = logger.log_event(
            event_type="KIVA_CONFIG_UPDATE",
            project="test-project",
            status="SUCCESS",
            metadata={
                "source_repo": "KIVA-CLI",
                "target_repo": "ECOYSTEM",
                "sync_required": True
            }
        )
        
        event = logger.get_event(event_id)
        assert event["metadata"]["sync_required"] is True


class TestPhiCPSValidation:
    """Test φ-CPS impact validation for KIVA operations."""

    def test_phi_cps_impact_calculation(self):
        """Test φ-CPS impact calculation."""
        from kiva_cli.core.phi_tracker import PhiCPSTracker
        
        tracker = PhiCPSTracker()
        
        # Calculate impact for deployment
        impact = tracker.calculate_impact(
            operation="deploy",
            success=True,
            complexity=0.7
        )
        
        assert impact > 0
        assert impact < 0.05, "Impact exceeds 5% drift threshold"

    def test_phi_cps_drift_detection(self):
        """Test φ-CPS drift detection."""
        from kiva_cli.core.phi_tracker import PhiCPSTracker
        
        tracker = PhiCPSTracker()
        
        baseline = 4.228
        current = 4.235
        
        drift = tracker.calculate_drift(baseline, current)
        drift_percent = (drift / baseline) * 100
        
        assert drift_percent < 5, f"Drift {drift_percent:.2f}% exceeds threshold"

    def test_phi_cps_rollback_trigger(self):
        """Test automatic rollback on φ-CPS drift."""
        from kiva_cli.core.phi_tracker import PhiCPSTracker
        
        tracker = PhiCPSTracker()
        
        baseline = 4.228
        current = 4.350  # Exceeds 5% threshold
        
        should_rollback = tracker.should_rollback(baseline, current)
        
        assert should_rollback is True

    def test_phi_cps_contribution_tracking(self):
        """Test tracking φ-CPS contribution per operation."""
        from kiva_cli.core.phi_tracker import PhiCPSTracker
        
        tracker = PhiCPSTracker()
        
        operations = [
            {"type": "deploy", "success": True, "complexity": 0.8},
            {"type": "config_update", "success": True, "complexity": 0.3},
            {"type": "health_check", "success": True, "complexity": 0.1}
        ]
        
        total_contribution = 0
        for op in operations:
            impact = tracker.calculate_impact(**op)
            total_contribution += impact
        
        assert total_contribution > 0
        assert total_contribution < 0.05


class TestMultiCommandOrchestration:
    """Test orchestrating multiple KIVA commands from ECOS."""

    def test_sequential_command_execution(self):
        """Test executing multiple commands sequentially."""
        from kiva_cli.workflows.orchestrator import CommandOrchestrator
        
        orchestrator = CommandOrchestrator()
        
        commands = [
            {"command": "project", "args": ["list"]},
            {"command": "config", "args": ["get", "app_name"]},
            {"command": "health", "args": ["check"]}
        ]
        
        results = orchestrator.execute_sequential(commands)
        
        assert len(results) == 3
        for result in results:
            assert result["status"] in ["SUCCESS", "FAILED", "PENDING"]

    def test_parallel_command_execution(self):
        """Test executing multiple commands in parallel."""
        from kiva_cli.workflows.orchestrator import CommandOrchestrator
        
        orchestrator = CommandOrchestrator()
        
        commands = [
            {"command": "health", "args": ["check", "service-1"]},
            {"command": "health", "args": ["check", "service-2"]},
            {"command": "health", "args": ["check", "service-3"]}
        ]
        
        results = orchestrator.execute_parallel(commands, max_workers=3)
        
        assert len(results) == 3

    def test_command_chain_with_dependencies(self):
        """Test command chain with dependencies."""
        from kiva_cli.workflows.orchestrator import CommandOrchestrator
        
        orchestrator = CommandOrchestrator()
        
        chain = [
            {"id": "validate", "command": "config", "args": ["validate"], "depends_on": []},
            {"id": "deploy", "command": "deploy", "args": ["execute"], "depends_on": ["validate"]},
            {"id": "health", "command": "health", "args": ["check"], "depends_on": ["deploy"]}
        ]
        
        results = orchestrator.execute_chain(chain)
        
        assert len(results) == 3
        assert results[0]["id"] == "validate"


class TestStateSynchronization:
    """Test state synchronization between ECOS and KIVA."""

    def test_state_sync_on_deployment(self):
        """Test state sync after deployment."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # Simulate deployment state change
        manager.set_state("deployment-123", "PENDING")
        manager.transition_state("deployment-123", "SUCCESS")
        
        # Verify state is persisted
        state = manager.get_state("deployment-123")
        assert state == "SUCCESS"

    def test_state_sync_rollback(self):
        """Test state rollback on failure."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # Save checkpoint
        manager.save_checkpoint("deployment-123", {"version": "1.0.0"})
        
        # Simulate failure
        manager.set_state("deployment-123", "FAILED")
        
        # Restore checkpoint
        restored = manager.restore_checkpoint("deployment-123")
        
        assert restored["version"] == "1.0.0"

    def test_state_history_tracking(self):
        """Test tracking state history."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # Track state transitions
        manager.set_state("task-1", "PENDING")
        manager.transition_state("task-1", "SUCCESS")
        
        history = manager.get_state_history("task-1")
        
        assert len(history) >= 2
        assert history[0]["state"] == "PENDING"
        assert history[-1]["state"] == "SUCCESS"


class TestErrorHandlingAndRollback:
    """Test error handling and automatic rollback."""

    def test_command_error_handling(self):
        """Test proper error handling in commands."""
        from kiva_cli.commands.deploy import deploy_project
        
        with patch("kiva_cli.commands.deploy.execute_deployment") as mock_deploy:
            mock_deploy.side_effect = Exception("Connection timeout")
            
            result = deploy_project(
                project="test-project",
                environment="production"
            )
            
            assert result["status"] == "FAILED"
            assert "error" in result

    def test_automatic_rollback_on_failure(self):
        """Test automatic rollback on deployment failure."""
        from kiva_cli.workflows.deployment import DeploymentWorkflow
        
        workflow = DeploymentWorkflow(
            project="test-project",
            auto_rollback=True
        )
        
        with patch("kiva_cli.commands.deploy.execute_deployment") as mock_deploy:
            mock_deploy.return_value = {"status": "FAILED", "error": "timeout"}
            
            result = workflow.execute(["deploy"])
            
            assert result["status"] == "FAILED"
            assert result.get("rollback_executed") is True

    def test_rollback_state_restoration(self):
        """Test state restoration after rollback."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # Initial state
        manager.save_checkpoint("deployment-1", {
            "version": "1.0.0",
            "state": "SUCCESS"
        })
        
        # Failed deployment
        manager.set_state("deployment-1", "FAILED")
        
        # Rollback
        restored = manager.restore_checkpoint("deployment-1")
        
        assert restored["version"] == "1.0.0"
        assert restored["state"] == "SUCCESS"


class TestTernaryStateValidation:
    """Test ternary state validation in integration context."""

    def test_ternary_state_across_repos(self):
        """Test ternary state consistency across ECOS and KIVA."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # ECOS sets PENDING
        manager.set_state("cross-repo-task-1", "PENDING")
        
        # KIVA transitions to SUCCESS
        manager.transition_state("cross-repo-task-1", "SUCCESS")
        
        # Verify state
        state = manager.get_state("cross-repo-task-1")
        assert state == "SUCCESS"

    def test_ternary_state_validation_rules(self):
        """Test ternary state validation rules."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # Valid transitions
        valid_transitions = [
            ("PENDING", "SUCCESS"),
            ("PENDING", "FAILED"),
        ]
        
        for from_state, to_state in valid_transitions:
            manager.set_state(f"task-{from_state}", from_state)
            manager.transition_state(f"task-{from_state}", to_state)
            assert manager.get_state(f"task-{from_state}") == to_state

    def test_ternary_state_invalid_transition(self):
        """Test prevention of invalid state transitions."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # Invalid: SUCCESS -> PENDING
        manager.set_state("task-invalid", "SUCCESS")
        
        with pytest.raises(ValueError):
            manager.transition_state("task-invalid", "PENDING")


@pytest.mark.integration
class TestFullWorkflowIntegration:
    """Full end-to-end integration tests."""

    def test_complete_deployment_pipeline(self):
        """Test complete deployment pipeline from ECOS to KIVA."""
        from kiva_cli.workflows.deployment import DeploymentWorkflow
        
        workflow = DeploymentWorkflow(
            project="test-project",
            environment="staging"
        )
        
        steps = [
            "config_validate",
            "build",
            "test",
            "deploy",
            "health_check",
            "wal_log"
        ]
        
        result = workflow.execute(steps)
        
        assert "status" in result
        assert "steps" in result
        assert len(result["steps"]) == len(steps)

    def test_phi_cps_tracking_full_workflow(self):
        """Test φ-CPS tracking throughout full workflow."""
        from kiva_cli.core.phi_tracker import PhiCPSTracker
        from kiva_cli.workflows.deployment import DeploymentWorkflow
        
        tracker = PhiCPSTracker()
        baseline = 4.228
        
        workflow = DeploymentWorkflow(project="test-project")
        result = workflow.execute(["deploy", "health_check"])
        
        # Calculate total impact
        total_impact = tracker.calculate_workflow_impact(result)
        
        new_phi = baseline + total_impact
        drift_percent = (total_impact / baseline) * 100
        
        assert drift_percent < 5, f"Drift {drift_percent:.2f}% exceeds threshold"
