# Integration tests for KIVA CLI
import pytest
import subprocess
from pathlib import Path


@pytest.mark.integration
def test_kiva_cli_direct(tmp_path):
    """Test KIVA CLI works directly."""
    cmd = [
        'python', '-m', 'kiva_cli.kiva',
        'project', 'init',
        '--template', 'fastapi',
        '--name', 'test-direct',
        '--path', str(tmp_path)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    assert proc.returncode == 0
    assert 'initialized' in proc.stdout.lower()
    assert (tmp_path / 'test-direct').exists()


@pytest.mark.integration
def test_kiva_cli_config_validate(tmp_path):
    """Test KIVA config validation."""
    import yaml
    
    # Create valid config
    config_file = tmp_path / 'test.yaml'
    config_data = {
        'name': 'test-project',
        'version': '1.0.0',
        'environment': 'development'
    }
    config_file.write_text(yaml.dump(config_data))
    
    cmd = [
        'python', '-m', 'kiva_cli.kiva',
        'config', 'validate',
        str(config_file)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    
    assert proc.returncode == 0
    assert 'valid' in proc.stdout.lower()


@pytest.mark.integration
def test_kiva_cli_deploy_dry_run():
    """Test KIVA deploy dry-run."""
    cmd = [
        'python', '-m', 'kiva_cli.kiva',
        'deploy', 'staging',
        'test-api',
        '--dry-run'
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    
    assert proc.returncode == 0
    assert 'dry run' in proc.stdout.lower()
    assert 'successful' in proc.stdout.lower()


@pytest.mark.integration
def test_kiva_cli_help():
    """Test KIVA CLI help command."""
    cmd = ['python', '-m', 'kiva_cli.kiva', '--help']
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    
    assert proc.returncode == 0
    assert 'project' in proc.stdout.lower()
    assert 'deploy' in proc.stdout.lower()
    assert 'config' in proc.stdout.lower()


@pytest.mark.integration
@pytest.mark.skip(reason="Requires ECOS CLI installed")
def test_ecos_delegates_to_kiva(tmp_path):
    """Test ECOS CLI delegates to KIVA (requires ECOS installed)."""
    cmd = [
        'ecos', 'project', 'init',
        '--template', 'react',
        '--name', 'test-delegation',
        '--path', str(tmp_path)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    # Should show deprecation warning
    assert 'deprecated' in proc.stdout.lower() or proc.returncode == 0
    
    # Project should be created
    if proc.returncode == 0:
        assert (tmp_path / 'test-delegation').exists()
