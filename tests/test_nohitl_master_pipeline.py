#!/usr/bin/env python3
"""
Tests for NoHitlMasterPipeline
"""

import pytest
import asyncio
from tools.pipeline.nohitl_master_pipeline import (
    NoHitlMasterPipeline,
    ValidationState,
    LifecycleState,
    WorkflowStage,
)


@pytest.mark.asyncio
async def test_initialization():
    """Test pipeline initialization"""
    pipeline = NoHitlMasterPipeline(phi_cps_threshold=0.05)
    assert pipeline.phi_cps_threshold == 0.05
    assert pipeline.lifecycle == LifecycleState.GENESIS
    assert len(pipeline.stages_completed) == 0
    assert len(pipeline.intent_hash_chain) == 0


@pytest.mark.asyncio
async def test_execute_missing_params():
    """Test execution with missing parameters"""
    pipeline = NoHitlMasterPipeline()
    result = await pipeline.execute({})
    assert result.state == ValidationState.FAILED
    assert result.lifecycle == LifecycleState.DEPRECATED
    assert result.rollback_triggered == False


@pytest.mark.asyncio
async def test_execute_complete_workflow():
    """Test complete workflow execution success"""
    pipeline = NoHitlMasterPipeline(phi_cps_threshold=0.05)
    result = await pipeline.execute({
        'issue_number': 42,
        'repository': 'gerivdb/KIVA-CLI',
        'mode': 'auto',
    })
    assert result.state == ValidationState.SUCCESS
    assert result.lifecycle == LifecycleState.ACTIVE
    assert len(result.stages) == 3  # Clarify, Implement, Validate
    assert result.rollback_triggered == False
    assert len(result.intent_hash_chain) == 3
    assert result.phi_cps_delta > 0.0


@pytest.mark.asyncio
async def test_clarify_stage_success():
    """Test clarify stage execution"""
    pipeline = NoHitlMasterPipeline()
    result = await pipeline._execute_clarify({
        'issue_number': 42,
        'repository': 'gerivdb/KIVA-CLI',
    })
    assert result.state == ValidationState.SUCCESS
    assert result.stage == WorkflowStage.CLARIFY
    assert result.data is not None
    assert 'objectives' in result.data
    assert result.confidence >= 0.9


@pytest.mark.asyncio
async def test_implement_stage_success():
    """Test implement stage execution"""
    pipeline = NoHitlMasterPipeline()
    specs = {'objectives': ['Test objective']}
    result = await pipeline._execute_implement({}, specs)
    assert result.state == ValidationState.SUCCESS
    assert result.stage == WorkflowStage.IMPLEMENT
    assert 'files_created' in result.data
    assert 'commits' in result.data


@pytest.mark.asyncio
async def test_validate_stage_success():
    """Test validate stage success"""
    pipeline = NoHitlMasterPipeline(phi_cps_threshold=0.05)
    implementation = {'files_created': ['file1.py']}
    result = await pipeline._execute_validate({}, implementation)
    assert result.state == ValidationState.SUCCESS
    assert result.stage == WorkflowStage.VALIDATE
    assert result.data['tests_passed'] == True
    assert result.data['phi_cps_within_threshold'] == True


@pytest.mark.asyncio
async def test_validate_stage_phi_cps_failure():
    """Test validate stage with φ-CPS threshold exceeded"""
    pipeline = NoHitlMasterPipeline(phi_cps_threshold=0.01)  # Low threshold
    implementation = {'files_created': ['file1.py']}
    result = await pipeline._execute_validate({}, implementation)
    assert result.state == ValidationState.FAILED
    assert result.error is not None
    assert "φ-CPS" in result.error


@pytest.mark.asyncio
async def test_rollback_trigger():
    """Test rollback triggered on validation failure"""
    pipeline = NoHitlMasterPipeline(phi_cps_threshold=0.01)
    result = await pipeline.execute({
        'issue_number': 42,
        'repository': 'gerivdb/KIVA-CLI',
    })
    assert result.state == ValidationState.FAILED
    assert result.rollback_triggered == True
    assert len(result.stages) == 4  # Clarify, Implement, Validate, Rollback
    assert result.stages[-1].stage == WorkflowStage.ROLLBACK


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test pipeline status endpoint"""
    pipeline = NoHitlMasterPipeline(phi_cps_threshold=0.08)
    status = pipeline.get_status()
    assert status['lifecycle'] == LifecycleState.GENESIS.value
    assert status['stages_completed'] == 0
    assert status['phi_cps_threshold'] == 0.08
    assert len(status['intent_hash_chain']) == 0
