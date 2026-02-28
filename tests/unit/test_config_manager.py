# Unit Tests ConfigManager
import pytest
from pathlib import Path
from kiva_cli.core.config_manager import ConfigManager, ConfigResult

def test_config_manager_init():
    manager = ConfigManager()
    assert manager is not None

def test_validate_missing_file():
    manager = ConfigManager()
    result = manager.validate_config('/tmp/nonexistent.yaml', strict=True, schema=None)
    
    assert result.success is False
    assert len(result.errors) > 0
    assert 'File not found' in result.errors[0]

def test_validate_existing_file_placeholder(tmp_path):
    '''Placeholder until real validation implemented'''
    test_file = tmp_path / 'test.yaml'
    test_file.write_text('key: value\n')
    
    manager = ConfigManager()
    result = manager.validate_config(str(test_file), strict=False, schema=None)
    
    assert result.success is True
