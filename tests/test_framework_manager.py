#!/usr/bin/env python3
"""
Tests for FrameworkManager
"""
import pytest
import tempfile
from pathlib import Path
from kiva_cli.managers.framework_manager import FrameworkManager, TemplateConfig


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def framework_manager(temp_output_dir):
    """Create FrameworkManager instance"""
    return FrameworkManager(templates_root=temp_output_dir / "templates")


class TestFastAPIScaffold:
    """Test FastAPI project scaffolding"""
    
    def test_scaffold_fastapi_creates_structure(self, framework_manager, temp_output_dir):
        """Test FastAPI project structure is created"""
        config = TemplateConfig(
            name="test-api",
            framework="fastapi",
            description="Test API",
            target_path=temp_output_dir / "test-api",
            features=["auth", "db"],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_fastapi(config)
        
        # Check project directory exists
        assert project_path.exists()
        assert project_path.is_dir()
        
        # Check main structure
        assert (project_path / "app" / "main.py").exists()
        assert (project_path / "app" / "core" / "config.py").exists()
        assert (project_path / "requirements.txt").exists()
        assert (project_path / "Dockerfile").exists()
        assert (project_path / "docker-compose.yml").exists()
        assert (project_path / "README.md").exists()
    
    def test_scaffold_fastapi_has_api_structure(self, framework_manager, temp_output_dir):
        """Test FastAPI has proper API structure"""
        config = TemplateConfig(
            name="api-test",
            framework="fastapi",
            description="API Test",
            target_path=temp_output_dir / "api-test",
            features=[],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_fastapi(config)
        
        # Check API structure
        assert (project_path / "app" / "api" / "v1" / "__init__.py").exists()
        assert (project_path / "app" / "api" / "v1" / "endpoints").is_dir()
        assert (project_path / "app" / "models").is_dir()
        assert (project_path / "app" / "schemas").is_dir()
    
    def test_scaffold_fastapi_has_db_support(self, framework_manager, temp_output_dir):
        """Test FastAPI has database support"""
        config = TemplateConfig(
            name="db-api",
            framework="fastapi",
            description="DB API",
            target_path=temp_output_dir / "db-api",
            features=["db"],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_fastapi(config)
        
        # Check DB structure
        assert (project_path / "app" / "db" / "base.py").exists()
        assert (project_path / "app" / "db" / "session.py").exists()
        assert (project_path / "alembic").is_dir()
        assert (project_path / "alembic" / "versions").is_dir()
    
    def test_scaffold_fastapi_has_tests(self, framework_manager, temp_output_dir):
        """Test FastAPI has test structure"""
        config = TemplateConfig(
            name="test-api",
            framework="fastapi",
            description="Test API",
            target_path=temp_output_dir / "test-api",
            features=[],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_fastapi(config)
        
        # Check test structure
        assert (project_path / "tests").is_dir()
        assert (project_path / "tests" / "api").is_dir()
        assert (project_path / "tests" / "unit").is_dir()
    
    def test_scaffold_fastapi_has_ci_workflow(self, framework_manager, temp_output_dir):
        """Test FastAPI has CI workflow"""
        config = TemplateConfig(
            name="ci-api",
            framework="fastapi",
            description="CI API",
            target_path=temp_output_dir / "ci-api",
            features=[],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_fastapi(config)
        
        # Check CI workflow
        assert (project_path / ".github" / "workflows" / "ci.yml").exists()
        
        # Verify workflow content
        workflow_content = (project_path / ".github" / "workflows" / "ci.yml").read_text()
        assert "pytest" in workflow_content
        assert "postgres" in workflow_content


class TestReactScaffold:
    """Test React project scaffolding"""
    
    def test_scaffold_react_creates_structure(self, framework_manager, temp_output_dir):
        """Test React project structure is created"""
        config = TemplateConfig(
            name="test-app",
            framework="react",
            description="Test App",
            target_path=temp_output_dir / "test-app",
            features=["routing"],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_react(config)
        
        # Check project directory exists
        assert project_path.exists()
        assert project_path.is_dir()
        
        # Check main structure
        assert (project_path / "src" / "main.tsx").exists()
        assert (project_path / "src" / "App.tsx").exists()
        assert (project_path / "package.json").exists()
        assert (project_path / "README.md").exists()
    
    def test_scaffold_react_has_proper_dirs(self, framework_manager, temp_output_dir):
        """Test React has proper directory structure"""
        config = TemplateConfig(
            name="react-app",
            framework="react",
            description="React App",
            target_path=temp_output_dir / "react-app",
            features=[],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_react(config)
        
        # Check directory structure
        assert (project_path / "src" / "components").is_dir()
        assert (project_path / "src" / "pages").is_dir()
        assert (project_path / "src" / "hooks").is_dir()
        assert (project_path / "src" / "services").is_dir()
        assert (project_path / "public").is_dir()


class TestGoServiceScaffold:
    """Test Go service scaffolding"""
    
    def test_scaffold_go_creates_structure(self, framework_manager, temp_output_dir):
        """Test Go service structure is created"""
        config = TemplateConfig(
            name="test-service",
            framework="go-service",
            description="Test Service",
            target_path=temp_output_dir / "test-service",
            features=["api"],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_go_service(config)
        
        # Check project directory exists
        assert project_path.exists()
        assert project_path.is_dir()
        
        # Check main structure
        assert (project_path / "cmd" / "server" / "main.go").exists()
        assert (project_path / "go.mod").exists()
        assert (project_path / "Dockerfile").exists()
        assert (project_path / "Makefile").exists()
        assert (project_path / "README.md").exists()
    
    def test_scaffold_go_has_internal_structure(self, framework_manager, temp_output_dir):
        """Test Go service has internal structure"""
        config = TemplateConfig(
            name="go-svc",
            framework="go-service",
            description="Go Service",
            target_path=temp_output_dir / "go-svc",
            features=[],
            metadata={}
        )
        
        project_path = framework_manager.scaffold_go_service(config)
        
        # Check internal structure
        assert (project_path / "internal" / "api").is_dir()
        assert (project_path / "internal" / "models").is_dir()
        assert (project_path / "internal" / "repository").is_dir()
        assert (project_path / "pkg").is_dir()


class TestFrameworkManagerGeneral:
    """Test general FrameworkManager functionality"""
    
    def test_unsupported_framework_raises_error(self, framework_manager, temp_output_dir):
        """Test unsupported framework raises ValueError"""
        config = TemplateConfig(
            name="test",
            framework="unsupported",
            description="Test",
            target_path=temp_output_dir / "test",
            features=[],
            metadata={}
        )
        
        with pytest.raises(ValueError, match="Unsupported framework"):
            framework_manager.scaffold_project(config)
    
    def test_scaffold_project_routes_correctly(self, framework_manager, temp_output_dir):
        """Test scaffold_project routes to correct scaffolder"""
        configs = [
            ("fastapi", "test-api"),
            ("react", "test-app"),
            ("go-service", "test-svc"),
        ]
        
        for framework, name in configs:
            config = TemplateConfig(
                name=name,
                framework=framework,
                description=f"Test {framework}",
                target_path=temp_output_dir / name,
                features=[],
                metadata={}
            )
            
            project_path = framework_manager.scaffold_project(config)
            assert project_path.exists()
            assert project_path.is_dir()
