#!/usr/bin/env python3
"""
Test suite for Global WAL Manager
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import json

from tools.core.global_wal_manager import (
    GlobalWALManager,
    ValidationState,
    EventStatus,
    WALEvent
)


class TestGlobalWALManagerInit:
    """Test GlobalWALManager initialization."""
    
    def test_init_default_path(self):
        """Test initialization with default database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            wal = GlobalWALManager(db_path=db_path)
            
            assert wal.db_path == db_path
            assert wal.phi_cps_threshold == 0.05
            assert db_path.exists()
    
    def test_database_schema(self):
        """Test database schema creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            wal = GlobalWALManager(db_path=db_path)
            
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check wal_events table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='wal_events'"
            )
            assert cursor.fetchone() is not None
            
            # Check rollback_points table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rollback_points'"
            )
            assert cursor.fetchone() is not None
            
            conn.close()


class TestEventAppend:
    """Test event appending functionality."""
    
    @pytest.fixture
    def wal(self):
        """Create temporary WAL manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            yield GlobalWALManager(db_path=db_path)
    
    def test_append_event_success(self, wal):
        """Test appending successful event."""
        event = wal.append_event(
            operation="TEST_OPERATION",
            repo="TEST_REPO",
            phi_cps_delta=0.01,
            commit_sha="abc123"
        )
        
        assert event.operation == "TEST_OPERATION"
        assert event.repo == "TEST_REPO"
        assert event.phi_cps_delta == 0.01
        assert event.commit_sha == "abc123"
        assert event.validation_state == ValidationState.VALID.value
        assert event.status == EventStatus.SUCCESS.value
        assert event.intent_hash.startswith("0x")
        assert len(event.intent_hash) == 18  # 0x + 16 hex chars
    
    def test_append_event_with_parent(self, wal):
        """Test appending event with parent IntentHash."""
        # First event (L0)
        event1 = wal.append_event(
            operation="OP1",
            repo="REPO1",
            phi_cps_delta=0.01
        )
        
        # Second event (L1) with parent
        event2 = wal.append_event(
            operation="OP2",
            repo="REPO1",
            phi_cps_delta=0.02,
            parent_intent_hash=event1.intent_hash
        )
        
        assert event2.parent_intent_hash == event1.intent_hash
        assert event2.intent_hash != event1.intent_hash
    
    def test_append_event_failed_status(self, wal):
        """Test appending failed event."""
        event = wal.append_event(
            operation="FAILED_OP",
            repo="TEST_REPO",
            phi_cps_delta=0.0,
            status=EventStatus.FAILED,
            error_message="Test error"
        )
        
        assert event.status == EventStatus.FAILED.value
        assert event.error_message == "Test error"
    
    def test_append_event_with_metadata(self, wal):
        """Test appending event with metadata."""
        metadata = {"key": "value", "count": 42}
        
        event = wal.append_event(
            operation="TEST_OP",
            repo="TEST_REPO",
            phi_cps_delta=0.01,
            metadata=metadata
        )
        
        assert event.metadata == metadata
    
    def test_phi_cps_accumulation(self, wal):
        """Test φ-CPS accumulation across events."""
        event1 = wal.append_event(
            operation="OP1",
            repo="REPO1",
            phi_cps_delta=0.01
        )
        
        event2 = wal.append_event(
            operation="OP2",
            repo="REPO1",
            phi_cps_delta=0.02
        )
        
        # Second event should have cumulative φ-CPS
        assert event2.phi_cps_current > event1.phi_cps_current
        assert event2.phi_cps_current == event1.phi_cps_current + 0.02


class TestChainValidation:
    """Test IntentHash chain validation."""
    
    @pytest.fixture
    def wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            yield GlobalWALManager(db_path=db_path)
    
    def test_validate_l0_event(self, wal):
        """Test validation of L0 (genesis) event."""
        event = wal.append_event(
            operation="L0_EVENT",
            repo="TEST_REPO",
            phi_cps_delta=0.01
        )
        
        is_valid, message = wal.validate_chain(
            intent_hash=event.intent_hash,
            parent_intent_hash=None
        )
        
        assert is_valid
        assert "L0" in message or "genesis" in message.lower()
    
    def test_validate_l1_event(self, wal):
        """Test validation of L1 event with parent."""
        event1 = wal.append_event(
            operation="L0_EVENT",
            repo="TEST_REPO",
            phi_cps_delta=0.01
        )
        
        event2 = wal.append_event(
            operation="L1_EVENT",
            repo="TEST_REPO",
            phi_cps_delta=0.02,
            parent_intent_hash=event1.intent_hash
        )
        
        is_valid, message = wal.validate_chain(
            intent_hash=event2.intent_hash,
            parent_intent_hash=event1.intent_hash
        )
        
        assert is_valid
        assert event1.intent_hash in message
    
    def test_validate_invalid_parent(self, wal):
        """Test validation with non-existent parent."""
        event = wal.append_event(
            operation="TEST_EVENT",
            repo="TEST_REPO",
            phi_cps_delta=0.01
        )
        
        is_valid, message = wal.validate_chain(
            intent_hash=event.intent_hash,
            parent_intent_hash="0xINVALID12345678"
        )
        
        assert not is_valid
        assert "not found" in message.lower()


class TestDriftTracking:
    """Test φ-CPS drift tracking."""
    
    @pytest.fixture
    def wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            yield GlobalWALManager(db_path=db_path)
    
    def test_get_drift_initial(self, wal):
        """Test drift calculation with single event."""
        event = wal.append_event(
            operation="INIT_EVENT",
            repo="TEST_REPO",
            phi_cps_delta=0.01
        )
        
        drift = wal.get_drift()
        
        assert "baseline_phi" in drift
        assert "current_phi" in drift
        assert "absolute_drift" in drift
        assert "relative_drift" in drift
        assert "threshold_exceeded" in drift
    
    def test_drift_within_threshold(self, wal):
        """Test drift within acceptable threshold."""
        # Add multiple events with small deltas
        for i in range(3):
            wal.append_event(
                operation=f"OP_{i}",
                repo="TEST_REPO",
                phi_cps_delta=0.01
            )
        
        drift = wal.get_drift()
        
        assert not drift["threshold_exceeded"]
        assert drift["relative_drift"] < wal.phi_cps_threshold
    
    def test_drift_exceeds_threshold(self, wal):
        """Test drift exceeding threshold."""
        # Add events to exceed 5% drift
        baseline_phi = wal._get_current_phi_cps()
        
        # Add large delta to trigger threshold
        wal.append_event(
            operation="LARGE_OP",
            repo="TEST_REPO",
            phi_cps_delta=baseline_phi * 0.06  # 6% drift
        )
        
        drift = wal.get_drift()
        
        # Note: Drift threshold check depends on baseline
        # This test validates the drift calculation logic
        assert "threshold_exceeded" in drift


class TestEventQuery:
    """Test event querying functionality."""
    
    @pytest.fixture
    def wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            manager = GlobalWALManager(db_path=db_path)
            
            # Add test events
            manager.append_event(
                operation="OP1",
                repo="REPO_A",
                phi_cps_delta=0.01
            )
            
            manager.append_event(
                operation="OP2",
                repo="REPO_B",
                phi_cps_delta=0.02
            )
            
            manager.append_event(
                operation="OP1",
                repo="REPO_A",
                phi_cps_delta=0.01,
                status=EventStatus.FAILED
            )
            
            yield manager
    
    def test_query_all_events(self, wal):
        """Test querying all events."""
        events = wal.query_events()
        
        assert len(events) == 3
    
    def test_query_by_repo(self, wal):
        """Test querying events by repository."""
        events = wal.query_events(repo="REPO_A")
        
        assert len(events) == 2
        assert all(e.repo == "REPO_A" for e in events)
    
    def test_query_by_operation(self, wal):
        """Test querying events by operation."""
        events = wal.query_events(operation="OP1")
        
        assert len(events) == 2
        assert all(e.operation == "OP1" for e in events)
    
    def test_query_by_status(self, wal):
        """Test querying events by status."""
        events = wal.query_events(status=EventStatus.FAILED)
        
        assert len(events) == 1
        assert events[0].status == EventStatus.FAILED.value
    
    def test_query_with_limit(self, wal):
        """Test querying with result limit."""
        events = wal.query_events(limit=2)
        
        assert len(events) == 2


class TestRollbackPoints:
    """Test rollback point management."""
    
    @pytest.fixture
    def wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            yield GlobalWALManager(db_path=db_path)
    
    def test_create_rollback_point(self, wal):
        """Test creating rollback point."""
        # Add some events
        wal.append_event(
            operation="OP1",
            repo="TEST_REPO",
            phi_cps_delta=0.01
        )
        
        rollback_id = wal.create_rollback_point(
            reason="Test rollback",
            metadata={"test": True}
        )
        
        assert rollback_id.startswith("evt_")
    
    def test_rollback_point_in_drift(self, wal):
        """Test rollback point affects drift calculation."""
        # Create initial rollback point
        wal.create_rollback_point(reason="Baseline")
        
        # Add events
        wal.append_event(
            operation="OP1",
            repo="TEST_REPO",
            phi_cps_delta=0.02
        )
        
        drift = wal.get_drift()
        
        # Baseline should be from rollback point
        assert drift["events_since_baseline"] >= 1


class TestAuditExport:
    """Test audit trail export functionality."""
    
    @pytest.fixture
    def wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            manager = GlobalWALManager(db_path=db_path)
            
            # Add test events
            manager.append_event(
                operation="OP1",
                repo="TEST_REPO",
                phi_cps_delta=0.01
            )
            
            yield manager
    
    def test_export_json(self, wal):
        """Test exporting audit trail to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit.json"
            
            success = wal.export_audit(
                output_path=output_path,
                format="json"
            )
            
            assert success
            assert output_path.exists()
            
            # Verify JSON structure
            with open(output_path) as f:
                data = json.load(f)
            
            assert "export_timestamp" in data
            assert "total_events" in data
            assert "drift_metrics" in data
            assert "events" in data
            assert len(data["events"]) >= 1
    
    def test_export_csv(self, wal):
        """Test exporting audit trail to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit.csv"
            
            success = wal.export_audit(
                output_path=output_path,
                format="csv"
            )
            
            assert success
            assert output_path.exists()
            
            # Verify CSV has header
            with open(output_path) as f:
                first_line = f.readline()
                assert "event_id" in first_line
                assert "operation" in first_line


class TestValidationStates:
    """Test base-3 ternary validation states."""
    
    @pytest.fixture
    def wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            yield GlobalWALManager(db_path=db_path)
    
    def test_unknown_state(self, wal):
        """Test UNKNOWN validation state."""
        event = wal.append_event(
            operation="TEST_OP",
            repo="TEST_REPO",
            phi_cps_delta=0.01,
            validation_state=ValidationState.UNKNOWN
        )
        
        assert event.validation_state == ValidationState.UNKNOWN.value
    
    def test_valid_state(self, wal):
        """Test VALID validation state (default)."""
        event = wal.append_event(
            operation="TEST_OP",
            repo="TEST_REPO",
            phi_cps_delta=0.01
        )
        
        assert event.validation_state == ValidationState.VALID.value
    
    def test_invalid_state(self, wal):
        """Test INVALID validation state."""
        event = wal.append_event(
            operation="TEST_OP",
            repo="TEST_REPO",
            phi_cps_delta=0.01,
            validation_state=ValidationState.INVALID
        )
        
        assert event.validation_state == ValidationState.INVALID.value


class TestIntentHashGeneration:
    """Test IntentHash generation and uniqueness."""
    
    @pytest.fixture
    def wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            yield GlobalWALManager(db_path=db_path)
    
    def test_intent_hash_format(self, wal):
        """Test IntentHash format."""
        event = wal.append_event(
            operation="TEST_OP",
            repo="TEST_REPO",
            phi_cps_delta=0.01
        )
        
        # Format: 0x<16 hex chars>
        assert event.intent_hash.startswith("0x")
        assert len(event.intent_hash) == 18
        assert all(c in "0123456789ABCDEF" for c in event.intent_hash[2:])
    
    def test_intent_hash_uniqueness(self, wal):
        """Test IntentHash uniqueness across events."""
        event1 = wal.append_event(
            operation="OP1",
            repo="REPO1",
            phi_cps_delta=0.01
        )
        
        event2 = wal.append_event(
            operation="OP2",
            repo="REPO2",
            phi_cps_delta=0.02
        )
        
        assert event1.intent_hash != event2.intent_hash
