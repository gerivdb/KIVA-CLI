#!/usr/bin/env python3
"""
Tests for CometFallbackSkill
"""

import pytest
import asyncio
from tools.skill.comet_fallback_skill import (
    CometFallbackSkill,
    ValidationState,
    LifecycleState,
)


@pytest.mark.asyncio
async def test_initialization():
    """Test skill initialization"""
    skill = CometFallbackSkill(max_retries=3, retry_delay=2.0)
    assert skill.max_retries == 3
    assert skill.retry_delay == 2.0
    assert skill.lifecycle == LifecycleState.GENESIS


@pytest.mark.asyncio
async def test_execute_missing_action():
    """Test execution with missing action parameter"""
    skill = CometFallbackSkill()
    result = await skill.execute({})
    assert result.state == ValidationState.FAILED
    assert "Missing required 'action' parameter" in result.error
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_execute_unknown_action():
    """Test execution with unknown action"""
    skill = CometFallbackSkill()
    result = await skill.execute({'action': 'unknown_action'})
    assert result.state == ValidationState.FAILED
    assert "Unknown action" in result.error


@pytest.mark.asyncio
async def test_list_issues_success():
    """Test list issues fallback success"""
    skill = CometFallbackSkill()
    result = await skill.execute({
        'action': 'list_issues',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'state': 'open',
    })
    assert result.state == ValidationState.SUCCESS
    assert result.data is not None
    assert 'issues' in result.data
    assert result.confidence >= 0.9
    assert skill.lifecycle == LifecycleState.ACTIVE


@pytest.mark.asyncio
async def test_get_pull_request_success():
    """Test get pull request fallback success"""
    skill = CometFallbackSkill()
    result = await skill.execute({
        'action': 'get_pr',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'pr_number': 42,
    })
    assert result.state == ValidationState.SUCCESS
    assert result.data is not None
    assert result.data['number'] == 42
    assert result.confidence >= 0.85


@pytest.mark.asyncio
async def test_list_commits_success():
    """Test list commits fallback success"""
    skill = CometFallbackSkill()
    result = await skill.execute({
        'action': 'list_commits',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'branch': 'main',
    })
    assert result.state == ValidationState.SUCCESS
    assert result.data is not None
    assert 'commits' in result.data
    assert result.confidence >= 0.85


@pytest.mark.asyncio
async def test_get_file_contents_success():
    """Test get file contents fallback success"""
    skill = CometFallbackSkill()
    result = await skill.execute({
        'action': 'get_file',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'path': 'README.md',
        'branch': 'main',
    })
    assert result.state == ValidationState.SUCCESS
    assert result.data is not None
    assert result.data['path'] == 'README.md'
    assert result.confidence >= 0.8


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test skill status endpoint"""
    skill = CometFallbackSkill(max_retries=5, retry_delay=1.5)
    status = skill.get_status()
    assert status['lifecycle'] == LifecycleState.GENESIS.value
    assert status['max_retries'] == 5
    assert status['retry_delay'] == 1.5
