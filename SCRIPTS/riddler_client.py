#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
riddler_client.py — RIDDLER : Runtime Intelligence & Dispatch for Documentation Lifecycle Enforcement.

Détecte les repos manquant le workflow RSS-v2 réutilisable et orchestre l'injection.

IntentHash: 0xRIDDLER_CLIENT_20260705
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

GOVERNANCE_HUB = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB")
WORKFLOW_NAME = ".github/workflows/rss-v2-reusable.yml"
WORKFLOW_SOURCE = Path(__file__).parent.parent / ".github/workflows/rss-v2-reusable.yml"


def discover_repos() -> dict:
    repos = {}
    for root in [
        Path("D:/DO/WEB/TOOLS/L0-CANON"),
        Path("D:/DO/WEB/TOOLS/L1-INFRA"),
        Path("D:/DO/WEB/TOOLS/L4-TOOLS"),
        Path("D:/DO/WEB"),
    ]:
        if not root.exists():
            continue
        for item in sorted(root.iterdir()):
            if item.is_dir() and (item / ".git").exists():
                if item.name in repos:
                    continue
                repos[item.name] = str(item)
    return repos


def check_workflow_exists(repo_path: str) -> bool:
    try:
        workflow_path = Path(repo_path).expanduser().resolve() / WORKFLOW_NAME
        return workflow_path.exists()
    except Exception:
        return False


def inject_workflow(repo_name: str, repo_path: str, dry_run: bool = False) -> dict:
    result = {
        "repo": repo_name,
        "path": repo_path,
        "status": "unknown",
        "action": None,
    }

    if check_workflow_exists(repo_path):
        result["status"] = "already_present"
        return result

    if dry_run:
        result["status"] = "missing"
        result["action"] = "inject_workflow"
        return result

    dest_path = Path(repo_path) / WORKFLOW_NAME
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    source_content = Path(WORKFLOW_SOURCE).read_text(encoding="utf-8")
    dest_path.write_text(source_content, encoding="utf-8")
    
    subprocess.run(
        ["git", "-C", repo_path, "add", str(WORKFLOW_NAME)],
        capture_output=True,
    )
    proc = subprocess.run(
        ["git", "-C", repo_path, "commit", "-m", f"feat(workflow): inject RSS-v2 reusable workflow from REPO-STANDARDS (EPIC-400)"],
        capture_output=True,
        text=True,
    )
    
    if proc.returncode == 0:
        result["status"] = "injected"
        result["action"] = "committed"
        result["commit"] = proc.stdout.strip()[-12:] if proc.stdout else ""
    else:
        result["status"] = "inject_failed"
        result["error"] = proc.stderr.strip()[:200]

    return result


def main():
    parser = argparse.ArgumentParser(description="RIDDLER Client — Workflow injection")
    parser.add_argument("--scan", action="store_true", help="Scan repos for missing workflow")
    parser.add_argument("--inject", action="store_true", help="Inject workflow into missing repos")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without applying")
    parser.add_argument("--limit", type=int, default=10, help="Max repos to process")
    args = parser.parse_args()

    repos = discover_repos()
    missing = []
    already = []
    
    for name, path in sorted(repos.items()):
        if check_workflow_exists(path):
            already.append(name)
        else:
            missing.append((name, path))

    if args.scan:
        print(f"\n[RIDDLER] Scan complete:")
        print(f"  {len(already)} repos have workflow present")
        print(f"  {len(missing)} repos missing workflow")
        if missing:
            print(f"\n[RIDDLER] Missing in:")
            for name, _ in missing[:args.limit]:
                print(f"  - {name}")
        print(f"\n[RIDDLER] Already present in:")
        for name in already[:args.limit]:
            print(f"  - {name}")

    elif args.inject:
        print(f"\n[RIDDLER] Injecting into {len(missing)} repos...")
        results = []
        for name, path in missing[:args.limit]:
            result = inject_workflow(name, path, dry_run=args.dry_run)
            results.append(result)
            icon = "[OK]" if result["status"] in ("already_present", "injected") else "[!!]"
            print(f"  {icon} {name:25s} | {result['status']}")
        
        print(f"\n[RIDDLER] Injection complete: {sum(1 for r in results if r['status']=='injected')} injected")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()