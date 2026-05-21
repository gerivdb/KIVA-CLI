"""Integration tests for DeploymentManager."""

import pytest
import json
from pathlib import Path
from kiva_cli.managers.project_manager import ProjectManager
from kiva_cli.managers.deployment_manager import DeploymentManager


@pytest.mark.integration
class TestDeploymentManagerIntegration:
    """Integration tests for DeploymentManager."""
    
    def test_deploy_project(self, temp_workspace, mock_ecos_cli, temp_deployments_dir):
        """Test deploying project."""
        # Create project first
        project_manager = ProjectManager(workspace_root=temp_workspace)
        init_result = project_manager.init_project(
            name="test-api",
            template="fastapi",
        )
        project_path = Path(init_result["project_path"])
        
        # Deploy
        deployment_manager = DeploymentManager(deployments_dir=temp_deployments_dir)
        result = deployment_manager.deploy(
            project_path=project_path,
            environment="staging",
            target="k8s-cluster-1",
            strategy="rolling",
            replicas=2,
        )
        
        assert result["status"] == "SUCCESS"
        assert "deployment_id" in result
        assert result["environment"] == "staging"
        assert result["strategy"] == "rolling"
        assert "intent_hash" in result
        assert result["phi_delta"] > 0.0
    
    def test_deploy_invalid_project(self, temp_workspace):
        """Test deploying non-existent project fails."""
        deployment_manager = DeploymentManager()
        
        result = deployment_manager.deploy(
            project_path=temp_workspace / "nonexistent",
            environment="staging",
            target="k8s-cluster-1",
        )
        
        assert result["status"] == "FAILED"
        assert "error" in result
    
    def test_rollback_deployment(self, temp_workspace, mock_ecos_cli):
        """Test rolling back deployment."""
        # Create and deploy project
        project_manager = ProjectManager(workspace_root=temp_workspace)
        init_result = project_manager.init_project(
            name="test-api",
            template="fastapi",
        )
        project_path = Path(init_result["project_path"])
        
        deployment_manager = DeploymentManager()
        deploy_result = deployment_manager.deploy(
            project_path=project_path,
            environment="production",
            target="k8s-cluster-1",
        )
        deployment_id = deploy_result["deployment_id"]
        
        # Rollback
        result = deployment_manager.rollback(deployment_id=deployment_id)
        
        assert result["status"] == "SUCCESS"
        assert "rollback_id" in result
        assert result["deployment_id"] == deployment_id
        assert "intent_hash" in result
        assert result["phi_delta"] > 0.0
    
    def test_list_deployments(self, temp_workspace, mock_ecos_cli):
        """Test listing deployments."""
        # Create projects and deploy
        project_manager = ProjectManager(workspace_root=temp_workspace)
        deployment_manager = DeploymentManager()
        
        for i in range(3):
            init_result = project_manager.init_project(
                name=f"project-{i}",
                template="fastapi",
            )
            deployment_manager.deploy(
                project_path=Path(init_result["project_path"]),
                environment="staging" if i % 2 == 0 else "production",
                target="k8s-cluster-1",
            )
        
        # List all
        result = deployment_manager.list_deployments()
        
        assert result["status"] == "SUCCESS"
        assert result["total_count"] == 3
        assert len(result["deployments"]) == 3
    
    def test_list_deployments_filtered(self, temp_workspace, mock_ecos_cli, temp_deployments_dir):
        """Test listing deployments with filters."""
        project_manager = ProjectManager(workspace_root=temp_workspace)
        deployment_manager = DeploymentManager(deployments_dir=temp_deployments_dir)
        
        # Create deployments with unique names
        envs = ["staging", "staging", "production"]
        for i, env in enumerate(envs):
            init_result = project_manager.init_project(
                name=f"project-{i}-{env}",
                template="fastapi",
            )
            if init_result["status"] == "SUCCESS":
                deployment_manager.deploy(
                    project_path=Path(init_result["project_path"]),
                    environment=env,
                    target="k8s-cluster-1",
                )
        
        # Filter by environment
        result = deployment_manager.list_deployments(environment="staging")
        
        assert result["status"] == "SUCCESS"
        assert result["total_count"] == 2
        assert all(d["environment"] == "staging" for d in result["deployments"])
    
    def test_get_deployment(self, temp_workspace, mock_ecos_cli):
        """Test getting deployment details."""
        project_manager = ProjectManager(workspace_root=temp_workspace)
        init_result = project_manager.init_project(
            name="test-api",
            template="fastapi",
        )
        
        deployment_manager = DeploymentManager()
        deploy_result = deployment_manager.deploy(
            project_path=Path(init_result["project_path"]),
            environment="production",
            target="k8s-cluster-1",
        )
        deployment_id = deploy_result["deployment_id"]
        
        # Get details
        result = deployment_manager.get_deployment(deployment_id=deployment_id)
        
        assert result["status"] == "SUCCESS"
        assert "deployment" in result
        assert result["deployment"]["deployment_id"] == deployment_id
        assert result["deployment"]["environment"] == "production"
