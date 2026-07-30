#!/usr/bin/env python3
"""
inject_canary.py — Injection atomique du workflow RSS-v2 avec gestion d'état.
Gère le stash, commit et push en une opération.

IntentHash: 0xINJECT_CANARY_20260705
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_git(args: list, cwd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Exécute git -C dans le répertoire."""
    proc = subprocess.run(
        ["git", "-C", cwd] + args,
        capture_output=True, text=True, timeout=timeout
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def has_uncommitted_changes(repo_path: str) -> bool:
    """Vérifie s'il y a des changements non commités."""
    code, out, _ = run_git(["status", "--porcelain"], repo_path)
    return bool(out)


def stash_changes(repo_path: str, message: str) -> bool:
    """Stashe les changements si présents."""
    if not has_uncommitted_changes(repo_path):
        return True
    code, _, err = run_git(["stash", "push", "-m", message], repo_path)
    return code == 0


def pop_stash(repo_path: str) -> bool:
    """Restore le stash."""
    code, _, _ = run_git(["stash", "pop"], repo_path)
    return code == 0


def inject_workflow_atomic(repo_name: str, repo_path: str, source_path: Path, dry_run: bool = False) -> dict:
    result = {
        "repo": repo_name,
        "path": repo_path,
        "status": "unknown",
        "action": None,
    }

    workflow_path = Path(repo_path) / ".github/workflows/rss-v2-reusable.yml"

    if workflow_path.exists():
        result["status"] = "already_present"
        return result

    if dry_run:
        result["status"] = "missing"
        result["action"] = "inject_workflow"
        return result

    try:
        # Créer le workflow
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        # Git add + commit sur nouvelle branche
        branch_name = "feat/epic-400-rss-v2-workflow"
        run_git(["checkout", "-b", branch_name], repo_path)
        run_git(["add", str(workflow_path.relative_to(repo_path))], repo_path)
        code, out, err = run_git([
            "commit", "-m", f"feat(workflow): inject RSS-v2 reusable workflow from REPO-STANDARDS (EPIC-400)"
        ], repo_path, timeout=15)

        if code == 0:
            result["status"] = "injected"
            result["action"] = "committed"
            result["branch"] = branch_name
        else:
            result["status"] = "inject_failed"
            result["error"] = err[:200]

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]

    return result


def main():
    parser = argparse.ArgumentParser(description="Canary injection - RSS-v2 workflow")
    parser.add_argument("--scan", action="store_true", help="Scan repos")
    parser.add_argument("--inject", action="store_true", help="Inject workflow")
    parser.add_argument("--dry-run", action="store_true", help="Simulate")
    parser.add_argument("--layer", default="L1", help="Layer to target (L1, L3, L4)")
    parser.add_argument("--limit", type=int, default=10, help="Max repos")
    args = parser.parse_args()

    # Définir les racines selon la strate
    layer_roots = {
        "L0": [Path("D:/DO/WEB/TOOLS/L0-CANON")],
        "L1": [Path("D:/DO/WEB/TOOLS/L0-CANON"), Path("D:/DO/WEB/TOOLS/L1-INFRA")],
        "L3": [Path("D:/DO/WEB/TOOLS/L3-CITIZENS")],
        "L4": [Path("D:/DO/WEB/TOOLS/L4-TOOLS")],
    }
    roots = layer_roots.get(args.layer, layer_roots["L1"])

    # Source workflow
    source_path = Path(__file__).parent.parent / ".github/workflows/rss-v2-reusable.yml"

    # Découvrir les repos
    repos = {}
    for root in roots:
        if not root.exists():
            continue
        for item in sorted(root.iterdir()):
            if item.is_dir() and (item / ".git").exists():
                repos[item.name] = str(item)

    # Classifier les repos
    missing = []
    already = []
    for name, path in sorted(repos.items()):
        if (Path(path) / ".github/workflows/rss-v2-reusable.yml").exists():
            already.append(name)
        else:
            missing.append((name, path))

    if args.scan:
        print(f"\n[INJECT_CANARY] Scan ({args.layer}):")
        print(f"  {len(already)} present, {len(missing)} missing, limit={args.limit}")
        for name in missing[:args.limit]:
            print(f"  - {name}")

    elif args.inject:
        print(f"\n[INJECT_CANARY] Injecting ({args.layer})...")
        results = []
        for name, path in missing[:args.limit]:
            res = inject_workflow_atomic(name, path, source_path, dry_run=args.dry_run)
            results.append(res)
            status = "[OK]" if res["status"] == "injected" else "[!!]"
            print(f"  {status} {name:25s} | {res['status']}")
        injected = sum(1 for r in results if r["status"] == "injected")
        print(f"\n[INJECT_CANARY] Done: {injected} injected")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()