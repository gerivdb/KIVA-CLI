# Unit tests for DeploymentManager
import pytest
from kiva_cli.core.deployment_manager import DeploymentManager, DeploymentStrategy


def test_deploy_staging_dry_run():
    """Test dry-run deployment to staging."""
    manager = DeploymentManager()
    result = manager.deploy(
        target='api',
        env='staging',
        strategy='rolling',
        dry_run=True
    )
    
    assert result.success is True
    assert result.version is not None
    assert 'staging' in result.deployment_url
    assert result.health_check_passed is True


def test_deploy_rolling_strategy():
    """Test rolling deployment strategy."""
    manager = DeploymentManager()
    result = manager.deploy(
        target='api',
        env='staging',
        strategy='rolling',
        dry_run=False
    )
    
    assert result.success is True
    assert result.strategy == 'rolling'
    assert result.duration_seconds >= 0


def test_deploy_blue_green_strategy():
    """Test blue-green deployment strategy."""
    manager = DeploymentManager()
    result = manager.deploy(
        target='frontend',
        env='production',
        strategy='blue-green',
        dry_run=False
    )
    
    assert result.success is True
    assert result.strategy == 'blue-green'


def test_deploy_canary_strategy():
    """Test canary deployment strategy."""
    manager = DeploymentManager()
    result = manager.deploy(
        target='api',
        env='staging',
        strategy='canary',
        dry_run=False
    )
    
    assert result.success is True
    assert result.strategy == 'canary'
    assert result.warnings is not None


def test_deploy_invalid_strategy():
    """Test deployment with invalid strategy."""
    manager = DeploymentManager()
    result = manager.deploy(
        target='api',
        env='staging',
        strategy='unknown-strategy',
        dry_run=False
    )
    
    assert result.success is False
    assert 'Invalid strategy' in result.error


def test_rollback_success():
    """Test successful rollback."""
    manager = DeploymentManager()
    
    # Deploy first
    deploy_result = manager.deploy(target='api', env='staging', strategy='rolling', dry_run=False)
    deployment_id = f"api-{deploy_result.version}"
    
    # Rollback
    rollback_result = manager.rollback(
        deployment_id=deployment_id,
        to_version='v1.0.0'
    )
    
    assert rollback_result.success is True
    assert rollback_result.version == 'v1.0.0'


def test_rollback_unknown_deployment():
    """Test rollback of unknown deployment."""
    manager = DeploymentManager()
    result = manager.rollback(
        deployment_id='unknown-deployment',
        to_version='v1.0.0'
    )
    
    assert result.success is False
    assert 'not found' in result.error.lower()


def test_get_deployment_status():
    """Test getting deployment status."""
    manager = DeploymentManager()
    
    # Deploy
    deploy_result = manager.deploy(target='api', env='staging', strategy='rolling', dry_run=False)
    deployment_id = f"api-{deploy_result.version}"
    
    # Get status
    status = manager.get_deployment_status(deployment_id)
    
    assert status is not None
    assert 'target' in status
    assert status['target'] == 'api'
    assert 'version' in status
