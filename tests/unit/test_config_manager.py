# Unit tests for ConfigManager
import pytest
from pathlib import Path
import yaml
import json
from kiva_cli.core.config_manager import ConfigManager


def test_validate_yaml_config_valid(tmp_path):
    """Test validation of valid YAML config."""
    config_file = tmp_path / 'config.yaml'
    config_data = {
        'name': 'test-project',
        'version': '1.0.0',
        'environment': 'development'
    }
    config_file.write_text(yaml.dump(config_data))
    
    manager = ConfigManager()
    result = manager.validate_config(str(config_file))
    
    assert result.success is True
    assert result.config_data['name'] == 'test-project'


def test_validate_json_config_valid(tmp_path):
    """Test validation of valid JSON config."""
    config_file = tmp_path / 'config.json'
    config_data = {
        'name': 'test-project',
        'version': '1.0.0',
        'environment': 'production'
    }
    config_file.write_text(json.dumps(config_data))
    
    manager = ConfigManager()
    result = manager.validate_config(str(config_file))
    
    assert result.success is True
    assert result.config_data['version'] == '1.0.0'


def test_validate_config_missing_required(tmp_path):
    """Test validation with missing required fields."""
    config_file = tmp_path / 'config.yaml'
    config_data = {'environment': 'development'}  # Missing name, version
    config_file.write_text(yaml.dump(config_data))
    
    manager = ConfigManager()
    result = manager.validate_config(str(config_file), strict=True)
    
    assert result.success is False
    assert len(result.errors) > 0


def test_validate_config_non_strict(tmp_path):
    """Test non-strict validation mode."""
    config_file = tmp_path / 'config.yaml'
    config_data = {'environment': 'development'}  # Missing name, version
    config_file.write_text(yaml.dump(config_data))
    
    manager = ConfigManager()
    result = manager.validate_config(str(config_file), strict=False)
    
    # Should succeed with warnings
    assert result.success is True
    assert result.warnings is not None


def test_validate_config_file_not_found():
    """Test validation of non-existent file."""
    manager = ConfigManager()
    result = manager.validate_config('nonexistent.yaml')
    
    assert result.success is False
    assert 'not found' in result.errors[0].lower()


def test_generate_config(tmp_path):
    """Test config file generation."""
    output_file = tmp_path / 'generated.yaml'
    
    manager = ConfigManager()
    result = manager.generate_config(
        name='my-project',
        version='0.1.0',
        output_file=str(output_file)
    )
    
    assert result.success is True
    assert output_file.exists()
    assert result.config_data['name'] == 'my-project'


def test_validate_config_invalid_replicas(tmp_path):
    """Test validation with invalid deployment replicas."""
    config_file = tmp_path / 'config.yaml'
    config_data = {
        'name': 'test',
        'version': '1.0.0',
        'deployment': {
            'replicas': 0  # Invalid: must be >= 1
        }
    }
    config_file.write_text(yaml.dump(config_data))
    
    manager = ConfigManager()
    result = manager.validate_config(str(config_file))
    
    assert result.success is False
    assert any('replicas' in error.lower() for error in result.errors)
