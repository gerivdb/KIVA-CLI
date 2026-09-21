#!/usr/bin/env python3
"""
KIVA-012 S3 — Automated publish workflow.

Creates a feature branch, commits changes, pushes, and creates a PR.
This replaces the manual workflow that caused ERR-016.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str] | str, check: bool = True) -> subprocess.CompletedProcess:
    if isinstance(cmd, str):
        cmd = cmd.split()
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def git_add(paths: list[str]) -> None:
    run(["git", "add"] + paths)


def git_commit(message: str) -> None:
    run(["git", "commit", "-m", message])


def git_push(branch: str) -> None:
    run(["git", "push", "-u", "origin", branch])


def create_pr(title: str, body: str) -> str:
    token = os.environ.get("GITHUB_TOKEN") or _read_keyring_token()
    if not token:
        raise RuntimeError("GITHUB_TOKEN not found in environment or keyring")

    repo = _detect_repo()
    api_url = f"https://api.github.com/repos/{repo}/pulls"

    import requests
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.post(api_url, headers=headers, json={"title": title, "body": body, "head": branch, "base": "main"})
    resp.raise_for_status()
    return resp.json()["html_url"]


def _detect_repo() -> str:
    result = run(["git", "remote", "get-url", "origin"], check=False)
    if result.returncode != 0:
        raise RuntimeError("No remote 'origin' found")
    url = result.stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(\.git)?$", url)
    if not match:
        raise RuntimeError(f"Cannot parse repo from remote URL: {url}")
    return match.group(1)


def _read_keyring_token() -> str | None:
    try:
        import keyring
        return keyring.get_password("gh:github.com", "user")
    except Exception:
        return None


def publish(branch_name: str, title: str, body: str = "") -> str:
    current = run(["git", "branch", "--show-current"], check=False).stdout.strip()
    if not current:
        raise RuntimeError("Not on a git branch")

    git_add(["."])
    git_commit(f"chore: {title}")
    git_push(branch_name)
    pr_url = create_pr(title, body)
    print(f"PR created: {pr_url}")
    return pr_url


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: publish.py <branch-name> [title]", file=sys.stderr)
        sys.exit(1)

    branch = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else branch
    publish(branch, title)
