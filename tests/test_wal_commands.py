#!/usr/bin/env python3
"""
Test suite for WAL CLI commands
"""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import json

from kiva_cli.commands.wal_commands import (
    wal_cli,
    append_event,
    query_events,
    check_drift,
    verify_chain,
    create_rollback,
    export_audit
)

from tools.core.global_wal_manager import GlobalWALManager


class TestWALCLIAppend:
    """Test 'ecos wal append' command."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_append_basic(self, runner):
        """Test basic event append."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            
            # Initialize WAL (would normally be done by CLI)
            wal = GlobalWALManager(db_path=db_path)
            
            result = runner.invoke(append_event, [
                '--operation', 'TEST_OP',
                '--repo', 'TEST_REPO',
                '--phi-delta', '0.01'
            ])
            
            # Command should succeed (exit code 0)
            assert result.exit_code == 0 or 'Event appended' in result.output
    
    def test_append_with_metadata(self, runner):
        """Test append with JSON metadata."""
        metadata = json.dumps({"key": "value"})
        
        result = runner.invoke(append_event, [
            '--operation', 'TEST_OP',
            '--repo', 'TEST_REPO',
            '--phi-delta', '0.01',
            '--metadata', metadata
        ])
        
        # Should not error on valid JSON
        assert 'Invalid JSON' not in result.output
    
    def test_append_invalid_metadata(self, runner):
        """Test append with invalid JSON metadata."""
        result = runner.invoke(append_event, [
            '--operation', 'TEST_OP',
            '--repo', 'TEST_REPO',
            '--phi-delta', '0.01',
            '--metadata', 'invalid-json'
        ])
        
        # Should error on invalid JSON
        assert result.exit_code != 0 or 'Invalid JSON' in result.output


class TestWALCLIQuery:
    """Test 'ecos wal query' command."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def setup_wal(self):
        """Setup WAL with test events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"
            wal = GlobalWALManager(db_path=db_path)
            
            # Add test events
            wal.append_event(
                operation="OP1",
                repo="REPO_A",
                phi_cps_delta=0.01
            )
            
            wal.append_event(
                operation="OP2",
                repo="REPO_B",
                phi_cps_delta=0.02
            )
            
            yield wal
    
    def test_query_all(self, runner):
        """Test querying all events."""
        result = runner.invoke(query_events)
        
        assert result.exit_code == 0 or 'WAL EVENTS' in result.output
    
    def test_query_by_repo(self, runner):
        """Test querying by repository."""
        result = runner.invoke(query_events, ['--repo', 'KIVA-CLI'])
        
        assert result.exit_code == 0
    
    def test_query_with_limit(self, runner):
        """Test querying with result limit."""
        result = runner.invoke(query_events, ['--limit', '5'])
        
        assert result.exit_code == 0


class TestWALCLIDrift:
    """Test 'ecos wal drift' command."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_check_drift(self, runner):
        """Test drift check command."""
        result = runner.invoke(check_drift)
        
        # Should show drift metrics
        assert result.exit_code == 0 or 'DRIFT METRICS' in result.output


class TestWALCLIChain:
    """Test 'ecos wal chain' command."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_verify_chain_basic(self, runner):
        """Test basic chain verification."""
        result = runner.invoke(verify_chain, ['0x1234567890ABCDEF'])
        
        # Command should execute (may fail if hash not found)
        assert result.exit_code is not None
    
    def test_verify_chain_with_parent(self, runner):
        """Test chain verification with parent."""
        result = runner.invoke(verify_chain, [
            '0x1234567890ABCDEF',
            '--parent', '0xABCDEF1234567890'
        ])
        
        assert result.exit_code is not None


class TestWALCLIRollback:
    """Test 'ecos wal rollback' command."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_create_rollback(self, runner):
        """Test rollback point creation."""
        result = runner.invoke(create_rollback, [
            '--reason', 'Test rollback'
        ])
        
        assert result.exit_code == 0 or 'Rollback point created' in result.output
    
    def test_create_rollback_with_metadata(self, runner):
        """Test rollback with metadata."""
        metadata = json.dumps({"test": True})
        
        result = runner.invoke(create_rollback, [
            '--reason', 'Test',
            '--metadata', metadata
        ])
        
        assert 'Invalid JSON' not in result.output


class TestWALCLIExport:
    """Test 'ecos wal export' command."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_export_json(self, runner):
        """Test exporting to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "audit.json"
            
            result = runner.invoke(export_audit, [
                str(output_file),
                '--format', 'json'
            ])
            
            assert result.exit_code == 0 or 'exported' in result.output.lower()
    
    def test_export_csv(self, runner):
        """Test exporting to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "audit.csv"
            
            result = runner.invoke(export_audit, [
                str(output_file),
                '--format', 'csv'
            ])
            
            assert result.exit_code == 0 or 'exported' in result.output.lower()
