"""
Tests for PipelineManager
"""

import pytest
import sqlite3
from pathlib import Path
from kiva_cli.core.pipeline_manager import (
    PipelineManager, PipelineType, StepType,
    ValidationState, LifecycleState, ExecutionState
)


class TestPipelineManagerInit:
    def test_init_creates_db(self, tmp_path):
        db_path = str(tmp_path / "test_pipelines.db")
        manager = PipelineManager(db_path=db_path)
        assert Path(db_path).exists()

    def test_init_creates_tables(self, tmp_path):
        db_path = str(tmp_path / "test_pipelines.db")
        manager = PipelineManager(db_path=db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert 'pipelines' in tables
        assert 'pipeline_steps' in tables
        assert 'pipeline_executions' in tables
        assert 'step_executions' in tables
        assert 'dag_edges' in tables


class TestRegisterPipeline:
    def test_register_sequential_pipeline(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test_pipeline", PipelineType.SEQUENTIAL)
        assert pipeline_id
        assert len(pipeline_id) == 16

    def test_register_with_description(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline(
            "test_pipeline",
            PipelineType.DAG,
            description="Test DAG pipeline"
        )
        pipelines = manager.list_pipelines()
        assert len(pipelines) == 1
        assert pipelines[0]['description'] == "Test DAG pipeline"

    def test_initial_state_unknown(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test", PipelineType.SEQUENTIAL)
        pipelines = manager.list_pipelines()
        assert pipelines[0]['validation_state'] == ValidationState.UNKNOWN.value


class TestAddStep:
    def test_add_step_to_pipeline(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test", PipelineType.SEQUENTIAL)
        step_id = manager.add_step(
            pipeline_id=pipeline_id,
            name="step1",
            step_type=StepType.SKILL_EXECUTION,
            config={"skill_id": "test_skill"}
        )
        assert step_id
        assert len(step_id) == 16

    def test_add_multiple_steps(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test", PipelineType.SEQUENTIAL)
        step1 = manager.add_step(pipeline_id, "step1", StepType.SKILL_EXECUTION, {}, order_index=0)
        step2 = manager.add_step(pipeline_id, "step2", StepType.API_CALL, {}, order_index=1)
        assert step1 != step2


class TestDAGEdges:
    def test_add_dag_edge(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test", PipelineType.DAG)
        step1 = manager.add_step(pipeline_id, "step1", StepType.SKILL_EXECUTION, {})
        step2 = manager.add_step(pipeline_id, "step2", StepType.API_CALL, {})
        edge_id = manager.add_dag_edge(pipeline_id, step1, step2)
        assert edge_id
        assert len(edge_id) == 16


class TestValidatePipeline:
    def test_validate_empty_pipeline_invalid(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test", PipelineType.SEQUENTIAL)
        state = manager.validate_pipeline(pipeline_id)
        assert state == ValidationState.INVALID

    def test_validate_with_steps_valid(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test", PipelineType.SEQUENTIAL)
        manager.add_step(pipeline_id, "step1", StepType.SKILL_EXECUTION, {})
        state = manager.validate_pipeline(pipeline_id)
        assert state == ValidationState.VALID


class TestExecutePipeline:
    def test_execute_sequential_pipeline(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        pipeline_id = manager.register_pipeline("test", PipelineType.SEQUENTIAL)
        manager.add_step(pipeline_id, "step1", StepType.SKILL_EXECUTION, {}, order_index=0)
        manager.add_step(pipeline_id, "step2", StepType.API_CALL, {}, order_index=1)
        execution_id = manager.execute_pipeline(pipeline_id, async_mode=False)
        assert execution_id
        status = manager.get_execution_status(execution_id)
        assert status['execution_state'] == ExecutionState.SUCCESS.value


class TestListPipelines:
    def test_list_all_pipelines(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        manager.register_pipeline("p1", PipelineType.SEQUENTIAL)
        manager.register_pipeline("p2", PipelineType.PARALLEL)
        pipelines = manager.list_pipelines()
        assert len(pipelines) == 2

    def test_filter_by_type(self, tmp_path):
        manager = PipelineManager(db_path=str(tmp_path / "test.db"))
        manager.register_pipeline("p1", PipelineType.SEQUENTIAL)
        manager.register_pipeline("p2", PipelineType.PARALLEL)
        pipelines = manager.list_pipelines(pipeline_type=PipelineType.SEQUENTIAL)
        assert len(pipelines) == 1
        assert pipelines[0]['type'] == PipelineType.SEQUENTIAL.value
