#!/usr/bin/env python3
"""
Context Manager - KIVA CLI

Manages the active repository context for KIVA-CLI operations.
Provides context-aware path resolution and default repo selection.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any, Any


class ContextManager:
    """Manages the active repository context."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self.context: Dict[str, Any] = self._load_context()

    def _default_config_path(self) -> str:
        """Get default config path."""
        return str(Path.home() / ".kiva" / "context.json")

    def _load_context(self) -> Dict[str, Optional[str]]:
        """Load context from config file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "active_repo": None,
            "last_path": None,
            "last_command": None
        }

    def _save_context(self):
        """Save context to config file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.context, f, indent=2, ensure_ascii=False)

    def set_active_repo(self, repo_name: str):
        """Set the active repository."""
        self.context["active_repo"] = repo_name
        self._save_context()

    def get_active_repo(self) -> Optional[str]:
        """Get the active repository."""
        return self.context.get("active_repo")

    def clear_context(self):
        """Clear the current context."""
        self.context = {
            "active_repo": None,
            "last_path": None,
            "last_command": None
        }
        self._save_context()

    def set_last_path(self, path: str):
        """Set the last used path."""
        self.context["last_path"] = path
        self._save_context()

    def get_last_path(self) -> Optional[str]:
        """Get the last used path."""
        return self.context.get("last_path")

    def set_last_command(self, command: str):
        """Set the last executed command."""
        self.context["last_command"] = command
        self._save_context()

    def get_last_command(self) -> Optional[str]:
        """Get the last executed command."""
        return self.context.get("last_command")

    def detect_current_repo(self) -> Optional[str]:
        """Detect the repository of the current working directory using git."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                git_root = Path(result.stdout.strip())
                # Try to get remote URL
                remote_result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(git_root),
                    capture_output=True, text=True, timeout=5
                )
                if remote_result.returncode == 0:
                    remote_url = remote_result.stdout.strip()
                    # Extract repo name from remote URL
                    # Handles: gerivdb/repo-name, https://github.com/gerivdb/repo-name.git
                    if "gerivdb/" in remote_url:
                        repo_name = remote_url.split("gerivdb/")[-1].replace(".git", "")
                        return repo_name
                    elif "github.com/" in remote_url:
                        parts = remote_url.split("github.com/")[-1].replace(".git", "").split("/")
                        if len(parts) >= 2:
                            return parts[-1]
                # Fallback: use directory name
                return git_root.name
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def get_context_summary(self) -> Dict[str, Optional[str]]:
        """Get a summary of the current context."""
        return {
            "active_repo": self.get_active_repo(),
            "last_path": self.get_last_path(),
            "last_command": self.get_last_command(),
            "detected_repo": self.detect_current_repo()
        }

    def resolve_path_with_context(self, path: str, path_resolver) -> str:
        """
        Resolve a path using the current context.
        
        If path is relative and active_repo is set, prepend the repo's local path.
        """
        if os.path.isabs(path):
            return path
        
        active_repo = self.get_active_repo()
        if active_repo and active_repo in path_resolver.repos:
            repo_info = path_resolver.repos[active_repo]
            return str(repo_info.local_path / path)
        
        return path