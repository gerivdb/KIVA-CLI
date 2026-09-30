#!/usr/bin/env python3
"""
KIVA-012 S3 — Pre-push sync check.

Verifies that the local branch is up to date with the remote before
allowing a push. Prevents ERR-018 (git ref lock errors).
"""
from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def get_current_branch() -> str:
    result = run(["git", "branch", "--show-current"])
    if result.returncode != 0:
        raise RuntimeError("Not on a git branch")
    return result.stdout.strip()


def is_synced_with_remote(branch: str) -> bool:
    """Check if local branch is up to date with remote."""
    # Fetch latest refs
    fetch = run(["git", "fetch", "origin", branch])
    if fetch.returncode != 0:
        return True  # No remote branch yet, allow push

    # Count commits ahead/behind
    ahead = run(["git", "rev-list", "--count", f"HEAD..origin/{branch}"])
    behind = run(["git", "rev-list", "--count", f"origin/{branch}..HEAD"])

    if ahead.returncode != 0 or behind.returncode != 0:
        return True  # Can't determine, allow push

    ahead_count = int(ahead.stdout.strip())
    behind_count = int(behind.stdout.strip())

    if behind_count > 0:
        print(f"ERROR: Branch '{branch}' is behind origin/{branch} by {behind_count} commit(s).", file=sys.stderr)
        print("Run: git pull --rebase origin " + branch, file=sys.stderr)
        return False

    return True


def main() -> int:
    try:
        branch = get_current_branch()
        if not is_synced_with_remote(branch):
            return 1
        print(f"OK: Branch '{branch}' is synced with remote")
        return 0
    except Exception as exc:
        print(f"WARN: Pre-push sync check failed: {exc}", file=sys.stderr)
        return 0  # Non-blocking


if __name__ == "__main__":
    sys.exit(main())
