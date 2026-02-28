# Unit Tests ProjectManager
import pytest
from pathlib import Path
from kiva_cli.core.project_manager import ProjectManager, ProjectResult

def test_project_manager_init():
    manager = ProjectManager()
    assert manager is not None
    assert len(manager.TEMPLATES) >= 2

def test_init_project_fastapi_success(tmp_path):
    manager = ProjectManager()
    result = manager.init_project('fastapi', 'test-api', str(tmp_path))
    
    assert result.success is True
    assert result.project_path == tmp_path / 'test-api'
    assert (tmp_path / 'test-api').exists()

def test_init_project_unknown_template(tmp_path):
    manager = ProjectManager()
    result = manager.init_project('unknown', 'test', str(tmp_path))
    
    assert result.success is False
    assert 'Unknown template' in result.error

def test_init_project_react_success(tmp_path):
    manager = ProjectManager()
    result = manager.init_project('react', 'test-app', str(tmp_path))
    
    assert result.success is True
    assert (tmp_path / 'test-app' / 'package.json').exists()
