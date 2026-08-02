#!/usr/bin/env python3
"""
BLO-MOX Bridge — Synchronise les intents validés BLO vers MOX.
Usage: python blo_mox_bridge.py [--dry-run]
"""

import sys
import json
import subprocess
from pathlib import Path

BLO_DB = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\BLO\bloom_intents.db")
MOX_TEMPLATE = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\MOX\templates\PRD-MOC.template.md")
PRD_DIR = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\PLIX\PRD")

# Intents BLO éligibles pour MOX (statut approved/proposed)
ELIGIBLE_STATUSES = {"approved", "proposed"}
ELIGIBLE_TYPES = {"PRD"}


def sync_blo_to_mox(dry_run: bool = False) -> list[str]:
    """Synchronise les PRDs validés BLO vers MOX."""
    results = []
    if not BLO_DB.exists():
        results.append(f"[SKIP] BLO DB not found: {BLO_DB}")
        return results
    
    try:
        import sqlite3
        conn = sqlite3.connect(BLO_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT intent_hash, title, type, status, repo, body FROM intents "
            "WHERE type IN ({}) AND status IN ({})".format(
                ','.join('?' for _ in ELIGIBLE_TYPES),
                ','.join('?' for _ in ELIGIBLE_STATUSES)
            ),
            list(ELIGIBLE_TYPES) + list(ELIGIBLE_STATUSES)
        )
        intents = cursor.fetchall()
        conn.close()
    except Exception as e:
        results.append(f"[ERROR] BLO query failed: {e}")
        return results
    
    if not intents:
        results.append("[SYNC] No eligible intents found")
        return results
    
    template = MOX_TEMPLATE.read_text(encoding="utf-8") if MOX_TEMPLATE.exists() else ""
    
    for intent in intents:
        intent_hash = intent["intent_hash"]
        title = intent["title"]
        repo = intent["repo"]
        body = intent["body"]
        
        prd_file = PRD_DIR / f"PRD-{intent_hash[:8]}-{title.lower().replace(' ', '-')}.md"
        
        if dry_run:
            results.append(f"[DRY-RUN] Would sync {intent_hash[:16]} -> {prd_file}")
        else:
            PRD_DIR.mkdir(parents=True, exist_ok=True)
            content = body or template.replace("{{REPO}}", repo).replace("{{DATE}}", "2026-08-02")
            prd_file.write_text(content, encoding="utf-8")
            results.append(f"[SYNC] Created {prd_file}")
    
    return results


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"[BLO-MOX] {'Dry run' if dry_run else 'Live sync'}")
    for msg in sync_blo_to_mox(dry_run):
        print(f"  {msg}")
    print("[BLO-MOX] Done")


if __name__ == "__main__":
    main()