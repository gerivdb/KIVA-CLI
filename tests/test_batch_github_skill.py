#!/usr/bin/env python3
"""
Tests for BatchGitHubSkill
"""

import pytest
import asyncio
from tools.skill.batch_github_skill import (
    BatchGitHubSkill,
    ValidationState,
    LifecycleState,
)


@pytest.mark.asyncio
async def test_initialization():
    """Test skill initialization"""
    skill = BatchGitHubSkill()
    assert skill.MAX_BATCH_SIZE == 50
    assert skill.lifecycle == LifecycleState.GENESIS


@pytest.mark.asyncio
async def test_execute_missing_operation():
    """Test execution with missing operation"""
    skill = BatchGitHubSkill()
    result = await skill.execute({})
    assert result.state == ValidationState.FAILED
    assert "Missing operation" in result.failed[0]['error']
    assert result.total == 0


@pytest.mark.asyncio
async def test_batch_create_issues_success():
    """Test batch create issues success"""
    skill = BatchGitHubSkill()
    issues = [{'title': f'Issue {i}', 'body': f'Body {i}'} for i in range(10)]
    result = await skill.execute({
        'operation': 'batch_create_issues',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'issues': issues,
    })
    assert result.state == ValidationState.SUCCESS
    assert len(result.successful) == 10
    assert len(result.failed) == 0
    assert result.total == 10
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_batch_update_issues_success():
    """Test batch update issues success"""
    skill = BatchGitHubSkill()
    updates = [{'number': i, 'state': 'closed'} for i in range(1, 6)]
    result = await skill.execute({
        'operation': 'batch_update_issues',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'updates': updates,
    })
    assert result.state == ValidationState.SUCCESS
    assert len(result.successful) == 5
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_batch_close_issues_success():
    """Test batch close issues success"""
    skill = BatchGitHubSkill()
    result = await skill.execute({
        'operation': 'batch_close_issues',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'issue_numbers': [1, 2, 3, 4, 5],
    })
    assert result.state == ValidationState.SUCCESS
    assert len(result.successful) == 5
    assert all(item['state'] == 'closed' for item in result.successful)


@pytest.mark.asyncio
async def test_batch_merge_prs_success():
    """Test batch merge PRs success"""
    skill = BatchGitHubSkill()
    result = await skill.execute({
        'operation': 'batch_merge_prs',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'pr_numbers': [10, 11, 12],
    })
    assert result.state == ValidationState.SUCCESS
    assert len(result.successful) == 3
    assert all(item['merged'] for item in result.successful)


@pytest.mark.asyncio
async def test_batch_add_labels_success():
    """Test batch add labels success"""
    skill = BatchGitHubSkill()
    items = [
        {'number': 1, 'labels': ['bug', 'critical']},
        {'number': 2, 'labels': ['feature']},
    ]
    result = await skill.execute({
        'operation': 'batch_add_labels',
        'owner': 'gerivdb',
        'repo': 'KIVA-CLI',
        'items': items,
    })
    assert result.state == ValidationState.SUCCESS
    assert len(result.successful) == 2


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test skill status endpoint"""
    skill = BatchGitHubSkill()
    status = skill.get_status()
    assert status['lifecycle'] == LifecycleState.GENESIS.value
    assert status['max_batch_size'] == 50
