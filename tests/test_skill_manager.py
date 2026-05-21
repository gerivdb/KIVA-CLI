"""
Unit tests for SkillManager
"""

import pytest
import tempfile
from pathlib import Path
from tools.ecosystem.skill_manager import SkillManager, SkillType
from kiva_cli.core.pipeline_manager import ValidationState

class TestSkillRegistry:
    """Test skill registration and retrieval"""
    
    def test_register_python_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "skills.db")
            sm = SkillManager(db_path=db_path)
            
            skill_id = sm.register_skill(
                name="hello_world",
                script_content="print('Hello, World!')",
                skill_type=SkillType.PYTHON,
                description="Simple hello world"
            )
            
            assert skill_id > 0
            
            skill = sm.get_skill("hello_world")
            assert skill is not None
            assert skill['name'] == "hello_world"
            assert skill['skill_type'] == SkillType.PYTHON.value
    
    def test_list_skills(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "skills.db")
            sm = SkillManager(db_path=db_path)
            
            sm.register_skill("skill1", "print('1')", SkillType.PYTHON)
            sm.register_skill("skill2", "print('2')", SkillType.PYTHON)
            sm.register_skill("skill3", "print('3')", SkillType.PYTHON)
            
            skills = sm.list_skills()
            assert len(skills) == 3
            assert skills[0]['name'] == "skill1"
    
    def test_get_nonexistent_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "skills.db")
            sm = SkillManager(db_path=db_path)
            
            skill = sm.get_skill("nonexistent")
            assert skill is None

class TestSkillExecution:
    """Test skill execution"""
    
    def test_execute_python_skill_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "skills.db")
            sm = SkillManager(db_path=db_path)
            
            sm.register_skill(
                name="echo",
                script_content="print('Output from skill')",
                skill_type=SkillType.PYTHON,
                timeout_seconds=10
            )
            
            result = sm.execute_skill("echo")
            assert result['validation_state'] == ValidationState.SUCCESS
            assert 'Output from skill' in result['output']
    
    def test_execute_skill_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "skills.db")
            sm = SkillManager(db_path=db_path)
            
            sm.register_skill(
                name="fail",
                script_content="import sys; sys.exit(1)",
                skill_type=SkillType.PYTHON,
                max_retries=0
            )
            
            result = sm.execute_skill("fail")
            assert result['validation_state'] == ValidationState.FAILED
            assert result['exit_code'] == 1
    
    def test_execute_nonexistent_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "skills.db")
            sm = SkillManager(db_path=db_path)
            
            result = sm.execute_skill("nonexistent")
            assert result['validation_state'] == ValidationState.FAILED
            assert "not found" in result['error']

class TestPipelineIntegration:
    """Test SkillManager integration with PipelineManager"""

    def test_skill_execution_step(self, tmp_path):
        skill_db = str(tmp_path / "skills.db")
        pipeline_db = str(tmp_path / "pipelines.db")

        from kiva_cli.core.pipeline_manager import PipelineManager, PipelineType, StepType
        from tools.ecosystem.skill_manager import SkillManager

        sm = SkillManager(db_path=skill_db)
        pm = PipelineManager(db_path=pipeline_db)
        pm._skill_manager = sm  # Inject for testing

        # Register skill
        sm.register_skill(
            name="test_skill",
            script_content="print('Skill executed')",
            skill_type=SkillType.PYTHON
        )

        # Create pipeline with SKILL_EXECUTION step
        pipeline_id = pm.create_pipeline("Test", "Test", PipelineType.SEQUENTIAL)
        step_id = pm.add_step(
            pipeline_id,
            "execute_skill",
            StepType.SKILL_EXECUTION,
            {"skill_name": "test_skill"}
        )

        # Execute step
        result = pm.execute_step(step_id)
        assert result['validation_state'] == ValidationState.SUCCESS

    def test_skill_execution_step_missing_skill(self, tmp_path):
        skill_db = str(tmp_path / "skills.db")
        pipeline_db = str(tmp_path / "pipelines.db")

        from kiva_cli.core.pipeline_manager import PipelineManager, PipelineType, StepType
        from tools.ecosystem.skill_manager import SkillManager

        sm = SkillManager(db_path=skill_db)
        pm = PipelineManager(db_path=pipeline_db)
        pm._skill_manager = sm

        pipeline_id = pm.create_pipeline("Test", "Test", PipelineType.SEQUENTIAL)
        step_id = pm.add_step(
            pipeline_id,
            "execute_missing",
            StepType.SKILL_EXECUTION,
            {"skill_name": "missing_skill"}
        )

        result = pm.execute_step(step_id)
        assert result['validation_state'] == ValidationState.FAILED
