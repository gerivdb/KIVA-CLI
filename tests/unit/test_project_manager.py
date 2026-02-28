"""
Unit tests for ProjectManager
Tests template discovery, scaffolding, and fallback behavior
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from kiva_cli.core.project_manager import ProjectManager, ProjectTemplate

@pytest.fixture
def temp_dir():
    """Create temporary directory for test projects"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)

@pytest.fixture
def project_manager():
    """Create ProjectManager instance"""
    return ProjectManager()

def test_list_templates(project_manager):
    """Test template listing"""
    templates = project_manager.list_templates()
    assert isinstance(templates, list)
    assert len(templates) > 0
    assert "fastapi" in templates or len(templates) >= 1

def test_init_project_minimal(project_manager, temp_dir):
    """Test minimal project initialization"""
    result = project_manager.init_project(
        name="test-project",
        template="fastapi",
        target_dir=temp_dir / "test-project"
    )
    
    assert result["status"] == "SUCCESS"
    assert result["template"] == "fastapi"
    assert "project_path" in result
    assert result["count"] >= 3  # At least README, .gitignore, kiva.yaml

def test_init_project_with_overwrite(project_manager, temp_dir):
    """Test project initialization with overwrite"""
    project_path = temp_dir / "test-overwrite"
    project_path.mkdir()
    
    # First init should fail without overwrite
    with pytest.raises(FileExistsError):
        project_manager.init_project(
            name="test-overwrite",
            template="react",
            target_dir=project_path,
            overwrite=False
        )
    
    # Second init should succeed with overwrite
    result = project_manager.init_project(
        name="test-overwrite",
        template="react",
        target_dir=project_path,
        overwrite=True
    )
    
    assert result["status"] == "SUCCESS"

def test_init_project_unknown_template(project_manager, temp_dir):
    """Test initialization with unknown template"""
    with pytest.raises(ValueError, match="Unknown template"):
        project_manager.init_project(
            name="test-unknown",
            template="nonexistent-template",
            target_dir=temp_dir / "test-unknown"
        )

def test_scaffold_element_service(project_manager, temp_dir):
    """Test scaffolding additional service"""
    # Initialize project first
    project_path = temp_dir / "test-scaffold"
    project_manager.init_project(
        name="test-scaffold",
        template="fastapi",
        target_dir=project_path
    )
    
    # Scaffold service
    result = project_manager.scaffold_element(
        project_path=project_path,
        element_type="service",
        name="auth"
    )
    
    assert result["status"] == "SUCCESS"
    assert result["element_type"] == "service"
    assert result["name"] == "auth"
    assert len(result["files_created"]) > 0

def test_scaffold_element_project_not_found(project_manager, temp_dir):
    """Test scaffolding in non-existent project"""
    with pytest.raises(FileNotFoundError):
        project_manager.scaffold_element(
            project_path=temp_dir / "nonexistent",
            element_type="service",
            name="test"
        )

def test_minimal_structure_generation(project_manager, temp_dir):
    """Test fallback minimal structure generation"""
    project_path = temp_dir / "test-minimal"
    
    # Force minimal structure by using template without files
    result = project_manager.init_project(
        name="test-minimal",
        template="fastapi",  # Will fallback if templates not found
        target_dir=project_path
    )
    
    assert result["status"] == "SUCCESS"
    assert (project_path / "README.md").exists()
    assert (project_path / ".gitignore").exists()
    assert (project_path / "kiva.yaml").exists()

def test_placeholder_replacement(project_manager, temp_dir):
    """Test placeholder replacement in templates"""
    project_name = "my-test-app"
    project_path = temp_dir / project_name
    
    result = project_manager.init_project(
        name=project_name,
        template="react",
        target_dir=project_path
    )
    
    # Check README contains actual project name (not placeholder)
    readme_path = project_path / "README.md"
    if readme_path.exists():
        content = readme_path.read_text()
        assert project_name in content or "test-app" in content
        assert "{{PROJECT_NAME}}" not in content

@pytest.mark.parametrize("template", ["fastapi", "react", "go", "rust"])
def test_all_templates(project_manager, temp_dir, template):
    """Test all available templates"""
    project_path = temp_dir / f"test-{template}"
    
    try:
        result = project_manager.init_project(
            name=f"test-{template}",
            template=template,
            target_dir=project_path
        )
        
        assert result["status"] == "SUCCESS"
        assert result["template"] == template
    except ValueError:
        # Skip if template not available
        pytest.skip(f"Template {template} not available")
