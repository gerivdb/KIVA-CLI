"""
Tests for GlobalWALManager
"""

import pytest
import tempfile
from pathlib import Path
from kiva_cli.core.global_wal_manager import (
    GlobalWALManager, EventType, Severity, ValidationState
)

class TestGlobalWALManagerInit:
    def test_init_creates_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_wal.db")
            manager = GlobalWALManager(db_path=db_path)
            assert Path(db_path).exists()
    
    def test_init_creates_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_wal.db")
            manager = GlobalWALManager(db_path=db_path)
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()
            assert 'events' in tables
            assert 'operations' in tables
            assert 'dependencies' in tables
            assert 'rollbacks' in tables

class TestAppendEvent:
    def test_append_event_no_alert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            event_id = manager.append_event(
                event_type=EventType.COMPONENT_IMPLEMENTATION,
                ecosystem_id="test-eco",
                repositories=["repo1", "repo2"],
                phi_cps_baseline=4.0,
                phi_cps_current=4.02
            )
            event = manager.get_event(event_id)
            assert event['phi_cps_delta'] == 0.02
            assert not event['phi_cps_alert']
            assert event['validation_state'] == ValidationState.SUCCESS.value
    
    def test_append_event_with_alert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            event_id = manager.append_event(
                event_type=EventType.COMPONENT_IMPLEMENTATION,
                ecosystem_id="test-eco",
                repositories=["repo1"],
                phi_cps_baseline=4.0,
                phi_cps_current=4.10
            )
            event = manager.get_event(event_id)
            assert event['phi_cps_delta'] == 0.10
            assert event['phi_cps_alert']
            assert event['validation_state'] == ValidationState.PENDING.value
    
    def test_intent_hash_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            event_id = manager.append_event(
                event_type=EventType.VALIDATION,
                ecosystem_id="test-eco",
                repositories=["repo1"],
                phi_cps_baseline=4.0,
                phi_cps_current=4.01
            )
            event = manager.get_event(event_id)
            assert event['intent_hash'].startswith('0x')
            assert len(event['intent_hash']) == 18

class TestOperations:
    def test_add_operation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            event_id = manager.append_event(
                EventType.COMPONENT_IMPLEMENTATION,
                "test-eco",
                ["repo1"],
                4.0,
                4.01
            )
            operation_id = manager.add_operation(
                event_id=event_id,
                operation_type="CREATE_FILE",
                repository="repo1",
                status=ValidationState.SUCCESS,
                path="test/file.py",
                commit_sha="abc123"
            )
            event = manager.get_event(event_id)
            assert len(event['operations']) == 1
            assert event['operations'][0]['operation_type'] == "CREATE_FILE"
            assert event['operations'][0]['status'] == ValidationState.SUCCESS.value

class TestQuery:
    def test_query_by_ecosystem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            manager.append_event(EventType.VALIDATION, "eco1", ["r1"], 4.0, 4.01)
            manager.append_event(EventType.VALIDATION, "eco2", ["r2"], 4.0, 4.01)
            events = manager.query_events(ecosystem_id="eco1")
            assert len(events) == 1
            assert events[0]['ecosystem_id'] == "eco1"
    
    def test_query_by_event_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            manager.append_event(EventType.VALIDATION, "eco", ["r1"], 4.0, 4.01)
            manager.append_event(EventType.DEPLOYMENT, "eco", ["r1"], 4.0, 4.01)
            events = manager.query_events(event_type=EventType.DEPLOYMENT)
            assert len(events) == 1
            assert events[0]['event_type'] == EventType.DEPLOYMENT.value
    
    def test_query_phi_alert_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            manager.append_event(EventType.VALIDATION, "eco", ["r1"], 4.0, 4.01)
            manager.append_event(EventType.VALIDATION, "eco", ["r1"], 4.0, 4.10)
            events = manager.query_events(phi_cps_alert_only=True)
            assert len(events) == 1
            assert events[0]['phi_cps_alert']

class TestStatistics:
    def test_statistics_calculation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            manager.append_event(EventType.VALIDATION, "eco", ["r1"], 4.0, 4.02)
            manager.append_event(EventType.DEPLOYMENT, "eco", ["r1"], 4.02, 4.03)
            stats = manager.get_statistics(ecosystem_id="eco")
            assert stats['total_events'] == 2
            assert stats['events_by_type']['VALIDATION'] == 1
            assert stats['events_by_type']['DEPLOYMENT'] == 1
            assert stats['success_rate'] == 1.0

class TestRollback:
    def test_perform_rollback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            event_id = manager.append_event(
                EventType.COMPONENT_IMPLEMENTATION,
                "eco",
                ["r1"],
                4.0,
                4.10
            )
            rollback_id = manager.perform_rollback(
                event_id=event_id,
                reason="φ-CPS threshold exceeded",
                commits_reverted=["abc123", "def456"],
                phi_cps_before=4.10,
                phi_cps_after=4.00,
                success=True
            )
            event = manager.get_event(event_id)
            assert event['rollback_performed']
            assert event['validation_state'] == ValidationState.FAILED.value
            assert len(event['rollbacks']) == 1
            assert event['rollbacks'][0]['rollback_reason'] == "φ-CPS threshold exceeded"

class TestExport:
    def test_export_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GlobalWALManager(db_path=str(Path(tmpdir) / "test.db"))
            manager.append_event(EventType.VALIDATION, "eco", ["r1"], 4.0, 4.01)
            output = manager.export_events(format="json")
            import json
            data = json.loads(output)
            assert len(data) == 1
            assert data[0]['event_type'] == EventType.VALIDATION.value
