#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renumber_dupes.py -- Renumérotation des artefacts en double (F2)

Résout les doublons de numéros en renommant les fichiers les plus récents
avec des numéros disponibles.

Usage:
    python scripts/renumber_dupes.py --repo . --dry-run
    python scripts/renumber_dupes.py --repo .
"""

import argparse
import os
import re
import sys
from pathlib import Path


def find_dupes(repo_path):
    """Trouve les fichiers avec doublons de numéro."""
    dupes = {}
    for d in ("PRD", "ADR", "EPICS", "SPEC", "INTENTS"):
        dpath = Path(repo_path) / d
        if not dpath.exists():
            continue
        for f in sorted(dpath.iterdir()):
            if not f.name.endswith(".md"):
                continue
            m = re.match(r"(\w+)-(\d{3})-", f.name)
            if not m:
                continue
            atype = m.group(1).upper()
            num = int(m.group(2))
            if atype == "INTENT":
                atype = "INTENT"
            key = (atype, num)
            dupes.setdefault(key, []).append(f)
    return {k: v for k, v in dupes.items() if len(v) > 1}


def find_available_numbers(repo_path, atype, used_nums):
    """Trouve les numéros disponibles pour un type."""
    max_num = max(used_nums) if used_nums else 0
    return [i for i in range(1, max_num + 10) if i not in used_nums]


def renumber_file(filepath, new_num, dry_run=False):
    """Renomme un fichier avec un nouveau numéro et met à jour le frontmatter."""
    old_name = filepath.name
    # Extraire le type et le slug
    m = re.match(r"(\w+)-\d{3}-(.+)", old_name)
    if not m:
        return None
    atype = m.group(1)
    slug = m.group(2)
    new_name = f"{atype}-{new_num:03d}-{slug}"
    new_path = filepath.parent / new_name

    if dry_run:
        return {"old": old_name, "new": new_name, "status": "dry_run"}

    # Lire le contenu et mettre à jour le frontmatter
    content = filepath.read_text(encoding="utf-8")
    # Remplacer l'id dans le frontmatter
    content = re.sub(
        rf"^id:\s*{atype}-\d{{3}}",
        f"id: {atype}-{new_num:03d}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Écrire le nouveau fichier
    new_path.write_text(content, encoding="utf-8")
    # Supprimer l'ancien
    filepath.unlink()

    return {"old": old_name, "new": new_name, "status": "renamed"}


def main():
    parser = argparse.ArgumentParser(description="Renumérotation des doublons F2")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dupes = find_dupes(args.repo)
    if not dupes:
        print("Aucun doublon détecté.")
        return

    print(f"\n{'='*60}")
    print(f"Renumérotation doublons F2 : {args.repo}")
    print(f"{'='*60}")

    for (atype, num), files in sorted(dupes.items()):
        print(f"\n{atype}-{num:03d} ({len(files)} fichiers):")
        for f in sorted(files, key=lambda x: os.path.getmtime(x), reverse=True):
            marker = " (garde)" if f == sorted(files, key=lambda x: os.path.getmtime(x))[0] else " (renomme)"
            print(f"  {f.name}{marker}")

    if args.dry_run:
        print("\n[DRY RUN] Aucun changement effectué.")
        return

    # Effectuer les renommages
    for (atype, num), files in sorted(dupes.items()):
        # Trouver les numéros utilisés par ce type
        dpath = Path(args.repo) / (atype + "S" if atype == "EPIC" else atype + "S" if atype == "INTENT" else atype)
        used = set()
        for f in dpath.iterdir():
            m = re.match(rf"{atype}-(\d{3})-", f.name)
            if m:
                used.add(int(m.group(1)))

        available = find_available_numbers(args.repo, atype, used)

        # Trier par date de modification (le plus ancien garde son numéro)
        files_sorted = sorted(files, key=lambda x: os.path.getmtime(x))
        to_rename = files_sorted[1:]  # Tous sauf le premier

        for i, f in enumerate(to_rename):
            if i < len(available):
                result = renumber_file(f, available[i])
                if result:
                    print(f"  Renomme: {result['old']} -> {result['new']}")


if __name__ == "__main__":
    main()
