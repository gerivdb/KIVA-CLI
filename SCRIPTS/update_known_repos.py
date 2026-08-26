#!/usr/bin/env python3
"""
Ajoute enforcement_mode + fork_source dans known_repositories.yaml
Basé sur ADR-2026-07-12-005 (Constitutional CI), ADR-2026-07-12-006 (Fork Sync), ADR-2026-07-12-007 (External Forks)
"""
import yaml
import shutil
from pathlib import Path

KNOWN_REPOS = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml")
BACKUP = KNOWN_REPOS.with_suffix(".yaml.bak2")

# Mapping strate -> enforcement_mode
STRATE_ENFORCEMENT = {
    "L0_CONSTITUTIONAL": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L0-CANON": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L1_CAUSALITY": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L1_INFRA": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L1b": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L2_COMPOSITION": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L2b_QUALIFIER": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L2b_SENSOR": {
        "ci": "full", "branch_protection": "full", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "full"
    },
    "L3_EMERGENCE": {
        "ci": "full", "branch_protection": "status-checks-only", "hooks": "full",
        "rss_lint": "all-checks", "vyoa": "full", "brgs": "naming-only"
    },
    "L4_TOOLS": {
        "ci": "hooks-only", "branch_protection": "status-checks-only", "hooks": "minimal",
        "rss_lint": "profile-only", "vyoa": "commit-only", "brgs": "none"
    },
    "L5_ARCHIVE": {
        "ci": "none", "branch_protection": "none", "hooks": "none",
        "rss_lint": "none", "vyoa": "none", "brgs": "none"
    },
}

# Repos externes connus (enforcement_mode: none)
EXTERNAL_REPOS = {
    "HERMES-NousResearch": True,
}

# Fork sources connus
FORK_SOURCES = {
    "HERMES": {
        "owner": "gerivdb",
        "repo": "HERMES",
        "branch": "main",
        "sync_frequency": "daily",
        "conflict_strategy": "hitl"
    },
    "HERMES-NousResearch": {
        "owner": "NousResearch",
        "repo": "hermes-agent",
        "branch": "main",
        "sync_frequency": "manual",
        "conflict_strategy": "hitl"
    },
}

def get_layer(repo: dict) -> str:
    return repo.get("layer") or repo.get("strate") or "L4_TOOLS"

def is_external(repo: dict) -> bool:
    name = repo.get("name", "")
    if name in EXTERNAL_REPOS:
        return True
    # Check fork_source owner
    fork_source = repo.get("fork_source")
    if isinstance(fork_source, dict):
        return fork_source.get("owner") != "gerivdb"
    return False

def get_enforcement_mode(layer: str, is_ext: bool) -> dict:
    if is_ext:
        return {
            "ci": "none", "branch_protection": "none", "hooks": "none",
            "rss_lint": "none", "vyoa": "none", "brgs": "none"
        }
    return STRATE_ENFORCEMENT.get(layer, STRATE_ENFORCEMENT["L4_TOOLS"])

def main():
    # Backup
    shutil.copy2(KNOWN_REPOS, BACKUP)
    print(f"[BACKUP] {BACKUP}")
    
    with open(KNOWN_REPOS, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    updated = 0
    tiers = ["P0_REPOS", "P1_REPOS", "P2_REPOS", "P3_REPOS", "P4_REPOS", "P5_REPOS"]
    
    for tier in tiers:
        repos = data.get(tier, [])
        for repo in repos:
            name = repo.get("name", "unknown")
            layer = get_layer(repo)
            is_ext = is_external(repo)
            
            # enforcement_mode
            enforcement = get_enforcement_mode(layer, is_ext)
            repo["enforcement_mode"] = enforcement
            
            # fork_source
            if name in FORK_SOURCES and "fork_source" not in repo:
                repo["fork_source"] = FORK_SOURCES[name]
                print(f"[FORK] {name}: fork_source added")
            
            # status cleanup for external
            if is_ext and repo.get("status") != "active":
                repo["status"] = "active"
            
            updated += 1
            print(f"  {name} ({layer}) {'EXTERNAL' if is_ext else 'INTERNAL'} -> enforcement_mode.{list(enforcement.keys())[0]}={list(enforcement.values())[0]}")
    
    # Write
    with open(KNOWN_REPOS, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"\n[OK] Updated {updated} repos in {KNOWN_REPOS}")
    print(f"[BACKUP] {BACKUP}")

if __name__ == "__main__":
    main()