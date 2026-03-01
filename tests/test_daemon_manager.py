#!/usr/bin/env python3
"""Tests for DaemonManager."""

import unittest
import tempfile
import os
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.core.daemon_manager import DaemonManager


class TestDaemonManagerInit(unittest.TestCase):
    """Test DaemonManager initialization."""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
    
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_init_creates_database(self):
        """Test database initialization."""
        manager = DaemonManager(db_path=self.db_path)
        self.assertTrue(os.path.exists(self.db_path))
        manager.shutdown()
    
    def test_init_creates_tables(self):
        """Test table creation."""
        manager = DaemonManager(db_path=self.db_path)
        
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('daemons', tables)
        self.assertIn('daemon_executions', tables)
        self.assertIn('daemon_health_checks', tables)
        
        conn.close()
        manager.shutdown()


class TestRegisterDaemon(unittest.TestCase):
    """Test daemon registration."""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.manager = DaemonManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.shutdown()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_register_python_daemon(self):
        """Test registering Python daemon."""
        daemon_id = self.manager.register_daemon(
            name="test-daemon",
            daemon_type="PYTHON_SCRIPT",
            script_path="/tmp/test.py",
            description="Test daemon"
        )
        
        self.assertTrue(daemon_id.startswith('dmn_'))
        
        daemon = self.manager.get_daemon(daemon_id)
        self.assertEqual(daemon['name'], 'test-daemon')
        self.assertEqual(daemon['daemon_type'], 'PYTHON_SCRIPT')
        self.assertEqual(daemon['validation_state'], 'UNKNOWN')
        self.assertEqual(daemon['lifecycle_state'], 'GENESIS')
        self.assertEqual(daemon['runtime_state'], 'STOPPED')
    
    def test_register_duplicate_name_fails(self):
        """Test duplicate name registration fails."""
        self.manager.register_daemon(
            name="duplicate",
            daemon_type="PYTHON_SCRIPT"
        )
        
        with self.assertRaises(ValueError):
            self.manager.register_daemon(
                name="duplicate",
                daemon_type="BASH_SCRIPT"
            )
    
    def test_register_invalid_type_fails(self):
        """Test invalid daemon type fails."""
        with self.assertRaises(ValueError):
            self.manager.register_daemon(
                name="invalid",
                daemon_type="INVALID_TYPE"
            )


class TestListDaemons(unittest.TestCase):
    """Test daemon listing."""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.manager = DaemonManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.shutdown()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_list_empty(self):
        """Test listing with no daemons."""
        daemons = self.manager.list_daemons()
        self.assertEqual(len(daemons), 0)
    
    def test_list_multiple_daemons(self):
        """Test listing multiple daemons."""
        self.manager.register_daemon(name="daemon1", daemon_type="PYTHON_SCRIPT")
        self.manager.register_daemon(name="daemon2", daemon_type="BASH_SCRIPT")
        self.manager.register_daemon(name="daemon3", daemon_type="PYTHON_SCRIPT")
        
        daemons = self.manager.list_daemons()
        self.assertEqual(len(daemons), 3)
    
    def test_list_filter_by_type(self):
        """Test filtering by daemon type."""
        self.manager.register_daemon(name="py1", daemon_type="PYTHON_SCRIPT")
        self.manager.register_daemon(name="bash1", daemon_type="BASH_SCRIPT")
        self.manager.register_daemon(name="py2", daemon_type="PYTHON_SCRIPT")
        
        python_daemons = self.manager.list_daemons(daemon_type="PYTHON_SCRIPT")
        self.assertEqual(len(python_daemons), 2)
        
        bash_daemons = self.manager.list_daemons(daemon_type="BASH_SCRIPT")
        self.assertEqual(len(bash_daemons), 1)


class TestDaemonStates(unittest.TestCase):
    """Test daemon state management."""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.manager = DaemonManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.shutdown()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_validation_states(self):
        """Test validation states."""
        self.assertEqual(self.manager.VALIDATION_STATES, ["UNKNOWN", "VALID", "INVALID"])
    
    def test_lifecycle_states(self):
        """Test lifecycle states."""
        self.assertEqual(self.manager.LIFECYCLE_STATES, 
                        ["GENESIS", "ACTIVE", "DEPRECATED", "ARCHIVED"])
    
    def test_runtime_states(self):
        """Test runtime states."""
        expected = ["STOPPED", "STARTING", "RUNNING", "STOPPING", "FAILED", "RESTARTING"]
        self.assertEqual(self.manager.RUNTIME_STATES, expected)
    
    def test_phi_cps_values(self):
        """Test φ-CPS base values."""
        self.assertEqual(self.manager.PHI_CPS_BASE["UNKNOWN"], 0.007)
        self.assertEqual(self.manager.PHI_CPS_BASE["VALID"], 0.018)
        self.assertEqual(self.manager.PHI_CPS_BASE["INVALID"], 0.002)


class TestDaemonTypes(unittest.TestCase):
    """Test daemon types."""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.manager = DaemonManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.shutdown()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_daemon_types_available(self):
        """Test all daemon types."""
        expected = [
            "PYTHON_SCRIPT",
            "POWERSHELL_SCRIPT",
            "BASH_SCRIPT",
            "SYSTEM_SERVICE",
            "DOCKER_CONTAINER",
            "MONITORING_AGENT"
        ]
        self.assertEqual(self.manager.DAEMON_TYPES, expected)
    
    def test_register_all_types(self):
        """Test registering all daemon types."""
        for i, daemon_type in enumerate(self.manager.DAEMON_TYPES):
            daemon_id = self.manager.register_daemon(
                name=f"test-{daemon_type.lower()}-{i}",
                daemon_type=daemon_type
            )
            self.assertTrue(daemon_id.startswith('dmn_'))


if __name__ == '__main__':
    unittest.main()
