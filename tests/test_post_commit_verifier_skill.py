#!/usr/bin/env python3
"""Unit tests for PostCommitVerifierSkill."""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.core.post_commit_verifier_skill import (
    FileExpectation,
    PostCommitVerifierSkill,
    VerificationStatus,
    VerificationResult
)


class TestPostCommitVerifierSkill(unittest.TestCase):
    """Test PostCommitVerifierSkill."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.verifier = PostCommitVerifierSkill(
            github_token='test_token',
            max_retries=3,
            retry_delay=0.1,  # Fast for testing
            auto_rollback=False
        )
    
    def test_verify_file_success(self):
        """Test successful file verification."""
        # Mock GitHub API
        mock_file = Mock()
        mock_file.sha = 'abc123'
        mock_file.size = 1000
        
        mock_repo = Mock()
        mock_repo.get_contents.return_value = mock_file
        
        with patch.object(self.verifier, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            expected = FileExpectation(path='test.md', sha='abc123')
            result = self.verifier._verify_file(
                repository='owner/repo',
                commit_sha='commit123',
                branch='main',
                expected=expected
            )
            
            self.assertEqual(result.status, VerificationStatus.VALID)
            self.assertEqual(result.actual_sha, 'abc123')
            self.assertEqual(result.actual_size, 1000)
            self.assertEqual(result.attempts, 1)
    
    def test_verify_file_sha_mismatch(self):
        """Test file verification with SHA mismatch."""
        mock_file = Mock()
        mock_file.sha = 'xyz789'
        
        mock_repo = Mock()
        mock_repo.get_contents.return_value = mock_file
        
        with patch.object(self.verifier, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            expected = FileExpectation(path='test.md', sha='abc123')
            result = self.verifier._verify_file(
                repository='owner/repo',
                commit_sha='commit123',
                branch='main',
                expected=expected
            )
            
            self.assertEqual(result.status, VerificationStatus.INVALID)
            self.assertIn('SHA mismatch', result.error_message)
            self.assertEqual(result.attempts, 3)  # Should retry
    
    def test_verify_file_not_found(self):
        """Test file verification when file doesn't exist."""
        mock_repo = Mock()
        mock_repo.get_contents.side_effect = Exception('File not found')
        
        with patch.object(self.verifier, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            expected = FileExpectation(path='missing.md')
            result = self.verifier._verify_file(
                repository='owner/repo',
                commit_sha='commit123',
                branch='main',
                expected=expected
            )
            
            self.assertEqual(result.status, VerificationStatus.INVALID)
            self.assertIn('Error fetching file', result.error_message)
            self.assertEqual(result.attempts, 3)
    
    def test_verify_multiple_files(self):
        """Test verification of multiple files."""
        mock_file1 = Mock(sha='sha1', size=100)
        mock_file2 = Mock(sha='sha2', size=200)
        
        mock_repo = Mock()
        mock_repo.get_contents.side_effect = [mock_file1, mock_file2]
        
        with patch.object(self.verifier, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            expectations = [
                FileExpectation(path='file1.md', sha='sha1'),
                FileExpectation(path='file2.md', sha='sha2')
            ]
            
            verification = self.verifier.verify(
                repository='owner/repo',
                commit_sha='commit123',
                branch='main',
                expected_files=expectations
            )
            
            self.assertEqual(verification.overall_status, VerificationStatus.VALID)
            self.assertEqual(len(verification.results), 2)
            self.assertEqual(verification.total_attempts, 2)
    
    def test_overall_status_computation(self):
        """Test overall status computation."""
        # All valid
        results = [
            VerificationResult(
                status=VerificationStatus.VALID,
                expected_file=FileExpectation(path='file1.md')
            ),
            VerificationResult(
                status=VerificationStatus.VALID,
                expected_file=FileExpectation(path='file2.md')
            )
        ]
        status = self.verifier._compute_overall_status(results)
        self.assertEqual(status, VerificationStatus.VALID)
        
        # One invalid
        results[1].status = VerificationStatus.INVALID
        status = self.verifier._compute_overall_status(results)
        self.assertEqual(status, VerificationStatus.INVALID)
        
        # Empty results
        status = self.verifier._compute_overall_status([])
        self.assertEqual(status, VerificationStatus.UNKNOWN)
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        self.verifier.exponential_backoff = True
        self.verifier.retry_delay = 1.0
        
        self.assertEqual(self.verifier._calculate_retry_delay(1), 1.0)
        self.assertEqual(self.verifier._calculate_retry_delay(2), 2.0)
        self.assertEqual(self.verifier._calculate_retry_delay(3), 4.0)
    
    def test_linear_backoff(self):
        """Test linear backoff."""
        self.verifier.exponential_backoff = False
        self.verifier.retry_delay = 1.0
        
        self.assertEqual(self.verifier._calculate_retry_delay(1), 1.0)
        self.assertEqual(self.verifier._calculate_retry_delay(2), 1.0)
        self.assertEqual(self.verifier._calculate_retry_delay(3), 1.0)
    
    def test_error_summary_generation(self):
        """Test error summary generation."""
        results = [
            VerificationResult(
                status=VerificationStatus.VALID,
                expected_file=FileExpectation(path='file1.md')
            ),
            VerificationResult(
                status=VerificationStatus.INVALID,
                expected_file=FileExpectation(path='file2.md'),
                error_message='File not found'
            ),
            VerificationResult(
                status=VerificationStatus.INVALID,
                expected_file=FileExpectation(path='file3.md'),
                error_message='SHA mismatch'
            )
        ]
        
        summary = self.verifier._generate_error_summary(results)
        self.assertIn('2/3 files failed', summary)
        self.assertIn('file2.md', summary)
        self.assertIn('file3.md', summary)
        self.assertIn('File not found', summary)
        self.assertIn('SHA mismatch', summary)
    
    def test_auto_rollback_trigger(self):
        """Test auto-rollback triggers on failure."""
        self.verifier.auto_rollback = True
        
        mock_repo = Mock()
        mock_repo.get_contents.side_effect = Exception('File not found')
        
        with patch.object(self.verifier, 'github_client') as mock_client:
            mock_client.get_repo.return_value = mock_repo
            
            with patch.object(self.verifier, 'rollback') as mock_rollback:
                expectations = [FileExpectation(path='missing.md')]
                
                verification = self.verifier.verify(
                    repository='owner/repo',
                    commit_sha='commit123',
                    branch='main',
                    expected_files=expectations
                )
                
                self.assertEqual(verification.overall_status, VerificationStatus.INVALID)
                self.assertTrue(verification.rollback_triggered)
                mock_rollback.assert_called_once_with(verification)
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        from tools.core.post_commit_verifier_skill import PostCommitVerification
        
        verification = PostCommitVerification(
            repository='owner/repo',
            commit_sha='abc123',
            branch='main',
            expected_files=[FileExpectation(path='test.md')],
            overall_status=VerificationStatus.VALID,
            total_attempts=1,
            duration_seconds=1.5
        )
        verification.results = [
            VerificationResult(
                status=VerificationStatus.VALID,
                expected_file=FileExpectation(path='test.md'),
                actual_sha='sha123',
                actual_size=1000,
                attempts=1
            )
        ]
        
        json_str = self.verifier.to_json(verification)
        self.assertIn('"repository": "owner/repo"', json_str)
        self.assertIn('"overall_status": "VALID"', json_str)
        self.assertIn('"total_attempts": 1', json_str)
    
    def test_file_expectation_formats(self):
        """Test different FileExpectation formats."""
        # Path only
        exp1 = FileExpectation(path='file.md')
        self.assertEqual(exp1.path, 'file.md')
        self.assertIsNone(exp1.sha)
        self.assertIsNone(exp1.size)
        
        # Path + SHA
        exp2 = FileExpectation(path='file.md', sha='abc123')
        self.assertEqual(exp2.sha, 'abc123')
        
        # Path + SHA + size
        exp3 = FileExpectation(path='file.md', sha='abc123', size=1000)
        self.assertEqual(exp3.size, 1000)


if __name__ == '__main__':
    unittest.main()
