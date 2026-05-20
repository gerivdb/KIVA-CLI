#!/usr/bin/env python3
"""Unit tests for BranchProtectionHandlerSkill."""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kiva_cli.core.branch_protection_handler_skill import (
    BranchProtectionHandlerSkill,
    BranchProtectionStatus,
    FileChange,
    PRStatus,
    PRWorkflow
)


class TestBranchProtectionHandlerSkill(unittest.TestCase):
    """Test BranchProtectionHandlerSkill."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = BranchProtectionHandlerSkill(
            github_token='test_token',
            auto_merge=True,
            delete_branch_on_merge=True
        )
    
    def test_check_branch_protection_protected(self):
        """Test branch protection detection for protected branch."""
        mock_branch = Mock()
        mock_branch.protected = True
        
        mock_repo = Mock()
        mock_repo.get_branch.return_value = mock_branch
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            status = self.handler._check_branch_protection(
                repository='owner/repo',
                branch='main'
            )
            
            self.assertEqual(status, BranchProtectionStatus.PROTECTED)
    
    def test_check_branch_protection_unprotected(self):
        """Test branch protection detection for unprotected branch."""
        mock_branch = Mock()
        mock_branch.protected = False
        
        mock_repo = Mock()
        mock_repo.get_branch.return_value = mock_branch
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            status = self.handler._check_branch_protection(
                repository='owner/repo',
                branch='dev'
            )
            
            self.assertEqual(status, BranchProtectionStatus.UNPROTECTED)
    
    def test_generate_feature_branch_name(self):
        """Test feature branch name generation."""
        branch_name = self.handler._generate_feature_branch_name('main')
        
        self.assertTrue(branch_name.startswith('ecos-auto/main-'))
        self.assertEqual(len(branch_name.split('-')), 3)  # ecos-auto/main-YYYYMMDD-HHMMSS
    
    def test_create_feature_branch(self):
        """Test feature branch creation."""
        mock_commit = Mock()
        mock_commit.sha = 'abc123'
        
        mock_branch = Mock()
        mock_branch.commit = mock_commit
        
        mock_repo = Mock()
        mock_repo.get_branch.return_value = mock_branch
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            self.handler._create_feature_branch(
                repository='owner/repo',
                base_branch='main',
                feature_branch='ecos-auto/main-20260301'
            )
            
            mock_repo.create_git_ref.assert_called_once_with(
                ref='refs/heads/ecos-auto/main-20260301',
                sha='abc123'
            )
    
    def test_push_files_create_new(self):
        """Test pushing new files to branch."""
        mock_repo = Mock()
        mock_repo.get_contents.side_effect = Exception('File not found')
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            files = [
                FileChange(path='test.md', content='# Test')
            ]
            
            self.handler._push_files_to_branch(
                repository='owner/repo',
                branch='feature-branch',
                files=files
            )
            
            mock_repo.create_file.assert_called_once()
    
    def test_push_files_update_existing(self):
        """Test pushing updates to existing files."""
        mock_file = Mock()
        mock_file.sha = 'old_sha'
        
        mock_repo = Mock()
        mock_repo.get_contents.return_value = mock_file
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            files = [
                FileChange(path='test.md', content='# Updated')
            ]
            
            self.handler._push_files_to_branch(
                repository='owner/repo',
                branch='feature-branch',
                files=files
            )
            
            mock_repo.update_file.assert_called_once()
    
    def test_create_pull_request(self):
        """Test PR creation."""
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.html_url = 'https://github.com/owner/repo/pull/123'
        
        mock_repo = Mock()
        mock_repo.create_pull.return_value = mock_pr
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            pr = self.handler._create_pull_request(
                repository='owner/repo',
                base_branch='main',
                feature_branch='ecos-auto/main-20260301',
                title='Test PR',
                body='Test description'
            )
            
            self.assertEqual(pr.number, 123)
            mock_repo.create_pull.assert_called_once()
    
    def test_request_reviewers(self):
        """Test reviewer request."""
        mock_pr = Mock()
        
        self.handler._request_reviewers(mock_pr, ['user1', 'user2'])
        
        mock_pr.create_review_request.assert_called_once_with(
            reviewers=['user1', 'user2']
        )
    
    def test_merge_pull_request_success(self):
        """Test successful PR merge."""
        mock_result = Mock()
        mock_result.merged = True
        mock_result.sha = 'merge_sha_123'
        
        mock_pr = Mock()
        mock_pr.merge.return_value = mock_result
        
        result = self.handler._merge_pull_request(mock_pr)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['sha'], 'merge_sha_123')
        self.assertTrue(result['merged'])
    
    def test_merge_pull_request_failed(self):
        """Test failed PR merge."""
        mock_result = Mock()
        mock_result.merged = False
        mock_result.message = 'Merge conflict'
        
        mock_pr = Mock()
        mock_pr.merge.return_value = mock_result
        
        result = self.handler._merge_pull_request(mock_pr)
        
        self.assertIsNone(result)
    
    def test_delete_branch(self):
        """Test branch deletion."""
        mock_ref = Mock()
        
        mock_repo = Mock()
        mock_repo.get_git_ref.return_value = mock_ref
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            self.handler._delete_branch(
                repository='owner/repo',
                branch='ecos-auto/main-20260301'
            )
            
            mock_ref.delete.assert_called_once()
    
    def test_handle_unprotected_branch(self):
        """Test handling unprotected branch (should skip PR workflow)."""
        mock_branch = Mock()
        mock_branch.protected = False
        
        mock_repo = Mock()
        mock_repo.get_branch.return_value = mock_branch
        
        with patch.object(self.handler, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            files = [FileChange(path='test.md', content='# Test')]
            
            workflow = self.handler.handle(
                repository='owner/repo',
                base_branch='dev',
                files=files,
                title='Test PR',
                body='Test description'
            )
            
            self.assertEqual(workflow.pr_status, PRStatus.FAILED)
            self.assertIn('not protected', workflow.error_message)
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        workflow = PRWorkflow(
            repository='owner/repo',
            base_branch='main',
            feature_branch='ecos-auto/main-20260301',
            title='Test PR',
            body='Description',
            files=[FileChange(path='test.md', content='# Test')],
            protection_status=BranchProtectionStatus.PROTECTED,
            pr_status=PRStatus.MERGED,
            pr_number=123,
            pr_url='https://github.com/owner/repo/pull/123'
        )
        
        json_str = self.handler.to_json(workflow)
        
        self.assertIn('"repository": "owner/repo"', json_str)
        self.assertIn('"pr_status": "MERGED"', json_str)
        self.assertIn('"pr_number": 123', json_str)


if __name__ == '__main__':
    unittest.main()
