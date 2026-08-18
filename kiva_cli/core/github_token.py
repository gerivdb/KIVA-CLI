"""Shared GitHub token resolution for KIVA-CLI.

Priority:
1. GITHUB_TOKEN env var
2. GH_TOKEN env var
3. gh CLI keyring via `gh auth token`
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional


def _gh_executable() -> Optional[str]:
    candidates = [
        "gh",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\gh\bin\gh.exe"),
        r"C:\gh\bin\gh.exe",
    ]
    for candidate in candidates:
        if candidate == "gh":
            try:
                out = subprocess.run(
                    "command -v gh",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and out.stdout.strip():
                    return out.stdout.strip()
            except Exception:
                pass
        elif os.path.exists(candidate):
            return candidate
    return None


def get_github_token() -> str:
    """Resolve GitHub token from env or gh keyring."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    gh_exec = _gh_executable()
    if gh_exec:
        try:
            out = subprocess.run(
                f"{gh_exec} auth token",
                shell=True,
                capture_output=True,
                text=True,
            )
            if out.returncode == 0:
                token = out.stdout.strip()
                if token:
                    return token
        except Exception:
            pass
    raise RuntimeError(
        "GITHUB_TOKEN/gh keyring requis pour les commandes GitHub en BDCP"
    )
