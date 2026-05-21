#!/usr/bin/env python3
"""
Integration Tests for Cross-Repo Sync
Complete test suite for KIVA-CLI cross-repository synchronization
"""

import pytest
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from datetime import datetime

# Test fixtures and utilities

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)

@pytest.fixture
def mock_github_client():
    """Mock GitHub API client"""
    client = Mock()
    client.get_file_contents = Mock(return_value={"content": "test", "sha": "abc123"})
    client.create_or_update_file = Mock(return_value={"commit": {"sha": "def456"}})
    return client

@pytest.fixture
def sample_ecos_root():
    """Sample ECOS_ROOT.json for testing"""
    return {
        "manifest_version": "1.0.2",
        "ecosystem_id": "ecosystem-1",
        "phi_cps_genesis": 4.092,
        "phi_cps_current": 4.231,
        "repositories": [
            {
                "name": "KIVA-CLI",
                "owner": "gerivdb",
                "status": "ACTIVE",
                "phi_cps": 4.231
            }
        ],
        "global_metrics": {
            "total_repositories": 11,
            "total_commits": 23
        }
    }

@pytest.fixture
def wal_database(tmp_path):
    """Create test WAL database."""
    db_path = tmp_path / "test_wal.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wal_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            repo TEXT NOT NULL,
            event_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            intent_hash TEXT NOT NULL,
            phi_delta REAL NOT NULL,
            description TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    
    return db_path


# CATEGORY: Sync Operations Tests

class TestSyncOperations:
    """Test suite for cross-repo synchronization operations"""
    
    def test_ecos_root_sync_to_ecoystem(self, sample_ecos_root, mock_github_client, temp_dir):
        """Test ECOS_ROOT.json sync from KIVA-CLI to ECOYSTEM"""
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        # Setup
        sync = CrossRepoSync(github_client=mock_github_client)
        source_repo = "gerivdb/KIVA-CLI"
        target_repo = "gerivdb/ECOYSTEM"
        
        # Execute sync
        result = sync.sync_ecos_root(
            source_repo=source_repo,
            target_repo=target_repo,
            content=json.dumps(sample_ecos_root)
        )
        
        # Validate
        assert result["status"] == "SUCCESS"
        assert result["source_repo"] == source_repo
        assert result["target_repo"] == target_repo
        assert "commit_sha" in result
        
        # Verify GitHub API calls
        mock_github_client.create_or_update_file.assert_called_once()
    
    def test_wal_database_sync(self, wal_database, mock_github_client):
        """Test WAL database synchronization"""
        from kiva_cli.sync.wal_sync import WALSync
        
        # Add test event to WAL
        conn = sqlite3.connect(wal_database)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO wal_events 
            (timestamp, repo, event_type, entity_id, action, intent_hash, phi_delta, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            "KIVA-CLI",
            "test",
            "test123",
            "create",
            "0xTEST",
            0.001,
            "Test event"
        ))
        conn.commit()
        conn.close()
        
        # Execute sync
        sync = WALSync(github_client=mock_github_client)
        result = sync.sync_wal_to_remote(
            db_path=str(wal_database),
            target_repo="gerivdb/ECOYSTEM"
        )
        
        # Validate
        assert result["status"] == "SUCCESS"
        assert result["events_synced"] == 1
    
    def test_metrics_sync(self, sample_ecos_root, mock_github_client):
        """Test metrics synchronization"""
        from kiva_cli.sync.metrics_sync import MetricsSync
        
        sync = MetricsSync(github_client=mock_github_client)
        
        # Generate metrics
        metrics = sync.generate_metrics(sample_ecos_root)
        
        # Sync to remote
        result = sync.sync_metrics(
            metrics=metrics,
            target_repo="gerivdb/ECOYSTEM"
        )
        
        # Validate
        assert result["status"] == "SUCCESS"
        assert "metrics_count" in result
        assert result["metrics_count"] > 0
    
    def test_documentation_sync(self, mock_github_client, temp_dir):
        """Test documentation synchronization"""
        from kiva_cli.sync.doc_sync import DocumentationSync
        
        # Create test documentation
        doc_file = Path(temp_dir) / "test_doc.md"
        doc_file.write_text("# Test Documentation\\n\\nTest content")
        
        sync = DocumentationSync(github_client=mock_github_client)
        
        # Sync documentation
        result = sync.sync_documentation(
            doc_path=str(doc_file),
            target_repo="gerivdb/ECOYSTEM"
        )
        
        # Validate
        assert result["status"] == "SUCCESS"
        assert "files_synced" in result
    
    def test_config_sync(self, mock_github_client):
        """Test configuration synchronization"""
        from kiva_cli.sync.config_sync import ConfigSync
        
        config = {
            "wal_configuration": {
                "enabled": True,
                "database_path": "~/.kiva/global_wal.db"
            }
        }
        
        sync = ConfigSync(github_client=mock_github_client)
        result = sync.sync_config(
            config=config,
            target_repo="gerivdb/ECOYSTEM"
        )
        
        # Validate
        assert result["status"] == "SUCCESS"


# CATEGORY: Error Handling Tests

class TestErrorHandling:
    """Test suite for error handling and recovery"""
    
    def test_network_failure_recovery(self, mock_github_client, sample_ecos_root):
        """Test recovery from network failures"""
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        # Simulate network failure
        mock_github_client.create_or_update_file.side_effect = [
            ConnectionError("Network error"),
            {"commit": {"sha": "recovered"}}
        ]
        
        sync = CrossRepoSync(github_client=mock_github_client, max_retries=2)
        
        # Should recover after retry
        result = sync.sync_ecos_root(
            source_repo="gerivdb/KIVA-CLI",
            target_repo="gerivdb/ECOYSTEM",
            content=json.dumps(sample_ecos_root)
        )
        
        # Validate recovery
        assert result["status"] == "SUCCESS"
        assert result["retries"] == 1
    
    def test_github_rate_limit_handling(self, mock_github_client):
        """Test GitHub API rate limit handling"""
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        # Simulate rate limit
        mock_github_client.create_or_update_file.side_effect = Exception("Rate limit exceeded")
        
        sync = CrossRepoSync(github_client=mock_github_client)
        
        # Should handle rate limit gracefully
        result = sync.sync_ecos_root(
            source_repo="gerivdb/KIVA-CLI",
            target_repo="gerivdb/ECOYSTEM",
            content="{}"
        )
        
        # Validate
        assert result["status"] == "FAILED"
        assert "rate_limit" in result["error"].lower()
    
    def test_conflict_resolution(self, mock_github_client, sample_ecos_root):
        """Test conflict resolution during sync"""
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        # Simulate conflict
        mock_github_client.create_or_update_file.side_effect = Exception("Conflict: file changed")
        mock_github_client.get_file_contents.return_value = {
            "content": json.dumps(sample_ecos_root),
            "sha": "new_sha"
        }
        
        sync = CrossRepoSync(
            github_client=mock_github_client,
            conflict_strategy="ours"
        )
        
        # Should resolve using "ours" strategy
        result = sync.sync_ecos_root(
            source_repo="gerivdb/KIVA-CLI",
            target_repo="gerivdb/ECOYSTEM",
            content=json.dumps(sample_ecos_root)
        )
        
        # Validate conflict resolution
        assert "conflict_resolved" in result
    
    def test_rollback_on_failure(self, mock_github_client, wal_database):
        """Test automatic rollback on sync failure"""
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        # Create backup before sync
        backup_sha = "backup123"
        
        sync = CrossRepoSync(github_client=mock_github_client)
        
        # Simulate failure requiring rollback
        with patch.object(sync, '_create_backup', return_value=backup_sha):
            with patch.object(sync, '_rollback', return_value=True) as mock_rollback:
                mock_github_client.create_or_update_file.side_effect = Exception("Sync failed")
                
                result = sync.sync_ecos_root(
                    source_repo="gerivdb/KIVA-CLI",
                    target_repo="gerivdb/ECOYSTEM",
                    content="{}"
                )
                
                # Validate rollback was called
                mock_rollback.assert_called_once()
                assert result["status"] == "FAILED"
                assert result["rolled_back"] == True
    
    def test_partial_sync_recovery(self, mock_github_client):
        """Test recovery from partial sync"""
        from kiva_cli.sync.batch_sync import BatchSync
        
        # Simulate partial failure (2 out of 3 files succeed)
        mock_github_client.create_or_update_file.side_effect = [
            {"commit": {"sha": "file1"}},
            {"commit": {"sha": "file2"}},
            Exception("File 3 failed")
        ]
        
        sync = BatchSync(github_client=mock_github_client)
        
        files = [
            {"path": "file1.md", "content": "content1"},
            {"path": "file2.md", "content": "content2"},
            {"path": "file3.md", "content": "content3"}
        ]
        
        result = sync.sync_multiple_files(
            files=files,
            target_repo="gerivdb/ECOYSTEM"
        )
        
        # Validate partial success
        assert result["status"] == "PARTIAL"
        assert result["succeeded"] == 2
        assert result["failed"] == 1


# CATEGORY: Validation Tests

class TestValidation:
    """Test suite for validation checks"""
    
    def test_phi_cps_validation(self, sample_ecos_root):
        """Test φ-CPS validation"""
        from kiva_cli.validation.phi_cps_validator import PhiCPSValidator
        
        validator = PhiCPSValidator(drift_threshold=0.05)
        
        # Test within threshold
        result = validator.validate(
            baseline=4.231,
            current=4.233,
            delta=0.002
        )
        
        assert result["status"] == "VALID"
        assert result["drift_percentage"] < 5.0
        
        # Test exceeding threshold
        result = validator.validate(
            baseline=4.231,
            current=4.500,
            delta=0.269
        )
        
        assert result["status"] == "INVALID"
        assert result["drift_percentage"] > 5.0
    
    def test_intent_hash_chain_validation(self, wal_database):
        """Test IntentHash chain validation"""
        from kiva_cli.validation.intent_hash_validator import IntentHashValidator
        
        # Add chain of events to WAL
        conn = sqlite3.connect(wal_database)
        cursor = conn.cursor()
        
        hashes = [
            "0x5D8E4A7F9C2B1E3A-WAL-MANAGER",
            "0x9B7E4D2A8C5F1E3A-BATCH-PROCESSOR",
            "0x7E4D8A2F9C5B1E3A-ECOS-ROOT"
        ]
        
        for i, hash_val in enumerate(hashes):
            cursor.execute("""
                INSERT INTO wal_events 
                (timestamp, repo, event_type, entity_id, action, intent_hash, phi_delta, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                "KIVA-CLI",
                "commit",
                f"event{i}",
                "create",
                hash_val,
                0.001,
                f"Event {i}"
            ))
        
        conn.commit()
        conn.close()
        
        # Validate chain
        validator = IntentHashValidator()
        result = validator.validate_chain(str(wal_database))
        
        assert result["status"] == "VALID"
        assert result["chain_length"] == 3
        assert result["integrity"] == "INTACT"
    
    def test_base3_ternary_validation(self, sample_ecos_root):
        """Test base-3 ternary validation"""
        from kiva_cli.validation.base3_validator import Base3Validator
        
        validator = Base3Validator()
        
        # Test all sections
        result = validator.validate_manifest(sample_ecos_root)
        
        assert result["overall_status"] == "VALID"
        assert result["manifest_structure"] == "VALID"
        assert result["repositories"] == "VALID"
        assert result["global_metrics"] == "VALID"
    
    def test_manifest_schema_validation(self, sample_ecos_root):
        """Test manifest schema validation"""
        from kiva_cli.validation.schema_validator import SchemaValidator
        
        validator = SchemaValidator()
        
        # Valid manifest
        result = validator.validate(sample_ecos_root)
        assert result["status"] == "VALID"
        
        # Invalid manifest (missing required field)
        invalid_manifest = sample_ecos_root.copy()
        del invalid_manifest["manifest_version"]
        
        result = validator.validate(invalid_manifest)
        assert result["status"] == "INVALID"
        assert "manifest_version" in result["errors"]
    
    def test_wal_integrity_check(self, wal_database):
        """Test WAL database integrity check"""
        from kiva_cli.validation.wal_validator import WALValidator
        
        validator = WALValidator()
        
        # Check integrity
        result = validator.check_integrity(str(wal_database))
        
        assert result["status"] == "VALID"
        assert result["database_integrity"] == "ok"
        assert result["table_count"] > 0


# CATEGORY: Performance Tests

class TestPerformance:
    """Test suite for performance validation"""
    
    def test_batch_operations_performance(self, mock_github_client):
        """Test performance of batch operations"""
        from kiva_cli.sync.batch_sync import BatchSync
        
        sync = BatchSync(github_client=mock_github_client)
        
        # Create 50 test files
        files = [
            {"path": f"file{i}.md", "content": f"content{i}"}
            for i in range(50)
        ]
        
        mock_github_client.create_or_update_file.return_value = {"commit": {"sha": "test"}}
        
        # Measure performance
        start = time.time()
        result = sync.sync_multiple_files(
            files=files,
            target_repo="gerivdb/ECOYSTEM"
        )
        duration = time.time() - start
        
        # Validate performance (should complete in < 10 seconds)
        assert duration < 10
        assert result["succeeded"] == 50
    
    def test_large_file_sync(self, mock_github_client):
        """Test sync of large files"""
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        # Create large content (10 MB)
        large_content = "x" * (10 * 1024 * 1024)
        
        mock_github_client.create_or_update_file.return_value = {"commit": {"sha": "large"}}
        
        sync = CrossRepoSync(github_client=mock_github_client)
        
        start = time.time()
        result = sync.sync_file(
            path="large_file.txt",
            content=large_content,
            target_repo="gerivdb/ECOYSTEM"
        )
        duration = time.time() - start
        
        # Should complete in reasonable time
        assert result["status"] == "SUCCESS"
        assert duration < 30
    
    def test_concurrent_sync_operations(self, mock_github_client):
        """Test concurrent sync operations"""
        from kiva_cli.sync.concurrent_sync import ConcurrentSync
        import concurrent.futures
        
        sync = ConcurrentSync(github_client=mock_github_client, max_workers=4)
        
        mock_github_client.create_or_update_file.return_value = {"commit": {"sha": "concurrent"}}
        
        # Execute 20 concurrent syncs
        tasks = [
            {"path": f"file{i}.md", "content": f"content{i}"}
            for i in range(20)
        ]
        
        start = time.time()
        results = sync.sync_concurrent(
            tasks=tasks,
            target_repo="gerivdb/ECOYSTEM"
        )
        duration = time.time() - start
        
        # Should be faster than sequential
        assert len(results) == 20
        assert duration < 5  # Much faster than 20 sequential operations
    
    def test_memory_usage(self, sample_ecos_root):
        """Test memory usage during sync"""
        import tracemalloc
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        tracemalloc.start()
        
        # Perform multiple syncs
        sync = CrossRepoSync(github_client=Mock())
        
        for i in range(100):
            sync.prepare_sync_data(sample_ecos_root)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory should not exceed 100 MB
        assert peak / (1024 * 1024) < 100
    
    def test_sync_duration_limits(self, mock_github_client):
        """Test sync duration limits"""
        from kiva_cli.sync.cross_repo_sync import CrossRepoSync
        
        sync = CrossRepoSync(
            github_client=mock_github_client,
            timeout_seconds=5
        )
        
        # Simulate slow operation
        def slow_operation(*args, **kwargs):
            time.sleep(10)
            return {"commit": {"sha": "slow"}}
        
        mock_github_client.create_or_update_file.side_effect = slow_operation
        
        # Should timeout
        start = time.time()
        result = sync.sync_ecos_root(
            source_repo="gerivdb/KIVA-CLI",
            target_repo="gerivdb/ECOYSTEM",
            content="{}"
        )
        duration = time.time() - start
        
        # Should timeout before 10 seconds
        assert duration < 7
        assert result["status"] == "TIMEOUT"


# Test runner configuration

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--cov=kiva_cli",
        "--cov-report=html",
        "--cov-report=term",
        "--maxfail=5",
        "--tb=short"
    ])
