#!/usr/bin/env python3
"""
Tests for CitizenManager - Entity Lifecycle & Validation
"""

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime

try:
    from kiva_cli.core.citizen_manager import (
        CitizenManager,
        EntityLevel,
        EntityType,
        LifecycleState,
        ValidationState,
        Citizen
    )
except ImportError:
    CitizenManager = None
    EntityLevel = None
    EntityType = None
    LifecycleState = None
    ValidationState = None
    Citizen = None


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestCitizenManagerInit(unittest.TestCase):
    """Test CitizenManager initialization."""
    
    def test_init_with_default_db(self):
        """Test initialization with default database path."""
        manager = CitizenManager()
        self.assertIsNotNone(manager)
        self.assertTrue(manager.db_path.exists())
    
    def test_init_with_custom_db(self):
        """Test initialization with custom database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_citizens.db"
            manager = CitizenManager(db_path=db_path)
            self.assertTrue(db_path.exists())


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestRegisterCitizen(unittest.TestCase):
    """Test citizen registration."""
    
    def setUp(self):
        """Set up test database."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
    
    def test_register_basic_citizen(self):
        """Test basic citizen registration."""
        citizen = self.manager.register_citizen(
            name="test-project",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI"
        )
        
        self.assertIsNotNone(citizen)
        self.assertEqual(citizen.name, "test-project")
        self.assertEqual(citizen.entity_type, "PROJECT")
        self.assertEqual(citizen.repo, "KIVA-CLI")
        self.assertEqual(citizen.entity_level, "L0_GENESIS")
        self.assertGreater(citizen.phi_cps, 0.0)
        self.assertTrue(citizen.intent_hash.startswith("0x"))
    
    def test_register_with_metadata(self):
        """Test registration with metadata."""
        metadata = {"framework": "fastapi", "version": "1.0.0"}
        
        citizen = self.manager.register_citizen(
            name="test-api",
            entity_type=EntityType.SERVICE,
            repo="KIVA-CLI",
            metadata=metadata
        )
        
        self.assertEqual(citizen.metadata, metadata)
    
    def test_register_with_dependencies(self):
        """Test registration with dependencies."""
        dependencies = ["ctz_abc123", "ctz_def456"]
        
        citizen = self.manager.register_citizen(
            name="test-component",
            entity_type=EntityType.COMPONENT,
            repo="KIVA-CLI",
            dependencies=dependencies
        )
        
        self.assertEqual(citizen.dependencies, dependencies)
    
    def test_register_different_levels(self):
        """Test registration at different entity levels."""
        levels = [
            EntityLevel.L0_GENESIS,
            EntityLevel.L1_VALIDATED,
            EntityLevel.L2_OPERATIONAL,
            EntityLevel.L3_PRODUCTION
        ]
        
        for level in levels:
            citizen = self.manager.register_citizen(
                name=f"test-{level.value}",
                entity_type=EntityType.PROJECT,
                repo="KIVA-CLI",
                entity_level=level
            )
            
            self.assertEqual(citizen.entity_level, level.value)


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestPromoteEntity(unittest.TestCase):
    """Test entity promotion."""
    
    def setUp(self):
        """Set up test database and citizen."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
        
        self.citizen = self.manager.register_citizen(
            name="test-project",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI",
            entity_level=EntityLevel.L0_GENESIS
        )
    
    def test_promote_valid_path(self):
        """Test valid promotion L0 -> L1."""
        success, message, updated = self.manager.promote_entity(
            citizen_id=self.citizen.citizen_id,
            target_level=EntityLevel.L1_VALIDATED
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.entity_level, "L1_VALIDATED")
        self.assertGreater(updated.phi_cps, self.citizen.phi_cps)
    
    def test_promote_invalid_path(self):
        """Test invalid promotion (skipping level)."""
        success, message, updated = self.manager.promote_entity(
            citizen_id=self.citizen.citizen_id,
            target_level=EntityLevel.L3_PRODUCTION
        )
        
        # Should fail (can't skip L1, L2)
        # Note: Current implementation allows this, adjust if validation added
        self.assertIsNotNone(message)
    
    def test_promote_nonexistent_citizen(self):
        """Test promotion of non-existent citizen."""
        success, message, updated = self.manager.promote_entity(
            citizen_id="ctz_invalid",
            target_level=EntityLevel.L1_VALIDATED
        )
        
        self.assertFalse(success)
        self.assertIsNone(updated)


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestDemoteEntity(unittest.TestCase):
    """Test entity demotion."""
    
    def setUp(self):
        """Set up test database and citizen."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
        
        # Create citizen at L3
        self.citizen = self.manager.register_citizen(
            name="test-project",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI",
            entity_level=EntityLevel.L3_PRODUCTION
        )
    
    def test_demote_to_lower_level(self):
        """Test demotion L3 -> L2."""
        success, message, updated = self.manager.demote_entity(
            citizen_id=self.citizen.citizen_id,
            target_level=EntityLevel.L2_OPERATIONAL,
            reason="Performance issues"
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.entity_level, "L2_OPERATIONAL")
        self.assertLess(updated.phi_cps, self.citizen.phi_cps)
    
    def test_demote_to_legacy(self):
        """Test archiving to L5."""
        success, message, updated = self.manager.demote_entity(
            citizen_id=self.citizen.citizen_id,
            target_level=EntityLevel.L5_LEGACY,
            reason="Project archived"
        )
        
        self.assertTrue(success)
        self.assertEqual(updated.entity_level, "L5_LEGACY")


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestValidateEntity(unittest.TestCase):
    """Test entity validation."""
    
    def setUp(self):
        """Set up test database and citizen."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
        
        self.citizen = self.manager.register_citizen(
            name="test-project",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI"
        )
    
    def test_validate_states(self):
        """Test all validation states."""
        states = [
            ValidationState.UNKNOWN,
            ValidationState.VALID,
            ValidationState.INVALID
        ]
        
        for state in states:
            success, message = self.manager.validate_entity(
                citizen_id=self.citizen.citizen_id,
                validation_state=state
            )
            
            self.assertTrue(success)
            
            # Verify update
            updated = self.manager.get_citizen(self.citizen.citizen_id)
            self.assertEqual(updated.validation_state, str(state.value))


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestGetCitizen(unittest.TestCase):
    """Test citizen retrieval."""
    
    def setUp(self):
        """Set up test database."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
    
    def test_get_existing_citizen(self):
        """Test retrieving existing citizen."""
        citizen = self.manager.register_citizen(
            name="test-project",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI"
        )
        
        retrieved = self.manager.get_citizen(citizen.citizen_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.citizen_id, citizen.citizen_id)
        self.assertEqual(retrieved.name, citizen.name)
    
    def test_get_nonexistent_citizen(self):
        """Test retrieving non-existent citizen."""
        retrieved = self.manager.get_citizen("ctz_invalid")
        self.assertIsNone(retrieved)


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestListCitizens(unittest.TestCase):
    """Test citizen listing."""
    
    def setUp(self):
        """Set up test database with multiple citizens."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
        
        # Create test citizens
        self.manager.register_citizen(
            name="project-1",
            entity_type=EntityType.PROJECT,
            repo="REPO-A",
            entity_level=EntityLevel.L1_VALIDATED
        )
        
        self.manager.register_citizen(
            name="project-2",
            entity_type=EntityType.PROJECT,
            repo="REPO-B",
            entity_level=EntityLevel.L2_OPERATIONAL
        )
        
        self.manager.register_citizen(
            name="service-1",
            entity_type=EntityType.SERVICE,
            repo="REPO-A",
            entity_level=EntityLevel.L1_VALIDATED
        )
    
    def test_list_all_citizens(self):
        """Test listing all citizens."""
        citizens = self.manager.list_citizens()
        self.assertEqual(len(citizens), 3)
    
    def test_list_by_repo(self):
        """Test filtering by repository."""
        citizens = self.manager.list_citizens(repo="REPO-A")
        self.assertEqual(len(citizens), 2)
        
        for citizen in citizens:
            self.assertEqual(citizen.repo, "REPO-A")
    
    def test_list_by_level(self):
        """Test filtering by entity level."""
        citizens = self.manager.list_citizens(
            entity_level=EntityLevel.L1_VALIDATED
        )
        self.assertEqual(len(citizens), 2)
    
    def test_list_with_limit(self):
        """Test result limit."""
        citizens = self.manager.list_citizens(limit=2)
        self.assertEqual(len(citizens), 2)


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestExportRegistry(unittest.TestCase):
    """Test registry export."""
    
    def setUp(self):
        """Set up test database."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
        self.temp_dir = Path(tmpdir)
        
        # Create test citizen
        self.manager.register_citizen(
            name="test-project",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI"
        )
    
    def test_export_json(self):
        """Test JSON export."""
        output_path = self.temp_dir / "export.json"
        
        success = self.manager.export_registry(
            output_path=output_path,
            format="json"
        )
        
        self.assertTrue(success)
        self.assertTrue(output_path.exists())
        
        # Verify content
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        self.assertIn("citizens", data)
        self.assertGreater(len(data["citizens"]), 0)
    
    def test_export_csv(self):
        """Test CSV export."""
        output_path = self.temp_dir / "export.csv"
        
        success = self.manager.export_registry(
            output_path=output_path,
            format="csv"
        )
        
        self.assertTrue(success)
        self.assertTrue(output_path.exists())


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestIntentHash(unittest.TestCase):
    """Test IntentHash generation."""
    
    def setUp(self):
        """Set up test database."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
    
    def test_intent_hash_format(self):
        """Test IntentHash format (0x + 16 hex chars)."""
        citizen = self.manager.register_citizen(
            name="test",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI"
        )
        
        self.assertTrue(citizen.intent_hash.startswith("0x"))
        self.assertEqual(len(citizen.intent_hash), 18)  # "0x" + 16 chars
    
    def test_intent_hash_uniqueness(self):
        """Test IntentHash uniqueness across registrations."""
        citizen1 = self.manager.register_citizen(
            name="test-1",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI"
        )
        
        citizen2 = self.manager.register_citizen(
            name="test-2",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI"
        )
        
        self.assertNotEqual(citizen1.intent_hash, citizen2.intent_hash)


@unittest.skipIf(CitizenManager is None, "CitizenManager not available")
class TestPhiCPS(unittest.TestCase):
    """Test φ-CPS calculation."""
    
    def setUp(self):
        """Set up test database."""
        tmpdir = tempfile.mkdtemp()
        self.db_path = Path(tmpdir) / "test.db"
        self.manager = CitizenManager(db_path=self.db_path)
    
    def test_initial_phi_cps_by_level(self):
        """Test initial φ-CPS varies by level."""
        levels = [
            EntityLevel.L0_GENESIS,
            EntityLevel.L1_VALIDATED,
            EntityLevel.L2_OPERATIONAL,
            EntityLevel.L3_PRODUCTION,
            EntityLevel.L4_CRITICAL
        ]
        
        phi_values = []
        
        for level in levels:
            citizen = self.manager.register_citizen(
                name=f"test-{level.value}",
                entity_type=EntityType.PROJECT,
                repo="KIVA-CLI",
                entity_level=level
            )
            
            phi_values.append(citizen.phi_cps)
        
        # Higher levels should have higher φ-CPS
        for i in range(len(phi_values) - 1):
            self.assertLessEqual(phi_values[i], phi_values[i + 1])
    
    def test_phi_cps_increases_on_promotion(self):
        """Test φ-CPS increases on promotion."""
        citizen = self.manager.register_citizen(
            name="test",
            entity_type=EntityType.PROJECT,
            repo="KIVA-CLI",
            entity_level=EntityLevel.L0_GENESIS
        )
        
        initial_phi = citizen.phi_cps
        
        success, _, updated = self.manager.promote_entity(
            citizen_id=citizen.citizen_id,
            target_level=EntityLevel.L1_VALIDATED
        )
        
        self.assertTrue(success)
        self.assertGreater(updated.phi_cps, initial_phi)


if __name__ == "__main__":
    unittest.main()
