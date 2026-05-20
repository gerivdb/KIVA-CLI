#!/usr/bin/env python3
"""Unit tests for SkillManager CLI commands.

Tests:
- ecos skill register
- ecos skill execute
- ecos skill validate
- ecos skill list
- ecos skill export
- ecos skill link
- ecos skill info
- ecos skill delete
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from click.testing import CliRunner
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from kiva_cli.commands.skill_commands import skill_cli
from kiva_cli.core.skill_manager import SkillManager


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_db():
    """Create temporary database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def test_script():
    """Create temporary test script."""
    fd, path = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w") as f:
        f.write("""
import os
import json
params = json.loads(os.environ.get('SKILL_PARAMS', '{}'))
print(f"Executed: {params}")
""")
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestRegisterCommand:
    """Test 'ecos skill register' command."""
    
    def test_register_basic(self, runner, test_script, temp_db, monkeypatch):
        """Test basic skill registration."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        result = runner.invoke(skill_cli, [
            "register",
            "--name", "test-skill",
            "--type", "PYTHON_SCRIPT",
            "--script-path", test_script
        ])
        
        assert result.exit_code == 0
        assert "Skill registered successfully" in result.output
        assert "Skill ID:" in result.output
    
    def test_register_with_metadata(self, runner, test_script, temp_db, monkeypatch):
        """Test registration with metadata."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        metadata = '{"version": "1.0.0"}'
        result = runner.invoke(skill_cli, [
            "register",
            "--name", "test-skill-meta",
            "--type", "PYTHON_SCRIPT",
            "--metadata", metadata
        ])
        
        assert result.exit_code == 0
        assert "Skill registered successfully" in result.output
    
    def test_register_invalid_json(self, runner, temp_db, monkeypatch):
        """Test registration with invalid JSON metadata."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        result = runner.invoke(skill_cli, [
            "register",
            "--name", "invalid-json",
            "--type", "PYTHON_SCRIPT",
            "--metadata", "invalid-json"
        ])
        
        assert result.exit_code == 1
        assert "Invalid JSON" in result.output


class TestExecuteCommand:
    """Test 'ecos skill execute' command."""
    
    def test_execute_dry_run(self, runner, test_script, temp_db, monkeypatch):
        """Test dry-run execution."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        # Register skill first
        manager = SkillManager(db_path=temp_db)
        skill_id = manager.register_skill("exec-test", "PYTHON_SCRIPT", test_script)
        
        result = runner.invoke(skill_cli, [
            "execute",
            skill_id,
            "--mode", "dry-run"
        ])
        
        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would execute skill" in result.output
    
    def test_execute_nonexistent_skill(self, runner, temp_db, monkeypatch):
        """Test executing nonexistent skill."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        result = runner.invoke(skill_cli, [
            "execute",
            "skl_nonexistent",
            "--mode", "dry-run"
        ])
        
        assert result.exit_code == 1
        assert "Skill not found" in result.output


class TestValidateCommand:
    """Test 'ecos skill validate' command."""
    
    def test_validate_without_test_cases(self, runner, test_script, temp_db, monkeypatch):
        """Test validation without test cases."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        skill_id = manager.register_skill("validate-test", "PYTHON_SCRIPT", test_script)
        
        result = runner.invoke(skill_cli, [
            "validate",
            skill_id
        ])
        
        assert result.exit_code == 0
        assert "Validation state:" in result.output
    
    def test_validate_with_test_cases(self, runner, test_script, temp_db, monkeypatch):
        """Test validation with test cases."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        skill_id = manager.register_skill("validate-test-cases", "PYTHON_SCRIPT", test_script)
        
        test_cases = '[{"input": {}, "expected": "success"}]'
        result = runner.invoke(skill_cli, [
            "validate",
            skill_id,
            "--test-cases", test_cases
        ])
        
        assert result.exit_code == 0
        assert "Test cases:" in result.output


class TestListCommand:
    """Test 'ecos skill list' command."""
    
    def test_list_table_format(self, runner, test_script, temp_db, monkeypatch):
        """Test list with table format."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        manager.register_skill("list-test", "PYTHON_SCRIPT", test_script)
        
        result = runner.invoke(skill_cli, ["list"])
        
        assert result.exit_code == 0
        assert "Skill ID" in result.output
        assert "list-test" in result.output
    
    def test_list_json_format(self, runner, test_script, temp_db, monkeypatch):
        """Test list with JSON format."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        manager.register_skill("list-json-test", "PYTHON_SCRIPT", test_script)
        
        result = runner.invoke(skill_cli, ["list", "--format", "json"])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_list_with_filters(self, runner, test_script, temp_db, monkeypatch):
        """Test list with filters."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        manager.register_skill("py-skill", "PYTHON_SCRIPT", test_script)
        manager.register_skill("bash-skill", "BASH_SCRIPT")
        
        result = runner.invoke(skill_cli, [
            "list",
            "--type", "PYTHON_SCRIPT"
        ])
        
        assert result.exit_code == 0
        assert "py-skill" in result.output
        assert "bash-skill" not in result.output


class TestExportCommand:
    """Test 'ecos skill export' command."""
    
    def test_export_json(self, runner, test_script, temp_db, monkeypatch):
        """Test JSON export."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        manager.register_skill("export-test", "PYTHON_SCRIPT", test_script)
        
        fd, output_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        
        try:
            result = runner.invoke(skill_cli, [
                "export",
                output_path
            ])
            
            assert result.exit_code == 0
            assert "exported" in result.output
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestLinkCommand:
    """Test 'ecos skill link' command."""
    
    def test_link_valid(self, runner, test_script, temp_db, monkeypatch):
        """Test linking skill to citizen."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        skill_id = manager.register_skill("link-test", "PYTHON_SCRIPT", test_script)
        
        result = runner.invoke(skill_cli, [
            "link",
            skill_id,
            "ctz_abc123"
        ])
        
        assert result.exit_code == 0
        assert "linked" in result.output


class TestInfoCommand:
    """Test 'ecos skill info' command."""
    
    def test_info_valid(self, runner, test_script, temp_db, monkeypatch):
        """Test showing skill info."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        skill_id = manager.register_skill("info-test", "PYTHON_SCRIPT", test_script)
        
        result = runner.invoke(skill_cli, [
            "info",
            skill_id
        ])
        
        assert result.exit_code == 0
        assert "Skill Information" in result.output
        assert "info-test" in result.output
    
    def test_info_nonexistent(self, runner, temp_db, monkeypatch):
        """Test info for nonexistent skill."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        result = runner.invoke(skill_cli, [
            "info",
            "skl_nonexistent"
        ])
        
        assert result.exit_code == 1
        assert "Skill not found" in result.output


class TestDeleteCommand:
    """Test 'ecos skill delete' command."""
    
    def test_delete_with_confirm(self, runner, test_script, temp_db, monkeypatch):
        """Test deleting skill with confirmation flag."""
        monkeypatch.setenv("KIVA_SKILLS_DB", temp_db)
        
        manager = SkillManager(db_path=temp_db)
        skill_id = manager.register_skill("delete-test", "PYTHON_SCRIPT", test_script)
        
        result = runner.invoke(skill_cli, [
            "delete",
            skill_id,
            "--confirm"
        ])
        
        assert result.exit_code == 0
        assert "archived" in result.output
