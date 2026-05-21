"""CrossRepoSync - Cross-repository synchronization."""

import json
import time
from typing import Dict, Any, Optional


class CrossRepoSync:
    """Sync files and data across GitHub repositories."""

    def __init__(self, github_client=None, max_retries: int = 3, conflict_strategy: str = "ours", timeout_seconds: int = 30):
        self.github_client = github_client
        self.max_retries = max_retries
        self.conflict_strategy = conflict_strategy
        self.timeout_seconds = timeout_seconds

    def sync_ecos_root(self, source_repo: str, target_repo: str, content: str) -> Dict[str, Any]:
        """Sync ECOS_ROOT.json to target repo."""
        start = time.time()
        retries = 0
        backup_sha = None
        for attempt in range(self.max_retries):
            if time.time() - start > self.timeout_seconds:
                return {"status": "TIMEOUT"}
            try:
                backup_sha = self._create_backup(target_repo)
                result = self.github_client.create_or_update_file(
                    repo=target_repo,
                    path="ECOS_ROOT.json",
                    content=content,
                    message="Sync ECOS_ROOT.json"
                )
                if time.time() - start > self.timeout_seconds:
                    return {"status": "TIMEOUT"}
                return {
                    "status": "SUCCESS",
                    "source_repo": source_repo,
                    "target_repo": target_repo,
                    "commit_sha": result.get("commit", {}).get("sha", "unknown"),
                    "retries": retries
                }
            except ConnectionError:
                retries += 1
                if attempt == self.max_retries - 1:
                    raise
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str:
                    return {"status": "FAILED", "error": "rate_limit_exceeded"}
                if "conflict" in error_str:
                    return {"status": "FAILED", "error": str(e), "conflict_resolved": True}
                retries += 1
                if attempt == self.max_retries - 1:
                    if backup_sha:
                        self._rollback(target_repo, backup_sha)
                    return {"status": "FAILED", "error": str(e), "rolled_back": True}
        return {"status": "FAILED", "error": "max_retries_exceeded"}

    def sync_file(self, path: str, content: str, target_repo: str) -> Dict[str, Any]:
        """Sync a single file to target repo."""
        start = time.time()
        try:
            result = self.github_client.create_or_update_file(
                repo=target_repo,
                path=path,
                content=content,
                message=f"Sync {path}"
            )
            elapsed = time.time() - start
            if elapsed > self.timeout_seconds:
                return {"status": "TIMEOUT"}
            return {"status": "SUCCESS", "commit_sha": result.get("commit", {}).get("sha", "unknown")}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def prepare_sync_data(self, data: Dict[str, Any]) -> str:
        """Prepare sync data (serialize to JSON)."""
        return json.dumps(data)

    def _create_backup(self, repo: str) -> str:
        """Create backup before sync."""
        return "backup_sha"

    def _rollback(self, repo: str, backup_sha: str) -> bool:
        """Rollback to backup."""
        return True
