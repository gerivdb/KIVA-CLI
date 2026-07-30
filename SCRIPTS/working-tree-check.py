#!/usr/bin/env python3
"""
Working Tree Check - Vérifie la discipline du working tree.

Usage:
    python scripts/working-tree-check.py --repo <path>
    python scripts/working-tree-check.py --repo <path> --max-files 3

Refs: INTENT-087, ADR-099, KiloRule git-atomic-commit.md
"""
from __future__ import annotations

import argparse
import subprocess
import sys
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


def get_branch(repo_path: Path) -> str:
    return run_git(["branch", "--show-current"], repo_path)


def get_modified_files(repo_path: Path) -> list[str]:
    status = run_git(["status", "--short"], repo_path)
    if not status:
        return []
    return [line.strip() for line in status.splitlines() if line.strip()]


def check_working_tree(repo_path: Path, max_files: int = 3) -> dict:
    branch = get_branch(repo_path)
    modified = get_modified_files(repo_path)

    issues = []

    if branch == "main":
        issues.append("Working on main branch - create a feature branch first")

    if len(modified) > max_files:
        issues.append(f"Too many modified files: {len(modified)} > {max_files}")

    untracked = [f for f in modified if f.startswith("??")]
    if len(untracked) > 5:
        issues.append(f"Many untracked files: {len(untracked)}")

    if issues:
        return {"ok": False, "branch": branch, "modified_count": len(modified), "issues": issues}
    return {"ok": True, "branch": branch, "modified_count": len(modified)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Working Tree Check")
    parser.add_argument("--repo", required=True, help="Path to git repository")
    parser.add_argument("--max-files", type=int, default=3, help="Max modified files")
    args = parser.parse_args()

    repo_path = Path(args.repo)
    if not repo_path.exists() or not (repo_path / ".git").exists():
        print(f"[ERR] Not a git repository: {repo_path}")
        return 1

    result = check_working_tree(repo_path, args.max_files)

    if result["ok"]:
        print(f"[OK] Working tree clean (branch: {result['branch']}, modified: {result['modified_count']})")
        return 0

    print(f"[ERR] Working tree violations (branch: {result['branch']}):")
    for issue in result["issues"]:
        print(f"  - {issue}")

    print("\n[ACTION REQUIRED] Create a feature branch or commit/stash your changes")
    return 1


if __name__ == "__main__":
    exit(main())
