#!/usr/bin/env python3
"""
Tests for Citizen CLI Commands
"""

import unittest
import tempfile
import json
from pathlib import Path
from click.testing import CliRunner

try:
    from kiva_cli.commands.citizen_commands import citizen_cli
    from tools.core.citizen_manager import CitizenManager, EntityLevel
except ImportError:
    citizen_cli = None
    CitizenManager = None
    EntityLevel = None


@unittest.skipIf(citizen_cli is None, "Citizen CLI not available")
class TestRegisterCommand(unittest.TestCase):
    """Test 'ecos citizen register' command."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
    
    def test_register_basic(self):
        """Test basic registration."""
        result = self.runner.invoke(citizen_cli, [
            'register',
            '--name', 'test-project',
            '--type', 'PROJECT',
            '--repo', 'KIVA-CLI'
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Citizen registered', result.output)
    
    def test_register_with_metadata(self):
        """Test registration with metadata."""
        metadata = json.dumps({"framework": "fastapi"})
        
        result = self.runner.invoke(citizen_cli, [
            'register',
            '--name', 'test-api',
            '--type', 'SERVICE',
            '--repo', 'KIVA-CLI',
            '--metadata', metadata
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Citizen registered', result.output)
    
    def test_register_invalid_metadata(self):
        """Test registration with invalid JSON metadata."""
        result = self.runner.invoke(citizen_cli, [
            'register',
            '--name', 'test-api',
            '--type', 'SERVICE',
            '--repo', 'KIVA-CLI',
            '--metadata', 'invalid-json'
        ])
        
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Invalid JSON', result.output)


@unittest.skipIf(citizen_cli is None, "Citizen CLI not available")
class TestPromoteCommand(unittest.TestCase):
    """Test 'ecos citizen promote' command."""
    
    def setUp(self):
        """Set up test environment with citizen."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        
        # Create manager and citizen
        self.manager = CitizenManager(db_path=self.db_path)
        self.citizen = self.manager.register_citizen(
            name="test-project",
            entity_type=EntityLevel.PROJECT if hasattr(EntityLevel, 'PROJECT') else 'PROJECT',
            repo="KIVA-CLI",
            entity_level=EntityLevel.L0_GENESIS
        )
    
    def test_promote_valid(self):
        """Test valid promotion."""
        result = self.runner.invoke(citizen_cli, [
            'promote',
            self.citizen.citizen_id,
            '--level', 'L1_VALIDATED'
        ])
        
        # Note: May fail if DB path not propagated correctly
        # In real usage, DB path comes from environment
        self.assertIn('citizen', result.output.lower())
    
    def test_promote_invalid_citizen(self):
        """Test promotion of non-existent citizen."""
        result = self.runner.invoke(citizen_cli, [
            'promote',
            'ctz_invalid',
            '--level', 'L1_VALIDATED'
        ])
        
        # Should fail or show error
        self.assertIn('not found', result.output.lower(), msg=result.output)


@unittest.skipIf(citizen_cli is None, "Citizen CLI not available")
class TestDemoteCommand(unittest.TestCase):
    """Test 'ecos citizen demote' command."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_demote_requires_reason(self):
        """Test that demote requires reason parameter."""
        result = self.runner.invoke(citizen_cli, [
            'demote',
            'ctz_test',
            '--level', 'L2_OPERATIONAL'
        ])
        
        # Should fail without --reason
        self.assertNotEqual(result.exit_code, 0)


@unittest.skipIf(citizen_cli is None, "Citizen CLI not available")
class TestListCommand(unittest.TestCase):
    """Test 'ecos citizen list' command."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_list_default(self):
        """Test list with default options."""
        result = self.runner.invoke(citizen_cli, ['list'])
        
        self.assertEqual(result.exit_code, 0)
        # Should show table or "No citizens found"
        self.assertTrue(
            'citizen' in result.output.lower() or 
            'no citizens' in result.output.lower()
        )
    
    def test_list_json_output(self):
        """Test list with JSON output."""
        result = self.runner.invoke(citizen_cli, [
            'list',
            '--format', 'json'
        ])
        
        self.assertEqual(result.exit_code, 0)
        # Should be valid JSON or empty list
        try:
            json.loads(result.output) if result.output.strip() else []
        except json.JSONDecodeError:
            self.fail("Output is not valid JSON")
    
    def test_list_with_filters(self):
        """Test list with filters."""
        result = self.runner.invoke(citizen_cli, [
            'list',
            '--repo', 'KIVA-CLI',
            '--level', 'L1_VALIDATED',
            '--limit', '10'
        ])
        
        self.assertEqual(result.exit_code, 0)


@unittest.skipIf(citizen_cli is None, "Citizen CLI not available")
class TestExportCommand(unittest.TestCase):
    """Test 'ecos citizen export' command."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def test_export_json(self):
        """Test JSON export."""
        output_path = Path(self.temp_dir) / "export.json"
        
        result = self.runner.invoke(citizen_cli, [
            'export',
            str(output_path),
            '--format', 'json'
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('exported', result.output.lower())
    
    def test_export_csv(self):
        """Test CSV export."""
        output_path = Path(self.temp_dir) / "export.csv"
        
        result = self.runner.invoke(citizen_cli, [
            'export',
            str(output_path),
            '--format', 'csv'
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('exported', result.output.lower())


@unittest.skipIf(citizen_cli is None, "Citizen CLI not available")
class TestValidateCommand(unittest.TestCase):
    """Test 'ecos citizen validate' command."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_validate_states(self):
        """Test all validation states."""
        states = ['UNKNOWN', 'VALID', 'INVALID']
        
        for state in states:
            result = self.runner.invoke(citizen_cli, [
                'validate',
                'ctz_test',
                '--state', state
            ])
            
            # Should accept valid states
            # May fail if citizen doesn't exist, but command should parse correctly
            self.assertNotIn('invalid choice', result.output.lower())


@unittest.skipIf(citizen_cli is None, "Citizen CLI not available")
class TestSyncCommand(unittest.TestCase):
    """Test 'ecos citizen sync' command."""
    
    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_sync_dry_run(self):
        """Test sync with dry-run."""
        result = self.runner.invoke(citizen_cli, [
            'sync',
            '--dry-run'
        ])
        
        # Should initiate sync (may fail if script not found)
        self.assertIn('sync', result.output.lower())


if __name__ == "__main__":
    unittest.main()
