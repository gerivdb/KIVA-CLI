#!/usr/bin/env python3
"""Unit tests for SkillManager.

Tests:
- Skill registration (basic, metadata, dependencies)
- Skill execution (Python/PowerShell/Bash)
- Skill validation (test cases, state transitions)
- Skill retrieval and listing
- Registry export (JSON/CSV)
- Citizen linkage
- IntentHash generation
- φ-CPS calculation
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.core.skill_manager import SkillManager
from tools.core.global_wal_manager import GlobalWALManager


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_wal_db():
    """Create temporary WAL database for testing."""
    fd, path = tempfile.mkstemp(suffix="_wal.db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def manager(temp_db, temp_wal_db):
    """Create SkillManager instance with temp databases."""
    wal_manager = GlobalWALManager(db_path=temp_wal_db)
    return SkillManager(db_path=temp_db, wal_manager=wal_manager)


@pytest.fixture
def test_script():
    """Create temporary test script."""
    fd, path = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w") as f:
        f.write("""
import os
import json

params = json.loads(os.environ.get('SKILL_PARAMS', '{}'))
print(f"Test script executed with params: {params}")
""")
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestSkillManagerInit:
    """Test SkillManager initialization."""
    
    def test_init_default_db(self):
        """Test initialization with default database path."""
        manager = SkillManager()
        assert manager.db_path.endswith("skills.db")
        assert os.path.exists(manager.db_path)
    
    def test_init_custom_db(self, temp_db):
        """Test initialization with custom database path."""
        manager = SkillManager(db_path=temp_db)
        assert manager.db_path == temp_db
        assert os.path.exists(temp_db)


class TestRegisterSkill:
    """Test skill registration."""
    
    def test_register_basic(self, manager, test_script):
        """Test basic skill registration."""
        skill_id = manager.register_skill(
            name="test-skill",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script
        )
        
        assert skill_id.startswith("skl_")
        assert len(skill_id) == 20  # skl_ + 16 hex chars
        
        skill = manager.get_skill(skill_id)
        assert skill is not None
        assert skill["name"] == "test-skill"
        assert skill["skill_type"] == "PYTHON_SCRIPT"
        assert skill["validation_state"] == "UNKNOWN"
        assert skill["lifecycle_state"] == "GENESIS"
    
    def test_register_with_metadata(self, manager, test_script):
        """Test skill registration with metadata."""
        metadata = {"version": "1.0.0", "author": "test"}
        skill_id = manager.register_skill(
            name="test-skill-meta",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script,
            description="Test skill with metadata",
            metadata=metadata
        )
        
        skill = manager.get_skill(skill_id)
        assert skill["description"] == "Test skill with metadata"
        assert json.loads(skill["metadata"]) == metadata
    
    def test_register_with_dependencies(self, manager, test_script):
        """Test skill registration with dependencies."""
        # Register dependency skill first
        dep_id = manager.register_skill(
            name="dep-skill",
            skill_type="PYTHON_SCRIPT"
        )
        
        # Register skill with dependency
        skill_id = manager.register_skill(
            name="test-skill-deps",
            skill_type="PYTHON_SCRIPT",
            dependencies=[dep_id]
        )
        
        skill = manager.get_skill(skill_id)
        deps = json.loads(skill["dependencies"])
        assert dep_id in deps
    
    def test_register_invalid_type(self, manager):
        """Test registration with invalid skill type."""
        with pytest.raises(ValueError, match="Invalid skill_type"):
            manager.register_skill(
                name="invalid-skill",
                skill_type="INVALID_TYPE"
            )
    
    def test_register_duplicate_name(self, manager, test_script):
        """Test registration with duplicate name."""
        manager.register_skill(
            name="duplicate-skill",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script
        )
        
        with pytest.raises(ValueError, match="already exists"):
            manager.register_skill(
                name="duplicate-skill",
                skill_type="BASH_SCRIPT"
            )


class TestExecuteSkill:
    """Test skill execution."""
    
    def test_execute_python_script(self, manager, test_script):
        """Test Python script execution."""
        skill_id = manager.register_skill(
            name="exec-test",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script
        )
        
        result = manager.execute_skill(skill_id, {"key": "value"})
        
        assert result["status"] == "SUCCESS"
        assert "Test script executed" in result["output"]
        assert result["duration_ms"] > 0
    
    def test_execute_nonexistent_skill(self, manager):
        """Test execution of nonexistent skill."""
        with pytest.raises(ValueError, match="Skill not found"):
            manager.execute_skill("skl_nonexistent")
    
    def test_execute_invalid_skill(self, manager, test_script):
        """Test execution of invalid skill."""
        skill_id = manager.register_skill(
            name="invalid-exec",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script
        )
        
        # Mark as INVALID
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect(manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE skills SET validation_state = ? WHERE skill_id = ?",
            ("INVALID", skill_id)
        )
        conn.commit()
        conn.close()
        
        with pytest.raises(ValueError, match="Cannot execute INVALID skill"):
            manager.execute_skill(skill_id)
    
    def test_execute_missing_script(self, manager):
        """Test execution with missing script file."""
        skill_id = manager.register_skill(
            name="missing-script",
            skill_type="PYTHON_SCRIPT",
            script_path="/nonexistent/script.py"
        )
        
        result = manager.execute_skill(skill_id)
        assert result["status"] == "FAILED"
        assert "not found" in result["error"].lower()


class TestValidateSkill:
    """Test skill validation."""
    
    def test_validate_without_test_cases(self, manager, test_script):
        """Test validation without test cases."""
        skill_id = manager.register_skill(
            name="validate-test",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script
        )
        
        validation_state, phi_cps = manager.validate_skill(skill_id)
        
        assert validation_state == "VALID"
        assert phi_cps == manager.PHI_CPS_BASE["VALID"]
    
    def test_validate_with_test_cases(self, manager, test_script):
        """Test validation with test cases."""
        skill_id = manager.register_skill(
            name="validate-test-cases",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script
        )
        
        test_cases = [{"input": {"test": "data"}, "expected": "success"}]
        validation_state, phi_cps = manager.validate_skill(skill_id, test_cases)
        
        assert validation_state == "VALID"
        assert phi_cps > 0
    
    def test_validate_nonexistent_skill(self, manager):
        """Test validation of nonexistent skill."""
        with pytest.raises(ValueError, match="Skill not found"):
            manager.validate_skill("skl_nonexistent")


class TestGetSkill:
    """Test skill retrieval."""
    
    def test_get_existing_skill(self, manager, test_script):
        """Test getting existing skill."""
        skill_id = manager.register_skill(
            name="get-test",
            skill_type="PYTHON_SCRIPT",
            script_path=test_script
        )
        
        skill = manager.get_skill(skill_id)
        assert skill is not None
        assert skill["skill_id"] == skill_id
        assert skill["name"] == "get-test"
    
    def test_get_nonexistent_skill(self, manager):
        """Test getting nonexistent skill."""
        skill = manager.get_skill("skl_nonexistent")
        assert skill is None


class TestListSkills:
    """Test skill listing."""
    
    def test_list_all_skills(self, manager, test_script):
        """Test listing all skills."""
        skill_id1 = manager.register_skill("skill-1", "PYTHON_SCRIPT", test_script)
        skill_id2 = manager.register_skill("skill-2", "BASH_SCRIPT")
        
        skills = manager.list_skills()
        assert len(skills) == 2
        skill_ids = [s["skill_id"] for s in skills]
        assert skill_id1 in skill_ids
        assert skill_id2 in skill_ids
    
    def test_list_by_type(self, manager, test_script):
        """Test listing skills by type."""
        manager.register_skill("py-skill", "PYTHON_SCRIPT", test_script)
        manager.register_skill("bash-skill", "BASH_SCRIPT")
        
        py_skills = manager.list_skills(skill_type="PYTHON_SCRIPT")
        assert len(py_skills) == 1
        assert py_skills[0]["skill_type"] == "PYTHON_SCRIPT"
    
    def test_list_by_validation_state(self, manager, test_script):
        """Test listing skills by validation state."""
        skill_id = manager.register_skill("valid-skill", "PYTHON_SCRIPT", test_script)
        manager.validate_skill(skill_id)
        
        manager.register_skill("unknown-skill", "BASH_SCRIPT")
        
        valid_skills = manager.list_skills(validation_state="VALID")
        assert len(valid_skills) == 1
        assert valid_skills[0]["validation_state"] == "VALID"
    
    def test_list_with_limit(self, manager, test_script):
        """Test listing skills with limit."""
        for i in range(5):
            manager.register_skill(f"skill-{i}", "PYTHON_SCRIPT")
        
        skills = manager.list_skills(limit=3)
        assert len(skills) == 3


class TestExportRegistry:
    """Test registry export."""
    
    def test_export_json(self, manager, test_script):
        """Test JSON export."""
        manager.register_skill("export-test", "PYTHON_SCRIPT", test_script)
        
        fd, output_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        
        try:
            manager.export_registry(output_path, format="json")
            
            assert os.path.exists(output_path)
            with open(output_path, "r") as f:
                data = json.load(f)
            
            assert isinstance(data, list)
            assert len(data) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_export_csv(self, manager, test_script):
        """Test CSV export."""
        manager.register_skill("export-csv-test", "PYTHON_SCRIPT", test_script)
        
        fd, output_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        
        try:
            manager.export_registry(output_path, format="csv")
            
            assert os.path.exists(output_path)
            with open(output_path, "r") as f:
                content = f.read()
            
            assert "skill_id" in content
            assert "export-csv-test" in content
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_export_invalid_format(self, manager):
        """Test export with invalid format."""
        with pytest.raises(ValueError, match="Invalid format"):
            manager.export_registry("output.txt", format="txt")


class TestLinkToCitizen:
    """Test skill-citizen linkage."""
    
    def test_link_valid(self, manager, test_script):
        """Test linking skill to citizen."""
        skill_id = manager.register_skill("link-test", "PYTHON_SCRIPT", test_script)
        citizen_id = "ctz_abc123"
        
        manager.link_to_citizen(skill_id, citizen_id)
        
        skill = manager.get_skill(skill_id)
        assert skill["linked_citizen_id"] == citizen_id
    
    def test_link_nonexistent_skill(self, manager):
        """Test linking nonexistent skill."""
        with pytest.raises(ValueError, match="Skill not found"):
            manager.link_to_citizen("skl_nonexistent", "ctz_abc123")


class TestIntentHash:
    """Test IntentHash generation."""
    
    def test_intent_hash_format(self, manager, test_script):
        """Test IntentHash format."""
        skill_id = manager.register_skill("hash-test", "PYTHON_SCRIPT", test_script)
        skill = manager.get_skill(skill_id)
        
        assert skill["intent_hash"].startswith("0x")
        assert len(skill["intent_hash"]) == 18  # 0x + 16 hex chars
    
    def test_intent_hash_uniqueness(self, manager, test_script):
        """Test IntentHash uniqueness."""
        skill_id1 = manager.register_skill("hash-test-1", "PYTHON_SCRIPT", test_script)
        skill_id2 = manager.register_skill("hash-test-2", "BASH_SCRIPT")
        
        skill1 = manager.get_skill(skill_id1)
        skill2 = manager.get_skill(skill_id2)
        
        assert skill1["intent_hash"] != skill2["intent_hash"]


class TestPhiCPS:
    """Test φ-CPS calculation."""
    
    def test_phi_cps_initial_unknown(self, manager, test_script):
        """Test initial φ-CPS for UNKNOWN state."""
        skill_id = manager.register_skill("phi-test", "PYTHON_SCRIPT", test_script)
        skill = manager.get_skill(skill_id)
        
        assert skill["phi_cps"] == manager.PHI_CPS_BASE["UNKNOWN"]
    
    def test_phi_cps_after_validation(self, manager, test_script):
        """Test φ-CPS after validation."""
        skill_id = manager.register_skill("phi-valid-test", "PYTHON_SCRIPT", test_script)
        
        validation_state, phi_cps = manager.validate_skill(skill_id)
        
        assert phi_cps == manager.PHI_CPS_BASE["VALID"]
        assert phi_cps > manager.PHI_CPS_BASE["UNKNOWN"]
