"""Unit tests for TemplateRegistry."""

import pytest
from kiva_cli.core.template_registry import TemplateRegistry, Template


@pytest.mark.unit
class TestTemplateRegistry:
    """Test TemplateRegistry functionality."""
    
    def test_builtin_templates_registered(self):
        """Test that built-in templates are auto-registered."""
        registry = TemplateRegistry()
        
        templates = registry.list_templates()
        assert len(templates) >= 4  # FastAPI, React, Go, Rust
        assert "fastapi" in templates
        assert "react" in templates
        assert "go-service" in templates
        assert "rust-service" in templates
    
    def test_get_template_by_name(self):
        """Test retrieving template by name."""
        registry = TemplateRegistry()
        
        template = registry.get("fastapi")
        assert template is not None
        assert template.name == "fastapi"
        assert template.language == "python"
        assert template.framework == "FastAPI"
    
    def test_get_nonexistent_template(self):
        """Test retrieving non-existent template returns None."""
        registry = TemplateRegistry()
        
        template = registry.get("nonexistent")
        assert template is None
    
    def test_register_custom_template(self):
        """Test registering custom template."""
        registry = TemplateRegistry()
        
        custom = Template(
            name="custom",
            language="python",
            framework=None,
            description="Custom template",
        )
        
        registry.register(custom)
        
        retrieved = registry.get("custom")
        assert retrieved is not None
        assert retrieved.name == "custom"
    
    def test_template_to_dict(self):
        """Test Template serialization."""
        template = Template(
            name="test",
            language="python",
            framework="Django",
            description="Test template",
        )
        
        data = template.to_dict()
        assert data["name"] == "test"
        assert data["language"] == "python"
        assert data["framework"] == "Django"
        assert "dependencies" in data
        assert "scripts" in data
