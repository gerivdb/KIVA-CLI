"""
ECOS-CLI Phase 6 Batch 3/3 Integration Tests
CLI commands + φ-CPS manager + IntentHash validator

IntentHash: 0x69C0965C49825C93BDDF
Generated: 2026-02-28T22:00:31.548491
"""

import unittest
import json
from datetime import datetime
from kiva_cli.cli.ecos_cli_main import EcosCLI
from kiva_cli.core.metrics.phi_cps_manager import PhiCPSManager
from kiva_cli.core.security.intenthash_validator import IntentHashValidator, IntentHashChain


class TestCLICommands(unittest.TestCase):
    """Test CLI command parsing and execution"""
    
    def setUp(self):
        self.cli = EcosCLI()
    
    def test_cli_initialization(self):
        """Test CLI initializes correctly"""
        self.assertIsNotNone(self.cli)
    
    def test_validate_command_ternary(self):
        """Test ecos validate --mode ternary"""
        # Mock test (requires actual entity)
        result = self.cli.validate("test_entity", mode="ternary")
        self.assertIn("entity_id", result)
        self.assertEqual(result["mode"], "ternary")
    
    def test_validate_command_invalid_mode(self):
        """Test ecos validate with invalid mode"""
        result = self.cli.validate("test_entity", mode="invalid")
        self.assertIn("error", result)
    
    def test_lifecycle_show_not_found(self):
        """Test ecos lifecycle show with non-existent entity"""
        result = self.cli.lifecycle_show("nonexistent_entity")
        self.assertIn("error", result)
    
    def test_lifecycle_check_auto_transitions(self):
        """Test ecos lifecycle check-auto-transitions"""
        result = self.cli.lifecycle_check_auto_transitions()
        self.assertIn("pending_auto_transitions", result)
        self.assertIn("count", result)


class TestPhiCPSManager(unittest.TestCase):
    """Test φ-CPS management"""
    
    def setUp(self):
        self.phi_manager = PhiCPSManager()
    
    def test_get_metrics(self):
        """Test get_metrics returns valid data"""
        metrics = self.phi_manager.get_metrics()
        self.assertIn("genesis", metrics)
        self.assertIn("current", metrics)
        self.assertIn("threshold", metrics)
    
    def test_check_drift(self):
        """Test drift check"""
        exceeds, drift, recommendation = self.phi_manager.check_drift()
        self.assertIsInstance(exceeds, bool)
        self.assertIsInstance(drift, float)
        self.assertIsInstance(recommendation, str)
    
    def test_calculate_phi_delta(self):
        """Test φ-CPS delta calculation"""
        delta = self.phi_manager.calculate_phi_delta(
            semantic_weight=0.5,
            confidence=0.8
        )
        self.assertAlmostEqual(delta, 0.4, places=2)
    
    def test_validate_phi_increment_frozen(self):
        """Test φ-CPS increment validation when frozen"""
        allowed, reason = self.phi_manager.validate_phi_increment(0.01)
        # Should be False if φ-CPS is frozen
        self.assertIn("frozen", reason.lower())
    
    def test_prepare_baseline_reset_preview(self):
        """Test baseline reset preparation (preview)"""
        result = self.phi_manager.prepare_baseline_reset(preview=True)
        self.assertIn("preview", result)
        self.assertTrue(result["preview"])
        self.assertIn("migration_plan", result)
        self.assertIn("ecos_root_v2_preview", result)
    
    def test_baseline_reset_migration_plan(self):
        """Test baseline reset migration plan generation"""
        result = self.phi_manager.prepare_baseline_reset(preview=True)
        plan = result["migration_plan"]
        
        # Check all steps present
        self.assertGreaterEqual(len(plan), 8)
        
        # Check critical backup step
        backup_step = next((s for s in plan if "Backup" in s["action"]), None)
        self.assertIsNotNone(backup_step)
        self.assertTrue(backup_step.get("critical", False))


class TestIntentHashValidator(unittest.TestCase):
    """Test IntentHash validation"""
    
    def setUp(self):
        self.validator = IntentHashValidator()
    
    def test_format_validation_valid(self):
        """Test L0 format validation with valid hash"""
        valid_hash = "0x" + "A" * 40
        self.assertTrue(self.validator.validate_format(valid_hash))
    
    def test_format_validation_invalid_prefix(self):
        """Test L0 format validation with invalid prefix"""
        invalid_hash = "1x" + "A" * 40
        self.assertFalse(self.validator.validate_format(invalid_hash))
    
    def test_format_validation_invalid_length(self):
        """Test L0 format validation with invalid length"""
        invalid_hash = "0x" + "A" * 30  # Too short
        self.assertFalse(self.validator.validate_format(invalid_hash))
    
    def test_format_validation_invalid_chars(self):
        """Test L0 format validation with invalid characters"""
        invalid_hash = "0x" + "G" * 40  # G is not hex
        self.assertFalse(self.validator.validate_format(invalid_hash))
    
    def test_generate_intent_hash(self):
        """Test IntentHash generation"""
        hash_value = self.validator.generate_intent_hash(
            action="TEST_ACTION",
            context="Test context",
            timestamp="2026-02-28T22:00:00"
        )
        self.assertTrue(self.validator.validate_format(hash_value))
        self.assertEqual(len(hash_value), 42)  # "0x" + 40 chars
    
    def test_verify_hash_derivation(self):
        """Test hash derivation verification"""
        action = "TEST"
        context = "Context"
        timestamp = "2026-02-28T22:00:00"
        
        hash_value = self.validator.generate_intent_hash(action, context, timestamp)
        is_valid = self.validator.verify_hash_derivation(
            hash_value, action, context, timestamp
        )
        self.assertTrue(is_valid)
    
    def test_chain_continuity_genesis(self):
        """Test L1 chain validation for genesis hash"""
        hash_value = "0x" + "A" * 40
        is_valid, chain_data = self.validator.validate_chain_continuity(hash_value)
        
        self.assertTrue(is_valid)
        self.assertTrue(chain_data["is_genesis"])
        self.assertIsNone(chain_data["previous_hash"])
    
    def test_chain_continuity_linked(self):
        """Test L1 chain validation for linked hash"""
        hash1 = "0x" + "A" * 40
        hash2 = "0x" + "B" * 40
        
        # Add genesis
        self.validator.validate_chain_continuity(hash1)
        
        # Add linked hash
        is_valid, chain_data = self.validator.validate_chain_continuity(hash2, hash1)
        
        self.assertTrue(is_valid)
        self.assertFalse(chain_data["is_genesis"])
        self.assertEqual(chain_data["previous_hash"], hash1)


class TestIntentHashChain(unittest.TestCase):
    """Test IntentHash chain management"""
    
    def setUp(self):
        self.chain = IntentHashChain()
    
    def test_add_event(self):
        """Test adding event to chain"""
        event = self.chain.add_event(
            action="TEST_ACTION",
            context="Test context",
            entity_id="test_entity",
            phi_delta=0.01
        )
        
        self.assertIn("intent_hash", event)
        self.assertIn("timestamp", event)
        self.assertEqual(event["validation_l0"], "VALID")
        self.assertEqual(event["validation_l1"], "VALID")
    
    def test_chain_genesis_event(self):
        """Test genesis event has no previous_hash"""
        event = self.chain.add_event("GENESIS", "Genesis", "genesis_entity")
        self.assertIsNone(event["previous_hash"])
        self.assertEqual(event["chain_position"], 0)
    
    def test_chain_linked_events(self):
        """Test linked events maintain continuity"""
        event1 = self.chain.add_event("ACTION1", "Context1", "entity1")
        event2 = self.chain.add_event("ACTION2", "Context2", "entity2")
        
        self.assertEqual(event2["previous_hash"], event1["intent_hash"])
        self.assertEqual(event2["chain_position"], 1)
    
    def test_validate_full_chain_valid(self):
        """Test full chain validation (valid chain)"""
        self.chain.add_event("ACTION1", "Context1", "entity1")
        self.chain.add_event("ACTION2", "Context2", "entity2")
        self.chain.add_event("ACTION3", "Context3", "entity3")
        
        result = self.chain.validate_full_chain()
        self.assertTrue(result["valid"])
        self.assertEqual(result["length"], 3)
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(result["chain_integrity"], "INTACT")


if __name__ == "__main__":
    unittest.main()
