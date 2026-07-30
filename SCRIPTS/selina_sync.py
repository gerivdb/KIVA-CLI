#!/usr/bin/env python3
"""
selina_sync.py — Synchronisation intelligente post-merge (SELINA Layer).

SELINA = Symbolic Ecosystem Liaison & Intelligence Network Agent.
Détecte les désynchronisations cross-repo après un merge et orchestre
la récupération via fetch explicite + rebase.

Problème résolu : le `git pull --rebase` peut échouer silencieusement
si le merge commit distant a été créé APRÈS le fetch local.

SELINA :
1. Détecte tous les repos locaux
2. Pour chaque repo : fetch + compare HEAD vs origin/main
3. Si désynchronisé → rebase automatique
4. Si conflit → signale pour HITL
5. Log dans SWARM.yaml (events: selINA_sync)
6. Retourne un rapport JSON

Usage:
    python scripts/selina_sync.py --scan          # Scan tous les repos
    python scripts/selina_sync.py --sync          # Sync tous les repos
    python scripts/selina_sync.py --repo REPO-STANDARDS  # Sync un repo
    python scripts/selina_sync.py --status        # État uniquement

IntentHash: 0xSELINA_SYNC_20260629
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GOVERNANCE_HUB = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB")
SWARM_FILE = GOVERNANCE_HUB / "SWARM.yaml"

REPO_SCAN_ROOTS = [
    Path("D:/DO/WEB/TOOLS/L0-CANON"),
    Path("D:/DO/WEB/TOOLS/L1-INFRA"),
    Path("D:/DO/WEB/TOOLS/L4-TOOLS"),
    Path("D:/DO/WEB"),
]

DEFAULT_BRANCH = "main"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_run(repo_path: str, *args, check: bool = False, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True, text=True, check=check, timeout=timeout,
    )


def discover_repos() -> dict:
    repos = {}
    for root in REPO_SCAN_ROOTS:
        if not root.exists():
            continue
        for item in sorted(root.iterdir()):
            if item.is_dir() and (item / ".git").exists():
                repos[item.name] = str(item)
    return repos


def get_sha(repo_path: str, ref: str) -> str:
    r = git_run(repo_path, "rev-parse", ref)
    return r.stdout.strip() if r.returncode == 0 else ""


def get_behind_ahead(repo_path: str, local_ref: str = "HEAD", remote_ref: str = "origin/main") -> tuple[int, int]:
    r = git_run(repo_path, "rev-list", "--left-right", "--count", f"{remote_ref}...{local_ref}", timeout=15)
    if r.returncode == 0 and r.stdout.strip():
        parts = r.stdout.strip().split()
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    return -1, -1


def log_event(event_type: str, repo_name: str, details: dict) -> None:
    try:
        import yaml
        if SWARM_FILE.exists():
            data = yaml.safe_load(SWARM_FILE.read_text(encoding="utf-8")) or {}
        else:
            data = {"version": "2.0", "nodes": {}, "events": []}
        if "events" not in data:
            data["events"] = []
        data["events"].append({
            "type": event_type,
            "source_node": repo_name,
            "timestamp": _now(),
            "details": details,
        })
        data["events"] = data["events"][-200:]
        SWARM_FILE.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
    except Exception:
        pass


def sync_repo(repo_name: str, repo_path: str, dry_run: bool = False) -> dict:
    result = {
        "repo": repo_name,
        "path": repo_path,
        "status": "unknown",
        "action": None,
        "local_sha": "",
        "remote_sha": "",
        "behind": 0,
        "ahead": 0,
    }

    # Fetch
    r = git_run(repo_path, "fetch", "origin", timeout=30)
    if r.returncode != 0:
        result["status"] = "fetch_failed"
        result["error"] = r.stderr.strip()[:200]
        log_event("selina_sync_failed", repo_name, {"error": "fetch_failed"})
        return result

    local_sha = get_sha(repo_path, "HEAD")
    remote_sha = get_sha(repo_path, "origin/main")
    result["local_sha"] = local_sha[:12]
    result["remote_sha"] = remote_sha[:12]

    if local_sha == remote_sha:
        result["status"] = "in_sync"
        return result

    behind, ahead = get_behind_ahead(repo_path)
    result["behind"] = behind
    result["ahead"] = ahead

    if dry_run:
        result["status"] = "needs_sync"
        result["action"] = f"would rebase (behind={behind}, ahead={ahead})"
        return result

    if behind >= 0:
        r = git_run(repo_path, "pull", "--rebase", "origin", DEFAULT_BRANCH, timeout=60)
        if r.returncode == 0:
            new_sha = get_sha(repo_path, "HEAD")
            result["status"] = "synced"
            result["action"] = "pull --rebase origin/main"
            result["local_sha"] = new_sha[:12]
            log_event("selina_sync_ok", repo_name, {
                "behind": behind,
                "ahead": ahead,
                "new_sha": new_sha[:12],
            })
        else:
            result["status"] = "rebase_failed"
            result["error"] = r.stderr.strip()[:200]
            log_event("selina_sync_failed", repo_name, {"error": "rebase_failed"})
    else:
        result["status"] = "unknown"
        result["error"] = "Could not determine behind/ahead"

    return result


def scan_all() -> list[dict]:
    repos = discover_repos()
    results = []
    for name, path in sorted(repos.items()):
        result = sync_repo(name, path, dry_run=True)
        results.append(result)
    return results


def sync_all(dry_run: bool = False) -> list[dict]:
    repos = discover_repos()
    results = []
    for name, path in sorted(repos.items()):
        result = sync_repo(name, path, dry_run=dry_run)
        results.append(result)
        status_icon = "✅" if result["status"] in ("in_sync", "synced") else "⚠️"
        print(f"  {status_icon} {name:25s} | {result['status']:15s} | behind={result['behind']} ahead={result['ahead']}")
    return results


def main():
    parser = argparse.ArgumentParser(description="SELINA Sync — Synchronisation intelligente cross-repo")
    parser.add_argument("--scan", action="store_true", help="Scanner tous les repos (dry-run)")
    parser.add_argument("--sync", action="store_true", help="Synchroniser tous les repos")
    parser.add_argument("--repo", default="", help="Nom du repo ciblé")
    parser.add_argument("--dry-run", action="store_true", help="Simuler sans appliquer")
    parser.add_argument("--status", action="store_true", help="État uniquement (scan + summary)")
    args = parser.parse_args()

    if args.scan or args.status:
        print(f"\n[SELINA] Scan de l'écosystème...")
        results = scan_all()
        synced = sum(1 for r in results if r["status"] == "in_sync")
        needs = sum(1 for r in results if r["status"] != "in_sync")
        print(f"\n[SELINA] Résultat: {synced} synchronisés, {needs} à synchroniser")
        for r in results:
            icon = "✅" if r["status"] == "in_sync" else "⚠️"
            print(f"  {icon} {r['repo']:25s} | {r['status']:15s} | behind={r['behind']} ahead={r['ahead']}")
        print()
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif args.sync:
        target = args.repo if args.repo else "all"
        print(f"\n[SELINA] Synchronisation de {target}...")
        print(f"[SELINA] Mode: {'DRY-RUN' if args.dry_run else 'APPLY'}")
        print()
        if args.repo:
            repos = discover_repos()
            if args.repo in repos:
                result = sync_repo(args.repo, repos[args.repo], dry_run=args.dry_run)
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"[SELINA] ❌ Repo '{args.repo}' non trouvé localement")
                sys.exit(1)
        else:
            results = sync_all(dry_run=args.dry_run)
            failed = [r for r in results if r["status"] in ("fetch_failed", "rebase_failed")]
            if failed:
                print(f"\n[SELINA] ⚠️  {len(failed)} repo(s) en erreur — intervention requise")
                sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
