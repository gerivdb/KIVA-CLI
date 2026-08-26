#!/usr/bin/env python3
"""
PR Lifecycle Check - Vérifie et ferme les PR orphelines.

Usage:
    python scripts/pr-lifecycle-check.py --repo <path>
    python scripts/pr-lifecycle-check.py --repo <path> --auto-merge

Refs: INTENT-090, KiloRule pr-lifecycle-gate.md
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_gh(args: list[str]) -> str:
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_open_prs(repo: str) -> list[dict]:
    output = run_gh(["pr", "list", "--repo", repo, "--state", "open", "--json", "number,title,mergeable,mergeStateStatus,headRefName"])
    if not output:
        return []
    try:
        import json
        return json.loads(output)
    except Exception:
        return []


def check_pr_checks(repo: str, pr_number: int) -> dict:
    output = run_gh(["pr", "checks", "--repo", repo, str(pr_number)])
    if not output:
        return {"ok": True, "checks": []}
    failing = [line for line in output.splitlines() if "fail" in line.lower() or "error" in line.lower()]
    return {"ok": len(failing) == 0, "failing": failing, "raw": output}


def merge_pr(repo: str, pr_number: int, delete_branch: bool = True) -> bool:
    args = ["pr", "merge", "--repo", repo, str(pr_number), "--merge", "--delete-branch"]
    if not delete_branch:
        args = ["pr", "merge", "--repo", repo, str(pr_number), "--merge"]
    result = subprocess.run(["gh"] + args, capture_output=True, text=True)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PR Lifecycle Check")
    parser.add_argument("--repo", required=True, help="Repo (owner/name)")
    parser.add_argument("--auto-merge", action="store_true", help="Auto-merge passing PRs")
    args = parser.parse_args()

    prs = get_open_prs(args.repo)
    if not prs:
        print("[OK] No open PRs")
        return 0

    print(f"[INFO] Found {len(prs)} open PR(s)")

    for pr in prs:
        number = pr.get("number")
        title = pr.get("title", "N/A")
        mergeable = pr.get("mergeable", "UNKNOWN")
        print(f"\n[PR #{number}] {title}")
        print(f"  mergeable: {mergeable}")

        if mergeable != "MERGEABLE":
            print("  [SKIP] Not mergeable")
            continue

        checks = check_pr_checks(args.repo, number)
        if not checks["ok"]:
            print(f"  [SKIP] CI checks failing")
            continue

        if args.auto_merge:
            if merge_pr(args.repo, number):
                print(f"  [OK] Merged PR #{number}")
            else:
                print(f"  [ERR] Failed to merge PR #{number}")
        else:
            print(f"  [ACTION] Run with --auto-merge to merge")

    return 0


if __name__ == "__main__":
    exit(main())
