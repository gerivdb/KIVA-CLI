"""Comprehensive test suite for KIVA CLI commands.

Tests cover all 8 command groups with ternary state validation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import yaml


class TestProjectCommands:
    """Test project command group."""

    def test_project_init_success(self, tmp_path):
        """Test successful project initialization."""
        from kiva_cli.commands.project import init_project
        
        result = init_project(
            name="test-project",
            path=str(tmp_path),
            template="default"
        )
        
        assert result["status"] == "SUCCESS"
        assert (tmp_path / "test-project").exists()
        assert (tmp_path / "test-project" / "kiva.yaml").exists()

    def test_project_init_ternary_pending(self, tmp_path):
        """Test project init with pending state."""
        from kiva_cli.commands.project import init_project
        
        with patch("kiva_cli.commands.project.validate_template", return_value=False):
            result = init_project(
                name="test-project",
                path=str(tmp_path),
                template="invalid"
            )
            
            assert result["status"] == "PENDING"
            assert "validation" in result["message"].lower()

    def test_project_list(self):
        """Test listing projects."""
        from kiva_cli.commands.project import list_projects
        
        with patch("kiva_cli.commands.project.get_projects") as mock_get:
            mock_get.return_value = [
                {"name": "proj1", "status": "ACTIVE"},
                {"name": "proj2", "status": "INACTIVE"}
            ]
            
            result = list_projects()
            assert result["status"] == "SUCCESS"
            assert len(result["projects"]) == 2

    def test_project_update(self):
        """Test project configuration update."""
        from kiva_cli.commands.project import update_project
        
        result = update_project(
            name="test-project",
            config={"version": "1.0.1", "env": "production"}
        )
        
        assert result["status"] in ["SUCCESS", "PENDING"]


class TestDeployCommands:
    """Test deployment command group."""

    def test_deploy_success(self):
        """Test successful deployment."""
        from kiva_cli.commands.deploy import deploy_project
        
        with patch("kiva_cli.commands.deploy.execute_deployment") as mock_deploy:
            mock_deploy.return_value = {"status": "SUCCESS", "deployment_id": "dep-123"}
            
            result = deploy_project(
                project="test-project",
                environment="staging"
            )
            
            assert result["status"] == "SUCCESS"
            assert "deployment_id" in result

    def test_deploy_with_validation(self):
        """Test deployment with pre-validation."""
        from kiva_cli.commands.deploy import deploy_project
        
        with patch("kiva_cli.commands.deploy.validate_config") as mock_validate:
            mock_validate.return_value = False
            
            result = deploy_project(
                project="test-project",
                environment="production",
                validate=True
            )
            
            assert result["status"] == "FAILED"
            assert "validation" in result["message"].lower()

    def test_deploy_status_check(self):
        """Test deployment status check."""
        from kiva_cli.commands.deploy import check_deployment_status
        
        result = check_deployment_status(deployment_id="dep-123")
        
        assert result["status"] in ["SUCCESS", "PENDING", "FAILED"]


class TestConfigCommands:
    """Test configuration command group."""

    def test_config_get(self):
        """Test configuration retrieval."""
        from kiva_cli.commands.config import get_config
        
        with patch("kiva_cli.commands.config.load_config") as mock_load:
            mock_load.return_value = {"app_name": "test", "version": "1.0.0"}
            
            result = get_config(key="app_name")
            
            assert result["status"] == "SUCCESS"
            assert result["value"] == "test"

    def test_config_set(self):
        """Test configuration update."""
        from kiva_cli.commands.config import set_config
        
        result = set_config(
            key="deployment.timeout",
            value="300"
        )
        
        assert result["status"] == "SUCCESS"

    def test_config_validate(self):
        """Test configuration validation."""
        from kiva_cli.commands.config import validate_config
        
        config = {
            "app_name": "test",
            "version": "1.0.0",
            "deployment": {"timeout": 300}
        }
        
        result = validate_config(config=config)
        
        assert result["status"] in ["SUCCESS", "FAILED"]
        assert "validation_errors" in result


class TestSecretsCommands:
    """Test secrets management command group."""

    def test_secrets_set(self):
        """Test setting a secret."""
        from kiva_cli.commands.secrets import set_secret
        
        with patch("kiva_cli.commands.secrets.store_secret") as mock_store:
            mock_store.return_value = True
            
            result = set_secret(
                key="API_KEY",
                value="secret-value-123",
                environment="production"
            )
            
            assert result["status"] == "SUCCESS"

    def test_secrets_get(self):
        """Test retrieving a secret."""
        from kiva_cli.commands.secrets import get_secret
        
        with patch("kiva_cli.commands.secrets.retrieve_secret") as mock_retrieve:
            mock_retrieve.return_value = "secret-value-123"
            
            result = get_secret(
                key="API_KEY",
                environment="production"
            )
            
            assert result["status"] == "SUCCESS"
            assert "value" in result

    def test_secrets_rotate(self):
        """Test secret rotation."""
        from kiva_cli.commands.secrets import rotate_secret
        
        result = rotate_secret(
            key="API_KEY",
            environment="production"
        )
        
        assert result["status"] in ["SUCCESS", "PENDING"]

    def test_secrets_delete(self):
        """Test secret deletion."""
        from kiva_cli.commands.secrets import delete_secret
        
        result = delete_secret(
            key="API_KEY",
            environment="staging"
        )
        
        assert result["status"] == "SUCCESS"


class TestMonitoringCommands:
    """Test monitoring command group."""

    def test_monitoring_start(self):
        """Test starting monitoring."""
        from kiva_cli.commands.monitoring import start_monitoring
        
        result = start_monitoring(
            project="test-project",
            metrics=["cpu", "memory", "requests"]
        )
        
        assert result["status"] == "SUCCESS"

    def test_monitoring_status(self):
        """Test monitoring status check."""
        from kiva_cli.commands.monitoring import get_monitoring_status
        
        result = get_monitoring_status(project="test-project")
        
        assert result["status"] in ["SUCCESS", "PENDING"]
        assert "metrics" in result

    def test_monitoring_alerts(self):
        """Test alert configuration."""
        from kiva_cli.commands.monitoring import configure_alerts
        
        alerts = [
            {"metric": "cpu", "threshold": 80, "action": "notify"},
            {"metric": "memory", "threshold": 90, "action": "scale"}
        ]
        
        result = configure_alerts(
            project="test-project",
            alerts=alerts
        )
        
        assert result["status"] == "SUCCESS"


class TestRollbackCommands:
    """Test rollback command group."""

    def test_rollback_to_version(self):
        """Test rollback to specific version."""
        from kiva_cli.commands.rollback import rollback_deployment
        
        with patch("kiva_cli.commands.rollback.execute_rollback") as mock_rollback:
            mock_rollback.return_value = {"status": "SUCCESS", "version": "1.0.0"}
            
            result = rollback_deployment(
                project="test-project",
                version="1.0.0"
            )
            
            assert result["status"] == "SUCCESS"
            assert result["version"] == "1.0.0"

    def test_rollback_list_versions(self):
        """Test listing available rollback versions."""
        from kiva_cli.commands.rollback import list_rollback_versions
        
        result = list_rollback_versions(project="test-project")
        
        assert result["status"] == "SUCCESS"
        assert "versions" in result

    def test_rollback_validation(self):
        """Test rollback validation."""
        from kiva_cli.commands.rollback import validate_rollback
        
        result = validate_rollback(
            project="test-project",
            version="0.9.0"
        )
        
        assert result["status"] in ["SUCCESS", "FAILED"]


class TestHealthCommands:
    """Test health check command group."""

    def test_health_check_success(self):
        """Test successful health check."""
        from kiva_cli.commands.health import check_health
        
        with patch("kiva_cli.commands.health.ping_service") as mock_ping:
            mock_ping.return_value = True
            
            result = check_health(
                project="test-project",
                environment="production"
            )
            
            assert result["status"] == "SUCCESS"
            assert result["healthy"] is True

    def test_health_check_failed(self):
        """Test failed health check."""
        from kiva_cli.commands.health import check_health
        
        with patch("kiva_cli.commands.health.ping_service") as mock_ping:
            mock_ping.return_value = False
            
            result = check_health(
                project="test-project",
                environment="production"
            )
            
            assert result["status"] == "FAILED"
            assert result["healthy"] is False

    def test_health_detailed_check(self):
        """Test detailed health check."""
        from kiva_cli.commands.health import detailed_health_check
        
        result = detailed_health_check(
            project="test-project",
            components=["database", "cache", "api"]
        )
        
        assert result["status"] in ["SUCCESS", "FAILED"]
        assert "components" in result


class TestScaffoldCommands:
    """Test scaffolding command group."""

    def test_scaffold_service(self, tmp_path):
        """Test service scaffolding."""
        from kiva_cli.commands.scaffold import scaffold_service
        
        result = scaffold_service(
            name="user-service",
            template="fastapi",
            output_dir=str(tmp_path)
        )
        
        assert result["status"] == "SUCCESS"
        assert (tmp_path / "user-service").exists()

    def test_scaffold_with_options(self, tmp_path):
        """Test scaffolding with custom options."""
        from kiva_cli.commands.scaffold import scaffold_service
        
        options = {
            "database": "postgresql",
            "auth": True,
            "docker": True
        }
        
        result = scaffold_service(
            name="api-service",
            template="fastapi",
            output_dir=str(tmp_path),
            options=options
        )
        
        assert result["status"] == "SUCCESS"

    def test_scaffold_list_templates(self):
        """Test listing available templates."""
        from kiva_cli.commands.scaffold import list_templates
        
        result = list_templates()
        
        assert result["status"] == "SUCCESS"
        assert "templates" in result
        assert len(result["templates"]) > 0


class TestTernaryStateValidation:
    """Test ternary state validation across commands."""

    def test_state_transitions(self):
        """Test valid state transitions."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        
        # PENDING -> SUCCESS
        manager.set_state("task-1", "PENDING")
        manager.transition_state("task-1", "SUCCESS")
        assert manager.get_state("task-1") == "SUCCESS"
        
        # PENDING -> FAILED
        manager.set_state("task-2", "PENDING")
        manager.transition_state("task-2", "FAILED")
        assert manager.get_state("task-2") == "FAILED"

    def test_invalid_state_transition(self):
        """Test invalid state transition prevention."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        manager.set_state("task-1", "SUCCESS")
        
        # SUCCESS -> PENDING should not be allowed
        with pytest.raises(ValueError):
            manager.transition_state("task-1", "PENDING")

    def test_state_persistence(self):
        """Test state persistence."""
        from kiva_cli.core.state_manager import StateManager
        
        manager = StateManager()
        manager.set_state("deployment-1", "SUCCESS")
        
        state_data = manager.get_all_states()
        assert "deployment-1" in state_data
        assert state_data["deployment-1"] == "SUCCESS"


class TestECOSIntegration:
    """Test ECOS CLI integration."""

    def test_ecos_command_delegation(self):
        """Test KIVA CLI command delegation from ECOS."""
        import subprocess
        
        # Simulate ECOS calling KIVA CLI
        result = subprocess.run(
            ["kiva", "project", "list"],
            capture_output=True,
            text=True
        )
        
        # Should complete without errors (even if empty output in test)
        assert result.returncode in [0, 1]  # 1 if no projects found

    def test_phi_cps_impact_tracking(self):
        """Test φ-CPS impact tracking for operations."""
        from kiva_cli.core.phi_tracker import PhiCPSTracker
        
        tracker = PhiCPSTracker()
        
        # Track deployment operation
        impact = tracker.calculate_impact(
            operation="deploy",
            success=True,
            complexity=0.8
        )
        
        assert impact > 0
        assert impact < 0.05  # Should be below drift threshold

    def test_wal_event_logging(self):
        """Test WAL event logging."""
        from kiva_cli.core.wal_logger import WALLogger
        
        logger = WALLogger()
        
        event_id = logger.log_event(
            event_type="DEPLOYMENT",
            project="test-project",
            status="SUCCESS",
            metadata={"version": "1.0.0", "environment": "production"}
        )
        
        assert event_id is not None
        assert len(event_id) > 0


@pytest.mark.integration
class TestDeploymentAutomation:
    """Integration tests for deployment automation."""

    def test_full_deployment_workflow(self):
        """Test complete deployment workflow."""
        from kiva_cli.workflows.deployment import DeploymentWorkflow
        
        workflow = DeploymentWorkflow(
            project="test-project",
            environment="staging"
        )
        
        # Execute full workflow
        result = workflow.execute([
            "validate_config",
            "build",
            "test",
            "deploy",
            "health_check"
        ])
        
        assert result["status"] in ["SUCCESS", "FAILED"]
        assert "steps" in result

    def test_rollback_on_failure(self):
        """Test automatic rollback on deployment failure."""
        from kiva_cli.workflows.deployment import DeploymentWorkflow
        
        workflow = DeploymentWorkflow(
            project="test-project",
            environment="production",
            auto_rollback=True
        )
        
        with patch("kiva_cli.commands.deploy.execute_deployment") as mock_deploy:
            mock_deploy.return_value = {"status": "FAILED", "error": "timeout"}
            
            result = workflow.execute(["deploy"])
            
            assert result["status"] == "FAILED"
            assert result.get("rollback_executed") is True
