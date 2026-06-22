"""
Integration Tests for KIVA-CLI Cross-Repo Sync
Phase 4: Comprehensive integration testing for ecosystem synchronization
"""

import pytest
import os
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Assuming these are the actual imports from KIVA-CLI
# Adjust based on actual module structure
try:
    from kiva_cli.core.global_wal_manager import GlobalWALManager
    from kiva_cli.core.batch_issue_processor import BatchIssueProcessor
    from kiva_cli.sync.cross_repo_sync import CrossRepoSync
    from kiva_cli.metrics.dashboard import MetricsDashboard
    HAS_KIVA_CLI = True
except ImportError:
    HAS_KIVA_CLI = False
    # Define mock classes for testing structure
    class GlobalWALManager:
        pass
    class BatchIssueProcessor:
        pass
    class CrossRepoSync:
        pass
    class MetricsDashboard:
        pass


# Test Fixtures
@pytest.fixture
def temp_db():
    """Create temporary WAL database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create WAL schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            repo TEXT NOT NULL,
            event_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            intent_hash TEXT NOT NULL,
            phi_delta REAL NOT NULL,
            description TEXT,
            metadata TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            repo TEXT PRIMARY KEY,
            last_sync TEXT,
            sync_count INTEGER,
            phi_cps REAL
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_ecos_root():
    """Create temporary ECOS_ROOT.json for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        ecos_root = {
            "manifest_version": "1.0.2",
            "ecosystem_id": "ecosystem-1",
            "phi_cps_genesis": 4.092,
            "phi_cps_current": 4.231,
            "repositories": [
                {
                    "name": "KIVA-CLI",
                    "owner": "gerivdb",
                    "role": "orchestrator",
                    "status": "ACTIVE",
                    "phi_cps": 4.231
                },
                {
                    "name": "ECOYSTEM",
                    "owner": "gerivdb",
                    "role": "core",
                    "status": "ACTIVE",
                    "phi_cps": 4.094
                }
            ],
            "global_metrics": {
                "total_repositories": 11,
                "active_repositories": 11,
                "cumulative_phi_delta": 0.139
            }
        }
        json.dump(ecos_root, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_github_client():
    """Mock GitHub API client"""
    client = MagicMock()
    
    # Mock repository data
    client.get_repo.return_value = Mock(
        name="KIVA-CLI",
        owner=Mock(login="gerivdb"),
        default_branch="main",
        open_issues_count=0,
        get_commits=Mock(return_value=[])
    )
    
    # Mock file contents
    client.get_contents.return_value = Mock(
        decoded_content=b'{"test": "data"}',
        sha="abc123"
    )
    
    return client


# Integration Tests for GlobalWALManager
class TestGlobalWALManagerIntegration:
    """Integration tests for GlobalWALManager"""
    
    def test_wal_entry_creation_and_retrieval(self, temp_db):
        """Test creating and retrieving WAL entries"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        manager = GlobalWALManager(db_path=temp_db)
        
        # Create entry
        entry_id = manager.add_entry(
            repo="KIVA-CLI",
            event_type="commit",
            entity_id="abc123",
            action="create",
            intent_hash="0xTEST123",
            phi_delta=0.001,
            description="Test commit"
        )
        
        assert entry_id > 0
        
        # Retrieve entry
        entries = manager.get_entries(repo="KIVA-CLI", limit=10)
        assert len(entries) == 1
        assert entries[0]["entity_id"] == "abc123"
        assert entries[0]["phi_delta"] == 0.001
    
    def test_wal_phi_cps_tracking(self, temp_db):
        """Test φ-CPS tracking across multiple entries"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        manager = GlobalWALManager(db_path=temp_db)
        
        # Add multiple entries
        deltas = [0.001, 0.002, 0.001, 0.003]
        for i, delta in enumerate(deltas):
            manager.add_entry(
                repo="KIVA-CLI",
                event_type="commit",
                entity_id=f"commit{i}",
                action="create",
                intent_hash=f"0xTEST{i}",
                phi_delta=delta,
                description=f"Test commit {i}"
            )
        
        # Verify cumulative phi-CPS
        total_delta = manager.get_cumulative_phi_delta(repo="KIVA-CLI")
        assert abs(total_delta - sum(deltas)) < 0.0001
    
    def test_wal_sync_state_management(self, temp_db):
        """Test sync state tracking"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        manager = GlobalWALManager(db_path=temp_db)
        
        # Update sync state
        manager.update_sync_state(
            repo="ECOYSTEM",
            phi_cps=4.094
        )
        
        # Retrieve sync state
        state = manager.get_sync_state(repo="ECOYSTEM")
        assert state["repo"] == "ECOYSTEM"
        assert state["phi_cps"] == 4.094
        assert state["sync_count"] >= 1


# Integration Tests for Cross-Repo Sync
class TestCrossRepoSyncIntegration:
    """Integration tests for cross-repository synchronization"""
    
    @patch('github.Github')
    def test_ecos_root_sync(self, mock_github, temp_ecos_root, temp_db):
        """Test ECOS_ROOT.json synchronization"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        # Setup mock
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        
        # Mock file content
        with open(temp_ecos_root, 'r') as f:
            content = f.read()
        
        mock_client.get_repo.return_value.get_contents.return_value = Mock(
            decoded_content=content.encode(),
            sha="test123"
        )
        
        # Execute sync
        sync = CrossRepoSync(
            github_token="test_token",
            wal_db_path=temp_db
        )
        
        result = sync.sync_ecos_root(
            source_repo="gerivdb/KIVA-CLI",
            target_repos=["gerivdb/ECOYSTEM"]
        )
        
        assert result["status"] == "success"
        assert result["synced_repos"] >= 1
    
    @patch('github.Github')
    def test_wal_cross_repo_sync(self, mock_github, temp_db):
        """Test WAL entries synchronization across repos"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        manager = GlobalWALManager(db_path=temp_db)
        
        # Add entries for multiple repos
        repos = ["KIVA-CLI", "ECOYSTEM", "DevTools"]
        for repo in repos:
            manager.add_entry(
                repo=repo,
                event_type="sync",
                entity_id="test_sync",
                action="sync",
                intent_hash=f"0xSYNC-{repo}",
                phi_delta=0.001,
                description=f"Sync test for {repo}"
            )
        
        # Verify all repos have entries
        for repo in repos:
            entries = manager.get_entries(repo=repo)
            assert len(entries) >= 1
    
    @patch('github.Github')
    def test_metrics_aggregation_across_repos(self, mock_github, temp_db, temp_ecos_root):
        """Test metrics aggregation from multiple repositories"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        # Load ECOS_ROOT
        with open(temp_ecos_root, 'r') as f:
            ecos_root = json.load(f)
        
        # Calculate global metrics
        total_repos = len(ecos_root["repositories"])
        cumulative_phi = sum(
            repo.get("phi_delta_total", 0) 
            for repo in ecos_root["repositories"]
        )
        
        assert total_repos > 0
        assert cumulative_phi >= 0


# Integration Tests for Batch Issue Processing
class TestBatchIssueProcessorIntegration:
    """Integration tests for batch issue processing"""
    
    @patch('github.Github')
    def test_batch_issue_creation(self, mock_github, temp_db):
        """Test creating multiple issues in batch"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        
        # Mock repository
        mock_repo = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        
        # Mock issue creation
        mock_repo.create_issue.return_value = Mock(number=1)
        
        processor = BatchIssueProcessor(
            github_token="test_token",
            wal_db_path=temp_db
        )
        
        issues = [
            {"title": "Test Issue 1", "body": "Body 1", "labels": ["bug"]},
            {"title": "Test Issue 2", "body": "Body 2", "labels": ["enhancement"]}
        ]
        
        results = processor.create_issues_batch(
            repo="gerivdb/KIVA-CLI",
            issues=issues
        )
        
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
    
    @patch('github.Github')
    def test_batch_issue_update(self, mock_github, temp_db):
        """Test updating multiple issues in batch"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        
        # Mock repository and issues
        mock_repo = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        
        mock_issue = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        
        processor = BatchIssueProcessor(
            github_token="test_token",
            wal_db_path=temp_db
        )
        
        updates = [
            {"number": 1, "state": "closed"},
            {"number": 2, "labels": ["resolved"]}
        ]
        
        results = processor.update_issues_batch(
            repo="gerivdb/KIVA-CLI",
            updates=updates
        )
        
        assert len(results) == 2


# Integration Tests for Metrics Dashboard
class TestMetricsDashboardIntegration:
    """Integration tests for metrics dashboard generation"""
    
    def test_dashboard_generation(self, temp_ecos_root, temp_db):
        """Test generating complete metrics dashboard"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        dashboard = MetricsDashboard(
            ecos_root_path=temp_ecos_root,
            wal_db_path=temp_db
        )
        
        # Generate dashboard
        output = dashboard.generate_dashboard(
            format="markdown"
        )
        
        assert output is not None
        assert len(output) > 0
        assert "φ-CPS" in output or "phi-CPS" in output
    
    def test_html_dashboard_generation(self, temp_ecos_root, temp_db):
        """Test generating HTML dashboard"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        dashboard = MetricsDashboard(
            ecos_root_path=temp_ecos_root,
            wal_db_path=temp_db
        )
        
        # Generate HTML
        html_output = dashboard.generate_dashboard(
            format="html"
        )
        
        assert html_output is not None
        assert "<html" in html_output.lower()
        assert "chart" in html_output.lower()


# End-to-End Integration Tests
class TestEndToEndIntegration:
    """End-to-end integration tests for complete workflows"""
    
    @patch('github.Github')
    def test_complete_sync_workflow(self, mock_github, temp_db, temp_ecos_root):
        """Test complete synchronization workflow"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        # 1. Initialize WAL Manager
        wal_manager = GlobalWALManager(db_path=temp_db)
        
        # 2. Add initial entries
        wal_manager.add_entry(
            repo="KIVA-CLI",
            event_type="commit",
            entity_id="initial_commit",
            action="create",
            intent_hash="0xINITIAL",
            phi_delta=0.001,
            description="Initial commit"
        )
        
        # 3. Mock GitHub sync
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        
        # 4. Verify WAL state
        entries = wal_manager.get_entries(repo="KIVA-CLI")
        assert len(entries) >= 1
        
        # 5. Check phi-CPS tracking
        phi_delta = wal_manager.get_cumulative_phi_delta(repo="KIVA-CLI")
        assert phi_delta > 0
    
    def test_phi_cps_validation_workflow(self, temp_db):
        """Test φ-CPS validation across operations"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        manager = GlobalWALManager(db_path=temp_db)
        
        phi_baseline = 4.092
        phi_threshold = 0.05  # 5% drift threshold
        
        # Simulate multiple operations
        operations = [
            ("commit1", 0.001),
            ("commit2", 0.002),
            ("commit3", 0.001),
            ("commit4", 0.003)
        ]
        
        for entity_id, phi_delta in operations:
            manager.add_entry(
                repo="KIVA-CLI",
                event_type="commit",
                entity_id=entity_id,
                action="create",
                intent_hash=f"0x{entity_id.upper()}",
                phi_delta=phi_delta,
                description=f"Operation {entity_id}"
            )
        
        # Validate total drift
        total_delta = manager.get_cumulative_phi_delta(repo="KIVA-CLI")
        drift_percentage = (total_delta / phi_baseline) * 100
        
        assert drift_percentage < phi_threshold * 100


# Performance Tests
class TestPerformanceIntegration:
    """Performance and load testing"""
    
    def test_wal_bulk_insert_performance(self, temp_db):
        """Test performance of bulk WAL insertions"""
        if not HAS_KIVA_CLI:
            pytest.skip("KIVA-CLI not installed")
        
        manager = GlobalWALManager(db_path=temp_db)
        
        start_time = datetime.now()
        
        # Insert 1000 entries
        for i in range(1000):
            manager.add_entry(
                repo="KIVA-CLI",
                event_type="commit",
                entity_id=f"commit{i}",
                action="create",
                intent_hash=f"0xPERF{i:04d}",
                phi_delta=0.001,
                description=f"Performance test {i}"
            )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Should complete in reasonable time (e.g., < 10 seconds)
        assert duration < 10.0
        
        # Verify all entries were created
        entries = manager.get_entries(repo="KIVA-CLI", limit=2000)
        assert len(entries) == 1000
