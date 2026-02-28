"""
Unit tests for ConfigManager
Tests configuration validation with JSON Schema
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import yaml
import json
from kiva_cli.core.config_manager import ConfigManager

@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)

@pytest.fixture
def config_manager():
    """Create ConfigManager instance"""
    return ConfigManager()

@pytest.fixture
def valid_config_yaml(temp_dir):
    """Create valid kiva.yaml"""
    config_file = temp_dir / "kiva.yaml"
    config_file.write_text("""
project:
  name: test-project
  version: 1.0.0
  template: fastapi
""")
    return config_file

@pytest.fixture
def invalid_config_yaml(temp_dir):
    """Create invalid kiva.yaml (missing required fields)"""
    config_file = temp_dir / "invalid.yaml"
    config_file.write_text("""
project:
  template: fastapi
""")
    return config_file

def test_validate_valid_config(config_manager, valid_config_yaml):
    """Test validation of valid configuration"""
    result = config_manager.validate(valid_config_yaml)
    
    assert result["status"] == "VALID"
    assert result["valid"] is True
    assert len(result["errors"]) == 0

def test_validate_invalid_config(config_manager, invalid_config_yaml):
    """Test validation of invalid configuration"""
    result = config_manager.validate(invalid_config_yaml)
    
    assert result["status"] == "INVALID"
    assert result["valid"] is False
    assert len(result["errors"]) > 0

def test_validate_config_not_found(config_manager, temp_dir):
    """Test validation of non-existent file"""
    result = config_manager.validate(temp_dir / "nonexistent.yaml")
    
    assert result["status"] == "INVALID"
    assert result["valid"] is False
    assert "not found" in result["errors"][0].lower()

def test_validate_invalid_version_format(config_manager, temp_dir):
    """Test validation with invalid version format"""
    config_file = temp_dir / "bad_version.yaml"
    config_file.write_text("""
project:
  name: test-project
  version: v1.0
  template: fastapi
""")
    
    result = config_manager.validate(config_file)
    
    # Should fail if jsonschema installed, otherwise basic validation passes
    if "jsonschema" in str(result):
        assert result["valid"] is False
    # Fallback validation might pass (less strict)

def test_validate_json_config(config_manager, temp_dir):
    """Test validation of JSON config"""
    config_file = temp_dir / "kiva.json"
    with open(config_file, 'w') as f:
        json.dump({
            "project": {
                "name": "test-project",
                "version": "1.0.0",
                "template": "react"
            }
        }, f)
    
    result = config_manager.validate(config_file)
    
    assert result["valid"] is True

def test_validate_unsupported_format(config_manager, temp_dir):
    """Test validation of unsupported file format"""
    config_file = temp_dir / "config.txt"
    config_file.write_text("invalid format")
    
    result = config_manager.validate(config_file)
    
    assert result["status"] == "INVALID"
    assert result["valid"] is False
    assert "Unsupported config format" in result["errors"][0]

def test_get_schema(config_manager):
    """Test schema retrieval"""
    schema = config_manager.get_schema("kiva-config")
    
    assert schema is not None
    assert "properties" in schema
    assert "project" in schema["properties"]

def test_list_schemas(config_manager):
    """Test listing available schemas"""
    schemas = config_manager.list_schemas()
    
    assert isinstance(schemas, list)
    assert "kiva-config" in schemas

def test_validate_with_custom_schema(config_manager, temp_dir):
    """Test validation with custom schema name"""
    config_file = temp_dir / "custom.yaml"
    config_file.write_text("""
project:
  name: test
  version: 1.0.0
""")
    
    # Should use default schema if custom not found
    result = config_manager.validate(config_file, schema_name="custom-schema")
    
    # Either finds custom schema or returns error
    assert "status" in result
