#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ecos_propagate.py -- Propagation automatique RSS-v2 vers les repos citoyens.

Usage:
    python ecos_propagate.py --source REPO-STANDARDS --targets-root D:/DO/WEB --propagate citizens
    python ecos_propagate.py --source REPO-STANDARDS --targets-root D:/DO/WEB --propagate templates
    python ecos_propagate.py --source REPO-STANDARDS --targets-root D:/DO/WEB --audit rss --all
    python ecos_propagate.py --source REPO-STANDARDS --targets-root D:/DO/WEB --audit rss --repo BRAIN

Implémente les commandes :
    ecos propagate citizens.yaml  -> tous repos actifs
    ecos propagate templates       -> tous dérivés
    ecos audit rss --all           -> rapport global
    ecos audit rss --repo NOM     -> audit ciblé
"""

import argparse
import json
import os
import shutil
import sys
import io
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ajouter le répertoire scripts/ au path pour importer rss_lint
SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from rss_lint import (
    scan_repo, check_artifacts, check_profile_conformity,
    generate_repo_yaml, write_repo_yaml,
    _detect_profil, _detect_strate,
    REPO_YAML_PROFILES,
)

# Dépôts à exclure de la propagation (REPO-STANDARDS lui-même + gouvernance)
EXCLUDED_REPOS = {"REPO-STANDARDS", "GOVERNANCE-HUB", "ONTOLOGY", "TOPOS", "ECOYSTEM", "NEXUS", "LLM-REPO"}

# Fichiers à propager depuis REPO-STANDARDS
CITIZENS_SOURCE = "citizens.yaml"
TEMPLATES_SOURCE_DIR = "templates"


def find_repos(targets_root: str, include_archived: bool = False) -> list:
    """Découvre tous les repos git dans targets_root."""
    root = Path(targets_root)
    repos = []
    for item in sorted(root.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        if item.name in EXCLUDED_REPOS:
            continue
        git_dir = item / ".git"
        if not git_dir.exists():
            continue
        # Vérifier si c'est un repo gerivdb (a un remote gerivdb)
        repos.append(item)
    return repos


def propagate_citizens(source_repo: str, target_repo: str, dry_run: bool = False) -> dict:
    """Propage citizens.yaml du source vers le target, en adaptant le contenu."""
    source_path = Path(source_repo) / CITIZENS_SOURCE
    target_path = Path(target_repo) / CITIZENS_SOURCE

    if not source_path.exists():
        return {"status": "error", "error": f"Source {source_path} introuvable"}

    # Lire le citizens.yaml source
    content = source_path.read_text(encoding="utf-8")

    # Adapter le contenu : remplacer les références à REPO-STANDARDS par le nom du target
    repo_name = Path(target_repo).name
    adapted = content.replace("REPO-STANDARDS", repo_name)
    adapted = adapted.replace("<NOM>", repo_name)

    if dry_run:
        return {
            "status": "dry_run",
            "target": str(target_path),
            "action": "would_create" if not target_path.exists() else "would_update",
        }

    # Écrire le citizens.yaml adapté
    target_path.write_text(adapted, encoding="utf-8")
    return {
        "status": "ok",
        "target": str(target_path),
        "action": "created" if not target_path.exists() else "updated",
    }


def propagate_templates(source_repo: str, target_repo: str, dry_run: bool = False) -> dict:
    """Propose les templates du source vers le target (seulement si le target n'a pas de templates/)."""
    source_templates = Path(source_repo) / TEMPLATES_SOURCE_DIR
    target_templates = Path(target_repo) / TEMPLATES_SOURCE_DIR

    if not source_templates.exists():
        return {"status": "error", "error": f"Source templates {source_templates} introuvable"}

    if target_templates.exists():
        # Ne pas écraser les templates existants
        return {"status": "skipped", "reason": "templates already exist"}

    if dry_run:
        return {
            "status": "dry_run",
            "target": str(target_templates),
            "action": "would_copy_templates",
        }

    # Copier l'arborescence templates
    shutil.copytree(str(source_templates), str(target_templates))
    return {
        "status": "ok",
        "target": str(target_templates),
        "action": "copied",
    }


def audit_repo(repo_path: str) -> dict:
    """Audit complet d'un repo et retourne un rapport."""
    repo = Path(repo_path)
    name = repo.name

    report = {
        "repo": name,
        "path": str(repo),
        "strate": _detect_strate(repo_path),
        "profil": _detect_profil(repo_path),
        "timestamp": datetime.now().isoformat(),
    }

    # Scan structure
    violations = scan_repo(repo_path)
    report["structure"] = {
        "forbidden_root": len(violations["forbidden_root"]),
        "missing_dirs": violations["missing_dirs"],
        "depth_exceeded": len(violations["depth_exceeded"]),
    }

    # Profile conformity
    profile_v = check_profile_conformity(repo_path)
    report["profile"] = {
        "missing_dirs": profile_v["missing_dirs"],
        "forbidden_items": profile_v["forbidden_items"],
        "depth_exceeded": len(profile_v["depth_exceeded"]),
        "missing_files": profile_v["missing_files"],
        "crosslinks_violation": profile_v["crosslinks_violation"],
    }

    # Artifacts
    artifact_v = check_artifacts(repo_path)
    total_artifacts = sum(len(v) for v in artifact_v.values())
    report["artifacts"] = {
        "total_violations": total_artifacts,
        "naming": len(artifact_v["naming"]),
        "frontmatter": len(artifact_v["frontmatter"]),
        "duplicate_numbers": len(artifact_v["duplicate_numbers"]),
        "folder_canonical": len(artifact_v["folder_canonical"]),
        "index_sync": len(artifact_v["index_sync"]),
    }

    # Score de conformite
    total_violations = (
        report["structure"]["forbidden_root"] +
        len(report["structure"]["missing_dirs"]) +
        report["structure"]["depth_exceeded"] +
        len(report["profile"]["missing_dirs"]) +
        len(report["profile"]["forbidden_items"]) +
        len(report["profile"]["missing_files"]) +
        report["artifacts"]["total_violations"]
    )
    report["conformite"] = "PASS" if total_violations == 0 else "FAIL"
    report["total_violations"] = total_violations

    return report


def audit_all(repos_root: str) -> dict:
    """Audit tous les repos dans repos_root."""
    repos = find_repos(repos_root)
    results = {
        "timestamp": datetime.now().isoformat(),
        "repos_root": repos_root,
        "total_repos": len(repos),
        "repos": {},
        "summary": {
            "pass": 0,
            "fail": 0,
            "total_violations": 0,
        },
    }

    for repo in repos:
        name = repo.name
        try:
            report = audit_repo(str(repo))
            results["repos"][name] = report
            if report["conformite"] == "PASS":
                results["summary"]["pass"] += 1
            else:
                results["summary"]["fail"] += 1
            results["summary"]["total_violations"] += report["total_violations"]
        except Exception as e:
            results["repos"][name] = {"status": "error", "error": str(e)}
            results["summary"]["fail"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="ECOS propagate/audit RSS-v2")
    parser.add_argument("--source", default=".", help="Repo source (REPO-STANDARDS)")
    parser.add_argument("--targets-root", default="D:/DO/WEB", help="Racine des repos cibles")
    parser.add_argument("--propagate", choices=["citizens", "templates", "all"],
                        help="Type de propagation")
    parser.add_argument("--audit", choices=["rss", "all"],
                        help="Type d'audit")
    parser.add_argument("--repo", type=str, default=None,
                        help="Cibler un repo spécifique (nom)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mode dry-run (pas d'écriture)")
    parser.add_argument("--output", type=str, default=None,
                        help="Chemin du fichier de sortie JSON pour le rapport")
    parser.add_argument("--include-archived", action="store_true",
                        help="Inclure les repos archivés")

    args = parser.parse_args()

    source = Path(args.source).resolve()

    if args.propagate:
        # Mode propagation
        if args.repo:
            repos = [Path(args.targets_root) / args.repo]
        else:
            repos = find_repos(args.targets_root, include_archived=args.include_archived)

        print(f"\n{'='*60}")
        print(f"ECOS Propagate -- RSS-v2")
        print(f"Source: {source}")
        print(f"Targets: {len(repos)} repos")
        print(f"Type: {args.propagate}")
        if args.dry_run:
            print("[DRY RUN]")
        print(f"{'='*60}\n")

        success = 0
        skipped = 0
        errors = 0

        for repo in repos:
            name = repo.name
            if args.propagate in ("citizens", "all"):
                result = propagate_citizens(str(source), str(repo), dry_run=args.dry_run)
                status_icon = "✅" if result["status"] in ("ok", "dry_run") else "⏭️" if result["status"] == "skipped" else "❌"
                print(f"  {status_icon} {name}: {result['status']} ({result.get('action', result.get('reason', ''))})")
                if result["status"] == "ok":
                    success += 1
                elif result["status"] == "skipped":
                    skipped += 1
                else:
                    errors += 1

            if args.propagate in ("templates", "all"):
                result = propagate_templates(str(source), str(repo), dry_run=args.dry_run)
                status_icon = "✅" if result["status"] in ("ok", "dry_run") else "⏭️" if result["status"] == "skipped" else "❌"
                print(f"  {status_icon} {name}: templates {result['status']}")

        print(f"\nRésumé: {success} OK, {skipped} skipped, {errors} errors")

    elif args.audit:
        # Mode audit
        if args.repo:
            repo_path = Path(args.targets_root) / args.repo
            if not repo_path.exists():
                print(f"[ERROR] Repo introuvable: {repo_path}")
                sys.exit(1)
            report = audit_repo(str(repo_path))
            print(f"\n{'='*60}")
            print(f"ECOS Audit RSS-v2 -- {args.repo}")
            print(f"{'='*60}")
            print(f"  Strate: {report['strate']}")
            print(f"  Profil: {report['profil']}")
            print(f"  Conformité: {report['conformite']}")
            print(f"  Violations: {report['total_violations']}")
            if report["structure"]["missing_dirs"]:
                print(f"  Dossiers manquants: {', '.join(report['structure']['missing_dirs'])}")
            if report["profile"]["missing_files"]:
                print(f"  Fichiers requis manquants: {', '.join(report['profile']['missing_files'])}")
            if report["artifacts"]["total_violations"] > 0:
                print(f"  Artefacts: {report['artifacts']['total_violations']} violation(s)")
        else:
            print(f"\n{'='*60}")
            print(f"ECOS Audit RSS-v2 -- Tous repos")
            print(f"Racine: {args.targets_root}")
            print(f"{'='*60}\n")

            results = audit_all(args.targets_root)
            print(f"Total repos: {results['total_repos']}")
            print(f"PASS: {results['summary']['pass']}")
            print(f"FAIL: {results['summary']['fail']}")
            print(f"Violations totales: {results['summary']['total_violations']}")
            print()

            # Trier par nombre de violations (descending)
            sorted_repos = sorted(
                results["repos"].items(),
                key=lambda x: x[1].get("total_violations", 0) if isinstance(x[1], dict) else 0,
                reverse=True,
            )

            for name, report in sorted_repos:
                if not isinstance(report, dict):
                    continue
                violations = report.get("total_violations", 0)
                conf = report.get("conformite", "?")
                icon = "✅" if conf == "PASS" else "❌"
                print(f"  {icon} {name}: {conf} ({violations} violations)")

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"\nRapport sauvegardé: {args.output}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
