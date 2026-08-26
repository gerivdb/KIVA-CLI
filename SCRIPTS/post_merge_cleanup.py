#!/usr/bin/env python3
"""
Post-Merge Cleanup - Nettoyage automatique des branches après merge.

Usage:
    python scripts/post_merge_cleanup.py --repo <path>
    python scripts/post_merge_cleanup.py --repo <path> --branch feat/<slug>

Refs: INTENT-086, ADR-2026-06-30-001, KiloRule branch-lifecycle.md Section 8
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


def get_merged_remote_branches(repo_path: Path, base: str = "main") -> list[str]:
    output = run_git(["branch", "-r", "--merged", base], repo_path)
    if not output:
        return []
    branches = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("origin/") and line not in (f"origin/{base}", f"origin/HEAD"):
            branches.append(line)
    return branches


def get_merged_local_branches(repo_path: Path, base: str = "main") -> list[str]:
    output = run_git(["branch", "--merged", base], repo_path)
    if not output:
        return []
    branches = []
    for line in output.splitlines():
        line = line.strip().lstrip("* ").strip()
        if line and line != base:
            branches.append(line)
    return branches


def delete_remote_branch(repo_path: Path, branch: str) -> bool:
    branch_name = branch.replace("origin/", "")
    result = subprocess.run(
        ["git", "push", "origin", "--delete", branch_name],
        capture_output=True,
        text=True,
        cwd=str(repo_path),
    )
    return result.returncode == 0


def delete_local_branch(repo_path: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "branch", "-d", branch],
        capture_output=True,
        text=True,
        cwd=str(repo_path),
    )
    return result.returncode == 0


def cleanup(repo_path: Path, branch_name: str | None = None) -> dict:
    repo_path = Path(repo_path).resolve()
    if not (repo_path / ".git").exists():
        return {"ok": False, "error": f"Not a git repo: {repo_path}"}

    # Ensure on main
    current = run_git(["branch", "--show-current"], repo_path)
    if current != "main":
        run_git(["checkout", "main"], repo_path)

    # Pull + prune
    run_git(["pull", "--prune", "origin", "main"], repo_path)

    # Delete specific branch or all merged
    deleted_remote = []
    deleted_local = []

    if branch_name:
        if delete_local_branch(repo_path, branch_name):
            deleted_local.append(branch_name)
    else:
        for branch in get_merged_remote_branches(repo_path):
            if delete_remote_branch(repo_path, branch):
                deleted_remote.append(branch)

        for branch in get_merged_local_branches(repo_path):
            if delete_local_branch(repo_path, branch):
                deleted_local.append(branch)

    return {
        "ok": True,
        "deleted_remote": deleted_remote,
        "deleted_local": deleted_local,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-Merge Cleanup")
    parser.add_argument("--repo", required=True, help="Path to git repository")
    parser.add_argument("--branch", help="Specific branch to delete")
    args = parser.parse_args()

    result = cleanup(args.repo, args.branch)

    if not result["ok"]:
        print(f"[ERR] {result['error']}")
        return 1

    if result["deleted_remote"]:
        print(f"[OK] Deleted remote branches: {', '.join(result['deleted_remote'])}")
    else:
        print("[OK] No merged remote branches to delete")

    if result["deleted_local"]:
        print(f"[OK] Deleted local branches: {', '.join(result['deleted_local'])}")
    else:
        print("[OK] No merged local branches to delete")

    return 0


if __name__ == "__main__":
    exit(main())
