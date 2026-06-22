"""
Unit tests for DeploymentManager
Tests deployment workflows, rollback, and FLUENCE integration
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from kiva_cli.core.deployment_manager import DeploymentManager, DeploymentStrategy

@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    temp = tempfile.mkdtemp()
    project_path = Path(temp) / "test-project"
    project_path.mkdir()
    
    # Create minimal kiva.yaml
    (project_path / "kiva.yaml").write_text("""
project:
  name: test-project
  version: 1.0.0
  template: fastapi
""")
    
    yield project_path
    shutil.rmtree(temp)

@pytest.fixture
def deployment_manager():
    """Create DeploymentManager instance"""
    return DeploymentManager()

def test_deploy_dry_run(deployment_manager, temp_project):
    """Test dry-run deployment"""
    result = deployment_manager.deploy(
        project_path=temp_project,
        environment="staging",
        strategy="rolling",
        dry_run=True
    )
    
    assert result["status"] == "DRY_RUN_SUCCESS"
    assert result["environment"] == "staging"
    assert result["strategy"] == "rolling"
    assert result["rollback_available"] is False

def test_deploy_without_fluence_cli(deployment_manager, temp_project):
    """Test deployment without FLUENCE CLI (fallback)"""
    result = deployment_manager.deploy(
        project_path=temp_project,
        environment="dev",
        strategy="recreate",
        dry_run=False
    )
    
    assert result["status"] in ["SUCCESS", "DRY_RUN_SUCCESS"]
    assert "workflow_id" in result
    assert result["deployed_version"] == "1.0.0"

def test_deploy_project_not_found(deployment_manager):
    """Test deployment with non-existent project"""
    with pytest.raises(FileNotFoundError):
        deployment_manager.deploy(
            project_path=Path("/nonexistent/project"),
            environment="staging"
        )

def test_rollback_no_history(deployment_manager):
    """Test rollback without deployment history"""
    result = deployment_manager.rollback(
        project_name="test-project",
        environment="production"
    )
    
    assert result["status"] == "FAILED"
    assert "No previous deployments" in result["error"]

def test_rollback_to_previous(deployment_manager, temp_project):
    """Test rollback to previous version"""
    # Deploy version 1.0.0
    deploy1 = deployment_manager.deploy(
        project_path=temp_project,
        environment="production",
        dry_run=False
    )
    
    # Update version and deploy 2.0.0
    config = (temp_project / "kiva.yaml").read_text()
    config = config.replace("1.0.0", "2.0.0")
    (temp_project / "kiva.yaml").write_text(config)
    
    deploy2 = deployment_manager.deploy(
        project_path=temp_project,
        environment="production",
        dry_run=False
    )
    
    # Rollback
    rollback = deployment_manager.rollback(
        project_name="test-project",
        environment="production"
    )
    
    assert rollback["status"] == "SUCCESS"
    assert rollback["rolled_back_version"] == "1.0.0"

def test_rollback_to_specific_version(deployment_manager, temp_project):
    """Test rollback to specific version"""
    # Deploy multiple versions
    for version in ["1.0.0", "1.1.0", "1.2.0"]:
        config = (temp_project / "kiva.yaml").read_text()
        config = config.replace("version: ", f"# v").replace("1.0.0", version)
        (temp_project / "kiva.yaml").write_text(f"""
project:
  name: test-project
  version: {version}
  template: fastapi
""")
        deployment_manager.deploy(
            project_path=temp_project,
            environment="staging",
            dry_run=False
        )
    
    # Rollback to 1.1.0
    rollback = deployment_manager.rollback(
        project_name="test-project",
        environment="staging",
        target_version="1.1.0"
    )
    
    assert rollback["status"] == "SUCCESS"
    assert rollback["rolled_back_version"] == "1.1.0"

def test_get_deployment_status(deployment_manager, temp_project):
    """Test deployment status query"""
    # Deploy
    deploy_result = deployment_manager.deploy(
        project_path=temp_project,
        environment="dev",
        dry_run=True
    )
    
    workflow_id = deploy_result["workflow_id"]
    
    # Query status
    status = deployment_manager.get_deployment_status(workflow_id)
    
    assert status["workflow_id"] == workflow_id
    assert status["status"] == "DRY_RUN_SUCCESS"

def test_get_deployment_status_not_found(deployment_manager):
    """Test status query for non-existent workflow"""
    status = deployment_manager.get_deployment_status("nonexistent-workflow")
    
    assert status["status"] == "NOT_FOUND"

@pytest.mark.parametrize("strategy", ["rolling", "blue-green", "canary", "recreate"])
def test_all_strategies(deployment_manager, temp_project, strategy):
    """Test all deployment strategies"""
    result = deployment_manager.deploy(
        project_path=temp_project,
        environment="staging",
        strategy=strategy,
        dry_run=True
    )
    
    assert result["status"] == "DRY_RUN_SUCCESS"
    assert result["strategy"] == strategy
