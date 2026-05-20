#!/usr/bin/env python3
"""PostCommitVerifierSkill - Verify files exist after GitHub push.

This skill closes the verification loop by checking that files pushed to GitHub
actually exist at the expected paths with the expected content (SHA validation).

Prevents false positives where push succeeds but files are missing due to:
- Branch protection silent failures
- Race conditions in GitHub API
- Network timeouts during multi-file push
- Silent merge conflicts

Part of P0 critical skills for No-HITL autonomous operation.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class VerificationStatus(Enum):
    """Ternary verification status."""
    UNKNOWN = 0  # Not yet verified
    VALID = 1    # Files exist and match expected
    INVALID = 2  # Files missing or SHA mismatch


@dataclass
class FileExpectation:
    """Expected file after push."""
    path: str
    sha: Optional[str] = None  # Expected SHA, None = just check existence
    size: Optional[int] = None  # Expected size in bytes
    content_snippet: Optional[str] = None  # First 100 chars for validation


@dataclass
class VerificationResult:
    """Result of file verification."""
    status: VerificationStatus
    expected_file: FileExpectation
    actual_sha: Optional[str] = None
    actual_size: Optional[int] = None
    error_message: Optional[str] = None
    verified_at: Optional[str] = None
    attempts: int = 1


@dataclass
class PostCommitVerification:
    """Complete verification operation."""
    repository: str
    commit_sha: str
    branch: str
    expected_files: List[FileExpectation]
    results: List[VerificationResult] = field(default_factory=list)
    overall_status: VerificationStatus = VerificationStatus.UNKNOWN
    total_attempts: int = 0
    duration_seconds: float = 0.0
    rollback_triggered: bool = False
    error_summary: Optional[str] = None


class PostCommitVerifierSkill:
    """Skill to verify files exist after GitHub push.
    
    Usage:
        verifier = PostCommitVerifierSkill(
            github_token=os.getenv('GITHUB_TOKEN'),
            max_retries=3,
            retry_delay=2.0
        )
        
        expectations = [
            FileExpectation(
                path='guides/components/MyGuide.md',
                sha='abc123...',  # Optional
                size=15000       # Optional
            )
        ]
        
        verification = verifier.verify(
            repository='gerivdb/BRAIN',
            commit_sha='def456...',
            branch='main',
            expected_files=expectations
        )
        
        if verification.overall_status == VerificationStatus.VALID:
            print("All files verified!")
        else:
            print(f"Verification failed: {verification.error_summary}")
            if verifier.auto_rollback:
                verifier.rollback(verification)
    """
    
    def __init__(
        self,
        github_token: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        exponential_backoff: bool = True,
        auto_rollback: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize verifier.
        
        Args:
            github_token: GitHub API token
            max_retries: Maximum verification attempts per file
            retry_delay: Initial delay between retries (seconds)
            exponential_backoff: Use exponential backoff for retries
            auto_rollback: Automatically trigger rollback on verification failure
            logger: Logger instance (creates default if None)
        """
        self.github_token = github_token
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.auto_rollback = auto_rollback
        self.logger = logger or logging.getLogger(__name__)
        
        # Lazy import to avoid circular dependencies
        self._github_client = None
    
    @property
    def github_client(self):
        """Lazy-load GitHub client."""
        if self._github_client is None:
            try:
                from github import Github
                self._github_client = Github(self.github_token)
            except ImportError:
                raise RuntimeError(
                    "PyGithub not installed. Run: pip install PyGithub"
                )
        return self._github_client
    
    def verify(
        self,
        repository: str,
        commit_sha: str,
        branch: str,
        expected_files: List[FileExpectation]
    ) -> PostCommitVerification:
        """Verify files exist after commit.
        
        Args:
            repository: Repo in format 'owner/repo'
            commit_sha: Commit SHA to verify
            branch: Branch name
            expected_files: List of expected files
            
        Returns:
            PostCommitVerification with results
        """
        start_time = time.time()
        
        verification = PostCommitVerification(
            repository=repository,
            commit_sha=commit_sha,
            branch=branch,
            expected_files=expected_files
        )
        
        self.logger.info(
            f"Starting verification for {repository}@{commit_sha[:8]} "
            f"({len(expected_files)} files)"
        )
        
        # Verify each expected file
        for expected in expected_files:
            result = self._verify_file(
                repository=repository,
                commit_sha=commit_sha,
                branch=branch,
                expected=expected
            )
            verification.results.append(result)
            verification.total_attempts += result.attempts
        
        # Determine overall status
        verification.overall_status = self._compute_overall_status(
            verification.results
        )
        verification.duration_seconds = time.time() - start_time
        
        # Generate error summary if needed
        if verification.overall_status == VerificationStatus.INVALID:
            verification.error_summary = self._generate_error_summary(
                verification.results
            )
            
            # Trigger rollback if enabled
            if self.auto_rollback:
                self.logger.warning(
                    f"Auto-rollback triggered for {repository}@{commit_sha[:8]}"
                )
                verification.rollback_triggered = True
                self.rollback(verification)
        
        self.logger.info(
            f"Verification complete: {verification.overall_status.name} "
            f"({verification.duration_seconds:.2f}s, "
            f"{verification.total_attempts} total attempts)"
        )
        
        return verification
    
    def _verify_file(
        self,
        repository: str,
        commit_sha: str,
        branch: str,
        expected: FileExpectation
    ) -> VerificationResult:
        """Verify a single file with retries."""
        result = VerificationResult(
            status=VerificationStatus.UNKNOWN,
            expected_file=expected
        )
        
        for attempt in range(1, self.max_retries + 1):
            result.attempts = attempt
            
            try:
                # Fetch file from GitHub
                repo = self.github_client.get_repo(repository)
                file_content = repo.get_contents(expected.path, ref=commit_sha)
                
                # Validate SHA if provided
                if expected.sha and file_content.sha != expected.sha:
                    result.status = VerificationStatus.INVALID
                    result.error_message = (
                        f"SHA mismatch: expected {expected.sha[:8]}, "
                        f"got {file_content.sha[:8]}"
                    )
                    self.logger.warning(
                        f"Attempt {attempt}/{self.max_retries}: {result.error_message}"
                    )
                else:
                    # Success
                    result.status = VerificationStatus.VALID
                    result.actual_sha = file_content.sha
                    result.actual_size = file_content.size
                    result.verified_at = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    self.logger.debug(
                        f"File verified: {expected.path} "
                        f"(SHA: {file_content.sha[:8]}, {file_content.size} bytes)"
                    )
                    return result
                
            except Exception as e:
                result.status = VerificationStatus.INVALID
                result.error_message = f"Error fetching file: {str(e)}"
                self.logger.warning(
                    f"Attempt {attempt}/{self.max_retries}: {result.error_message}"
                )
            
            # Retry with backoff
            if attempt < self.max_retries:
                delay = self._calculate_retry_delay(attempt)
                self.logger.debug(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
        
        # All attempts failed
        return result
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with optional exponential backoff."""
        if self.exponential_backoff:
            return self.retry_delay * (2 ** (attempt - 1))
        return self.retry_delay
    
    def _compute_overall_status(
        self,
        results: List[VerificationResult]
    ) -> VerificationStatus:
        """Compute overall status from individual results."""
        if not results:
            return VerificationStatus.UNKNOWN
        
        # Any invalid result makes overall invalid
        if any(r.status == VerificationStatus.INVALID for r in results):
            return VerificationStatus.INVALID
        
        # All must be valid
        if all(r.status == VerificationStatus.VALID for r in results):
            return VerificationStatus.VALID
        
        return VerificationStatus.UNKNOWN
    
    def _generate_error_summary(self, results: List[VerificationResult]) -> str:
        """Generate human-readable error summary."""
        failed = [r for r in results if r.status == VerificationStatus.INVALID]
        
        if not failed:
            return "Unknown verification error"
        
        summary = f"{len(failed)}/{len(results)} files failed verification:\n"
        for result in failed:
            summary += f"  - {result.expected_file.path}: {result.error_message}\n"
        
        return summary.strip()
    
    def rollback(self, verification: PostCommitVerification) -> None:
        """Trigger rollback on verification failure.
        
        NOTE: Actual rollback implementation depends on integration with
        AutoRollbackPipeline. This is a placeholder that logs the intent.
        """
        self.logger.error(
            f"ROLLBACK TRIGGERED for {verification.repository}@"
            f"{verification.commit_sha[:8]}: {verification.error_summary}"
        )
        
        # TODO: Integrate with AutoRollbackPipeline
        # from tools.core.auto_rollback_pipeline import AutoRollbackPipeline
        # pipeline = AutoRollbackPipeline()
        # pipeline.rollback(commit_sha=verification.commit_sha)
    
    def to_json(self, verification: PostCommitVerification) -> str:
        """Serialize verification to JSON."""
        return json.dumps({
            "repository": verification.repository,
            "commit_sha": verification.commit_sha,
            "branch": verification.branch,
            "overall_status": verification.overall_status.name,
            "total_attempts": verification.total_attempts,
            "duration_seconds": verification.duration_seconds,
            "rollback_triggered": verification.rollback_triggered,
            "error_summary": verification.error_summary,
            "results": [
                {
                    "path": r.expected_file.path,
                    "status": r.status.name,
                    "actual_sha": r.actual_sha,
                    "actual_size": r.actual_size,
                    "error_message": r.error_message,
                    "verified_at": r.verified_at,
                    "attempts": r.attempts
                }
                for r in verification.results
            ]
        }, indent=2)
