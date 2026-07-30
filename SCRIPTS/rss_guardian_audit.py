#!/usr/bin/env python3
"""
rss_guardian_audit.py - Audit magistral RSS-v2 pour REPO-STANDARDS.

Orchestré par RSS_GUARDIAN citoyen.
Detecte et propose correction des repos non-conformes.

Usage:
    python scripts/rss_guardian_audit.py --all          # Audit tous les repos
    python scripts/rss_guardian_audit.py --target REPO   # Audit un repo
    python scripts/rss_guardian_audit.py --inject       # Injecter workflows (dry-run)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

REPO_STANDARDS = Path("D:/DO/WEB/TOOLS/L4-TOOLS/REPO-STANDARDS")
WORKFLOW_NAME = "rss-v2-reusable.yml"
KNOWN_REPOS_PATH = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml")


def get_non_compliant_repos() -> list[dict]:
    """Retourne la liste des repos n'ayant pas le workflow RSS-v2."""
    if yaml is None or not KNOWN_REPOS_PATH.exists():
        return []

    data = yaml.safe_load(KNOWN_REPOS_PATH.read_text(encoding="utf-8")) or {}
    non_compliant = []

    for section in ["P0_REPOS", "P1_REPOS", "P2_REPOS", "P3_REPOS", "P4_REPOS"]:
        for repo in data.get(section, []):
            if not isinstance(repo, dict):
                continue
            local_path = repo.get("local_path", "")
            if not local_path:
                continue
            workflow_path = Path(local_path) / ".github" / "workflows" / WORKFLOW_NAME
            if not workflow_path.exists():
                non_compliant.append({
                    "name": repo["name"],
                    "local_path": local_path,
                    "layer": repo.get("layer", "unknown"),
                })

    return non_compliant


def main():
    parser = argparse.ArgumentParser(description="RSS Guardian Audit")
    parser.add_argument("--all", action="store_true", help="Audit tous les repos")
    parser.add_argument("--target", help="Repo cible à auditer")
    parser.add_argument("--inject", action="store_true", help="Proposer injection (dry-run)")
    args = parser.parse_args()

    if args.all or not args.target:
        repos = get_non_compliant_repos()
        print(f"\n[RSS_GUARDIAN] Audit du metacluster...")
        print(f"[RSS_GUARDIAN] {len(repos)} repos non-conformes detectés:\n")
        for r in repos[:20]:
            print(f"  - {r['name']:25s} ({r['layer']})")
        if len(repos) > 20:
            print(f"  ... et {len(repos) - 20} autres")
        print()
        print(json.dumps(repos, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())