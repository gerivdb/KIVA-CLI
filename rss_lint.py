#!/usr/bin/env python3
"""
rss_lint.py — Gate de conformité RSS-v2 pour les repos gerivdb.

Usage:
    python rss_lint.py --repo <path> [--fix] [--strict] [--depth 2|4]

Vérifie qu'un repo respecte le Repo Structure Standard v2.
Gère deux profondeurs : 2 niveaux (repos simples) ou 4 niveaux (repos complexes).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ── Règles RSS-v2 ──

# Fichiers autorisés à la racine (communs aux deux profondeurs)
ROOT_ALLOWED = {
    "README.md", "CHANGELOG.md", ".gitignore", "pyproject.toml",
    "package.json", "package-lock.json", "Makefile", "LICENSE",
    "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
    "MANIFEST.in", "setup.py", "setup.cfg", "tox.ini", "Dockerfile",
    "docker-compose.yml", ".env.example", "conftest.py", "ECOSROOT.json",
    "requirements.txt", "requirements-test.txt",
}

# Fichiers autorisés à la racine UNIQUEMENT pour repos simples (depth=2)
ROOT_ALLOWED_SIMPLE_ONLY = {
    "requirements_lxc_env2.txt", "requirements_matrix_recoupement.txt",
    "requirements_nexus_ontology_api.txt",
}

# Patterns de fichiers interdits à la racine → destination
ROOT_FORBIDDEN_PATTERNS = [
    (r"^EPIC-.*\.md$", "EPICS/"),
    (r"^\.github_EPICS_EPIC-.*\.md$", "EPICS/"),
    (r"^PRD[-_].*\.md$", "PRD/"),
    (r"^ADR-.*\.md$", "ADR/"),
    (r"^test_.*\.py$", "tests/"),
    (r".*_test\.py$", "tests/"),
    (r"^trit_.*\.py$", "engines/trit/"),
    (r".*_primitives\.py$", "src/primitives/"),
    (r"^validate_.*\.py$", "tests/"),
    (r"^deploy_.*\.ps1$", "scripts/"),
    (r"^batch_report\.", ".gitignore"),
    (r"^integration_test_report\.", "config/reports/"),
    (r"^traceability_report\.", "config/reports/"),
    (r"^\.coverage$", ".gitignore"),
    (r".*__pycache__.*", ".gitignore"),
]

# Dossiers obligatoires — repos simples (depth=2)
REQUIRED_DIRS_SIMPLE = ["docs/", "tests/"]

# Dossiers obligatoires — repos complexes (depth=4)
REQUIRED_DIRS_COMPLEX = ["docs/", "tests/", "config/"]

# Sous-dossiers config/ recommandés pour repos complexes
CONFIG_SUBDIRS = [
    "archives/", "databases/", "epics/", "ontology/",
    "phase-logs/", "registries/", "reports/",
]

# Patterns pour détecter les artefacts de run
ARTEFACT_PATTERNS = [
    r"^\.coverage$",
    r"^batch_report\.",
    r"^integration_test_report\.",
    r"^traceability_report\.",
    r"^AUDITREPORT\.",
    r".*__pycache__.*",
]


def get_depth(repo_path: Path) -> int:
    """Détermine la profondeur du repo en scannant la structure existante."""
    max_depth = 0
    for item in repo_path.rglob("*"):
        if item.is_dir():
            # Ignorer les dossiers internes (git, node_modules, IDE, etc.)
            rel = item.relative_to(repo_path)
            parts = rel.parts
            if parts[0].startswith(".git") or parts[0].startswith(".kilo") or \
               parts[0] in ("node_modules", ".venv", "__pycache__"):
                continue
            depth = len(parts)
            if depth > max_depth:
                max_depth = depth
    # Si le repo a déjà 3+ niveaux, c'est un repo complexe
    return 4 if max_depth >= 3 else 2


def scan_repo(repo_path: str, depth: int = None) -> dict:
    """Scan un repo et retourne les violations."""
    repo = Path(repo_path)
    if not repo.exists():
        print(f"[ERROR] Repo introuvable: {repo_path}")
        sys.exit(1)

    # Auto-détecter la profondeur si non spécifiée
    if depth is None:
        depth = get_depth(repo)

    violations = {
        "forbidden_root": [],
        "missing_dirs": [],
        "artefacts": [],
        "depth_exceeded": [],
        "config_misplaced": [],
    }

    # Scanner la racine
    for item in repo.iterdir():
        if item.is_file():
            name = item.name

            # Vérifier si le fichier est autorisé à la racine
            if name in ROOT_ALLOWED:
                continue
            if depth == 2 and name in ROOT_ALLOWED_SIMPLE_ONLY:
                continue

            # Vérifier les patterns interdits
            matched = False
            for pattern, destination in ROOT_FORBIDDEN_PATTERNS:
                if re.match(pattern, name, re.IGNORECASE):
                    violations["forbidden_root"].append({
                        "file": name,
                        "destination": destination,
                    })
                    matched = True
                    break

            # Détecter les artefacts de run
            for pattern in ARTEFACT_PATTERNS:
                if re.match(pattern, name, re.IGNORECASE):
                    violations["artefacts"].append(name)
                    break

        elif item.is_dir() and item.name == "__pycache__":
            violations["artefacts"].append("__pycache__/")
        # Ignorer .git, .kilo, .kilocode, node_modules à la racine
        elif item.is_dir() and (item.name.startswith(".git") or item.name.startswith(".kilo") or
                                  item.name in ("node_modules", ".venv")):
            continue

    # Vérifier les dossiers obligatoires
    required = REQUIRED_DIRS_COMPLEX if depth == 4 else REQUIRED_DIRS_SIMPLE
    for required_dir in required:
        if not (repo / required_dir).exists():
            violations["missing_dirs"].append(required_dir)

    # Vérifier la profondeur des sous-dossiers (en ignorant les dossiers internes)
    for item in repo.rglob("*"):
        if item.is_dir():
            rel = item.relative_to(repo_path)
            parts = rel.parts
            # Ignorer les dossiers internes (git, node_modules, IDE, etc.)
            rel = item.relative_to(repo_path)
            parts = rel.parts
            if parts[0].startswith(".git") or parts[0].startswith(".kilo") or \
               parts[0] in ("node_modules", ".venv", "__pycache__", "temp_skills"):
                continue
            current_depth = len(parts)
            if current_depth > depth:
                violations["depth_exceeded"].append({
                    "path": str(rel),
                    "depth": current_depth,
                    "max": depth,
                })

    # Pour les repos complexes : vérifier que les fichiers de config/ ne sont pas à la racine
    if depth == 4:
        config_patterns = [
            (r".*_report\.json$", "config/reports/"),
            (r".*_results\.json$", "config/reports/"),
            (r".*_analysis\.json$", "config/reports/"),
            (r".*_registry\.json$", "config/registries/"),
            (r".*_config\.json$", "config/"),
            (r".*_state\.json$", "config/"),
            (r".*\.db$", "config/databases/"),
            (r".*\.duckdb$", "config/databases/"),
            (r".*\.pkl$", "config/databases/"),
            (r".*\.pdf$", "config/archives/"),
            (r".*\.zip$", "config/archives/"),
            (r".*\.exe$", "config/archives/"),
            (r".*\.whl$", "config/archives/"),
            (r".*\.bak$", "config/archives/"),
            (r".*\.patch$", "config/archives/"),
            (r".*\.emoji_backup$", "config/archives/"),
            (r".*\.log$", "config/archives/"),
            (r".*\.csv$", "config/archives/"),
            (r".*\.jsonl$", "config/archives/"),
            (r".*\.markdown$", "config/archives/"),
            (r".*\.txt$", "config/archives/"),
        ]
        for item in repo.iterdir():
            if item.is_file() and item.name not in ROOT_ALLOWED:
                for pattern, dest in config_patterns:
                    if re.match(pattern, item.name, re.IGNORECASE):
                        violations["config_misplaced"].append({
                            "file": item.name,
                            "destination": dest,
                        })
                        break

    return violations


def check_git_noise(repo_path: str, repo_type: str = "default") -> dict:
    """Vérifie le bruit git (fichiers untracked après .gitignore).

    Retourne un dict avec le compte et le seuil applicable.
    Les seuils sont alignés sur BRANCH-CHECK.yaml variables.git_noise.
    """
    thresholds = {
        "core": 50, "cli": 50, "mcp": 50, "tool": 200,
        "infra": 100, "plugin": 50, "docs": 500, "default": 100,
    }
    fail_multipliers = {
        "core": 10, "cli": 10, "mcp": 10, "tool": 10,
        "infra": 5, "plugin": 10, "docs": 10, "default": 10,
    }

    warn_threshold = thresholds.get(repo_type, thresholds["default"])
    fail_threshold = warn_threshold * fail_multipliers.get(repo_type, 10)

    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, cwd=repo_path
        )
        files = [f for f in result.stdout.strip().split("\n") if f.strip()]
        count = len(files)
    except (subprocess.SubprocessError, FileNotFoundError):
        return {"count": -1, "warn_threshold": warn_threshold,
                "fail_threshold": fail_threshold, "files": [], "error": "git not available"}

    return {
        "count": count,
        "warn_threshold": warn_threshold,
        "fail_threshold": fail_threshold,
        "files": files[:20],  # Échantillon pour le rapport
        "severity": (
            "FAIL" if count > fail_threshold else
            "WARN" if count > warn_threshold else
            "PASS"
        ),
    }


def check_gitignore_coverage(repo_path: str, repo_type: str = "default") -> dict:
    """Vérifie que le .gitignore contient les patterns requis.

    Les patterns requis sont alignés sur BRANCH-CHECK.yaml global.branch_content.gitignore_coverage.
    """
    gitignore_path = Path(repo_path) / ".gitignore"
    if not gitignore_path.exists():
        return {"missing": ["ALL"], "severity": "FAIL", "error": ".gitignore not found"}

    content = gitignore_path.read_text(encoding="utf-8")

    # Patterns obligatoires globaux
    required = [
        "__pycache__/", "*.py[cod]", ".DS_Store", "Thumbs.db",
        "*.egg-info/", "build/", "dist/", "*.so",
    ]
    # Patterns obligatoires par type
    required_by_type = {
        "tool": ["bin/portable/", "git/", "*.exe", "*.dll"],
        "infra": ["*.log", "*.tmp", "tmp/"],
    }

    missing = []
    for pattern in required:
        # Vérifier si le pattern ou une variante est présent
        pattern_base = pattern.rstrip("/").lstrip("*")
        if pattern_base and pattern_base not in content:
            missing.append(pattern)

    for pattern in required_by_type.get(repo_type, []):
        pattern_base = pattern.rstrip("/").lstrip("*")
        if pattern_base and pattern_base not in content:
            missing.append(pattern)

    return {
        "missing": missing,
        "severity": "FAIL" if len(missing) > 2 else "WARN" if missing else "PASS",
    }


def check_filesystem_integrity(repo_path: str) -> dict:
    """Vérifie l'intégrité du filesystem (junctions NTFS, dossiers vides, fichiers orphelins).

    Aligné sur BRANCH-CHECK.yaml global.branch_content.filesystem.
    """
    repo = Path(repo_path)
    junctions = []
    empty_dirs = []
    orphan_files = []

    # Détecter les junctions NTFS (Windows)
    try:
        result = subprocess.run(
            ["cmd", "/c", "dir", "/a:l", "/s", "/b"],
            capture_output=True, text=True, cwd=repo_path
        )
        junctions = [j.strip() for j in result.stdout.strip().split("\n") if j.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Détecter les dossiers vides non-trackés
    for item in repo.rglob("*"):
        if item.is_dir():
            rel = item.relative_to(repo)
            parts = rel.parts
            # Ignorer .git et dossiers internes
            if parts[0].startswith(".git") or parts[0].startswith(".kilo") or \
               parts[0] in ("node_modules", ".venv", "__pycache__"):
                continue
            # Vérifier si vide
            try:
                if not any(item.iterdir()):
                    empty_dirs.append(str(rel))
            except PermissionError:
                pass

    # Détecter les fichiers orphelins (trackés par git mais absents du disque)
    try:
        result = subprocess.run(
            ["git", "ls-files", "--deleted"],
            capture_output=True, text=True, cwd=repo_path
        )
        orphan_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return {
        "junctions": junctions,
        "junction_count": len(junctions),
        "empty_dirs": empty_dirs[:20],  # Échantillon
        "empty_dir_count": len(empty_dirs),
        "orphan_files": orphan_files,
        "orphan_count": len(orphan_files),
        "severity": (
            "FAIL" if orphan_files else
            "WARN" if len(junctions) > 10 or empty_dirs else
            "PASS"
        ),
    }


def fix_violations(repo_path: str, violations: dict, depth: int) -> int:
    """Corrige automatiquement les violations. Retourne le nombre de corrections."""
    repo = Path(repo_path)
    fixed = 0

    # Créer les dossiers manquants
    for missing_dir in violations["missing_dirs"]:
        (repo / missing_dir).mkdir(parents=True, exist_ok=True)
        print(f"  [FIX] Créé: {missing_dir}")
        fixed += 1

    # Déplacer les fichiers interdits à la racine
    for violation in violations["forbidden_root"]:
        src = repo / violation["file"]
        dest_dir = repo / violation["destination"]

        if src.exists():
            if violation["destination"] == ".gitignore":
                continue  # Traité par la section artefacts

            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / violation["file"]

            if dest.exists():
                print(f"  [SKIP] Destination existe déjà: {dest}")
            else:
                shutil.move(str(src), str(dest))
                print(f"  [FIX] Déplacé: {violation['file']} -> {violation['destination']}")
                fixed += 1

    # Déplacer les fichiers de config/ mal placés (repos complexes)
    for violation in violations["config_misplaced"]:
        src = repo / violation["file"]
        dest_dir = repo / violation["destination"]

        if src.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / violation["file"]

            if dest.exists():
                print(f"  [SKIP] Destination existe déjà: {dest}")
            else:
                shutil.move(str(src), str(dest))
                print(f"  [FIX] Déplacé: {violation['file']} -> {violation['destination']}")
                fixed += 1

    # Ajouter les artefacts au .gitignore
    if violations["artefacts"]:
        gitignore = repo / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""

        additions = []
        for artefact in violations["artefacts"]:
            if artefact.endswith("/"):
                artefact = artefact[:-1]
            if artefact not in existing:
                additions.append(artefact)

        if additions:
            with open(gitignore, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("\n# RSS-v2 — Artefacts de run (auto-ajouté)\n")
                for a in additions:
                    f.write(f"{a}\n")
            print(f"  [FIX] Ajouté au .gitignore: {', '.join(additions)}")
            fixed += len(additions)

    return fixed


def main():
    parser = argparse.ArgumentParser(description="RSS-v2 — Gate de conformite")
    parser.add_argument("--repo", required=True, help="Chemin du repo a verifier")
    parser.add_argument("--fix", action="store_true", help="Corriger automatiquement")
    parser.add_argument("--strict", action="store_true", help="Mode strict (WARN = FAIL)")
    parser.add_argument("--depth", type=int, choices=[2, 4], default=None,
                        help="Profondeur max (2=simple, 4=complexe). Auto-detecte si omis.")
    parser.add_argument("--check-git-noise", action="store_true",
                        help="Verifier le bruit git (fichiers untracks apres .gitignore)")
    parser.add_argument("--check-gitignore", action="store_true",
                        help="Verifier la couverture du .gitignore")
    parser.add_argument("--check-filesystem", action="store_true",
                        help="Verifier l'integrite du filesystem (junctions, orphelins)")
    parser.add_argument("--repo-type", type=str, default="default",
                        choices=["core", "cli", "mcp", "docs", "plugin", "tool", "infra", "default"],
                        help="Type de repo pour les seuils git noise (defaut: default)")
    parser.add_argument("--all-checks", action="store_true",
                        help="Activer toutes les verifications (git noise, gitignore, filesystem)")
    parser.add_argument("--check-artifacts", action="store_true",
                        help="Verifier la conformite des artefacts de gouvernance (PRD, ADR, EPIC, SPEC)")
    parser.add_argument("--index", choices=["rebuild"], default=None,
                        help="Reconstruire les index d'artefacts")
    parser.add_argument("--artifact-dir", type=str, default=None,
                        help="Dossier d'artefact cible pour --index (PRD, ADR, EPICS, SPEC). Tous si omis.")

    args = parser.parse_args()

    # --all-checks active tous les checks
    if args.all_checks:
        args.check_git_noise = True
        args.check_gitignore = True
        args.check_filesystem = True
        args.check_artifacts = True

    # Auto-detecter la profondeur
    depth = args.depth or get_depth(Path(args.repo))

    print(f"\n{'='*60}")
    print(f"RSS-v2 — Gate de conformite")
    print(f"Repo: {args.repo}")
    print(f"Profondeur: {depth} niveaux")
    if args.repo_type != "default":
        print(f"Type: {args.repo_type}")
    print(f"{'='*60}\n")

    # ── Index rebuild ──
    if args.index == "rebuild":
        dirs_to_rebuild = [args.artifact_dir] if args.artifact_dir else list(ARTIFACT_DIRS)
        for d in dirs_to_rebuild:
            if rebuild_index(args.repo, d):
                print(f"  [OK] Index reconstruit: {d}/{ARTIFACT_INDEX_FILES.get(d.rstrip('S'), 'N/A')}")
            else:
                print(f"  [SKIP] Dossier inexistant ou type non supporte: {d}")
        sys.exit(0)

    violations = scan_repo(args.repo, depth)

    total_violations = (
        len(violations["forbidden_root"]) +
        len(violations["missing_dirs"]) +
        len(violations["artefacts"]) +
        len(violations["depth_exceeded"]) +
        len(violations["config_misplaced"])
    )

    # ── Git Noise Check ──
    git_noise_result = None
    if args.check_git_noise:
        git_noise_result = check_git_noise(args.repo, args.repo_type)
        severity = git_noise_result.get("severity", "PASS")
        count = git_noise_result.get("count", 0)
        warn_t = git_noise_result.get("warn_threshold", 100)
        fail_t = git_noise_result.get("fail_threshold", 500)

        if severity == "FAIL":
            print(f"[FAIL] Git noise: {count} untracked files (seuil FAIL: {fail_t})")
        elif severity == "WARN":
            print(f"[WARN] Git noise: {count} untracked files (seuil WARN: {warn_t})")
        else:
            print(f"[PASS] Git noise: {count} untracked files (seuil OK: <{warn_t})")

        if git_noise_result.get("files"):
            for f in git_noise_result["files"][:5]:
                print(f"   {f}")
            if count > 5:
                print(f"   ... et {count - 5} autres")

    # ── Gitignore Coverage Check ──
    gitignore_result = None
    if args.check_gitignore:
        gitignore_result = check_gitignore_coverage(args.repo, args.repo_type)
        severity = gitignore_result.get("severity", "PASS")
        missing = gitignore_result.get("missing", [])

        if severity == "FAIL":
            print(f"[FAIL] .gitignore coverage: {len(missing)} patterns manquants")
        elif severity == "WARN":
            print(f"[WARN] .gitignore coverage: {len(missing)} patterns manquants")
        else:
            print(f"[PASS] .gitignore coverage: tous les patterns requis sont présents")

        for m in missing:
            print(f"   manquant: {m}")

    # ── Filesystem Integrity Check ──
    fs_result = None
    if args.check_filesystem:
        fs_result = check_filesystem_integrity(args.repo)
        severity = fs_result.get("severity", "PASS")

        if severity == "FAIL":
            print(f"[FAIL] Filesystem: {fs_result['orphan_count']} fichiers orphelins")
        elif severity == "WARN":
            print(f"[WARN] Filesystem: {fs_result['junction_count']} junctions, {fs_result['empty_dir_count']} dossiers vides")
        else:
            print(f"[PASS] Filesystem: intégrité OK ({fs_result['junction_count']} junctions, {fs_result['orphan_count']} orphelins)")

        if fs_result.get("junctions"):
            for j in fs_result["junctions"][:5]:
                print(f"   junction: {j}")
        if fs_result.get("orphan_files"):
            for o in fs_result["orphan_files"][:5]:
                print(f"   orphelin: {o}")

    # ── Artifact Policy Check (PRD-001) ──
    artifact_violations = None
    if args.check_artifacts:
        artifact_violations = check_artifacts(args.repo)
        artifact_total = (
            len(artifact_violations["naming"]) +
            len(artifact_violations["frontmatter"]) +
            len(artifact_violations["index_missing"]) +
            len(artifact_violations["mirrors"]) +
            len(artifact_violations["stubs"]) +
            len(artifact_violations["status"])
        )

        if artifact_total == 0:
            print("[PASS] Artefacts de gouvernance: conformes RSS-v2")
        else:
            if artifact_violations["naming"]:
                print(f"[FAIL] Nommage artefacts ({len(artifact_violations['naming'])}):")
                for v in artifact_violations["naming"]:
                    print(f"   {v['file']} -> attendu: {v['pattern']}")
            if artifact_violations["frontmatter"]:
                print(f"[FAIL] Frontmatter artefacts ({len(artifact_violations['frontmatter'])}):")
                for v in artifact_violations["frontmatter"]:
                    print(f"   {v['file']}: {v['error']}")
            if artifact_violations["index_missing"]:
                print(f"[FAIL] Index manquants ({len(artifact_violations['index_missing'])}):")
                for v in artifact_violations["index_missing"]:
                    print(f"   {v['dir']}/{v['expected']}")
            if artifact_violations["mirrors"]:
                print(f"[FAIL] Mirrors non declares ({len(artifact_violations['mirrors'])}):")
                for v in artifact_violations["mirrors"]:
                    print(f"   {v['file']}: {v['error']}")
            if artifact_violations["stubs"]:
                print(f"[FAIL] Stubs superseded invalides ({len(artifact_violations['stubs'])}):")
                for v in artifact_violations["stubs"]:
                    print(f"   {v['file']}: {v['error']}")
            if artifact_violations["status"]:
                print(f"[FAIL] Statuts invalides ({len(artifact_violations['status'])}):")
                for v in artifact_violations["status"]:
                    print(f"   {v['file']}: '{v['status']}' → attendu: {v['valid']}")

        # Fix artefacts simples
        if args.fix and artifact_total > 0:
            print(f"\nCorrection automatique artefacts...")
            fixed = fix_artifacts(args.repo, artifact_violations)
            print(f"{fixed} correction(s) appliquee(s)")

    # ── Standard RSS-v2 violations ──
    if total_violations == 0 and not any([
        git_noise_result and git_noise_result.get("severity") == "FAIL",
        gitignore_result and gitignore_result.get("severity") == "FAIL",
        fs_result and fs_result.get("severity") == "FAIL",
    ]) and (artifact_violations is None or (
        len(artifact_violations["naming"]) == 0 and
        len(artifact_violations["frontmatter"]) == 0 and
        len(artifact_violations["index_missing"]) == 0 and
        len(artifact_violations["mirrors"]) == 0 and
        len(artifact_violations["stubs"]) == 0 and
        len(artifact_violations["status"]) == 0
    )):
        # Verifier aussi les WARN
        has_warns = any([
            git_noise_result and git_noise_result.get("severity") == "WARN",
            gitignore_result and gitignore_result.get("severity") == "WARN",
            fs_result and fs_result.get("severity") == "WARN",
        ])
        if not has_warns or not args.strict:
            print("[PASS] Repo conforme RSS-v2")
            sys.exit(0)

    if total_violations == 0 and not args.check_git_noise and not args.check_gitignore and not args.check_filesystem and not args.check_artifacts:
        print("[PASS] Repo conforme RSS-v2")
        sys.exit(0)

    # Afficher les violations RSS-v2 standard
    if violations["forbidden_root"]:
        print(f"[FAIL] Fichiers interdits à la racine ({len(violations['forbidden_root'])}):")
        for v in violations["forbidden_root"]:
            print(f"   {v['file']} → devrait être dans {v['destination']}")

    if violations["missing_dirs"]:
        print(f"[FAIL] Dossiers obligatoires manquants ({len(violations['missing_dirs'])}):")
        for d in violations["missing_dirs"]:
            print(f"   {d}")

    if violations["artefacts"]:
        print(f"[FAIL] Artefacts de run ({len(violations['artefacts'])}):")
        for a in violations["artefacts"]:
            print(f"   {a}")

    if violations["depth_exceeded"]:
        print(f"[FAIL] Profondeur dépassée ({len(violations['depth_exceeded'])}):")
        for v in violations["depth_exceeded"]:
            print(f"   {v['path']} (profondeur {v['depth']} > max {v['max']})")

    if violations["config_misplaced"]:
        print(f"[WARN] Fichiers de config à la racine ({len(violations['config_misplaced'])}):")
        for v in violations["config_misplaced"]:
            print(f"   {v['file']} -> suggere: {v['destination']}")

    # Corriger si demandé
    if args.fix:
        print(f"\nCorrection automatique...")
        fixed = fix_violations(args.repo, violations, depth)
        print(f"\n{fixed} correction(s) appliquée(s)")
    elif total_violations > 0:
        print(f"\n{total_violations} violation(s) détectée(s)")
        print(f"   Utilisez --fix pour corriger automatiquement")

    # Determiner le statut final
    artifact_failures = (
        artifact_violations is not None and (
            len(artifact_violations["naming"]) > 0 or
            len(artifact_violations["frontmatter"]) > 0 or
            len(artifact_violations["index_missing"]) > 0 or
            len(artifact_violations["mirrors"]) > 0 or
            len(artifact_violations["stubs"]) > 0 or
            len(artifact_violations["status"]) > 0
        )
    )

    has_failures = (
        len(violations["forbidden_root"]) > 0 or
        len(violations["missing_dirs"]) > 0 or
        len(violations["artefacts"]) > 0 or
        len(violations["depth_exceeded"]) > 0 or
        (git_noise_result and git_noise_result.get("severity") == "FAIL") or
        (gitignore_result and gitignore_result.get("severity") == "FAIL") or
        (fs_result and fs_result.get("severity") == "FAIL") or
        artifact_failures
    )

    has_warns = (
        len(violations["config_misplaced"]) > 0 or
        (git_noise_result and git_noise_result.get("severity") == "WARN") or
        (gitignore_result and gitignore_result.get("severity") == "WARN") or
        (fs_result and fs_result.get("severity") == "WARN")
    )

    if has_failures or (args.strict and has_warns):
        print(f"\n[FAIL] Repo non conforme RSS-v2")
        sys.exit(1)
    elif has_warns:
        print(f"\n[WARN] Violations mineures — repo fonctionnel mais non standardise")
        sys.exit(0)
    else:
        print(f"\n[PASS] Repo conforme RSS-v2")
        sys.exit(0)


# ── RSS-v2 Artifact Policy (PRD-001) ──

import yaml as _yaml

# Patterns de nommage par type d'artefact
ARTIFACT_NAMING = {
    "PRD":  re.compile(r"^PRD-\d{3}-[a-z0-9][a-z0-9-]*\.md$"),
    "ADR":  re.compile(r"^ADR-\d{3}-[a-z0-9][a-z0-9-]*\.md$"),
    "EPIC": re.compile(r"^EPIC-\d{3}-[a-z0-9][a-z0-9-]*\.md$"),
    "SPEC": re.compile(r"^SPEC-\d{3}-[a-z0-9][a-z0-9-]*\.md$"),
}

# Statuts valides par type
ARTIFACT_STATUSES = {
    "PRD":  {"draft", "active", "deprecated", "superseded"},
    "ADR":  {"proposed", "accepted", "deprecated", "superseded"},
    "EPIC": {"draft", "active", "done", "deprecated", "superseded"},
    "SPEC": {"draft", "stable", "deprecated", "superseded"},
}

# Champs frontmatter obligatoires (noyau commun)
FRONTMATTER_CORE_FIELDS = {"id", "title", "repo", "status", "created", "author"}

# Champs additionnels par type
FRONTMATTER_OPTIONAL_FIELDS = {
    "PRD":  {"intent_hash", "superseded_by", "source_repo", "source_path", "updated"},
    "ADR":  {"intent_hash", "superseded_by", "source_repo", "source_path", "updated"},
    "EPIC": {"intent_hash", "superseded_by", "updated"},
    "SPEC": {"intent_hash", "superseded_by", "source_repo", "source_path", "updated"},
}

# Index reserves
ARTIFACT_INDEX_FILES = {
    "PRD":  "PRD-000-index.md",
    "ADR":  "ADR-000-index.md",
    "EPIC": "EPIC-000-index.md",
}

# Dossiers d'artefacts
ARTIFACT_DIRS = {"PRD", "ADR", "EPICS", "SPEC", "INTENTS"}


def _parse_frontmatter(content: str) -> dict:
    """Extrait le frontmatter YAML d'un fichier markdown."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        return _yaml.safe_load(content[3:end]) or {}
    except _yaml.YAMLError:
        return {}


def _is_stub_superseded(content: str) -> bool:
    """Detecte si un fichier est un stub superseded (3 lignes max apres frontmatter)."""
    if not content.startswith("---"):
        return False
    end = content.find("---", 3)
    if end == -1:
        return False
    body = content[end + 3:].strip()
    lines = [l for l in body.split("\n") if l.strip()]
    return len(lines) <= 3


def check_artifacts(repo_path: str) -> dict:
    """Verifie la conformite des artefacts de gouvernance (PRD, ADR, EPIC, SPEC)."""
    repo = Path(repo_path)
    violations = {
        "naming": [],       # Fichiers mal nommes
        "frontmatter": [],  # Frontmatter manquant ou incomplet
        "index_missing": [],# Index reserves manquants
        "mirrors": [],      # Mirrors sans source_repo/source_path
        "stubs": [],        # Fichiers superseded qui ne sont pas des stubs
        "status": [],       # Statut invalide pour le type
    }

    for artifact_dir_name in ARTIFACT_DIRS:
        artifact_dir = repo / artifact_dir_name
        if not artifact_dir.exists():
            continue

        # Normaliser le type (EPICS/ -> EPIC)
        artifact_type = artifact_dir_name.rstrip("S")
        if artifact_type not in ARTIFACT_NAMING:
            continue

        naming_pattern = ARTIFACT_NAMING[artifact_type]
        valid_statuses = ARTIFACT_STATUSES[artifact_type]
        index_file = ARTIFACT_INDEX_FILES.get(artifact_type)

        # Verifier l'index
        if index_file and not (artifact_dir / index_file).exists():
            violations["index_missing"].append({
                "dir": artifact_dir_name,
                "expected": index_file,
            })

        # Scanner les fichiers du dossier
        for item in artifact_dir.iterdir():
            if not item.is_file() or item.name.startswith("."):
                continue
            if item.name == index_file:
                continue

            fname = item.name

            # 1. Check nommage
            if not naming_pattern.match(fname):
                violations["naming"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "pattern": naming_pattern.pattern,
                })
                continue  # Pas la peine de verifier le frontmatter si le nom est faux

            # 2. Check frontmatter
            content = item.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)

            if not fm:
                violations["frontmatter"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "error": "frontmatter manquant",
                })
                continue

            missing_fields = FRONTMATTER_CORE_FIELDS - set(fm.keys())
            if missing_fields:
                violations["frontmatter"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "error": f"champs manquants: {', '.join(sorted(missing_fields))}",
                })
                continue

            # 3. Check statut
            status = fm.get("status", "")
            if status and valid_statuses and status not in valid_statuses:
                violations["status"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "status": status,
                    "valid": ", ".join(sorted(valid_statuses)),
                })

            # 4. Check stub superseded
            if status == "superseded" and not _is_stub_superseded(content):
                violations["stubs"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "error": "fichier superseded qui n'est pas un stub",
                })

            # 5. Check mirrors (si source_repo != repo name)
            source_repo = fm.get("source_repo")
            if source_repo and not fm.get("source_path"):
                violations["mirrors"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "error": "source_repo present mais source_path manquant",
                })

    return violations


def fix_artifacts(repo_path: str, violations: dict) -> int:
    """Corrige automatiquement les violations artefacts simples. Retourne le nombre de corrections."""
    repo = Path(repo_path)
    fixed = 0

    # Creer les index manquants
    for v in violations.get("index_missing", []):
        artifact_dir = repo / v["dir"]
        index_path = artifact_dir / v["expected"]
        if not index_path.exists():
            # Generer un index minimal
            lines = [
                f"# {v['expected']} — Index des {v['dir']} de ce repo",
                "",
                "> Index genere automatiquement. Ne pas editer a la main.",
                f"> Pour regenerer : `python rss_lint.py --repo . --index rebuild`",
                "",
                "## Actifs",
                "",
                "| ID | Fichier | Titre | Statut | Date |",
                "|----|---------|-------|--------|------|",
                "",
                "## Archives",
                "",
                "*Aucun artefact archive pour le moment.*",
                "",
                "",
                f"*Derniere mise a jour : auto-genere*",
            ]
            index_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"  [FIX] Index cree: {v['dir']}/{v['expected']}")
            fixed += 1

    return fixed


def rebuild_index(repo_path: str, artifact_dir_name: str) -> bool:
    """Reconstruit l'index d'un type d'artefact donne."""
    repo = Path(repo_path)
    artifact_type = artifact_dir_name.rstrip("S")
    if artifact_type not in ARTIFACT_INDEX_FILES:
        return False

    artifact_dir = repo / artifact_dir_name
    index_file = ARTIFACT_INDEX_FILES[artifact_type]
    index_path = artifact_dir / index_file

    if not artifact_dir.exists():
        return False

    active_rows = []
    archive_rows = []

    for item in sorted(artifact_dir.iterdir()):
        if not item.is_file() or item.name.startswith(".") or item.name == index_file:
            continue
        content = item.read_text(encoding="utf-8")
        fm = _parse_frontmatter(content)
        if not fm:
            continue

        fid = fm.get("id", item.stem)
        title = fm.get("title", "—")
        status = fm.get("status", "—")
        created = fm.get("created", "—")
        row = f"| {fid} | {item.name} | {title} | {status} | {created} |"

        if status in ("superseded", "deprecated", "done"):
            archive_rows.append(row)
        else:
            active_rows.append(row)

    lines = [
        f"# {index_file} — Index des {artifact_dir_name} de ce repo",
        "",
        "> Index genere automatiquement. Ne pas editer a la main.",
        f"> Pour regenerer : `python rss_lint.py --repo . --index rebuild`",
        "",
        "## Actifs",
        "",
        "| ID | Fichier | Titre | Statut | Date |",
        "|----|---------|-------|--------|------|",
    ]
    if active_rows:
        lines.extend(active_rows)
    else:
        lines.append("| — | — | — | — | — |")

    lines.extend([
        "",
        "## Archives",
        "",
        "| ID | Fichier | Titre | Statut | Date |",
        "|----|---------|-------|--------|------|",
    ])
    if archive_rows:
        lines.extend(archive_rows)
    else:
        lines.append("| — | — | — | — | — |")

    lines.extend([
        "",
        "",
        f"*Derniere mise a jour : auto-genere*",
    ])

    index_path.write_text("\n".join(lines), encoding="utf-8")
    return True


if __name__ == "__main__":
    main()
