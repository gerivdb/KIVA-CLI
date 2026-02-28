# Unit Tests DeploymentManager
import pytest
from kiva_cli.core.deployment_manager import DeploymentManager, DeploymentResult

def test_deployment_manager_init():
    manager = DeploymentManager()
    assert manager is not None

def test_deploy_dry_run_success():
    manager = DeploymentManager()
    result = manager.deploy('api', 'staging', 'rolling', dry_run=True)
    
    assert result.success is True
    assert 'v1.0.0-dry' in result.version
    assert 'staging.example.com' in result.deployment_url

def test_deploy_production_simulation():
    manager = DeploymentManager()
    result = manager.deploy('frontend', 'production', 'blue-green', dry_run=False)
    
    assert result.success is True
    assert result.version is not None
    assert 'production.example.com' in result.deployment_url
