#!/usr/bin/env python3
"""
Path Resolver - KIVA CLI

Resolves and converts paths between local filesystem and remote repository URLs.
Provides context-aware path resolution for multi-repo ECOS ecosystem.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HAS_KVCACHE = False
try:
    from tools.core.kvcache_manager import KVCacheManager
    HAS_KVCACHE = True
except ImportError:
    pass

# EnvGuard Integration - ITAD Pattern
from tools.core.env_guard import env_guard


class RepoInfo:
    """Information about a repository."""
    def __init__(self, name: str, local_path: str, remote_url: str, remote_path: str):
        self.name = name
        self.local_path = Path(local_path)
        self.remote_url = remote_url  # e.g., "gerivdb/DevTools"
        self.remote_path = remote_path  # e.g., "gerivdb/DevTools"


class PathResolver:
    """Resolves paths between local filesystem and remote repository URLs."""
    
    DEFAULT_REPOS = {}

    def __init__(self, config_path: Optional[str] = None):
        self.repos: Dict[str, RepoInfo] = dict(self.DEFAULT_REPOS)
        self.config_path = config_path or self._default_config_path()
        self.cache = None
        if HAS_KVCACHE:
            try:
                self.cache = KVCacheManager()
            except Exception:
                pass
        self._load_config()
        
        # EnvGuard Auto-Configuration
        env_guard.adapt("path_resolver")

    def _default_config_path(self) -> str:
        """Get default config path."""
        return str(Path.home() / ".kiva" / "path_resolver.json")

    def _load_config(self):
        """Load custom repo config from file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                for name, info in config.get("repos", {}).items():
                    self.repos[name] = RepoInfo(
                        name=name,
                        local_path=info["local_path"],
                        remote_url=info["remote_url"],
                        remote_path=info.get("remote_path", info["remote_url"])
                    )
            except (json.JSONDecodeError, IOError, KeyError) as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")

    def save_config(self):
        """Save current repo registry to config file."""
        config = {
            "repos": {
                name: {
                    "local_path": str(repo.local_path),
                    "remote_url": repo.remote_url,
                    "remote_path": repo.remote_path
                }
                for name, repo in self.repos.items()
            }
        }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def add_repo(self, name: str, local_path: str, remote_url: str, remote_path: Optional[str] = None):
        """Add a new repository to the registry."""
        self.repos[name] = RepoInfo(
            name=name,
            local_path=local_path,
            remote_url=remote_url,
            remote_path=remote_path or remote_url
        )
        self.save_config()

    def remove_repo(self, name: str):
        """Remove a repository from the registry."""
        if name in self.repos:
            del self.repos[name]
            self.save_config()

    def list_repos(self) -> Dict[str, Dict[str, str]]:
        """List all registered repositories."""
        return {
            name: {
                "local_path": str(repo.local_path),
                "remote_url": repo.remote_url,
                "remote_path": repo.remote_path
            }
            for name, repo in self.repos.items()
        }

    def detect_repo(self, path: str) -> Optional[str]:
        """Detect which repository contains the given path."""
        path_obj = Path(path).resolve()
        
        # First, check if path is within any registered repo
        for name, repo in self.repos.items():
            try:
                repo_path = repo.local_path.resolve()
                if path_obj == repo_path or path_obj.is_relative_to(repo_path):
                    return name
            except (ValueError, OSError):
                continue
        
        # Second, try git remote detection
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(path_obj if path_obj.is_dir() else path_obj.parent),
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                git_root = Path(result.stdout.strip())
                for name, repo in self.repos.items():
                    if git_root == repo.local_path.resolve():
                        return name
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        
        return None

    def detect_current_repo(self) -> Optional[str]:
        """Detect the repository of the current working directory."""
        return self.detect_repo(str(Path.cwd()))

    def local_to_remote(self, local_path: str, repo_name: Optional[str] = None) -> Optional[str]:
        """Convert a local path to a remote repository path."""
        cache_key = f"local_to_remote:{local_path}:{repo_name}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        path_obj = Path(local_path).resolve()
        if repo_name is None:
            repo_name = self.detect_repo(local_path)
        if repo_name is None or repo_name not in self.repos:
            return None
        repo = self.repos[repo_name]
        try:
            repo_path = repo.local_path.resolve()
            if path_obj.is_relative_to(repo_path):
                relative = path_obj.relative_to(repo_path)
                remote_relative = str(relative).replace("\\", "/")
                result = f"{repo.remote_path}/{remote_relative}"
                if self.cache:
                    self.cache.put(cache_key, result)
                return result
        except (ValueError, OSError):
            pass
        return None
        
        repo = self.repos[repo_name]
        
        try:
            repo_path = repo.local_path.resolve()
            if path_obj.is_relative_to(repo_path):
                relative = path_obj.relative_to(repo_path)
                # Convert Windows path separators to forward slashes
                remote_relative = str(relative).replace("\\", "/")
                return f"{repo.remote_path}/{remote_relative}"
        except (ValueError, OSError):
            pass
        
        return None

    def remote_to_local(self, remote_path: str, repo_name: Optional[str] = None) -> Optional[str]:
        """
        Convert a remote repository path to a local path.
        
        Example:
            gerivdb/DevTools/bin/script.ps1 → C:\\DevTools\\bin\\script.ps1
        """
        # Try to match repo from remote_path
        if repo_name is None:
            for name, repo in self.repos.items():
                if remote_path.startswith(repo.remote_path):
                    repo_name = name
                    break
        
        if repo_name is None or repo_name not in self.repos:
            return None
        
        repo = self.repos[repo_name]
        
        # Remove repo prefix from remote_path
        prefix = repo.remote_path
        if remote_path.startswith(prefix):
            relative = remote_path[len(prefix):].lstrip("/")
            # Convert forward slashes to Windows path separators
            local_relative = relative.replace("/", "\\")
            return str(repo.local_path / local_relative)
        
        return None

    def resolve(self, path: str, repo_name: Optional[str] = None) -> Dict[str, str]:
        """
        Resolve a path and return both local and remote versions.
        
        Returns dict with:
        - local: Local filesystem path
        - remote: Remote repository path
        - repo: Repository name
        - exists: Whether the local path exists
        """
        result = {
            "input": path,
            "local": None,
            "remote": None,
            "repo": None,
            "exists": False
        }
        
        # Check if input looks like a remote path
        if path.startswith("gerivdb/") or "/" in path and "\\" not in path:
            local = self.remote_to_local(path, repo_name)
            if local:
                result["local"] = local
                result["remote"] = path
                result["repo"] = repo_name or self.detect_repo(local)
                result["exists"] = os.path.exists(local)
                return result
        
        # Otherwise treat as local path
        result["local"] = str(Path(path).resolve())
        result["exists"] = os.path.exists(result["local"])
        result["repo"] = self.detect_repo(path)
        result["remote"] = self.local_to_remote(path, result["repo"])
        
        return result

    def get_repo_for_file(self, file_path: str) -> Optional[str]:
        """Get the repository name for a given file path."""
        return self.detect_repo(file_path)

    def convert_path(self, path: str, target_format: str = "auto") -> str:
        """
        Convert path between local and remote formats.
        
        Args:
            path: Path to convert
            target_format: "local", "remote", or "auto" (auto-detect and convert to other)
        
        Returns:
            Converted path
        """
        if target_format == "auto":
            # Auto-detect format and convert to the other
            if path.startswith("gerivdb/") or ("/" in path and "\\" not in path):
                # Looks like remote path, convert to local
                result = self.remote_to_local(path)
                return result or path
            else:
                # Looks like local path, convert to remote
                result = self.local_to_remote(path)
                return result or path
        elif target_format == "local":
            return self.remote_to_local(path) or path
        elif target_format == "remote":
            return self.local_to_remote(path) or path
        
        return path