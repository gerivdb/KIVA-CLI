#!/usr/bin/env python3
"""
Tests for IntentAuditorCitizen
"""

import pytest
import asyncio
from tools.citizen.intent_auditor_citizen import (
    IntentAuditorCitizen,
    ValidationState,
    LifecycleState,
)


@pytest.mark.asyncio
async def test_initialization():
    """Test citizen initialization"""
    citizen = IntentAuditorCitizen()
    assert citizen.lifecycle == LifecycleState.GENESIS
    assert citizen.INTENT_HASH_PATTERN.pattern == r'^0x[A-F0-9]{16}$'


@pytest.mark.asyncio
async def test_validate_format_all_valid():
    """Test format validation with all valid hashes"""
    citizen = IntentAuditorCitizen()
    result = await citizen.execute({
        'operation': 'validate_format',
        'intent_hashes': [
            '0xA3E9F8D2C7B14506',
            '0xD7C4B3A2E8F19650',
            '0xE8F19650D7C4B3A2',
        ],
    })
    assert result.state == ValidationState.SUCCESS
    assert len(result.valid_hashes) == 3
    assert len(result.invalid_hashes) == 0
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_validate_format_with_invalid():
    """Test format validation with invalid hashes"""
    citizen = IntentAuditorCitizen()
    result = await citizen.execute({
        'operation': 'validate_format',
        'intent_hashes': [
            '0xA3E9F8D2C7B14506',  # Valid
            'invalid_hash',        # Invalid
            '0xGGGGGGGGGGGGGGGG',  # Invalid (wrong chars)
        ],
    })
    assert result.state == ValidationState.FAILED
    assert len(result.valid_hashes) == 1
    assert len(result.invalid_hashes) == 2
    assert result.confidence < 0.5


@pytest.mark.asyncio
async def test_validate_chain_continuity():
    """Test chain continuity validation"""
    citizen = IntentAuditorCitizen()
    hashes = [
        '0xA3E9F8D2C7B14506',
        '0xD7C4B3A2E8F19650',
        '0xE8F19650D7C4B3A2',
    ]
    parent_map = {
        '0xD7C4B3A2E8F19650': '0xA3E9F8D2C7B14506',
        '0xE8F19650D7C4B3A2': '0xD7C4B3A2E8F19650',
    }
    result = await citizen.execute({
        'operation': 'validate_chain',
        'intent_hashes': hashes,
        'parent_map': parent_map,
    })
    assert result.state == ValidationState.SUCCESS
    assert result.chain_continuous == True
    assert len(result.anomalies) == 0


@pytest.mark.asyncio
async def test_detect_anomalies_duplicates():
    """Test anomaly detection for duplicates"""
    citizen = IntentAuditorCitizen()
    result = await citizen.execute({
        'operation': 'detect_anomalies',
        'intent_hashes': [
            '0xA3E9F8D2C7B14506',
            '0xD7C4B3A2E8F19650',
            '0xA3E9F8D2C7B14506',  # Duplicate
        ],
    })
    assert result.state == ValidationState.FAILED
    assert len(result.anomalies) > 0
    assert any('Duplicate' in anomaly for anomaly in result.anomalies)


@pytest.mark.asyncio
async def test_execute_missing_operation():
    """Test execution with missing operation"""
    citizen = IntentAuditorCitizen()
    result = await citizen.execute({})
    assert result.state == ValidationState.FAILED
    assert "Missing operation" in result.anomalies[0]


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test citizen status endpoint"""
    citizen = IntentAuditorCitizen()
    status = citizen.get_status()
    assert status['lifecycle'] == LifecycleState.GENESIS.value
    assert 'pattern' in status
