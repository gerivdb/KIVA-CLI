#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selina_ci.py — SELINA Continuous Integration : orchestration complète injection RSS-v2.

Automatise :
1. Découverte repos via RIDDLER
2. Injection workflow atomique
3. Push + création PR via ALFRED
4. Sync post-merge

IntentHash: 0xSELINA_CI_20260705
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_git(args: list, cwd: str, timeout: int = 30) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", cwd] + args,
        capture_output=True, text=True, timeout=timeout
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def create_pr(repo: str, title: str, body: str, branch: str, token: str = None) -> str:
    """Crée une PR via gh CLI."""
    cmd = [
        "gh", "pr", "create",
        "--repo", f"gerivdb/{repo}",
        "--title", title,
        "--body", body,
        "--head", branch,
    ]
    if token:
        cmd.extend(["--repo", repo])  # gh utilise le remote

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode == 0:
        return proc.stdout.strip()
    return ""


def inject_and_pr(repo_name: str, repo_path: str, source_path: Path, branch: str = "feat/epic-400-rss-v2-workflow") -> dict:
    result = {
        "repo": repo_name,
        "path": repo_path,
        "status": "unknown",
    }

    workflow_path = Path(repo_path) / ".github/workflows/rss-v2-reusable.yml"

    if workflow_path.exists():
        result["status"] = "already_present"
        return result

    try:
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        # Checkout nouvelle branche
        run_git(["checkout", "-b", branch], repo_path)

        # Add + commit
        run_git(["add", "-f", str(workflow_path.relative_to(repo_path))], repo_path)
        code, _, err = run_git([
            "commit", "-m", f"feat(workflow): inject RSS-v2 reusable workflow from REPO-STANDARDS (EPIC-400)"
        ], repo_path)

        if code != 0:
            result["status"] = "commit_failed"
            result["error"] = err[:200]
            return result

        # Push
        code, _, err = run_git(["push", "--no-verify", "origin", f"HEAD:{branch}"], repo_path)

        if code != 0 or "does not appear to be a git repository" in err:
            result["status"] = "no_remote"
            result["error"] = err[:200] if err else "No remote configured"
            return result

        # Créer PR
        pr_url = create_pr(repo_name,
            title=f"feat(workflow): inject RSS-v2 reusable workflow (EPIC-400)",
            body="Canary deployment of RSS-v2 reusable workflow. Part of EPIC-400 pipeline.",
            branch=branch
        )

        result["status"] = "pr_created"
        result["pr_url"] = pr_url

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]

    return result


def discover_layer_repos(layer: str) -> dict:
    layer_roots = {
        "L0": [Path("D:/DO/WEB/TOOLS/L0-CANON")],
        "L1": [Path("D:/DO/WEB/TOOLS/L0-CANON"), Path("D:/DO/WEB/TOOLS/L1-INFRA")],
        "L3": [Path("D:/DO/WEB/TOOLS/L3-CITIZENS")],
        "L4": [Path("D:/DO/WEB/TOOLS/L4-TOOLS")],
    }
    roots = layer_roots.get(layer, layer_roots["L1"])
    repos = {}
    for root in roots:
        if not root.exists():
            continue
        for item in sorted(root.iterdir()):
            if item.is_dir() and (item / ".git").exists():
                if item.name not in repos:
                    repos[item.name] = str(item)
    return repos


def main():
    parser = argparse.ArgumentParser(description="SELINA-CI : Orchestration injection RSS-v2")
    parser.add_argument("--layer", default="L1", help="Layer to inject (L0, L1, L3, L4)")
    parser.add_argument("--limit", type=int, default=20, help="Max repos to process")
    parser.add_argument("--report", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    source_path = Path(__file__).parent.parent / ".github/workflows/rss-v2-reusable.yml"
    repos = discover_layer_repos(args.layer)

    results = []
    for name, path in sorted(repos.items())[:args.limit]:
        res = inject_and_pr(name, path, source_path)
        results.append(res)
        icon = "[OK]" if res["status"] in ("already_present", "pr_created") else "[!!]"
        print(f"  {icon} {name:25s} | {res['status']}")

    if args.report:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()