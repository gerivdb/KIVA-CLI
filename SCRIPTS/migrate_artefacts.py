#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_artefacts.py -- Migration des artefacts RSS-v1 vers RSS-v2

Normalise le frontmatter de tous les artefacts (PRD, ADR, EPIC, SPEC, INTENT)
au format RSS-v2 standard.

Usage:
    python scripts/migrate_artefacts.py --repo . --dry-run
    python scripts/migrate_artefacts.py --repo .
    python scripts/migrate_artefacts.py --repo . --type PRD
"""

import argparse
import os
import re
import sys
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

ARTIFACT_DIRS = {
    "PRD": "PRD",
    "ADR": "ADR",
    "EPIC": "EPICS",
    "EPICS": "EPICS",
    "SPEC": "SPEC",
    "INTENT": "INTENTS",
    "INTENTS": "INTENTS",
}

EXCLUDE_PATTERNS = [
    r".*-index\.md$",
    r".*-example\.md$",
    r".*\.gitkeep$",
]


def is_excluded(fname):
    for pat in EXCLUDE_PATTERNS:
        if re.match(pat, fname, re.IGNORECASE):
            return True
    return False


def parse_frontmatter(content):
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_str = content[3:end].strip()
    body = content[end + 3:]
    if yaml:
        try:
            fm = yaml.safe_load(fm_str) if fm_str else {}
            return (fm if isinstance(fm, dict) else {}), body
        except:
            return {}, content
    return {}, content


def derive_id_from_filename(fname):
    m = re.match(r"(PRD|ADR|EPIC|SPEC|INTENT)-(\d{3})-[a-z0-9]", fname, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}"
    return ""


def derive_type_from_dir(dir_name):
    mapping = {"PRD": "PRD", "ADR": "ADR", "EPICS": "EPIC", "SPEC": "SPEC", "INTENT": "INTENT", "INTENTS": "INTENT"}
    return mapping.get(dir_name.upper(), dir_name.upper())


def normalize_status(status):
    status = status.lower().strip()
    mapping = {
        "actif": "active", "actifs": "active",
        "proposed": "proposed", "accepted": "accepted",
        "draft": "draft", "active": "active",
        "done": "done", "completed": "completed",
        "planned": "draft", "deprecated": "deprecated",
        "superseded": "superseded", "archived": "deprecated",
        "stable": "stable",
    }
    return mapping.get(status, status)


def normalize_frontmatter(fm, fname, dir_name, body):
    artifact_type = derive_type_from_dir(dir_name)
    derived_id = derive_id_from_filename(fname)

    fid = str(fm.get("id", fm.get("ID", derived_id))).strip()
    if fid in ("None", "", "0") or "-000" in fid:
        fid = derived_id

    title = str(fm.get("title", fm.get("Titre", ""))).strip().strip('"')

    fm_repo = str(fm.get("repo", fm.get("Repo", ""))).strip()
    if not fm_repo:
        fm_repo = "gerivdb/REPO-STANDARDS"

    fm_status = str(fm.get("status", fm.get("Statut", "draft"))).strip()
    fm_status = normalize_status(fm_status)

    created = str(fm.get("created", fm.get("Date", fm.get("date", "")))).strip().strip('"')
    if not created:
        created = "2026-06-16"

    author = str(fm.get("author", fm.get("Auteur", "gerivdb"))).strip()
    if author.lower() in ("hitl", "kilo agent", "gerivdb (assisté comet/env1)"):
        author = "gerivdb"

    intent_hash = str(fm.get("intent_hash", "")).strip()
    if not intent_hash.startswith("0x"):
        m = re.search(r"IntentHash[`\s:]+`(0x[A-F0-9_]+)`", body, re.IGNORECASE)
        if m:
            intent_hash = m.group(1)
        else:
            intent_hash = "0xPENDING"

    superseded_by = fm.get("superseded_by", None)
    if superseded_by == "None" or superseded_by == "":
        superseded_by = None

    if not title:
        m = re.search(r"^#\s+.+?—\s+(.+)$", body, re.MULTILINE)
        if m:
            title = m.group(1).strip()
        else:
            m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            if m:
                raw = m.group(1).strip()
                title = re.sub(r"^[A-Z]+-\d{3}\s*[—–-]\s*", "", raw).strip()

    if not title:
        title = fname.replace(".md", "").replace("-", " ").title()

    normalized = {
        "id": fid,
        "title": title,
        "repo": fm_repo,
        "status": fm_status,
        "created": created,
        "author": author,
        "intent_hash": intent_hash,
    }
    if superseded_by:
        normalized["superseded_by"] = str(superseded_by)

    return normalized


def clean_body(body):
    lines = body.split("\n")
    cleaned = []
    in_metadata_section = False

    for line in lines:
        stripped = line.strip()

        if re.match(r"\*\*[^*]+\*\*:\s*{", stripped):
            in_metadata_section = True
            continue

        if in_metadata_section:
            if stripped.startswith("#") or stripped.startswith("---") or stripped == "":
                in_metadata_section = False
                if stripped == "":
                    continue

        if in_metadata_section:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def build_artifact_content(fm, body):
    lines = ["---"]
    for key in ("id", "title", "repo", "status", "created", "author", "intent_hash", "superseded_by", "prd_ref", "epic_ref", "source_repo", "source_path"):
        val = fm.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            if ":" in val or "#" in val:
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")
        elif isinstance(val, bool):
            lines.append(f"{key}: {str(val).lower()}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    lines.append("")

    cleaned_body = clean_body(body)
    lines.append(cleaned_body)

    return "\n".join(lines)


def migrate_file(filepath, dry_run=False):
    content = filepath.read_text(encoding="utf-8")
    fname = filepath.name
    dir_name = filepath.parent.name

    fm, body = parse_frontmatter(content)
    normalized = normalize_frontmatter(fm, fname, dir_name, body)
    new_content = build_artifact_content(normalized, body)

    if dry_run:
        return {
            "file": str(filepath),
            "status": "dry_run",
            "original_id": fm.get("id", "MISSING"),
            "normalized_id": normalized["id"],
            "normalized_status": normalized["status"],
        }

    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        return {"file": str(filepath), "status": "migrated", "id": normalized["id"]}
    else:
        return {"file": str(filepath), "status": "already_conform", "id": normalized["id"]}


def migrate_repo(repo_path, artifact_type=None, dry_run=False):
    repo = Path(repo_path)
    results = []

    dirs_to_migrate = []
    if artifact_type:
        dir_name = ARTIFACT_DIRS.get(artifact_type.upper())
        if dir_name:
            dirs_to_migrate.append(repo / dir_name)
    else:
        for d in ("PRD", "ADR", "EPICS", "SPEC", "INTENTS"):
            dpath = repo / d
            if dpath.exists():
                dirs_to_migrate.append(dpath)

    for dpath in dirs_to_migrate:
        for item in sorted(dpath.iterdir()):
            if not item.is_file() or not item.name.endswith(".md"):
                continue
            if is_excluded(item.name):
                continue
            result = migrate_file(item, dry_run=dry_run)
            results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Migration artefacts RSS-v1 -> RSS-v2")
    parser.add_argument("--repo", default=".", help="Chemin du repo")
    parser.add_argument("--type", choices=["PRD", "ADR", "EPIC", "SPEC", "INTENT"],
                        help="Type d'artefact a migrer (tous si omis)")
    parser.add_argument("--dry-run", action="store_true", help="Simulation")

    args = parser.parse_args()
    results = migrate_repo(args.repo, args.type, args.dry_run)

    migrated = sum(1 for r in results if r["status"] == "migrated")
    already = sum(1 for r in results if r["status"] == "already_conform")

    print(f"\n{'='*60}")
    print(f"Migration RSS-v1 -> RSS-v2 : {args.repo}")
    if args.type:
        print(f"Type: {args.type}")
    print(f"{'='*60}")
    print(f"Total fichiers: {len(results)}")
    print(f"Migres: {migrated}")
    print(f"Deja conformes: {already}")

    if args.dry_run:
        print(f"\n[DRY RUN] Exemples de changements :")
        for r in results[:15]:
            print(f"  {r['original_id']:30s} -> {r['normalized_id']:30s} ({r['normalized_status']})")


if __name__ == "__main__":
    main()
