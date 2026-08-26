#!/usr/bin/env python3
"""
Commit Discipline Check - Vérifie la discipline de commit atomique.

Usage:
    python scripts/commit-discipline-check.py --repo <path>
    python scripts/commit-discipline-check.py --repo <path> --max-files 3 --max-minutes 30

Refs: INTENT-084, ADR-099, KiloRule git-atomic-commit.md
"""
from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_last_commit_time(repo_path: Path) -> datetime | None:
    timestamp_str = run_git(["log", "-1", "--format=%ct"], repo_path)
    if not timestamp_str:
        return None
    return datetime.fromtimestamp(int(timestamp_str))


def get_modified_files_count(repo_path: Path) -> int:
    status = run_git(["status", "--short"], repo_path)
    if not status:
        return 0
    return len(status.splitlines())


def check_discipline(
    repo_path: Path,
    max_files: int = 3,
    max_minutes: int = 30,
) -> dict:
    last_commit = get_last_commit_time(repo_path)
    modified_files = get_modified_files_count(repo_path)
    now = datetime.now()

    issues = []

    if modified_files > max_files:
        issues.append(f"Too many modified files: {modified_files} > {max_files}")

    if last_commit is not None:
        elapsed = (now - last_commit).total_seconds() / 60.0
        if elapsed > max_minutes:
            issues.append(f"No commit for {elapsed:.1f} minutes (max {max_minutes})")

    if issues:
        return {"ok": False, "issues": issues}
    return {"ok": True, "modified_files": modified_files}


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit Discipline Check")
    parser.add_argument("--repo", required=True, help="Path to git repository")
    parser.add_argument("--max-files", type=int, default=3, help="Max modified files")
    parser.add_argument("--max-minutes", type=int, default=30, help="Max minutes without commit")
    args = parser.parse_args()

    repo_path = Path(args.repo)
    if not repo_path.exists() or not (repo_path / ".git").exists():
        print(f"[ERR] Not a git repository: {repo_path}")
        return 1

    result = check_discipline(repo_path, args.max_files, args.max_minutes)

    if result["ok"]:
        print(f"[OK] Commit discipline OK (modified files: {result['modified_files']})")
        return 0

    print("[ERR] Commit discipline VIOLATIONS:")
    for issue in result["issues"]:
        print(f"  - {issue}")

    print("\n[ACTION REQUIRED] Commit your changes or stash them")
    return 1


if __name__ == "__main__":
    exit(main())
