#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renumber_dupes_v2.py -- Renumérotation des artefacts en double (F2) - v2

Usage:
    python scripts/renumber_dupes_v2.py --repo . --dry-run
    python scripts/renumber_dupes_v2.py --repo .
"""

import os
import re
import sys
from pathlib import Path


def get_artifact_type(dirname):
    mapping = {"PRD": "PRD", "ADR": "ADR", "EPICS": "EPIC", "SPEC": "SPEC", "INTENTS": "INTENT"}
    return mapping.get(dirname, dirname)


def find_all_files(repo_path):
    """Retourne dict: (type, num) -> [files]"""
    result = {}
    for d in ("PRD", "ADR", "EPICS", "SPEC", "INTENTS"):
        dpath = Path(repo_path) / d
        if not dpath.exists():
            continue
        for f in sorted(dpath.iterdir()):
            if not f.name.endswith(".md") or "index" in f.name or "example" in f.name:
                continue
            m = re.match(r"(\w+)-(\d{3})-", f.name)
            if not m:
                continue
            atype = get_artifact_type(d)
            num = int(m.group(2))
            key = (atype, num)
            result.setdefault(key, []).append(f)
    return result


def find_used_numbers(files_dict, atype):
    """Retourne l'ensemble des numéros utilisés pour un type."""
    used = set()
    for (t, num) in files_dict:
        if t == atype:
            used.add(num)
    return used


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files_dict = find_all_files(args.repo)

    # Trouver les doublons
    dupes = {k: v for k, v in files_dict.items() if len(v) > 1}
    if not dupes:
        print("Aucun doublon.")
        return

    print(f"\nDoublons detectes : {len(dupes)} groupes\n")

    for (atype, num), files in sorted(dupes.items()):
        print(f"  {atype}-{num:03d} ({len(files)} fichiers):")
        for f in sorted(files, key=lambda x: os.path.getmtime(x)):
            print(f"    - {f.name}")

    if args.dry_run:
        print("\n[DRY RUN]")
        return

    # Pour chaque groupe de doublons, garder le plus ancien, renommer les autres
    renamed = []
    for (atype, num), files in sorted(dupes.items()):
        # Trier par date de modification (plus ancien en premier)
        files_sorted = sorted(files, key=lambda x: os.path.getmtime(x))
        keeper = files_sorted[0]
        to_rename = files_sorted[1:]

        # Trouver les numéros disponibles
        used = find_used_numbers(files_dict, atype)
        available = sorted(set(range(1, max(used) + 10)) - used)

        print(f"\n{atype}-{num:03d}:")
        print(f"  Garde: {keeper.name}")

        for i, f in enumerate(to_rename):
            if i >= len(available):
                print(f"  ERREUR: Plus de numero disponible pour {f.name}")
                continue
            new_num = available[i]

            # Construire le nouveau nom
            old_name = f.name
            m = re.match(r"\w+-\d{3}-(.+)", old_name)
            slug = m.group(1) if m else old_name
            new_name = f"{atype}-{new_num:03d}-{slug}"
            new_path = f.parent / new_name

            # Mettre a jour le frontmatter et renommer
            content = f.read_text(encoding="utf-8")
            content = re.sub(
                rf"^id:\s*{atype}-\d{{3}}",
                f"id: {atype}-{new_num:03d}",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            # Mettre a jour aussi le titre si contient l'ancien numéro
            content = re.sub(
                rf"^#\s+{atype}-\d{{3}}\s*[—–-]",
                f"# {atype}-{new_num:03d} —",
                content,
                count=1,
                flags=re.MULTILINE,
            )

            new_path.write_text(content, encoding="utf-8")
            f.unlink()
            renamed.append((old_name, new_name))
            print(f"  Renomme: {old_name} -> {new_name}")

    print(f"\nTotal: {len(renamed)} fichiers renommes.")


if __name__ == "__main__":
    main()
