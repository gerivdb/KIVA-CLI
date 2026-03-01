#!/usr/bin/env python3
"""Tests for AutoRollback Pipeline."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from tools.pipeline.auto_rollback_pipeline import (
    AutoRollbackPipeline,
    ValidationState,
)


class TestAutoRollbackPipeline:
    """Test suite for AutoRollbackPipeline."""

    @pytest.fixture
    def mock_ecos_root(self, tmp_path):
        """Create mock ECOS_ROOT.json with recent operations."""
        ecos_path = tmp_path / "ECOS_ROOT.json"
        data = {
            "phi_cps_baseline": 4.092,
            "phi_cps_current": 4.200,
            "phi_cps_delta": 0.108,
            "phi_cps_threshold": 0.05,
            "recent_operations": [
                {
                    "operation": "VALID_OP",
                    "commit": "abc123",
                    "phi_cps_delta": 0.03,
                    "repository": "KIVA-CLI",
                },
                {
                    "operation": "PROBLEMATIC_OP_1",
                    "commit": "def456",
                    "phi_cps_delta": 0.04,
                    "repository": "KIVA-CLI",
                },
                {
                    "operation": "PROBLEMATIC_OP_2",
                    "commit": "ghi789",
                    "phi_cps_delta": 0.038,
                    "repository": "KIVA-CLI",
                },
            ],
        }
        with open(ecos_path, 'w') as f:
            json.dump(data, f)
        return ecos_path

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, mock_ecos_root):
        """Test pipeline initialization."""
        pipeline = AutoRollbackPipeline(ecos_root_path=str(mock_ecos_root))
        
        assert pipeline.state == ValidationState.PENDING
        assert len(pipeline.rollback_log) == 0

    @pytest.mark.asyncio
    async def test_read_ecos_root(self, mock_ecos_root):
        """Test reading ECOS_ROOT.json."""
        pipeline = AutoRollbackPipeline(ecos_root_path=str(mock_ecos_root))
        data = await pipeline._read_ecos_root()
        
        assert data is not None
        assert data["phi_cps_delta"] == 0.108
        assert len(data["recent_operations"]) == 3

    @pytest.mark.asyncio
    async def test_find_last_valid_operation(self, mock_ecos_root):
        """Test finding last valid operation."""
        pipeline = AutoRollbackPipeline(ecos_root_path=str(mock_ecos_root))
        data = await pipeline._read_ecos_root()
        last_valid = await pipeline._find_last_valid_operation(data)
        
        assert last_valid is not None
        assert last_valid["operation"] == "VALID_OP"
        assert last_valid["commit"] == "abc123"

    @pytest.mark.asyncio
    async def test_identify_commits_to_revert(self, mock_ecos_root):
        """Test identifying commits to revert."""
        pipeline = AutoRollbackPipeline(ecos_root_path=str(mock_ecos_root))
        data = await pipeline._read_ecos_root()
        last_valid = await pipeline._find_last_valid_operation(data)
        commits = await pipeline._identify_commits_to_revert(data, last_valid)
        
        assert len(commits) == 2
        assert commits[0]["sha"] == "ghi789"  # Most recent first
        assert commits[1]["sha"] == "def456"

    @pytest.mark.asyncio
    async def test_update_ecos_root_restores_state(self, mock_ecos_root):
        """Test ECOS_ROOT.json restoration."""
        pipeline = AutoRollbackPipeline(ecos_root_path=str(mock_ecos_root))
        data = await pipeline._read_ecos_root()
        last_valid = await pipeline._find_last_valid_operation(data)
        
        success = await pipeline._update_ecos_root(last_valid)
        
        assert success is True
        
        # Verify restored state
        with open(mock_ecos_root, 'r') as f:
            restored = json.load(f)
        
        assert restored["phi_cps_delta"] == 0.03
        assert restored["phi_cps_alert"] is False
        assert restored["phi_cps_status"] == "ROLLBACK_RESTORED"

    @pytest.mark.asyncio
    async def test_rollback_log_entries(self, mock_ecos_root):
        """Test rollback log entries are created."""
        pipeline = AutoRollbackPipeline(ecos_root_path=str(mock_ecos_root))
        data = await pipeline._read_ecos_root()
        last_valid = await pipeline._find_last_valid_operation(data)
        
        await pipeline._update_ecos_root(last_valid)
        await pipeline._restore_wal_entries(last_valid)
        
        assert len(pipeline.rollback_log) >= 2
        assert any(log["action"] == "UPDATE_ECOS_ROOT" for log in pipeline.rollback_log)
        assert any(log["action"] == "RESTORE_WAL" for log in pipeline.rollback_log)


class TestRollbackSafetyLimits:
    """Test safety limits for rollback."""

    @pytest.fixture
    def mock_many_commits(self, tmp_path):
        """Create ECOS_ROOT with many commits to revert."""
        ecos_path = tmp_path / "ECOS_ROOT.json"
        
        # Create 15 problematic operations
        operations = [{
            "operation": "VALID_OP",
            "commit": "valid123",
            "phi_cps_delta": 0.02,
            "repository": "KIVA-CLI",
        }]
        
        for i in range(15):
            operations.append({
                "operation": f"PROBLEMATIC_OP_{i}",
                "commit": f"commit{i:03d}",
                "phi_cps_delta": 0.01,
                "repository": "KIVA-CLI",
            })
        
        data = {
            "phi_cps_baseline": 4.092,
            "phi_cps_current": 4.242,
            "phi_cps_delta": 0.150,
            "phi_cps_threshold": 0.05,
            "recent_operations": operations,
        }
        
        with open(ecos_path, 'w') as f:
            json.dump(data, f)
        return ecos_path

    @pytest.mark.asyncio
    async def test_max_commits_safety_limit(self, mock_many_commits):
        """Test max commits safety limit prevents excessive rollback."""
        pipeline = AutoRollbackPipeline(
            ecos_root_path=str(mock_many_commits),
            max_commits_to_revert=10,
        )
        
        result = await pipeline.execute()
        
        assert result["status"] == "FAILED"
        assert "Too many commits" in result["error"]
        assert pipeline.state == ValidationState.FAILED


class TestTernaryValidationStates:
    """Test ternary validation states in rollback."""

    def test_validation_state_values(self):
        """Test ValidationState enum values."""
        assert ValidationState.PENDING.value == 0.0
        assert ValidationState.SUCCESS.value == 1.0
        assert ValidationState.FAILED.value == 0.5

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self, tmp_path):
        """Test state transitions during pipeline execution."""
        # Create minimal valid ECOS_ROOT
        ecos_path = tmp_path / "ECOS_ROOT.json"
        data = {
            "phi_cps_baseline": 4.092,
            "phi_cps_current": 4.092,
            "phi_cps_delta": 0.0,
            "phi_cps_threshold": 0.05,
            "recent_operations": [],
        }
        with open(ecos_path, 'w') as f:
            json.dump(data, f)
        
        pipeline = AutoRollbackPipeline(ecos_root_path=str(ecos_path))
        
        # Initial state
        assert pipeline.state == ValidationState.PENDING
        
        # Execute (will fail due to no operations)
        result = await pipeline.execute()
        
        # Should transition to FAILED
        assert pipeline.state == ValidationState.FAILED
        assert result["status"] == "FAILED"
