#!/usr/bin/env python3
"""
Clone Gate Check - Vérifie les 5 étapes avant tout git clone.

Usage:
    python scripts/clone-gate-check.py --repo gerivdb/CTULU
    python scripts/clone-gate-check.py --audit-existing

Refs: INTENT-085, ADR-091, ADR-20260622-001, KiloRules hitl-clone-gate.md, clone-causal-prevention.md
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_STANDARDS = Path(__file__).resolve().parent.parent
KNOWN_REPOS = REPO_STANDARDS / "known_repositories.yaml"


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


def load_known_repos() -> dict | None:
    if not KNOWN_REPOS.exists():
        return None
    try:
        import yaml

        with open(KNOWN_REPOS, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            # Normalize: support both {repos: [...]} and top-level list
            if isinstance(data, dict):
                return data.get("repos", data)
            return data
    except Exception:
        return None


def find_repo_in_yaml(repo_name: str, data) -> dict | None:
    repos = data if isinstance(data, list) else [data]
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        if repo.get("full_name") == repo_name or repo.get("name") == repo_name:
            return repo
    return None


def check_known_repos(repo_name: str) -> dict:
    data = load_known_repos()
    if data is None:
        return {"ok": False, "error": "known_repositories.yaml not found"}
    repo = find_repo_in_yaml(repo_name, data)
    if repo is None:
        return {"ok": False, "error": f"{repo_name} not in known_repositories.yaml"}
    return {"ok": True, "repo": repo}


def check_local_path(repo_data: dict) -> dict:
    local_path = repo_data.get("local_path")
    if not local_path:
        return {"ok": False, "error": "No local_path defined"}
    return {"ok": True, "local_path": local_path}


def check_directory_exists(local_path: str) -> dict:
    p = Path(local_path)
    if p.exists() and p.is_dir():
        return {"ok": False, "error": f"Directory already exists: {local_path}"}
    return {"ok": True}


def check_strate(local_path: str) -> dict:
    valid_prefixes = [
        "D:\\DO\\WEB\\TOOLS\\L0-CANON",
        "D:\\DO\\WEB\\TOOLS\\L0-INFRASTRUCTURE",
        "D:\\DO\\WEB\\TOOLS\\L1-INFRA",
        "D:\\DO\\WEB\\TOOLS\\L2-PLATFORM",
        "D:\\DO\\WEB\\TOOLS\\L3-CITIZENS",
        "D:\\DO\\WEB\\TOOLS\\L4-TOOLS",
        "D:\\DO\\WEB\\TOOLS\\L5-ARCHIVE",
    ]
    if any(local_path.startswith(prefix) for prefix in valid_prefixes):
        return {"ok": True}
    return {"ok": False, "error": f"Invalid strate path: {local_path}"}


def check_illegitimate_clones(repo_name: str, local_path: str) -> dict:
    repo_dir = Path(local_path).name
    tools_dir = Path(local_path).parent
    if not tools_dir.name.startswith("L"):
        return {"ok": True}  # Already checked in check_strate
    base_name = repo_dir
    possible_illegitimate = tools_dir.parent / base_name
    if possible_illegitimate.exists():
        return {
            "ok": False,
            "error": f"Illegitimate clone exists: {possible_illegitimate}",
        }
    return {"ok": True}


def audit_existing_clones() -> list[dict]:
    data = load_known_repos()
    if data is None:
        return []
    repos = data if isinstance(data, list) else [data]
    results = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        local_path = repo.get("local_path")
        if not local_path:
            continue
        p = Path(local_path)
        exists = p.exists() and p.is_dir()
        results.append({"repo": repo.get("full_name"), "local_path": local_path, "exists": exists})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Clone Gate Check")
    parser.add_argument("--repo", help="Repo name (gerivdb/<repo>)")
    parser.add_argument("--audit-existing", action="store_true", help="Audit existing clones")
    args = parser.parse_args()

    if args.audit_existing:
        clones = audit_existing_clones()
        for clone in clones:
            status = "OK" if clone["exists"] else "MISSING"
            print(f"[{status}] {clone['repo']} -> {clone['local_path']}")
        return 0

    if not args.repo:
        print("[ERR] --repo or --audit-existing required")
        return 1

    checks = []

    # ETAPE-1: known_repositories.yaml
    check1 = check_known_repos(args.repo)
    checks.append(("CHECK-1: known_repos", check1))
    if not check1["ok"]:
        for name, check in checks:
            print(f"[BLOCKED] {name}: {check.get('error')}")
        return 1

    repo_data = check1["repo"]

    # ETAPE-2: local_path present
    check2 = check_local_path(repo_data)
    checks.append(("CHECK-2: local_path", check2))
    if not check2["ok"]:
        for name, check in checks:
            print(f"[BLOCKED] {name}: {check.get('error')}")
        return 1

    local_path = check2["local_path"]

    # ETAPE-3: directory exists
    check3 = check_directory_exists(local_path)
    checks.append(("CHECK-3: directory_exists", check3))
    if not check3["ok"]:
        for name, check in checks:
            print(f"[BLOCKED] {name}: {check.get('error')}")
        return 1

    # ETAPE-4: strate valid
    check4 = check_strate(local_path)
    checks.append(("CHECK-4: strate_valid", check4))
    if not check4["ok"]:
        for name, check in checks:
            print(f"[BLOCKED] {name}: {check.get('error')}")
        return 1

    # ETAPE-5: illegitimate clones
    check5 = check_illegitimate_clones(args.repo, local_path)
    checks.append(("CHECK-5: illegitimate_clones", check5))
    if not check5["ok"]:
        for name, check in checks:
            print(f"[BLOCKED] {name}: {check.get('error')}")
        return 1

    for name, check in checks:
        print(f"[OK] {name}")

    print(f"\n[OK] All clone gate checks passed")
    print(f"[ACTION] Clone authorized at: {local_path}")
    print(f"[HITL] Confirm before executing: git clone https://github.com/{args.repo}.git {local_path}")
    return 0


if __name__ == "__main__":
    exit(main())
