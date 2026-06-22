#!/usr/bin/env python3
"""Tests for PhiMonitor Daemon."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.daemon.phi_monitor_daemon import (
    PhiMonitorDaemon,
    ValidationState,
    LifecycleState,
)


class TestPhiMonitorDaemon:
    """Test suite for PhiMonitorDaemon."""

    @pytest.fixture
    def mock_ecos_root(self, tmp_path):
        """Create mock ECOS_ROOT.json."""
        ecos_path = tmp_path / "ECOS_ROOT.json"
        data = {
            "phi_cps_baseline": 4.092,
            "phi_cps_current": 4.192,
            "phi_cps_delta": 0.100,
            "phi_cps_threshold": 0.05,
        }
        with open(ecos_path, 'w') as f:
            json.dump(data, f)
        return ecos_path

    @pytest.mark.asyncio
    async def test_daemon_initialization(self, mock_ecos_root):
        """Test daemon initialization."""
        daemon = PhiMonitorDaemon(
            ecos_root_path=str(mock_ecos_root),
            check_interval=1,
        )
        
        assert daemon.lifecycle_state == LifecycleState.GENESIS
        assert daemon.validation_state == ValidationState.UNKNOWN
        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_read_ecos_root_valid(self, mock_ecos_root):
        """Test reading valid ECOS_ROOT.json."""
        daemon = PhiMonitorDaemon(ecos_root_path=str(mock_ecos_root))
        await daemon._read_ecos_root()
        
        assert daemon.phi_baseline == 4.092
        assert daemon.phi_current == 4.192
        assert daemon.phi_delta == 0.100

    @pytest.mark.asyncio
    async def test_validate_phi_drift_within_threshold(self, mock_ecos_root):
        """Test validation when drift is within threshold."""
        # Update mock to have valid drift
        with open(mock_ecos_root, 'r') as f:
            data = json.load(f)
        data["phi_cps_delta"] = 0.03
        with open(mock_ecos_root, 'w') as f:
            json.dump(data, f)
        
        daemon = PhiMonitorDaemon(ecos_root_path=str(mock_ecos_root))
        await daemon._read_ecos_root()
        daemon._validate_phi_drift()
        
        assert daemon.validation_state == ValidationState.VALID
        assert daemon.alert_triggered_at is None

    @pytest.mark.asyncio
    async def test_validate_phi_drift_exceeds_threshold(self, mock_ecos_root):
        """Test validation when drift exceeds threshold."""
        daemon = PhiMonitorDaemon(ecos_root_path=str(mock_ecos_root))
        await daemon._read_ecos_root()
        daemon._validate_phi_drift()
        
        assert daemon.validation_state == ValidationState.INVALID
        assert daemon.alert_triggered_at is not None

    @pytest.mark.asyncio
    async def test_get_status(self, mock_ecos_root):
        """Test get_status method."""
        daemon = PhiMonitorDaemon(ecos_root_path=str(mock_ecos_root))
        await daemon._read_ecos_root()
        daemon._validate_phi_drift()
        
        status = daemon.get_status()
        
        assert status["lifecycle_state"] == LifecycleState.GENESIS.value
        assert status["validation_state"] == ValidationState.INVALID.name
        assert status["phi_delta"] == 0.100
        assert status["alert_active"] is True


class TestPhiMonitorAlertLogic:
    """Test alert triggering and grace period."""

    @pytest.fixture
    def mock_ecos_root_alert(self, tmp_path):
        """Create mock ECOS_ROOT.json with alert condition."""
        ecos_path = tmp_path / "ECOS_ROOT.json"
        data = {
            "phi_cps_baseline": 4.092,
            "phi_cps_current": 4.200,
            "phi_cps_delta": 0.108,
            "phi_cps_threshold": 0.05,
        }
        with open(ecos_path, 'w') as f:
            json.dump(data, f)
        return ecos_path

    @pytest.mark.asyncio
    async def test_alert_triggers_on_threshold_exceed(self, mock_ecos_root_alert):
        """Test alert triggers when threshold exceeded."""
        daemon = PhiMonitorDaemon(
            ecos_root_path=str(mock_ecos_root_alert),
            grace_period=1,
        )
        await daemon._read_ecos_root()
        daemon._validate_phi_drift()
        
        assert daemon.validation_state == ValidationState.INVALID
        assert daemon.alert_triggered_at is not None

    @pytest.mark.asyncio
    async def test_grace_period_not_exceeded(self, mock_ecos_root_alert):
        """Test grace period not yet exceeded."""
        daemon = PhiMonitorDaemon(
            ecos_root_path=str(mock_ecos_root_alert),
            grace_period=300,  # 5 minutes
        )
        await daemon._read_ecos_root()
        daemon._validate_phi_drift()
        
        # Trigger alert
        assert daemon.alert_triggered_at is not None
        
        # Check grace period (should not trigger rollback)
        with patch.object(daemon, '_trigger_rollback') as mock_rollback:
            await daemon._monitor_cycle()
            mock_rollback.assert_not_called()


class TestTernaryStates:
    """Test ternary state transitions."""

    def test_validation_state_values(self):
        """Test ValidationState enum values."""
        assert ValidationState.PENDING.value == 0.0
        assert ValidationState.SUCCESS.value == 1.0
        assert ValidationState.FAILED.value == 0.5

    def test_lifecycle_state_values(self):
        """Test LifecycleState enum values."""
        assert LifecycleState.GENESIS.value == "GENESIS"
        assert LifecycleState.ACTIVE.value == "ACTIVE"
        assert LifecycleState.DEPRECATED.value == "DEPRECATED"
        assert LifecycleState.ARCHIVED.value == "ARCHIVED"
