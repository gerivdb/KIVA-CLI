#!/usr/bin/env python3
"""
KIVA-CLI no-verify prohibition check.
Detects historical or pending use of `git commit/push --no-verify`.
"""

import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def run_git(args: str) -> str:
    result = subprocess.run(
        ["git"] + args.split(),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return (result.stdout or result.stderr).strip()


def check_recent_commits(limit: int = 20) -> list[str]:
    """Inspect recent commit messages for explicit --no-verify usage."""
    log = run_git(f"log --no-merges --pretty=format:%B -{limit}")
    if not log:
        return []
    messages = [m.strip() for m in log.split("\n\n") if m.strip()]
    hits = []
    for msg in messages:
        lower = msg.lower()
        if "--no-verify" in lower or "no-verify" in lower or "no_verify" in lower:
            hits.append(msg.splitlines()[0])
    return hits


def check_push_candidates() -> list[str]:
    """For pre-push, inspect commits that are not yet on origin/main."""
    try:
        candidates = run_git("log --no-merges --pretty=format:%B origin/main..HEAD")
    except Exception:
        return []
    if not candidates:
        return []
    messages = [m.strip() for m in candidates.split("\n\n") if m.strip()]
    hits = []
    for msg in messages:
        if "--no-verify" in msg.lower() or "no-verify" in msg.lower() or "no_verify" in msg.lower():
            hits.append(msg.splitlines()[0])
    return hits


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre-commit"

    if mode == "pre-push":
        hits = check_push_candidates()
    else:
        hits = check_recent_commits(limit=20)

    if hits:
        print("[NO-VERIFY PROHIBITION] BLOCKED: --no-verify usage detected")
        for hit in hits[:10]:
            print(f"  - {hit}")
        print("Fix: remove bypass usage and recommit properly.")
        return 1

    print("[NO-VERIFY PROHIBITION] OK: no --no-verify usage detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
