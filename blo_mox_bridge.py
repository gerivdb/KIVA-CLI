#!/usr/bin/env python3
"""
BLO-MOX Bridge — Synchronise les PRDs validés BLO vers MOX.
Usage: python blo_mox_bridge.py [--dry-run]
"""

import sys
import re
import yaml
from pathlib import Path

BLO_PRD_DIR = Path(r"D:\DO\WEB\TOOLS\L0-CANON\BLO\PRD")
MOX_TEMPLATE = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\MOX\templates\PRD-MOC.template.md")
PRD_OUTPUT_DIR = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\PLIX\PRD")

# Statuts éligibles pour la synchronisation
ELIGIBLE_STATUSES = {"active", "proposed", "draft", "approved", "implemented"}


def extract_frontmatter(filepath: Path) -> dict | None:
    """Extrait le frontmatter YAML d'un fichier PRD."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = filepath.read_text(encoding="latin-1")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def sync_blo_to_mox(dry_run: bool = False) -> list[str]:
    """Synchronise les PRDs BLO vers MOX."""
    results = []
    
    if not BLO_PRD_DIR.exists():
        results.append(f"[SKIP] BLO PRD dir not found: {BLO_PRD_DIR}")
        return results
    
    template = MOX_TEMPLATE.read_text(encoding="utf-8") if MOX_TEMPLATE.exists() else ""
    
    prd_files = list(BLO_PRD_DIR.glob("PRD-*.md"))
    if not prd_files:
        results.append("[SYNC] No PRD files found in BLO")
        return results
    
    synced = 0
    for p in prd_files:
        fm = extract_frontmatter(p)
        if not fm:
            results.append(f"[SKIP] No frontmatter: {p.name}")
            continue
        
        status = fm.get("status", "").lower()
        if status not in ELIGIBLE_STATUSES:
            results.append(f"[SKIP] Status '{status}' not eligible: {p.name}")
            continue
        
        intent_hash = fm.get("intent_hash", "")
        title = fm.get("title", p.stem)
        repo = fm.get("repo", "gerivdb/BLO")
        body = fm.get("body", "")
        
        # Nom du fichier de sortie
        safe_title = re.sub(r'[^\w\-]', '-', title.lower())
        output_name = f"PRD-{intent_hash[:8] if intent_hash else p.stem}-{safe_title}.md"
        if len(output_name) > 200:
            output_name = f"PRD-{intent_hash[:8] if intent_hash else p.stem}.md"
        
        output_file = PRD_OUTPUT_DIR / output_name
        
        if dry_run:
            results.append(f"[DRY-RUN] Would sync {p.name} -> {output_name} (status: {status})")
        else:
            PRD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            content = body or template.replace("{{REPO}}", repo).replace("{{DATE}}", "2026-08-03").replace("{{VERSION}}", "19.5")
            output_file.write_text(content, encoding="utf-8")
            results.append(f"[SYNC] Created {output_name}")
            synced += 1
    
    if not dry_run:
        results.append(f"[SYNC] Total: {synced} PRD(s) synchronisés")
    
    return results


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"[BLO-MOX] {'Dry run' if dry_run else 'Live sync'}")
    for msg in sync_blo_to_mox(dry_run):
        print(f"  {msg}")
    print("[BLO-MOX] Done")


if __name__ == "__main__":
    main()