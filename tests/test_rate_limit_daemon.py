#!/usr/bin/env python3
"""
Tests for RateLimitDaemon
"""

import pytest
import asyncio
from tools.daemon.rate_limit_daemon import (
    RateLimitDaemon,
    ValidationState,
    LifecycleState,
)


@pytest.mark.asyncio
async def test_initialization():
    """Test daemon initialization"""
    daemon = RateLimitDaemon(alert_threshold=0.8, check_interval=60)
    assert daemon.alert_threshold == 0.8
    assert daemon.check_interval == 60
    assert daemon.lifecycle == LifecycleState.GENESIS
    assert daemon.running == False
    assert daemon.alert_triggered == False


@pytest.mark.asyncio
async def test_check_rate_limit():
    """Test rate limit checking"""
    daemon = RateLimitDaemon(alert_threshold=0.8)
    status = await daemon._check_rate_limit()
    assert status.limit > 0
    assert status.remaining >= 0
    assert 0.0 <= status.usage_percent <= 1.0
    assert status.state in [ValidationState.SUCCESS, ValidationState.FAILED]


@pytest.mark.asyncio
async def test_alert_trigger():
    """Test alert triggering at threshold"""
    daemon = RateLimitDaemon(alert_threshold=0.5)  # Low threshold
    status = await daemon._check_rate_limit()
    # With mock data (24% remaining = 76% used), should trigger alert
    assert status.usage_percent > 0.5
    assert status.alert_triggered == True
    assert status.state == ValidationState.FAILED


@pytest.mark.asyncio
async def test_handle_alert():
    """Test alert handling"""
    daemon = RateLimitDaemon(alert_threshold=0.8)
    status = await daemon._check_rate_limit()
    # Should not raise exception
    await daemon._handle_alert(status)


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    daemon = RateLimitDaemon()
    health = await daemon.health_check()
    assert 'healthy' in health
    assert 'lifecycle' in health
    assert 'rate_limit_status' in health
    assert health['lifecycle'] == LifecycleState.GENESIS.value


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test daemon status endpoint"""
    daemon = RateLimitDaemon(alert_threshold=0.75, check_interval=120)
    status = daemon.get_status()
    assert status['lifecycle'] == LifecycleState.GENESIS.value
    assert status['running'] == False
    assert status['alert_threshold'] == 0.75
    assert status['check_interval'] == 120
    assert status['alert_triggered'] == False
