#!/usr/bin/env python3
"""
Repository Discovery - KIVA CLI

Automatically scans directories for git repositories and adds them to the PathResolver registry.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click


class RepoDiscovery:
    """Discovers git repositories in a directory tree."""

    def __init__(self, scan_dirs: Optional[List[str]] = None):
        if scan_dirs is None:
            scan_dirs = [
                "D:\\DO\\WEB",
                "D:\\DO\\WEB\\TOOLS",
                "C:\\DevTools"
            ]
        self.scan_dirs = [Path(d) for d in scan_dirs]

    def discover_repos(self) -> List[Dict[str, str]]:
        """
        Scan directories for git repositories.
        
        Returns:
            List of dicts with keys: name, path, remote
        """
        repos = []
        for scan_dir in self.scan_dirs:
            if not scan_dir.exists():
                continue
            repos.extend(self._scan_directory(scan_dir))
        return repos

    def _scan_directory(self, base_dir: Path) -> List[Dict[str, str]]:
        """Recursively scan a directory for git repos."""
        repos = []
        
        try:
            # Check if current directory is a git repo
            if (base_dir / ".git").exists():
                repo_info = self._get_repo_info(base_dir)
                if repo_info:
                    repos.append(repo_info)
                # Don't recurse into a git repo
                return repos
            
            # Not a git repo, scan subdirectories
            for item in base_dir.iterdir():
                if item.is_dir() and item.name.startswith('.'):
                    continue
                
                if item.is_dir():
                    repos.extend(self._scan_directory(item))
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not scan {base_dir}: {e}")
        
        return repos

    def _get_repo_info(self, repo_path: Path) -> Optional[Dict[str, str]]:
        """Get repository information."""
        try:
            # Get repo name
            name = repo_path.name
            
            # Get remote URL
            remote_url = ""
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(repo_path),
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    remote_url = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass
            
            return {
                "name": name,
                "path": str(repo_path),
                "remote": remote_url
            }
        except Exception:
            return None

    def compare_with_registry(self, discovered: List[Dict[str, str]], registered: Dict[str, Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Compare discovered repos with registered repos.
        
        Returns:
            (new_repos, existing_repos) tuples
        """
        new_repos = []
        existing_repos = []
        
        registered_paths = {r["local_path"]: name for name, r in registered.items()}
        registered_remotes = {r["remote_url"]: name for name, r in registered.items()}
        
        for repo in discovered:
            if repo["path"] in registered_paths or repo["remote"] in registered_remotes:
                existing_repos.append(repo)
            else:
                new_repos.append(repo)
        
        return new_repos, existing_repos