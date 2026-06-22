#!/usr/bin/env python3
"""
CodeDB Manager - Integration via WSL for KIVA CLI

Manages CodeDB execution via WSL (Windows Subsystem for Linux).
Uses codedb_remote cloud service as fallback when binary unavailable.

IntentHash: 0xCODEDB_LXC_INTEGRATION_20260415
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any


class CodeDBManager:
    """
    Manages CodeDB via WSL for code intelligence.
    Uses remote cloud service as primary (more reliable).
    """

    INTENT_HASH = "0xCODEDB_LXC_INTEGRATION_20260415"
    VERSION = "v1.0.0"

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = "C:\\DevTools\\data\\codedb"
        self.data_dir = Path(data_dir)
        self.projects_file = self.data_dir / "projects.json"
        self.wsl_distro = "Ubuntu"
        self._ensure_dirs()

    def _ensure_dirs(self):
        os.makedirs(self.data_dir, exist_ok=True)

    def _run_wsl(self, cmd: str, cwd: str = None) -> subprocess.CompletedProcess:
        """Run command in WSL."""
        full_cmd = f"export PATH=/home/gervdb/bin:$PATH && {cmd}"
        args = ["wsl", "-d", self.wsl_distro, "bash", "-c", full_cmd]
        return subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=30)

    def _check_wsl(self) -> bool:
        """Verify WSL is available."""
        try:
            result = subprocess.run(["wsl", "-l"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get CodeDB integration status."""
        wsl_ok = self._check_wsl()

        return {
            "intent_hash": self.INTENT_HASH,
            "version": self.VERSION,
            "wsl_available": wsl_ok,
            "mode": "REMOTE" if wsl_ok else "UNAVAILABLE",
            "projects": len(self.get_projects()),
        }

    def remote_tree(self, repo: str) -> List[Dict[str, Any]]:
        """Get file tree via codedb_remote."""
        results = []
        try:
            result = self._run_wsl(
                f"/root/bin/codedb remote --repo {repo} --action tree"
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        results.append({"path": line.strip()})
        except Exception:
            pass
        return results

    def remote_search(self, repo: str, query: str) -> List[Dict[str, Any]]:
        """Search via codedb_remote."""
        results = []
        try:
            result = self._run_wsl(
                f"/root/bin/codedb remote --repo {repo} --action search --query '{query}'"
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line and ":" in line:
                        parts = line.split(":", 1)
                        results.append(
                            {
                                "match": parts[0],
                                "file": parts[1] if len(parts) > 1 else "",
                            }
                        )
        except Exception:
            pass
        return results

    def remote_outline(self, repo: str, file_path: str) -> List[Dict[str, Any]]:
        """Get symbol outline via codedb_remote."""
        results = []
        try:
            result = self._run_wsl(
                f"/root/bin/codedb remote --repo {repo} --action outline --path {file_path}"
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        results.append({"symbol": line.strip()})
        except Exception:
            pass
        return results

    def remote_meta(self, repo: str) -> Dict[str, Any]:
        """Get repo metadata via codedb_remote."""
        try:
            result = self._run_wsl(
                f"/root/bin/codedb remote --repo {repo} --action meta"
            )
            if result.stdout:
                return {"meta": result.stdout.strip()}
        except Exception:
            pass
        return {}

    def search(self, repo: str, query: str) -> List[Dict[str, Any]]:
        """Search - uses remote (reliable)."""
        return self.remote_search(repo, query)

    def tree(self, repo: str) -> List[Dict[str, Any]]:
        """Tree - uses remote (reliable)."""
        return self.remote_tree(repo)

    def outline(self, repo: str, file_path: str) -> List[Dict[str, Any]]:
        """Outline - uses remote (reliable)."""
        return self.remote_outline(repo, file_path)

    def _save_project(self, name: str, path: str):
        """Save indexed project."""
        projects = {}
        if self.projects_file.exists():
            with open(self.projects_file, "r", encoding="utf-8") as f:
                projects = json.load(f)
        projects[name] = {
            "path": path,
            "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(self.projects_file, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2)

    def get_projects(self) -> Dict[str, Any]:
        """Get indexed projects."""
        if self.projects_file.exists():
            with open(self.projects_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}


def main():
    """CLI entry point."""
    import sys

    mgr = CodeDBManager()
    status = mgr.get_status()

    print("=" * 44)
    print("CodeDB Manager - KIVA Integration")
    print("=" * 44)
    print(f"IntentHash: {status['intent_hash']}")
    print(f"Version: {status['version']}")
    print(f"Mode: {status['mode']}")
    print()

    repos = ["gerivdb/DevTools", "gerivdb/ECOYSTEM"]
    for repo in repos:
        print(f"Testing: {repo}")
        tree = mgr.remote_tree(repo)
        print(f"  Files: {len(tree)}")

    sys.exit(0)


if __name__ == "__main__":
    main()
