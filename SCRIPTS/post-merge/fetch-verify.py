#!/usr/bin/env python3
"""
fetch-verify.py — Fetch explicite + vérification de synchronisation post-merge.

Problème résolu : après un `gh pr merge --squash` ou un merge distant,
le `git pull --rebase` local peut ne pas récupérer le merge commit
car le fetch a eu lieu AVANT la création du merge commit côté distant.

Ce script :
1. Fetch explicitement origin/main
2. Compare HEAD local avec origin/main
3. Si derrière  -> pull --rebase
4. Si diverge  -> signale le problème
5. Log l'événement dans SWARM.yaml (event: post_merge_sync)

Usage:
    python scripts/post-merge/fetch-verify.py --repo-path <path> --repo-name <name>

IntentHash: 0xFETCH_VERIFY_POST_MERGE_20260629
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_run(repo_path: str, *args, check: bool = False, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True, text=True, check=check, timeout=timeout,
    )


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
        pass  # SWARM.yaml logging is best-effort


def fetch_verify(repo_path: str, repo_name: str) -> dict:
    result = {
        "repo": repo_name,
        "path": repo_path,
        "status": "unknown",
        "action_taken": None,
        "local_sha": "",
        "remote_sha": "",
        "behind": 0,
        "ahead": 0,
    }

    # 1. Fetch explicite
    print(f"[FETCH-VERIFY] Fetching origin for {repo_name}...")
    r = git_run(repo_path, "fetch", "origin", timeout=30)
    if r.returncode != 0:
        result["status"] = "fetch_failed"
        result["error"] = r.stderr.strip()[:200]
        print(f"[FETCH-VERIFY] [FAIL] Fetch failed: {r.stderr.strip()[:100]}")
        log_event("post_merge_sync_failed", repo_name, {"error": "fetch_failed"})
        return result

    # 2. Comparer HEAD local avec origin/main
    local_sha = get_sha(repo_path, "HEAD")
    remote_sha = get_sha(repo_path, "origin/main")
    result["local_sha"] = local_sha[:12]
    result["remote_sha"] = remote_sha[:12]

    if local_sha == remote_sha:
        result["status"] = "in_sync"
        print(f"[FETCH-VERIFY] [OK] {repo_name} synchronisé ({local_sha[:12]})")
        log_event("post_merge_sync_ok", repo_name, {"sha": local_sha[:12]})
        return result

    # 3. Calculer behind/ahead
    behind, ahead = get_behind_ahead(repo_path)
    result["behind"] = behind
    result["ahead"] = ahead

    if behind == 0 and ahead > 0:
        result["status"] = "local_ahead"
        print(f"[FETCH-VERIFY] [INFO]  {repo_name} local en avance ({ahead} commits) — OK")
        return result

    if behind > 0 and ahead == 0:
        # Cas simple : local derrière  -> pull --rebase
        print(f"[FETCH-VERIFY] {repo_name} en retard de {behind} commits  -> pull --rebase...")
        r = git_run(repo_path, "pull", "--rebase", "origin", "main", timeout=60)
        if r.returncode == 0:
            new_sha = get_sha(repo_path, "HEAD")
            result["status"] = "synced_via_rebase"
            result["action_taken"] = "pull --rebase origin/main"
            result["local_sha"] = new_sha[:12]
            print(f"[FETCH-VERIFY] [OK] Synchronisé via rebase  -> {new_sha[:12]}")
            log_event("post_merge_sync_rebase", repo_name, {
                "behind": behind,
                "new_sha": new_sha[:12],
            })
        else:
            result["status"] = "rebase_failed"
            result["error"] = r.stderr.strip()[:200]
            print(f"[FETCH-VERIFY] [FAIL] Rebase failed: {r.stderr.strip()[:100]}")
            log_event("post_merge_sync_failed", repo_name, {"error": "rebase_failed"})
        return result

    if behind > 0 and ahead > 0:
        # Divergence — nécessite rebase
        print(f"[FETCH-VERIFY] [WARN]  {repo_name} divergé (behind={behind}, ahead={ahead})  -> rebase...")
        r = git_run(repo_path, "pull", "--rebase", "origin", "main", timeout=60)
        if r.returncode == 0:
            new_sha = get_sha(repo_path, "HEAD")
            result["status"] = "synced_via_rebase_diverged"
            result["action_taken"] = "pull --rebase origin/main (diverged)"
            result["local_sha"] = new_sha[:12]
            print(f"[FETCH-VERIFY] [OK] Divergence résolue via rebase  -> {new_sha[:12]}")
            log_event("post_merge_sync_rebase_diverged", repo_name, {
                "behind": behind,
                "ahead": ahead,
                "new_sha": new_sha[:12],
            })
        else:
            result["status"] = "rebase_conflict"
            result["error"] = r.stderr.strip()[:200]
            print(f"[FETCH-VERIFY] [FAIL] Conflit de rebase — résolution manuelle requise")
            log_event("post_merge_sync_failed", repo_name, {"error": "rebase_conflict"})
        return result

    result["status"] = "unknown_state"
    print(f"[FETCH-VERIFY] [WARN]  État inconnu pour {repo_name}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch + Verify sync post-merge")
    parser.add_argument("--repo-path", required=True, help="Chemin local du repo")
    parser.add_argument("--repo-name", required=True, help="Nom du repo")
    args = parser.parse_args()

    result = fetch_verify(args.repo_path, args.repo_name)
    print()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Exit code : 0 = synced/OK, 1 = needs attention
    if result["status"] in ("in_sync", "local_ahead", "synced_via_rebase", "synced_via_rebase_diverged"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
