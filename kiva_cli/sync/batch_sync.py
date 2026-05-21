"""BatchSync - Batch file synchronization."""

from typing import Dict, Any, List


class BatchSync:
    """Sync multiple files in batch to remote repository."""

    def __init__(self, github_client=None):
        self.github_client = github_client

    def sync_multiple_files(self, files: List[Dict[str, str]], target_repo: str) -> Dict[str, Any]:
        """Sync multiple files to remote repo."""
        succeeded = 0
        failed = 0

        for f in files:
            try:
                self.github_client.create_or_update_file(
                    repo=target_repo,
                    path=f["path"],
                    content=f["content"],
                    message=f"Sync {f['path']}"
                )
                succeeded += 1
            except Exception:
                failed += 1

        if failed > 0 and succeeded > 0:
            status = "PARTIAL"
        elif failed > 0:
            status = "FAILED"
        else:
            status = "SUCCESS"

        return {
            "status": status,
            "succeeded": succeeded,
            "failed": failed,
            "target_repo": target_repo
        }
