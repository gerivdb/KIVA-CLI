"""Unit tests for ConfigValidator."""

import pytest
from kiva_cli.core.config_validator import ConfigValidator, ValidationResult


@pytest.mark.unit
class TestConfigValidator:
    """Test ConfigValidator functionality."""
    
    def test_validate_valid_project_config(self):
        """Test validation of valid project config."""
        validator = ConfigValidator()
        
        config = {
            "name": "my-project",
            "version": "1.0.0",
            "template": "fastapi",
            "description": "My project",
            "license": "MIT",
        }
        
        result = validator.validate_project(config)
        assert result.is_valid
        assert result.status == "VALID"
        assert len(result.errors) == 0
        assert result.confidence == 1.0
    
    def test_validate_project_config_missing_fields(self):
        """Test validation with missing required fields."""
        validator = ConfigValidator()
        
        config = {
            "name": "my-project",
            # Missing: version, template
        }
        
        result = validator.validate_project(config)
        assert result.is_invalid
        assert result.status == "INVALID"
        assert len(result.errors) >= 2
        assert any("version" in err.lower() for err in result.errors)
        assert any("template" in err.lower() for err in result.errors)
    
    def test_validate_project_config_invalid_name(self):
        """Test validation with invalid project name."""
        validator = ConfigValidator()
        
        config = {
            "name": "My Project!",  # Invalid: spaces and special chars
            "version": "1.0.0",
            "template": "fastapi",
        }
        
        result = validator.validate_project(config)
        assert result.is_invalid
        assert any("name" in err.lower() for err in result.errors)
    
    def test_validate_valid_deployment_config(self):
        """Test validation of valid deployment config."""
        validator = ConfigValidator()
        
        config = {
            "environment": "production",
            "target": "k8s-cluster-1",
            "strategy": "rolling",
            "replicas": 3,
        }
        
        result = validator.validate_deployment(config)
        assert result.is_valid
        assert result.status == "VALID"
        assert len(result.errors) == 0
    
    def test_validate_deployment_config_invalid_environment(self):
        """Test validation with invalid environment."""
        validator = ConfigValidator()
        
        config = {
            "environment": "invalid-env",
            "target": "k8s-cluster-1",
            "strategy": "rolling",
        }
        
        result = validator.validate_deployment(config)
        assert result.is_invalid
        assert any("environment" in err.lower() for err in result.errors)
    
    def test_validate_deployment_config_invalid_replicas(self):
        """Test validation with invalid replicas count."""
        validator = ConfigValidator()
        
        config = {
            "environment": "production",
            "target": "k8s-cluster-1",
            "strategy": "rolling",
            "replicas": 150,  # Invalid: >100
        }
        
        result = validator.validate_deployment(config)
        assert result.is_invalid
        assert any("replicas" in err.lower() for err in result.errors)
    
    def test_validation_result_base3_states(self):
        """Test ValidationResult Base-3 state properties."""
        # VALID
        valid = ValidationResult("VALID", [], [], 1.0)
        assert valid.is_valid
        assert not valid.is_invalid
        assert not valid.is_unknown
        
        # INVALID
        invalid = ValidationResult("INVALID", ["error"], [], 1.0)
        assert not invalid.is_valid
        assert invalid.is_invalid
        assert not invalid.is_unknown
        
        # UNKNOWN
        unknown = ValidationResult("UNKNOWN", [], [], 0.0)
        assert not unknown.is_valid
        assert not unknown.is_invalid
        assert unknown.is_unknown
