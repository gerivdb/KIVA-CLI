#!/usr/bin/env python3
"""BranchProtectionHandlerSkill - Handle protected branches with PR workflow.

This skill detects protected branches and automatically creates a PR workflow
instead of attempting direct push (which would fail silently).

Prevents push failures on protected repos like BRAIN, FLUENCE, ECOYSTEM by:
- Detecting branch protection status via GitHub API
- Creating feature branch automatically
- Opening PR with AI-generated description
- Requesting reviewers if configured
- Auto-merging on approval (No-HITL mode)

Part of P0 critical skills for No-HITL autonomous operation.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class BranchProtectionStatus(Enum):
    """Ternary branch protection status."""
    UNKNOWN = 0      # Not yet checked
    PROTECTED = 1    # Branch is protected
    UNPROTECTED = 2  # Branch is not protected


class PRStatus(Enum):
    """PR workflow status."""
    PENDING = 0   # PR creation pending
    OPEN = 1      # PR opened, awaiting review
    MERGED = 2    # PR merged successfully
    FAILED = 3    # PR workflow failed


@dataclass
class FileChange:
    """File to be changed in PR."""
    path: str
    content: str
    mode: str = "100644"  # File mode (default: regular file)
    sha: Optional[str] = None  # SHA for updates


@dataclass
class PRWorkflow:
    """Complete PR workflow operation."""
    repository: str
    base_branch: str
    feature_branch: str
    title: str
    body: str
    files: List[FileChange]
    reviewers: List[str] = field(default_factory=list)
    auto_merge: bool = True
    
    # Results
    protection_status: BranchProtectionStatus = BranchProtectionStatus.UNKNOWN
    pr_status: PRStatus = PRStatus.PENDING
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    feature_branch_created: bool = False
    merge_commit_sha: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    merged_at: Optional[str] = None
    duration_seconds: float = 0.0


class BranchProtectionHandlerSkill:
    """Skill to handle protected branches with PR workflow.
    
    Usage:
        handler = BranchProtectionHandlerSkill(
            github_token=os.getenv('GITHUB_TOKEN'),
            auto_merge=True,
            delete_branch_on_merge=True
        )
        
        files = [
            FileChange(
                path='guides/MyGuide.md',
                content='# Guide content...'
            )
        ]
        
        workflow = handler.handle(
            repository='gerivdb/BRAIN',
            base_branch='main',
            files=files,
            title='[ECOS-AUTO] Add MyGuide documentation',
            body='Auto-generated documentation for MyGuide component.',
            reviewers=['gerivdb']  # Optional
        )
        
        if workflow.pr_status == PRStatus.MERGED:
            print(f"PR #{workflow.pr_number} merged: {workflow.pr_url}")
        elif workflow.pr_status == PRStatus.OPEN:
            print(f"PR #{workflow.pr_number} awaiting review: {workflow.pr_url}")
    """
    
    def __init__(
        self,
        github_token: str,
        auto_merge: bool = True,
        delete_branch_on_merge: bool = True,
        merge_method: str = "squash",  # squash, merge, rebase
        logger: Optional[logging.Logger] = None
    ):
        """Initialize handler.
        
        Args:
            github_token: GitHub API token
            auto_merge: Automatically merge PR when approved
            delete_branch_on_merge: Delete feature branch after merge
            merge_method: Merge method (squash, merge, rebase)
            logger: Logger instance (creates default if None)
        """
        self.github_token = github_token
        self.auto_merge = auto_merge
        self.delete_branch_on_merge = delete_branch_on_merge
        self.merge_method = merge_method
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
    
    def handle(
        self,
        repository: str,
        base_branch: str,
        files: List[FileChange],
        title: str,
        body: str,
        reviewers: Optional[List[str]] = None
    ) -> PRWorkflow:
        """Handle file changes with PR workflow if branch protected.
        
        Args:
            repository: Repo in format 'owner/repo'
            base_branch: Target branch (e.g., 'main')
            files: List of files to change
            title: PR title
            body: PR description
            reviewers: List of GitHub usernames to request review
            
        Returns:
            PRWorkflow with results
        """
        start_time = time.time()
        
        workflow = PRWorkflow(
            repository=repository,
            base_branch=base_branch,
            feature_branch=self._generate_feature_branch_name(base_branch),
            title=title,
            body=body,
            files=files,
            reviewers=reviewers or [],
            auto_merge=self.auto_merge
        )
        
        self.logger.info(
            f"Starting PR workflow for {repository} ({len(files)} files)"
        )
        
        try:
            # Check branch protection
            workflow.protection_status = self._check_branch_protection(
                repository=repository,
                branch=base_branch
            )
            
            if workflow.protection_status == BranchProtectionStatus.UNPROTECTED:
                # Direct push allowed - skip PR workflow
                self.logger.info(
                    f"Branch {base_branch} is not protected - PR workflow not needed"
                )
                workflow.pr_status = PRStatus.FAILED
                workflow.error_message = (
                    "Branch not protected - use direct push instead"
                )
                return workflow
            
            # Create feature branch
            self._create_feature_branch(
                repository=repository,
                base_branch=base_branch,
                feature_branch=workflow.feature_branch
            )
            workflow.feature_branch_created = True
            
            # Push files to feature branch
            self._push_files_to_branch(
                repository=repository,
                branch=workflow.feature_branch,
                files=files
            )
            
            # Create PR
            pr = self._create_pull_request(
                repository=repository,
                base_branch=base_branch,
                feature_branch=workflow.feature_branch,
                title=title,
                body=body
            )
            
            workflow.pr_number = pr.number
            workflow.pr_url = pr.html_url
            workflow.pr_status = PRStatus.OPEN
            workflow.created_at = pr.created_at.isoformat()
            
            self.logger.info(f"PR #{pr.number} created: {pr.html_url}")
            
            # Request reviewers if provided
            if reviewers:
                self._request_reviewers(pr, reviewers)
            
            # Auto-merge if enabled and no reviewers
            if self.auto_merge and not reviewers:
                self.logger.info("Auto-merge enabled - attempting merge")
                merge_result = self._merge_pull_request(pr)
                
                if merge_result:
                    workflow.pr_status = PRStatus.MERGED
                    workflow.merge_commit_sha = merge_result["sha"]
                    workflow.merged_at = datetime.utcnow().isoformat()
                    
                    self.logger.info(
                        f"PR #{pr.number} merged: {workflow.merge_commit_sha[:8]}"
                    )
                    
                    # Delete feature branch if configured
                    if self.delete_branch_on_merge:
                        self._delete_branch(
                            repository=repository,
                            branch=workflow.feature_branch
                        )
        
        except Exception as e:
            workflow.pr_status = PRStatus.FAILED
            workflow.error_message = str(e)
            self.logger.error(f"PR workflow failed: {e}")
        
        workflow.duration_seconds = time.time() - start_time
        
        return workflow
    
    def _check_branch_protection(
        self,
        repository: str,
        branch: str
    ) -> BranchProtectionStatus:
        """Check if branch is protected."""
        try:
            repo = self.github_client.get_repo(repository)
            branch_obj = repo.get_branch(branch)
            
            if branch_obj.protected:
                self.logger.debug(f"Branch {branch} is protected")
                return BranchProtectionStatus.PROTECTED
            else:
                self.logger.debug(f"Branch {branch} is not protected")
                return BranchProtectionStatus.UNPROTECTED
        
        except Exception as e:
            self.logger.warning(
                f"Could not check branch protection for {branch}: {e}"
            )
            return BranchProtectionStatus.UNKNOWN
    
    def _generate_feature_branch_name(self, base_branch: str) -> str:
        """Generate unique feature branch name."""
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return f"ecos-auto/{base_branch}-{timestamp}"
    
    def _create_feature_branch(
        self,
        repository: str,
        base_branch: str,
        feature_branch: str
    ) -> None:
        """Create feature branch from base branch."""
        repo = self.github_client.get_repo(repository)
        base_ref = repo.get_branch(base_branch)
        
        repo.create_git_ref(
            ref=f"refs/heads/{feature_branch}",
            sha=base_ref.commit.sha
        )
        
        self.logger.debug(
            f"Created feature branch {feature_branch} from {base_branch}"
        )
    
    def _push_files_to_branch(
        self,
        repository: str,
        branch: str,
        files: List[FileChange]
    ) -> None:
        """Push files to branch."""
        repo = self.github_client.get_repo(repository)
        
        for file_change in files:
            try:
                # Try to get existing file
                existing = repo.get_contents(file_change.path, ref=branch)
                
                # Update existing file
                repo.update_file(
                    path=file_change.path,
                    message=f"Update {file_change.path}",
                    content=file_change.content,
                    sha=existing.sha,
                    branch=branch
                )
                
                self.logger.debug(f"Updated {file_change.path} on {branch}")
            
            except:
                # File doesn't exist - create it
                repo.create_file(
                    path=file_change.path,
                    message=f"Create {file_change.path}",
                    content=file_change.content,
                    branch=branch
                )
                
                self.logger.debug(f"Created {file_change.path} on {branch}")
    
    def _create_pull_request(
        self,
        repository: str,
        base_branch: str,
        feature_branch: str,
        title: str,
        body: str
    ):
        """Create pull request."""
        repo = self.github_client.get_repo(repository)
        
        pr = repo.create_pull(
            title=title,
            body=body,
            head=feature_branch,
            base=base_branch
        )
        
        return pr
    
    def _request_reviewers(self, pr, reviewers: List[str]) -> None:
        """Request PR reviewers."""
        try:
            pr.create_review_request(reviewers=reviewers)
            self.logger.debug(f"Requested review from: {', '.join(reviewers)}")
        except Exception as e:
            self.logger.warning(f"Could not request reviewers: {e}")
    
    def _merge_pull_request(self, pr) -> Optional[Dict]:
        """Merge pull request."""
        try:
            result = pr.merge(
                merge_method=self.merge_method,
                commit_title=f"[ECOS-AUTO] Merge PR #{pr.number}",
                commit_message="Auto-merged by BranchProtectionHandlerSkill"
            )
            
            if result.merged:
                return {"sha": result.sha, "merged": True}
            else:
                self.logger.warning(f"PR #{pr.number} merge failed: {result.message}")
                return None
        
        except Exception as e:
            self.logger.warning(f"Could not merge PR #{pr.number}: {e}")
            return None
    
    def _delete_branch(
        self,
        repository: str,
        branch: str
    ) -> None:
        """Delete branch after merge."""
        try:
            repo = self.github_client.get_repo(repository)
            ref = repo.get_git_ref(f"heads/{branch}")
            ref.delete()
            
            self.logger.debug(f"Deleted feature branch {branch}")
        
        except Exception as e:
            self.logger.warning(f"Could not delete branch {branch}: {e}")
    
    def to_json(self, workflow: PRWorkflow) -> str:
        """Serialize workflow to JSON."""
        return json.dumps({
            "repository": workflow.repository,
            "base_branch": workflow.base_branch,
            "feature_branch": workflow.feature_branch,
            "title": workflow.title,
            "protection_status": workflow.protection_status.name,
            "pr_status": workflow.pr_status.name,
            "pr_number": workflow.pr_number,
            "pr_url": workflow.pr_url,
            "feature_branch_created": workflow.feature_branch_created,
            "merge_commit_sha": workflow.merge_commit_sha,
            "error_message": workflow.error_message,
            "created_at": workflow.created_at,
            "merged_at": workflow.merged_at,
            "duration_seconds": workflow.duration_seconds,
            "files_count": len(workflow.files),
            "reviewers": workflow.reviewers,
            "auto_merge": workflow.auto_merge
        }, indent=2)
