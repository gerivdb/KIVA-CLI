# Unit tests for ProjectManager
import pytest
from pathlib import Path
from kiva_cli.core.project_manager import ProjectManager, ProjectResult


def test_init_project_fastapi(tmp_path):
    """Test FastAPI project initialization."""
    manager = ProjectManager()
    result = manager.init_project(template='fastapi', name='test-api', path=str(tmp_path))
    
    assert result.success is True
    assert result.project_path == tmp_path / 'test-api'
    assert (tmp_path / 'test-api' / 'main.py').exists()
    assert (tmp_path / 'test-api' / 'app').is_dir()


def test_init_project_react(tmp_path):
    """Test React project initialization."""
    manager = ProjectManager()
    result = manager.init_project(template='react', name='test-app', path=str(tmp_path))
    
    assert result.success is True
    assert result.project_path == tmp_path / 'test-app'
    assert (tmp_path / 'test-app' / 'package.json').exists()
    assert (tmp_path / 'test-app' / 'src').is_dir()


def test_init_project_unknown_template(tmp_path):
    """Test initialization with unknown template."""
    manager = ProjectManager()
    result = manager.init_project(template='unknown', name='test', path=str(tmp_path))
    
    assert result.success is False
    assert 'Unknown template' in result.error


def test_init_project_existing_directory(tmp_path):
    """Test initialization in existing directory."""
    manager = ProjectManager()
    project_path = tmp_path / 'existing'
    project_path.mkdir()
    
    result = manager.init_project(template='fastapi', name='existing', path=str(tmp_path))
    
    assert result.success is False
    assert 'exists' in result.error.lower()


def test_scaffold_component(tmp_path):
    """Test component scaffolding."""
    manager = ProjectManager()
    src_dir = tmp_path / 'src' / 'components'
    src_dir.mkdir(parents=True)
    
    result = manager.scaffold_element(
        element_type='component',
        name='Button',
        typescript=True,
        project_path=str(tmp_path)
    )
    
    assert result.success is True
    assert len(result.files_created) > 0
    assert (tmp_path / 'src' / 'components' / 'Button' / 'Button.tsx').exists()


def test_scaffold_component_javascript(tmp_path):
    """Test JS component scaffolding."""
    manager = ProjectManager()
    src_dir = tmp_path / 'src' / 'components'
    src_dir.mkdir(parents=True)
    
    result = manager.scaffold_element(
        element_type='component',
        name='Header',
        typescript=False,
        project_path=str(tmp_path)
    )
    
    assert result.success is True
    assert (tmp_path / 'src' / 'components' / 'Header' / 'Header.jsx').exists()


def test_scaffold_unsupported_type(tmp_path):
    """Test scaffolding with unsupported type."""
    manager = ProjectManager()
    
    result = manager.scaffold_element(
        element_type='unknown',
        name='Test',
        project_path=str(tmp_path)
    )
    
    assert result.success is False


def test_list_projects_empty(tmp_path):
    """Test listing projects in empty directory."""
    manager = ProjectManager()
    result = manager.list_projects(path=str(tmp_path))
    
    assert result.success is True


def test_list_projects_with_projects(tmp_path):
    """Test listing existing projects."""
    # Create mock projects
    (tmp_path / 'project1').mkdir()
    (tmp_path / 'project1' / 'package.json').write_text('{}')
    
    (tmp_path / 'project2').mkdir()
    (tmp_path / 'project2' / 'pyproject.toml').write_text('')
    
    manager = ProjectManager()
    result = manager.list_projects(path=str(tmp_path))
    
    assert result.success is True


def test_init_project_with_options(tmp_path):
    """Test project initialization with custom options."""
    manager = ProjectManager()
    result = manager.init_project(
        template='fastapi',
        name='custom-api',
        path=str(tmp_path),
        options={'author': 'test'}
    )
    
    assert result.success is True
    assert result.project_path.exists()
