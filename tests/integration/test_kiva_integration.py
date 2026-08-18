# Integration tests for KIVA CLI
import pytest
import subprocess
from pathlib import Path


@pytest.mark.integration
def test_kiva_cli_direct(tmp_path):
    """Test KIVA CLI works directly."""
    cmd = [
        'python', '-m', 'kiva_cli.kiva',
        'project', 'scaffold',
        'test-direct',
        '--framework', 'fastapi',
        '--workspace', str(tmp_path)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
    
    assert proc.returncode == 0
    assert 'scaffolding' in proc.stdout.lower() or 'initialized' in proc.stdout.lower()
    assert (tmp_path / 'projects' / 'test-direct').exists()


@pytest.mark.integration
@pytest.mark.skip(reason="config validate command does not exist in current CLI")
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
def test_kiva_cli_deploy_dry_run(tmp_path):
    """Test KIVA deploy dry-run."""
    # First scaffold a project, then deploy it
    scaffold_cmd = [
        'python', '-m', 'kiva_cli.kiva',
        'project', 'scaffold',
        'test-api',
        '--framework', 'fastapi',
        '--workspace', str(tmp_path)
    ]
    subprocess.run(scaffold_cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
    
    cmd = [
        'python', '-m', 'kiva_cli.kiva',
        'project', 'deploy',
        'test-api',
        '--target', 'docker',
        '--dry-run',
        '--workspace', str(tmp_path)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
    
    assert proc.returncode == 0
    assert 'dry run' in proc.stdout.lower() or 'dry-run' in proc.stdout.lower()


@pytest.mark.integration
def test_kiva_cli_help():
    """Test KIVA CLI help command."""
    cmd = ['python', '-m', 'kiva_cli.kiva', '--help']
    
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5, encoding='utf-8', errors='replace')
    
    assert proc.returncode == 0
    assert 'project' in proc.stdout.lower()
    assert 'pipeline' in proc.stdout.lower()
    assert 'doctor' in proc.stdout.lower()


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
