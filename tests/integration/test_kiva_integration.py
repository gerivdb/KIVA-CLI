# Integration Tests KIVA-CLI <-> ECOS CLI
import pytest
import subprocess
from pathlib import Path

def test_kiva_cli_version():
    '''Test KIVA CLI responds to --version'''
    result = subprocess.run(['python', '-m', 'kiva_cli.kiva', '--version'], 
                          capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert '0.1.0' in result.stdout

def test_kiva_project_init_fastapi(tmp_path):
    '''Test KIVA project init creates FastAPI project'''
    result = subprocess.run([
        'python', '-m', 'kiva_cli.kiva', 'project', 'init',
        '--template', 'fastapi',
        '--name', 'test-api',
        '--path', str(tmp_path)
    ], capture_output=True, text=True, timeout=30)
    
    assert result.returncode == 0
    assert (tmp_path / 'test-api').exists()
    assert (tmp_path / 'test-api' / 'main.py').exists()

def test_kiva_deploy_staging_dry_run():
    '''Test KIVA deploy staging with --dry-run'''
    result = subprocess.run([
        'python', '-m', 'kiva_cli.kiva', 'deploy', 'staging', 'api',
        '--env', 'preprod',
        '--dry-run'
    ], capture_output=True, text=True, timeout=30)
    
    assert result.returncode == 0
    assert 'Deployment successful' in result.stdout

def test_kiva_config_validate_missing_file():
    '''Test KIVA config validate handles missing file'''
    result = subprocess.run([
        'python', '-m', 'kiva_cli.kiva', 'config', 'validate', '/tmp/nonexistent.yaml'
    ], capture_output=True, text=True, timeout=10)
    
    # Should fail gracefully
    assert result.returncode != 0
    assert 'File not found' in result.stderr or 'not found' in result.stdout.lower()
