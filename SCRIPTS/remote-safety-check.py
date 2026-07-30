#!/usr/bin/env python3
"""
Remote Safety Check - Vérifie la sécurité du remote avant push.

Usage:
    python scripts/remote-safety-check.py --repo <path>
    python scripts/remote-safety-check.py --repo <path> --expected gerivdb/REPO-STANDARDS

Refs: INTENT-083, ADR-094, KiloRule git-remote-safety.md
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


def check_remote(repo_path: Path, expected: str | None = None) -> dict:
    if expected is None:
        remote_url = run_git(["remote", "get-url", "origin"], repo_path)
        if not remote_url:
            return {"ok": False, "error": "No remote 'origin' found"}
        expected = remote_url.split("/")[-1].replace(".git", "")
        expected_full = remote_url
    else:
        if not expected.startswith("gerivdb/"):
            expected = f"gerivdb/{expected}"
        expected_full = f"https://github.com/{expected}.git"

    remote_url = run_git(["remote", "get-url", "origin"], repo_path)
    if not remote_url:
        return {"ok": False, "error": "No remote 'origin' found"}

    # Remove credentials if present
    clean_url = remote_url.split("@")[-1].split(":")[-1]
    if "/" not in clean_url:
        clean_url = remote_url

    if remote_url != expected_full and clean_url != expected_full:
        return {
            "ok": False,
            "error": f"Remote mismatch: {remote_url} != {expected_full}",
        }

    return {"ok": True, "remote": remote_url, "expected": expected_full}


def check_detached_head(repo_path: Path) -> dict:
    branch = run_git(["symbolic-ref", "HEAD"], repo_path)
    if not branch:
        return {"ok": False, "error": "HEAD is detached"}
    return {"ok": True, "branch": branch}


def check_remote_sync(repo_path: Path) -> dict:
    fetch_head = run_git(["log", "HEAD..origin/main", "--oneline"], repo_path)
    if fetch_head:
        return {"ok": False, "error": f"Local behind remote by {len(fetch_head.splitlines())} commits"}
    return {"ok": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Remote Safety Check")
    parser.add_argument("--repo", required=True, help="Path to git repository")
    parser.add_argument("--expected", help="Expected repo name (gerivdb/<repo>)")
    args = parser.parse_args()

    repo_path = Path(args.repo)
    if not repo_path.exists() or not (repo_path / ".git").exists():
        print(f"[ERR] Not a git repository: {repo_path}")
        return 1

    results = []

    # CHECK-1: Remote URL
    remote_check = check_remote(repo_path, args.expected)
    results.append(("REMOTE_URL", remote_check))

    # CHECK-2: Detached HEAD
    head_check = check_detached_head(repo_path)
    results.append(("DETACHED_HEAD", head_check))

    # CHECK-3: Remote sync
    sync_check = check_remote_sync(repo_path)
    results.append(("REMOTE_SYNC", sync_check))

    all_ok = all(r[1]["ok"] for r in results)

    for name, check in results:
        status = "OK" if check["ok"] else "FAIL"
        print(f"[{status}] {name}: {check.get('error') or check.get('remote') or check.get('branch')}")

    if not all_ok:
        print("\n[ERR] Remote safety checks FAILED - push blocked")
        return 1

    print("\n[OK] All remote safety checks passed")
    return 0


if __name__ == "__main__":
    exit(main())
