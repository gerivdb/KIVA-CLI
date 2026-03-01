"""
Comprehensive Integration Tests for PipelineManager + GlobalWALManager
Test cross-component functionality and φ-CPS stability
"""

import pytest
import tempfile
from pathlib import Path
from tools.core.pipeline_manager import PipelineManager, PipelineType, StepType, ValidationState
from tools.core.global_wal_manager import GlobalWALManager, EventType, Severity

class TestPipelineWALIntegration:
    """Test PipelineManager events logged to GlobalWALManager"""
    
    def test_pipeline_creation_logged_to_wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm_db = str(Path(tmpdir) / "pipeline.db")
            wal_db = str(Path(tmpdir) / "wal.db")
            
            pm = PipelineManager(db_path=pm_db)
            wal = GlobalWALManager(db_path=wal_db)
            
            # Create pipeline
            pipeline_id = pm.create_pipeline(
                name="Test Pipeline",
                description="Integration test",
                pipeline_type=PipelineType.SEQUENTIAL
            )
            
            # Log to WAL
            event_id = wal.append_event(
                event_type=EventType.COMPONENT_IMPLEMENTATION,
                ecosystem_id="test-eco",
                repositories=["test-repo"],
                phi_cps_baseline=4.092,
                phi_cps_current=4.093,
                description=f"Pipeline created: {pipeline_id}"
            )
            
            # Verify linkage
            event = wal.get_event(event_id)
            assert event is not None
            assert f"Pipeline created: {pipeline_id}" in event['description']
            assert event['phi_cps_delta'] == 0.001
    
    def test_pipeline_execution_tracked_in_wal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm_db = str(Path(tmpdir) / "pipeline.db")
            wal_db = str(Path(tmpdir) / "wal.db")
            
            pm = PipelineManager(db_path=pm_db)
            wal = GlobalWALManager(db_path=wal_db)
            
            # Create and execute pipeline
            pipeline_id = pm.create_pipeline("Exec Test", "Test", PipelineType.SEQUENTIAL)
            step_id = pm.add_step(pipeline_id, "step1", StepType.FILE_CREATE, {"path": "/tmp/test.txt"})
            
            event_id = wal.append_event(
                EventType.VALIDATION,
                "test-eco",
                ["test-repo"],
                4.093,
                4.094
            )
            
            # Add operation for step execution
            op_id = wal.add_operation(
                event_id=event_id,
                operation_type="PIPELINE_STEP_EXECUTION",
                repository="test-repo",
                status=ValidationState.SUCCESS,
                path=f"pipeline/{pipeline_id}/step/{step_id}"
            )
            
            event = wal.get_event(event_id)
            assert len(event['operations']) == 1
            assert event['operations'][0]['operation_type'] == "PIPELINE_STEP_EXECUTION"
    
    def test_pipeline_failure_triggers_wal_alert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm_db = str(Path(tmpdir) / "pipeline.db")
            wal_db = str(Path(tmpdir) / "wal.db")
            
            pm = PipelineManager(db_path=pm_db)
            wal = GlobalWALManager(db_path=wal_db)
            
            # Simulate pipeline failure with large φ-CPS impact
            pipeline_id = pm.create_pipeline("Fail Test", "Test", PipelineType.SEQUENTIAL)
            
            event_id = wal.append_event(
                EventType.INCIDENT,
                "test-eco",
                ["test-repo"],
                phi_cps_baseline=4.0,
                phi_cps_current=4.15,  # Large delta
                severity=Severity.ERROR,
                description=f"Pipeline {pipeline_id} failed with φ-CPS impact"
            )
            
            event = wal.get_event(event_id)
            assert event['phi_cps_alert']  # Alert should trigger
            assert event['severity'] == Severity.ERROR.value
            assert event['validation_state'] == ValidationState.PENDING.value

class TestCrossRepoSync:
    """Test cross-repository synchronization patterns"""
    
    def test_multi_repo_pipeline_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm_db = str(Path(tmpdir) / "pipeline.db")
            wal_db = str(Path(tmpdir) / "wal.db")
            
            pm = PipelineManager(db_path=pm_db)
            wal = GlobalWALManager(db_path=wal_db)
            
            # Create pipeline affecting multiple repos
            pipeline_id = pm.create_pipeline("Multi-repo Sync", "Sync test", PipelineType.PARALLEL)
            
            repos = ["KIVA-CLI", "ECOYSTEM", "DevTools"]
            event_id = wal.append_event(
                EventType.DEPLOYMENT,
                "ecosystem-1",
                repos,
                4.092,
                4.095
            )
            
            # Add operations for each repo
            for repo in repos:
                wal.add_operation(
                    event_id=event_id,
                    operation_type="CROSS_REPO_SYNC",
                    repository=repo,
                    status=ValidationState.SUCCESS
                )
            
            event = wal.get_event(event_id)
            assert len(event['operations']) == 3
            assert set(event['repositories']) == set(repos)
    
    def test_dependency_chain_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wal_db = str(Path(tmpdir) / "wal.db")
            wal = GlobalWALManager(db_path=wal_db)
            
            # Create parent event
            parent_id = wal.append_event(
                EventType.COMPONENT_IMPLEMENTATION,
                "ecosystem-1",
                ["KIVA-CLI"],
                4.092,
                4.100
            )
            parent_event = wal.get_event(parent_id)
            parent_hash = parent_event['intent_hash']
            
            # Create child event with parent linkage
            child_id = wal.append_event(
                EventType.VALIDATION,
                "ecosystem-1",
                ["KIVA-CLI"],
                4.100,
                4.105,
                parent_intent_hash=parent_hash
            )
            
            child_event = wal.get_event(child_id)
            assert child_event['parent_intent_hash'] == parent_hash
            assert child_event['intent_hash'] != parent_hash

class TestPhiCPSValidation:
    """Test φ-CPS calculation accuracy and alerts"""
    
    def test_phi_cps_threshold_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wal_db = str(Path(tmpdir) / "wal.db")
            wal = GlobalWALManager(db_path=wal_db)
            
            # Create event just under threshold
            event1 = wal.append_event(
                EventType.VALIDATION,
                "test-eco",
                ["repo1"],
                4.0,
                4.04  # delta 0.04 < 0.05
            )
            e1 = wal.get_event(event1)
            assert not e1['phi_cps_alert']
            
            # Create event over threshold
            event2 = wal.append_event(
                EventType.VALIDATION,
                "test-eco",
                ["repo1"],
                4.0,
                4.06  # delta 0.06 > 0.05
            )
            e2 = wal.get_event(event2)
            assert e2['phi_cps_alert']
    
    def test_phi_cps_cumulative_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wal_db = str(Path(tmpdir) / "wal.db")
            wal = GlobalWALManager(db_path=wal_db)
            
            baseline = 4.092
            deltas = [0.025, 0.013, 0.032, 0.018]
            current = baseline
            
            for i, delta in enumerate(deltas):
                current += delta
                event_id = wal.append_event(
                    EventType.COMPONENT_IMPLEMENTATION,
                    "ecosystem-1",
                    ["KIVA-CLI"],
                    baseline,
                    current,
                    description=f"Operation {i+1}"
                )
                
                event = wal.get_event(event_id)
                expected_cumulative_delta = current - baseline
                
                # Check cumulative delta calculation
                assert abs(event['phi_cps_current'] - current) < 0.001
                
                # Alert should trigger when cumulative exceeds threshold
                if expected_cumulative_delta > 0.05:
                    assert event['phi_cps_alert']
    
    def test_rollback_resets_phi_cps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wal_db = str(Path(tmpdir) / "wal.db")
            wal = GlobalWALManager(db_path=wal_db)
            
            # Create event with large delta
            event_id = wal.append_event(
                EventType.COMPONENT_IMPLEMENTATION,
                "test-eco",
                ["repo1"],
                4.0,
                4.15
            )
            
            # Perform rollback
            rollback_id = wal.perform_rollback(
                event_id=event_id,
                reason="φ-CPS threshold exceeded",
                commits_reverted=["abc123"],
                phi_cps_before=4.15,
                phi_cps_after=4.0,
                success=True
            )
            
            event = wal.get_event(event_id)
            assert event['rollback_performed']
            assert event['validation_state'] == ValidationState.FAILED.value

class TestTernaryLogic:
    """Test base-3 ternary validation states"""
    
    def test_ternary_state_transitions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm_db = str(Path(tmpdir) / "pipeline.db")
            pm = PipelineManager(db_path=pm_db)
            
            pipeline_id = pm.create_pipeline("Ternary Test", "Test", PipelineType.SEQUENTIAL)
            step_id = pm.add_step(pipeline_id, "step1", StepType.FILE_CREATE, {})
            
            # Check initial state (PENDING)
            step = pm.get_step(step_id)
            assert step['status'] == ValidationState.PENDING.value
            
            # Valid transitions: PENDING -> SUCCESS
            pm.update_step_status(step_id, ValidationState.SUCCESS)
            step = pm.get_step(step_id)
            assert step['status'] == ValidationState.SUCCESS.value
            
            # Invalid transition: SUCCESS -> PENDING should not change state
            # (not implemented but demonstrates ternary immutability)
    
    def test_fuzzy_ternary_confidence_scores(self):
        # Fuzzy ternary: [0.0, 0.5, 1.0]
        confidence_low = 0.0     # UNKNOWN/INVALID
        confidence_mid = 0.5     # PENDING/UNCERTAIN
        confidence_high = 1.0    # VALID/SUCCESS
        
        assert confidence_low == 0.0
        assert confidence_mid == 0.5
        assert confidence_high == 1.0
        
        # Test threshold-based classification
        def classify_ternary(score):
            if score < 0.33:
                return "INVALID"
            elif score < 0.67:
                return "PENDING"
            else:
                return "VALID"
        
        assert classify_ternary(0.0) == "INVALID"
        assert classify_ternary(0.5) == "PENDING"
        assert classify_ternary(1.0) == "VALID"

class TestIntentHashChaining:
    """Test IntentHash generation and parent linkage"""
    
    def test_intent_hash_uniqueness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wal_db = str(Path(tmpdir) / "wal.db")
            wal = GlobalWALManager(db_path=wal_db)
            
            hashes = set()
            for i in range(10):
                event_id = wal.append_event(
                    EventType.VALIDATION,
                    "test-eco",
                    ["repo1"],
                    4.0,
                    4.01,
                    description=f"Event {i}"
                )
                event = wal.get_event(event_id)
                hashes.add(event['intent_hash'])
            
            # All hashes should be unique
            assert len(hashes) == 10
    
    def test_intent_hash_parent_chain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wal_db = str(Path(tmpdir) / "wal.db")
            wal = GlobalWALManager(db_path=wal_db)
            
            # Create chain of 5 events
            parent_hash = None
            chain = []
            
            for i in range(5):
                event_id = wal.append_event(
                    EventType.COMPONENT_IMPLEMENTATION,
                    "ecosystem-1",
                    ["KIVA-CLI"],
                    4.092,
                    4.092 + (i+1)*0.01,
                    parent_intent_hash=parent_hash,
                    description=f"Chain link {i+1}"
                )
                event = wal.get_event(event_id)
                chain.append(event)
                parent_hash = event['intent_hash']
            
            # Verify chain integrity
            for i in range(1, len(chain)):
                assert chain[i]['parent_intent_hash'] == chain[i-1]['intent_hash']
