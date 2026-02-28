#!/usr/bin/env python3
"""
Tests for GlobalWALManager
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from kiva_cli.core.global_wal_manager import (
    GlobalWALManager,
    WALEvent
)


class TestGlobalWALManager(unittest.TestCase):
    """Test GlobalWALManager initialization and basic operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_wal.db"
        self.manager = GlobalWALManager(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test WAL manager initialization"""
        self.assertTrue(self.db_path.exists())
        self.assertIsNotNone(self.manager)
    
    def test_database_schema(self):
        """Test database schema creation"""
        conn = self.manager._get_connection()
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('wal_events', tables)
        self.assertIn('phi_history', tables)
        self.assertIn('intent_chain', tables)


class TestEventOperations(unittest.TestCase):
    """Test WAL event operations"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_wal.db"
        self.manager = GlobalWALManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_append_event(self):
        """Test appending event to WAL"""
        event = self.manager.append_event(
            repo_name="KIVA-CLI",
            event_type=GlobalWALManager.EVENT_COMMIT,
            entity_id="test-123",
            action="create",
            phi_delta=0.01,
            metadata={"test": "data"}
        )
        
        self.assertIsNotNone(event.event_id)
        self.assertEqual(event.repo_name, "KIVA-CLI")
        self.assertEqual(event.event_type, GlobalWALManager.EVENT_COMMIT)
        self.assertEqual(event.phi_delta, 0.01)
        self.assertEqual(event.status, GlobalWALManager.STATUS_SUCCESS)
    
    def test_update_event_status(self):
        """Test updating event status"""
        event = self.manager.append_event(
            repo_name="KIVA-CLI",
            event_type=GlobalWALManager.EVENT_ISSUE,
            entity_id="issue-1",
            action="update",
            phi_delta=0.005,
            status=GlobalWALManager.STATUS_PENDING
        )
        
        # Update to success
        self.manager.update_event_status(
            event.event_id,
            GlobalWALManager.STATUS_SUCCESS
        )
        
        # Retrieve and verify
        retrieved = self.manager.get_event_by_id(event.event_id)
        self.assertEqual(retrieved.status, GlobalWALManager.STATUS_SUCCESS)
    
    def test_get_events_filtered(self):
        """Test querying events with filters"""
        # Create multiple events
        self.manager.append_event(
            repo_name="KIVA-CLI",
            event_type=GlobalWALManager.EVENT_COMMIT,
            entity_id="commit-1",
            action="create",
            phi_delta=0.01
        )
        
        self.manager.append_event(
            repo_name="ECOYSTEM",
            event_type=GlobalWALManager.EVENT_ISSUE,
            entity_id="issue-1",
            action="create",
            phi_delta=0.005
        )
        
        # Query by repo
        kiva_events = self.manager.get_events(repo_name="KIVA-CLI")
        self.assertEqual(len(kiva_events), 1)
        self.assertEqual(kiva_events[0].repo_name, "KIVA-CLI")
        
        # Query by event type
        commit_events = self.manager.get_events(
            event_type=GlobalWALManager.EVENT_COMMIT
        )
        self.assertEqual(len(commit_events), 1)
        self.assertEqual(commit_events[0].event_type, GlobalWALManager.EVENT_COMMIT)


class TestPhiCPSTracking(unittest.TestCase):
    """Test φ-CPS tracking"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_wal.db"
        self.manager = GlobalWALManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_get_current_phi(self):
        """Test getting current φ-CPS"""
        # Initial value should be genesis
        phi = self.manager.get_current_phi("KIVA-CLI")
        self.assertEqual(phi, GlobalWALManager.PHI_GENESIS)
    
    def test_phi_updates_with_events(self):
        """Test φ-CPS updates with events"""
        initial_phi = self.manager.get_current_phi("KIVA-CLI")
        
        # Add event with delta
        delta = 0.015
        self.manager.append_event(
            repo_name="KIVA-CLI",
            event_type=GlobalWALManager.EVENT_COMMIT,
            entity_id="commit-1",
            action="create",
            phi_delta=delta
        )
        
        # Check updated value
        updated_phi = self.manager.get_current_phi("KIVA-CLI")
        self.assertAlmostEqual(updated_phi, initial_phi + delta, places=4)
    
    def test_phi_history(self):
        """Test φ-CPS history tracking"""
        # Create multiple events
        for i in range(3):
            self.manager.append_event(
                repo_name="KIVA-CLI",
                event_type=GlobalWALManager.EVENT_COMMIT,
                entity_id=f"commit-{i}",
                action="create",
                phi_delta=0.01
            )
        
        # Get history
        history = self.manager.get_phi_history(repo_name="KIVA-CLI", limit=10)
        
        self.assertEqual(len(history), 3)
        
        # History should be in descending order
        for i in range(len(history) - 1):
            self.assertGreater(history[i]['timestamp'], history[i + 1]['timestamp'])


class TestIntentHashChain(unittest.TestCase):
    """Test IntentHash chain validation"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_wal.db"
        self.manager = GlobalWALManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_intent_hash_generation(self):
        """Test IntentHash generation"""
        event = self.manager.append_event(
            repo_name="KIVA-CLI",
            event_type=GlobalWALManager.EVENT_COMMIT,
            entity_id="commit-1",
            action="create",
            phi_delta=0.01
        )
        
        self.assertIsNotNone(event.intent_hash)
        self.assertTrue(event.intent_hash.startswith("IntentHash¹¹:"))
    
    def test_intent_chain_validation(self):
        """Test IntentHash chain validation"""
        # Create multiple events
        for i in range(5):
            self.manager.append_event(
                repo_name="KIVA-CLI",
                event_type=GlobalWALManager.EVENT_COMMIT,
                entity_id=f"commit-{i}",
                action="create",
                phi_delta=0.01
            )
        
        # Validate chain
        valid, errors = self.manager.validate_intent_chain()
        
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)


class TestStatistics(unittest.TestCase):
    """Test WAL statistics"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_wal.db"
        self.manager = GlobalWALManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_get_stats(self):
        """Test statistics retrieval"""
        # Create events with different statuses
        for i in range(3):
            self.manager.append_event(
                repo_name="KIVA-CLI",
                event_type=GlobalWALManager.EVENT_COMMIT,
                entity_id=f"commit-{i}",
                action="create",
                phi_delta=0.01,
                status=GlobalWALManager.STATUS_SUCCESS
            )
        
        event = self.manager.append_event(
            repo_name="KIVA-CLI",
            event_type=GlobalWALManager.EVENT_ISSUE,
            entity_id="issue-1",
            action="create",
            phi_delta=0.005,
            status=GlobalWALManager.STATUS_PENDING
        )
        
        self.manager.update_event_status(
            event.event_id,
            GlobalWALManager.STATUS_FAILED,
            error="Test error"
        )
        
        # Get stats
        stats = self.manager.get_stats(repo_name="KIVA-CLI")
        
        self.assertEqual(stats['total_events'], 4)
        self.assertEqual(stats['successful'], 3)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['pending'], 0)  # Was updated to failed
        self.assertAlmostEqual(stats['total_phi_delta'], 0.035, places=4)


class TestExport(unittest.TestCase):
    """Test WAL export functionality"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_wal.db"
        self.manager = GlobalWALManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_export_to_json(self):
        """Test exporting WAL to JSON"""
        # Create some events
        for i in range(3):
            self.manager.append_event(
                repo_name="KIVA-CLI",
                event_type=GlobalWALManager.EVENT_COMMIT,
                entity_id=f"commit-{i}",
                action="create",
                phi_delta=0.01
            )
        
        # Export
        export_path = self.temp_dir / "wal_export.json"
        self.manager.export_to_json(export_path, repo_name="KIVA-CLI")
        
        self.assertTrue(export_path.exists())
        
        # Verify export contents
        import json
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['repo_name'], "KIVA-CLI")
        self.assertEqual(data['total_events'], 3)
        self.assertEqual(len(data['events']), 3)


if __name__ == '__main__':
    unittest.main()
