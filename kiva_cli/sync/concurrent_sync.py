"""ConcurrentSync - Concurrent file synchronization."""

from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed


class ConcurrentSync:
    """Sync files concurrently to remote repository."""

    def __init__(self, github_client=None, max_workers: int = 4):
        self.github_client = github_client
        self.max_workers = max_workers

    def sync_concurrent(self, tasks: List[Dict[str, str]], target_repo: str) -> List[Dict[str, Any]]:
        """Sync multiple files concurrently."""
        results = []

        def _sync_one(task):
            try:
                self.github_client.create_or_update_file(
                    repo=target_repo,
                    path=task["path"],
                    content=task["content"],
                    message=f"Sync {task['path']}"
                )
                return {"status": "SUCCESS", "path": task["path"]}
            except Exception as e:
                return {"status": "FAILED", "path": task["path"], "error": str(e)}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_sync_one, task) for task in tasks]
            for future in as_completed(futures):
                results.append(future.result())

        return results
