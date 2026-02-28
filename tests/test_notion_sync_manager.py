#!/usr/bin/env python3
"""
Tests for NotionSyncManager

Validates:
- GitHub → Notion sync
- Notion → GitHub sync
- Conflict resolution strategies
- Batch operations
- IntentHash tracking
- Base-3 validation
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from kiva_cli.managers.notion_sync_manager import (
    NotionSyncManager,
    SyncConfig,
    SyncEvent
)


class TestSyncConfig:
    """Test SyncConfig dataclass"""
    
    def test_config_creation(self):
        """Test config creation with required fields"""
        config = SyncConfig(
            github_repo="owner/repo",
            notion_database_id="abc123"
        )
        
        assert config.github_repo == "owner/repo"
        assert config.notion_database_id == "abc123"
        assert config.sync_interval_seconds == 300
        assert config.bidirectional is True
        assert config.conflict_strategy == "notion_wins"
    
    def test_config_customization(self):
        """Test custom config values"""
        config = SyncConfig(
            github_repo="owner/repo",
            notion_database_id="abc123",
            sync_interval_seconds=600,
            bidirectional=False,
            conflict_strategy="github_wins"
        )
        
        assert config.sync_interval_seconds == 600
        assert config.bidirectional is False
        assert config.conflict_strategy == "github_wins"


class TestNotionSyncManager:
    """Test NotionSyncManager core functionality"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id",
            sync_interval_seconds=300,
            bidirectional=True,
            conflict_strategy="notion_wins"
        )
    
    @pytest.fixture
    def manager(self, config):
        """Create NotionSyncManager instance"""
        return NotionSyncManager(config)
    
    def test_manager_initialization(self, manager):
        """Test manager initialization"""
        assert manager.config.github_repo == "test/repo"
        assert manager.sync_history == []
        assert manager.last_sync_time is None
    
    def test_config_validation_missing_repo(self):
        """Test validation fails with missing repo"""
        with pytest.raises(ValueError, match="github_repo is required"):
            config = SyncConfig(
                github_repo="",
                notion_database_id="abc123"
            )
            NotionSyncManager(config)
    
    def test_config_validation_missing_db_id(self):
        """Test validation fails with missing DB ID"""
        with pytest.raises(ValueError, match="notion_database_id is required"):
            config = SyncConfig(
                github_repo="owner/repo",
                notion_database_id=""
            )
            NotionSyncManager(config)
    
    def test_config_validation_invalid_strategy(self):
        """Test validation fails with invalid conflict strategy"""
        with pytest.raises(ValueError, match="Invalid conflict_strategy"):
            config = SyncConfig(
                github_repo="owner/repo",
                notion_database_id="abc123",
                conflict_strategy="invalid_strategy"
            )
            NotionSyncManager(config)


class TestGitHubToNotionSync:
    """Test GitHub → Notion synchronization"""
    
    @pytest.fixture
    def manager(self):
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id"
        )
        return NotionSyncManager(config)
    
    @pytest.fixture
    def github_issue_data(self):
        """Sample GitHub issue data"""
        return {
            "number": 42,
            "title": "Test Issue",
            "state": "open",
            "labels": [
                {"name": "bug"},
                {"name": "priority-high"}
            ],
            "assignees": [
                {"login": "user1"},
                {"login": "user2"}
            ],
            "html_url": "https://github.com/test/repo/issues/42",
            "created_at": "2026-02-28T10:00:00Z",
            "updated_at": "2026-02-28T12:00:00Z"
        }
    
    def test_sync_github_issue_to_notion(self, manager, github_issue_data):
        """Test syncing GitHub issue to Notion"""
        event = manager.sync_github_issue_to_notion(github_issue_data)
        
        assert event.status == "SUCCESS"
        assert event.source == "github"
        assert event.target == "notion"
        assert event.entity_type == "issue"
        assert event.entity_id == "42"
        assert event.action == "sync"
        assert event.delta_phi == 0.002
        assert event.intent_hash_pre != ""
        assert event.intent_hash_post != ""
    
    def test_sync_records_history(self, manager, github_issue_data):
        """Test sync event is recorded in history"""
        initial_count = len(manager.sync_history)
        
        manager.sync_github_issue_to_notion(github_issue_data)
        
        assert len(manager.sync_history) == initial_count + 1
        assert manager.sync_history[-1].entity_id == "42"
    
    def test_map_github_issue_properties(self, manager):
        """Test mapping GitHub issue to Notion properties"""
        props = manager._map_github_issue_to_notion(
            issue_number=42,
            title="Test Issue",
            state="open",
            labels=["bug", "enhancement"],
            assignees=["user1"],
            url="https://github.com/test/repo/issues/42",
            created_at="2026-02-28T10:00:00Z",
            updated_at="2026-02-28T12:00:00Z"
        )
        
        assert props["Issue Number"] == 42
        assert props["Title"] == "Test Issue"
        assert props["Status"] == "Open"
        assert props["Labels"] == ["bug", "enhancement"]
        assert props["Assignees"] == ["user1"]
        assert props["GitHub URL"] == "https://github.com/test/repo/issues/42"
        assert props["Source"] == "GitHub"


class TestNotionToGitHubSync:
    """Test Notion → GitHub synchronization"""
    
    @pytest.fixture
    def manager(self):
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id"
        )
        return NotionSyncManager(config)
    
    @pytest.fixture
    def notion_page_data(self):
        """Sample Notion page data"""
        return {
            "id": "page-uuid-123",
            "properties": {
                "Issue Number": 42,
                "Title": "Updated Test Issue",
                "Status": "Closed",
                "Labels": ["bug", "resolved"],
                "Assignees": ["user1", "user2"]
            },
            "last_edited_time": "2026-02-28T14:00:00Z"
        }
    
    def test_sync_notion_page_to_github(self, manager, notion_page_data):
        """Test syncing Notion page to GitHub"""
        event = manager.sync_notion_page_to_github(notion_page_data)
        
        assert event.status == "SUCCESS"
        assert event.source == "notion"
        assert event.target == "github"
        assert event.entity_type == "issue"
        assert event.entity_id == "42"
        assert event.action == "sync"
    
    def test_map_notion_page_properties(self, manager):
        """Test mapping Notion page to GitHub issue format"""
        update = manager._map_notion_page_to_github(
            title="Updated Title",
            status="Closed",
            labels=["bug", "fixed"],
            assignees=["user1"]
        )
        
        assert update["title"] == "Updated Title"
        assert update["state"] == "closed"
        assert update["labels"] == ["bug", "fixed"]
        assert update["assignees"] == ["user1"]


class TestConflictResolution:
    """Test conflict resolution strategies"""
    
    @pytest.fixture
    def github_data(self):
        return {
            "title": "GitHub Title",
            "state": "open",
            "labels": [{"name": "bug"}],
            "assignees": [{"login": "user1"}],
            "updated_at": "2026-02-28T10:00:00Z"
        }
    
    @pytest.fixture
    def notion_data(self):
        return {
            "properties": {
                "Title": "Notion Title",
                "Status": "Closed",
                "Labels": ["bug", "enhancement"],
                "Assignees": ["user2"]
            },
            "last_edited_time": "2026-02-28T12:00:00Z"
        }
    
    def test_notion_wins_strategy(self, github_data, notion_data):
        """Test notion_wins conflict strategy"""
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id",
            conflict_strategy="notion_wins"
        )
        manager = NotionSyncManager(config)
        
        result = manager.resolve_conflict(github_data, notion_data)
        assert result == notion_data
    
    def test_github_wins_strategy(self, github_data, notion_data):
        """Test github_wins conflict strategy"""
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id",
            conflict_strategy="github_wins"
        )
        manager = NotionSyncManager(config)
        
        result = manager.resolve_conflict(github_data, notion_data)
        assert result == github_data
    
    def test_merge_strategy(self, github_data, notion_data):
        """Test merge conflict strategy"""
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id",
            conflict_strategy="merge"
        )
        manager = NotionSyncManager(config)
        
        result = manager.resolve_conflict(github_data, notion_data)
        
        # Should merge labels and assignees
        assert "bug" in result["labels"]
        assert "enhancement" in result["labels"]
        assert "user1" in result["assignees"]
        assert "user2" in result["assignees"]


class TestBatchOperations:
    """Test batch sync operations"""
    
    @pytest.fixture
    def manager(self):
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id"
        )
        return NotionSyncManager(config)
    
    def test_sync_multiple_github_issues(self, manager):
        """Test batch sync of multiple GitHub issues"""
        issues = [
            {"number": i, "title": f"Issue {i}", "state": "open",
             "labels": [], "assignees": [], "html_url": f"https://github.com/test/repo/issues/{i}",
             "created_at": "2026-02-28T10:00:00Z", "updated_at": "2026-02-28T12:00:00Z"}
            for i in range(1, 6)
        ]
        
        events = manager.sync_all_github_issues(issues)
        
        assert len(events) == 5
        assert all(e.status == "SUCCESS" for e in events)
        assert manager.last_sync_time is not None
    
    def test_sync_stats_after_batch(self, manager):
        """Test stats calculation after batch sync"""
        issues = [
            {"number": i, "title": f"Issue {i}", "state": "open",
             "labels": [], "assignees": [], "html_url": f"https://github.com/test/repo/issues/{i}",
             "created_at": "2026-02-28T10:00:00Z", "updated_at": "2026-02-28T12:00:00Z"}
            for i in range(1, 11)
        ]
        
        manager.sync_all_github_issues(issues)
        stats = manager.get_sync_stats()
        
        assert stats["total_events"] == 10
        assert stats["successful"] == 10
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["total_delta_phi"] > 0


class TestIntentHashTracking:
    """Test IntentHash tracking"""
    
    @pytest.fixture
    def manager(self):
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id",
            intent_hash_tracking=True
        )
        return NotionSyncManager(config)
    
    def test_intent_hash_generation(self, manager):
        """Test IntentHash generation"""
        data = {"test": "data", "number": 42}
        hash1 = manager._compute_intent_hash(data)
        
        assert hash1.startswith("IntentHash¹¹:sha3-256:")
        
        # Same data should produce same hash
        hash2 = manager._compute_intent_hash(data)
        assert hash1 == hash2
        
        # Different data should produce different hash
        data2 = {"test": "different", "number": 43}
        hash3 = manager._compute_intent_hash(data2)
        assert hash1 != hash3
    
    def test_sync_event_has_intent_hashes(self, manager):
        """Test sync events contain IntentHash values"""
        issue_data = {
            "number": 1,
            "title": "Test",
            "state": "open",
            "labels": [],
            "assignees": [],
            "html_url": "https://github.com/test/repo/issues/1",
            "created_at": "2026-02-28T10:00:00Z",
            "updated_at": "2026-02-28T12:00:00Z"
        }
        
        event = manager.sync_github_issue_to_notion(issue_data)
        
        assert event.intent_hash_pre != ""
        assert event.intent_hash_post != ""
        assert event.intent_hash_pre.startswith("IntentHash¹¹:")
        assert event.intent_hash_post.startswith("IntentHash¹¹:")


class TestSyncHistory:
    """Test sync history management"""
    
    @pytest.fixture
    def manager(self):
        config = SyncConfig(
            github_repo="test/repo",
            notion_database_id="test-db-id"
        )
        return NotionSyncManager(config)
    
    def test_export_sync_history(self, manager, tmp_path):
        """Test exporting sync history to JSON"""
        # Create some sync events
        issues = [
            {"number": i, "title": f"Issue {i}", "state": "open",
             "labels": [], "assignees": [], "html_url": f"https://github.com/test/repo/issues/{i}",
             "created_at": "2026-02-28T10:00:00Z", "updated_at": "2026-02-28T12:00:00Z"}
            for i in range(1, 4)
        ]
        manager.sync_all_github_issues(issues)
        
        # Export history
        output_file = tmp_path / "history.json"
        exported_path = manager.export_sync_history(output_file)
        
        assert exported_path.exists()
        
        # Verify JSON content
        with open(exported_path, 'r') as f:
            history = json.load(f)
        
        assert len(history) == 3
        assert all("event_id" in event for event in history)
        assert all("intent_hash_pre" in event for event in history)
