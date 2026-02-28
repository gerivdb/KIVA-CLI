"""Integration tests for ProjectManager."""

import pytest
import json
from pathlib import Path
from kiva_cli.managers.project_manager import ProjectManager


@pytest.mark.integration
class TestProjectManagerIntegration:
    """Integration tests for ProjectManager."""
    
    def test_init_project_fastapi(self, temp_workspace, mock_ecos_cli):
        """Test initializing FastAPI project."""
        manager = ProjectManager(workspace_root=temp_workspace)
        
        result = manager.init_project(
            name="test-api",
            template="fastapi",
            description="Test FastAPI project",
        )
        
        assert result["status"] == "SUCCESS"
        assert "project_path" in result
        assert "intent_hash" in result
        assert result["template"] == "fastapi"
        assert result["files_created"] >= 1
        
        # Verify project directory created
        project_path = Path(result["project_path"])
        assert project_path.exists()
        assert (project_path / "kiva.json").exists()
        assert (project_path / "main.py").exists()
        assert (project_path / "Dockerfile").exists()
    
    def test_init_project_react(self, temp_workspace, mock_ecos_cli):
        """Test initializing React project."""
        manager = ProjectManager(workspace_root=temp_workspace)
        
        result = manager.init_project(
            name="test-app",
            template="react",
        )
        
        assert result["status"] == "SUCCESS"
        assert result["template"] == "react"
        
        project_path = Path(result["project_path"])
        assert (project_path / "package.json").exists()
        assert (project_path / "index.html").exists()
    
    def test_init_project_invalid_template(self, temp_workspace):
        """Test initializing project with invalid template."""
        manager = ProjectManager(workspace_root=temp_workspace)
        
        result = manager.init_project(
            name="test-project",
            template="nonexistent",
        )
        
        assert result["status"] == "FAILED"
        assert "error" in result
        assert "available_templates" in result
    
    def test_init_project_existing_directory(self, temp_workspace, mock_ecos_cli):
        """Test initializing project in existing directory fails."""
        manager = ProjectManager(workspace_root=temp_workspace)
        
        # Create first project
        result1 = manager.init_project(
            name="test-project",
            template="fastapi",
        )
        assert result1["status"] == "SUCCESS"
        
        # Try to create again
        result2 = manager.init_project(
            name="test-project",
            template="fastapi",
        )
        assert result2["status"] == "FAILED"
        assert "already exists" in result2["error"].lower()
    
    def test_list_projects(self, temp_workspace, mock_ecos_cli):
        """Test listing projects in workspace."""
        manager = ProjectManager(workspace_root=temp_workspace)
        
        # Create multiple projects
        manager.init_project(name="project-1", template="fastapi")
        manager.init_project(name="project-2", template="react")
        manager.init_project(name="project-3", template="go-service")
        
        # List projects
        result = manager.list_projects()
        
        assert result["status"] == "SUCCESS"
        assert result["total_count"] == 3
        assert len(result["projects"]) == 3
        
        project_names = [p["name"] for p in result["projects"]]
        assert "project-1" in project_names
        assert "project-2" in project_names
        assert "project-3" in project_names
    
    def test_validate_project(self, temp_workspace, mock_ecos_cli):
        """Test project validation (Base-3)."""
        manager = ProjectManager(workspace_root=temp_workspace)
        
        # Create project
        init_result = manager.init_project(
            name="test-project",
            template="fastapi",
        )
        project_path = Path(init_result["project_path"])
        
        # Validate
        result = manager.validate_project(project_path)
        
        assert result["status"] == "VALID"
        assert len(result["errors"]) == 0
        assert result["confidence"] > 0.0
    
    def test_list_templates(self):
        """Test listing available templates."""
        manager = ProjectManager()
        
        result = manager.list_templates()
        
        assert result["status"] == "SUCCESS"
        assert result["total_count"] >= 4
        assert len(result["templates"]) >= 4
        
        template_names = [t["name"] for t in result["templates"]]
        assert "fastapi" in template_names
        assert "react" in template_names
