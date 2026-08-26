#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rss_lint.py -- Gate de conformite RSS-v2 pour les repos gerivdb.

Usage:
    python rss_lint.py --repo <path> [--fix] [--strict] [--depth 2|4]
    python rss_lint.py --repo <path> --check-governance
    python rss_lint.py --repo <path> --check-git-engineering
    python rss_lint.py --repo <path> --all-checks [--fix]
    python rss_lint.py --repo <path> --index rebuild [--artifact-dir PRD]

Verifie qu'un repo respecte le Repo Structure Standard v2.
Gere deux profondeurs : 2 niveaux (repos simples) ou 4 niveaux (repos complexes).

Governance checks (--check-governance ou --all-checks) :
  F1  frontmatter_id    -- id doit correspondre au numero dans le nom de fichier
  F1  frontmatter_repo  -- repo: ne doit pas etre 'unknown'
  F2  duplicate_numbers -- deux fichiers ACTIFS meme numero -> FAIL
                           (actif + stub superseded/deprecated = F2-PIPELINE, ignore)
  F3  folder_canonical  -- PRDs/, ADRS/ etc. non canoniques -> FAIL
  F4  superseded_chain  -- superseded_by pointe un actif, pas un stub
  POST index_sync       -- index reflète exactement le contenu reel

Reference: docs/GOVERNANCE-MAINTENANCE-WORKFLOW.md
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# -- Regles RSS-v2 --

ROOT_ALLOWED = {
    "README.md", "CHANGELOG.md", ".gitignore", "pyproject.toml",
    "package.json", "package-lock.json", "Makefile", "LICENSE",
    "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
    "MANIFEST.in", "setup.py", "setup.cfg", "tox.ini", "Dockerfile",
    "docker-compose.yml", ".env.example", "conftest.py", "ECOSROOT.json",
    "requirements.txt", "requirements-test.txt",
}

ROOT_ALLOWED_SIMPLE_ONLY = {
    "requirements_lxc_env2.txt", "requirements_matrix_recoupement.txt",
    "requirements_nexus_ontology_api.txt",
}

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

REQUIRED_DIRS_SIMPLE = ["docs/", "tests/"]
REQUIRED_DIRS_COMPLEX = ["docs/", "tests/", "config/"]

CONFIG_SUBDIRS = [
    "archives/", "databases/", "epics/", "ontology/",
    "phase-logs/", "registries/", "reports/",
]

ARTEFACT_PATTERNS = [
    r"^\.coverage$",
    r"^batch_report\.",
    r"^integration_test_report\.",
    r"^traceability_report\.",
    r"^AUDITREPORT\.",
    r".*__pycache__.*",
]

# Dossiers canoniques valides par type d'artefact
CANONICAL_DIRS = {
    "PRD": "PRD",
    "ADR": "ADR",
    "EPIC": "EPICS",
    "SPEC": "SPEC",
    "INTENT": "INTENTS",
}

# Dossiers non-canoniques connus (aliases, erreurs de nommage)
NON_CANONICAL_DIR_PATTERNS = [
    r"^PRDs$", r"^PRDS$", r"^prd$",
    r"^ADRs$", r"^ADRS$", r"^adr$",
    r"^Epics$", r"^epics$", r"^EPIC$",
    r"^Specs$", r"^SPECS$", r"^spec$",
    r"^Intents$", r"^INTENT$", r"^intents$",
]

# Statuts consideres comme "non actifs" pour le check F2
INACTIVE_STATUSES = {"superseded", "deprecated"}


def load_rssignore(repo_path: Path) -> list:
    """Charge les patterns d'exclusion depuis .rssignore."""
    ignore_file = repo_path / ".rssignore"
    patterns = []
    if ignore_file.exists():
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _is_ignored(path_parts: tuple, patterns: list) -> bool:
    import fnmatch
    path_str = "/".join(path_parts)
    for pat in patterns:
        clean_pat = pat.rstrip("/").rstrip("*")
        if clean_pat and path_str.startswith(clean_pat):
            return True
        if fnmatch.fnmatch(path_str, pat.rstrip("/")):
            return True
    return False


def get_depth(repo_path: Path, rssignore_patterns: list = None) -> int:
    """Determine la profondeur du repo en scannant la structure existante."""
    max_depth = 0
    artifact_dirs = {"ADR", "PRD", "EPICS", "INTENTS", "SPEC"}

    for root, dirs, files in os.walk(repo_path, topdown=True):
        rel_root = Path(root).relative_to(repo_path)
        parts = rel_root.parts if str(rel_root) != "." else ()

        if rssignore_patterns:
            dirs[:] = [d for d in dirs if not _is_ignored(parts + (d,), rssignore_patterns)]

        if parts and (parts[0].startswith(".git") or parts[0].startswith(".kilo") or
                      parts[0] in ("node_modules", ".venv", "__pycache__")):
            dirs.clear()
            continue

        if parts and parts[0] in artifact_dirs:
            depth = len(parts)
            if depth > max_depth:
                max_depth = depth
        elif not parts:
            dirs[:] = [d for d in dirs if d in artifact_dirs or d in ("config", ".github")]

    return 4 if max_depth >= 3 else 2


def scan_repo(repo_path: str, depth: int = None) -> dict:
    """Scan un repo et retourne les violations RSS-v2 structurelles."""
    repo = Path(repo_path)
    if not repo.exists():
        print(f"[ERROR] Repo introuvable: {repo_path}")
        sys.exit(1)

    rssignore_patterns = load_rssignore(repo)

    if depth is None:
        depth = get_depth(repo, rssignore_patterns)

    violations = {
        "forbidden_root": [],
        "missing_dirs": [],
        "artefacts": [],
        "depth_exceeded": [],
        "config_misplaced": [],
    }

    for item in repo.iterdir():
        if item.is_file():
            name = item.name
            if name in ROOT_ALLOWED:
                continue
            if depth == 2 and name in ROOT_ALLOWED_SIMPLE_ONLY:
                continue

            for pattern, destination in ROOT_FORBIDDEN_PATTERNS:
                if re.match(pattern, name, re.IGNORECASE):
                    violations["forbidden_root"].append({"file": name, "destination": destination})
                    break

            for pattern in ARTEFACT_PATTERNS:
                if re.match(pattern, name, re.IGNORECASE):
                    violations["artefacts"].append(name)
                    break

        elif item.is_dir() and item.name == "__pycache__":
            violations["artefacts"].append("__pycache__/")
        elif item.is_dir() and (item.name.startswith(".git") or item.name.startswith(".kilo") or
                                  item.name in ("node_modules", ".venv")):
            continue

    required = REQUIRED_DIRS_COMPLEX if depth == 4 else REQUIRED_DIRS_SIMPLE
    for required_dir in required:
        if not (repo / required_dir).exists():
            violations["missing_dirs"].append(required_dir)

    for root, dirs, files in os.walk(repo_path, topdown=True):
        rel_root = Path(root).relative_to(repo)
        parts = rel_root.parts if str(rel_root) != "." else ()
        if rssignore_patterns:
            dirs[:] = [d for d in dirs if not _is_ignored(parts + (d,), rssignore_patterns)]
        if parts and (parts[0].startswith(".git") or parts[0].startswith(".kilo") or
                      parts[0] in ("node_modules", ".venv", "__pycache__", "temp_skills")):
            dirs.clear()
            continue
        current_depth = len(parts)
        if current_depth > depth:
            violations["depth_exceeded"].append({
                "path": str(rel_root),
                "depth": current_depth,
                "max": depth,
            })

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
                        violations["config_misplaced"].append({"file": item.name, "destination": dest})
                        break

    return violations


def check_git_noise(repo_path: str, repo_type: str = "default") -> dict:
    """Verifie le bruit git (fichiers untracked apres .gitignore)."""
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
        "files": files[:20],
        "severity": (
            "FAIL" if count > fail_threshold else
            "WARN" if count > warn_threshold else
            "PASS"
        ),
    }


def check_gitignore_coverage(repo_path: str, repo_type: str = "default") -> dict:
    """Verifie que le .gitignore contient les patterns requis."""
    gitignore_path = Path(repo_path) / ".gitignore"
    if not gitignore_path.exists():
        return {"missing": ["ALL"], "severity": "FAIL", "error": ".gitignore not found"}

    content = gitignore_path.read_text(encoding="utf-8")
    required = [
        "__pycache__/", "*.py[cod]", ".DS_Store", "Thumbs.db",
        "*.egg-info/", "build/", "dist/", "*.so",
    ]
    required_by_type = {
        "tool": ["bin/portable/", "git/", "*.exe", "*.dll"],
        "infra": ["*.log", "*.tmp", "tmp/"],
    }
    missing = []
    for pattern in required:
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


def check_filesystem_integrity(repo_path: str, rssignore_patterns: list = None) -> dict:
    """Verifie l'integrite du filesystem (junctions NTFS, dossiers vides, fichiers orphelins)."""
    repo = Path(repo_path)
    junctions = []
    empty_dirs = []
    orphan_files = []

    try:
        result = subprocess.run(
            ["cmd", "/c", "dir", "/a:l", "/s", "/b"],
            capture_output=True, text=True, cwd=repo_path
        )
        junctions = [j.strip() for j in result.stdout.strip().split("\n") if j.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    for root, dirs, files in os.walk(repo_path, topdown=True):
        rel_root = Path(root).relative_to(repo)
        parts = rel_root.parts if str(rel_root) != "." else ()
        if rssignore_patterns:
            dirs[:] = [d for d in dirs if not _is_ignored(parts + (d,), rssignore_patterns)]
        if parts and (parts[0].startswith(".git") or parts[0].startswith(".kilo") or
                      parts[0] in ("node_modules", ".venv", "__pycache__")):
            dirs.clear()
            continue
        if not dirs and not files:
            empty_dirs.append(str(rel_root))

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
        "empty_dirs": empty_dirs[:20],
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
    """Corrige automatiquement les violations RSS-v2 structurelles."""
    repo = Path(repo_path)
    fixed = 0

    for missing_dir in violations["missing_dirs"]:
        (repo / missing_dir).mkdir(parents=True, exist_ok=True)
        print(f"  [FIX] Cree: {missing_dir}")
        fixed += 1

    for violation in violations["forbidden_root"]:
        src = repo / violation["file"]
        dest_dir = repo / violation["destination"]
        if src.exists():
            if violation["destination"] == ".gitignore":
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / violation["file"]
            if dest.exists():
                print(f"  [SKIP] Destination existe deja: {dest}")
            else:
                shutil.move(str(src), str(dest))
                print(f"  [FIX] Deplace: {violation['file']} -> {violation['destination']}")
                fixed += 1

    for violation in violations["config_misplaced"]:
        src = repo / violation["file"]
        dest_dir = repo / violation["destination"]
        if src.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / violation["file"]
            if dest.exists():
                print(f"  [SKIP] Destination existe deja: {dest}")
            else:
                shutil.move(str(src), str(dest))
                print(f"  [FIX] Deplace: {violation['file']} -> {violation['destination']}")
                fixed += 1

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
                f.write("\n# RSS-v2 -- Artefacts de run (auto-ajoute)\n")
                for a in additions:
                    f.write(f"{a}\n")
            print(f"  [FIX] Ajoute au .gitignore: {', '.join(additions)}")
            fixed += len(additions)

    return fixed


# ============================================================
# RSS-v2 Artifact Policy
# ============================================================

import yaml as _yaml

ARTIFACT_NAMING = {
    "PRD":    re.compile(r"^PRD-(?P<num>\d{3})-[a-z0-9][a-z0-9-]*\.md$"),
    "ADR":    re.compile(r"^ADR-(?P<num>\d{3})-[a-z0-9][a-z0-9-]*\.md$"),
    "EPIC":   re.compile(r"^EPIC-(?P<num>\d{3})-[a-z0-9][a-z0-9-]*\.md$"),
    "SPEC":   re.compile(r"^SPEC-(?P<num>\d{3})-[a-z0-9][a-z0-9-]*\.md$"),
    "INTENT": re.compile(r"^INTENT-(?P<num>\d{3})-[a-z0-9][a-z0-9-]*\.md$"),
}

ARTIFACT_STATUSES = {
    "PRD":    {"draft", "active", "proposed", "deprecated", "superseded"},
    "ADR":    {"proposed", "accepted", "deprecated", "superseded"},
    "EPIC":   {"draft", "active", "done", "deprecated", "superseded"},
    "SPEC":   {"draft", "stable", "deprecated", "superseded"},
    "INTENT": {"draft", "active", "completed", "deprecated", "superseded"},
}

FRONTMATTER_CORE_FIELDS = {"id", "title", "repo", "status", "created", "author"}

FRONTMATTER_OPTIONAL_FIELDS = {
    "PRD":    {"intent_hash", "superseded_by", "source_repo", "source_path", "updated"},
    "ADR":    {"intent_hash", "superseded_by", "source_repo", "source_path", "updated"},
    "EPIC":   {"intent_hash", "superseded_by", "updated"},
    "SPEC":   {"intent_hash", "superseded_by", "source_repo", "source_path", "updated"},
    "INTENT": {"intent_hash", "superseded_by", "updated", "prd_ref", "epic_ref"},
}

ARTIFACT_INDEX_FILES = {
    "PRD":    "PRD-000-index.md",
    "ADR":    "ADR-000-index.md",
    "EPIC":   "EPIC-000-index.md",
    "SPEC":   "SPEC-000-index.md",
    "INTENT": "INTENT-000-index.md",
}

ARTIFACT_DIRS = {"PRD", "ADR", "EPICS", "SPEC", "INTENTS"}

# -- Git Engineering conventions --
GIT_ENG_DIR = "git-engineering"
GIT_ENG_VALID_FILES = {
    "README.md",
    "dag-patterns.md",
    "cross-repo-flow.md",
    "dry-run-protocol.md",
    "hooks-catalog.md",
    "metagit-conventions.md",
}
GIT_ENG_MAX_LINES = 200
GIT_ENG_REQUIRED_REFERENCES = ["ADR-007", "INTENT-077"]

# -- REPO.yaml generation (EPIC-016/EPIC-017) --
REPO_YAML_SCHEMA = {
    "repo": "gerivdb/<NOM>",
    "strate": "L<0-9>",
    "profil": "<CRITICAL|TOOL|CITIZEN|ARCHIVE>",
    "rss_version": "2.1",
    "last_audited": "<YYYY-MM-DD>",
    "conformite": "PASS",
    "dossiers_presents": [],
    "dossiers_manquants": [],
    "fichiers_requis_absents": [],
    "crosslinks": [],
    "auteur": "gerivdb",
    "do_not_edit": True,
}

REPO_YAML_PROFILES = {
    "CRITICAL": {
        "required_dirs": [".github", "ADR", "EPICS", "PRD", "INTENTS", "docs", "schemas", "README.md", ".rssignore", "REPO.yaml"],
        "forbidden_items": ["node_modules", "__pycache__", "*.pyc", "*.tmp", "*.log", ".env", "*.zip", "*.tar.gz"],
        "max_depth": 4,
    },
    "TOOL": {
        "required_dirs": [".github", "ADR", "EPICS", "PRD", "docs", "tools", "src", "tests", "schemas", "README.md", ".rssignore", "REPO.yaml"],
        "forbidden_items": ["node_modules", "__pycache__", "*.pyc", "*.tmp", "*.log", ".env", "*.zip", "*.tar.gz"],
        "max_depth": 4,
    },
    "CITIZEN": {
        "required_dirs": [".github", "docs", "src", "tests", "README.md", ".rssignore", "REPO.yaml"],
        "forbidden_items": ["node_modules", "__pycache__", "*.pyc", "*.tmp", "*.log", ".env", "*.zip", "*.tar.gz"],
        "max_depth": 2,
    },
    "ARCHIVE": {
        "required_dirs": ["README.md", "REPO.yaml"],
        "forbidden_items": [],
        "max_depth": 2,
    },
}

# -- BLO push (EPIC-017) --
BLO_WAL_REPO = "gerivdb/BLO"
BLO_WAL_PATH = "WAL/{repo}/REPO.yaml"



# Placeholders interdits dans le champ 'id'
ID_PLACEHOLDERS = re.compile(
    r"^(PRD-000|PRD-NNN|ADR-000|ADR-NNN|EPIC-000|EPIC-NNN|SPEC-000|SPEC-NNN|INTENT-000|INTENT-NNN)$",
    re.IGNORECASE
)


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


def _id_from_filename(fname: str, artifact_type: str) -> str:
    """Derive l'ID attendu depuis le nom de fichier. Ex: ADR-010-foo.md -> ADR-010"""
    m = ARTIFACT_NAMING[artifact_type].match(fname)
    if m:
        return f"{artifact_type}-{m.group('num')}"
    return ""


def check_artifacts(repo_path: str) -> dict:
    """
    Verifie la conformite des artefacts de gouvernance (PRD, ADR, EPIC, SPEC).

    Checks inclus :
      - naming        : pattern de nommage
      - frontmatter   : champs obligatoires presents
      - frontmatter_id: F1 -- id correspond au numero dans le nom de fichier
      - frontmatter_repo: F1 -- repo != 'unknown'
      - duplicate_numbers: F2 -- deux fichiers ACTIFS meme numero -> FAIL
                           (actif + stub superseded/deprecated = F2-PIPELINE, ignore)
      - folder_canonical: F3 -- dossiers non canoniques (PRDs/, ADRS/, etc.)
      - superseded_chain: F4 -- superseded_by pointe un actif, pas un stub
      - index_missing : index reserve absent
      - index_sync    : POST -- index desynchronise avec contenu reel
      - mirrors       : source_repo sans source_path
      - stubs         : fichier superseded qui n'est pas un stub
      - status        : statut invalide
    """
    repo = Path(repo_path)
    violations = {
        "naming": [],
        "frontmatter": [],
        "frontmatter_id": [],       # F1
        "frontmatter_repo": [],     # F1
        "duplicate_numbers": [],    # F2
        "folder_canonical": [],     # F3
        "superseded_chain": [],     # F4
        "index_missing": [],
        "index_sync": [],           # POST
        "mirrors": [],
        "stubs": [],
        "status": [],
    }

    # ---- F3: dossiers non canoniques a la racine ----
    for item in repo.iterdir():
        if item.is_dir():
            for nc_pattern in NON_CANONICAL_DIR_PATTERNS:
                if re.match(nc_pattern, item.name):
                    canonical = None
                    for atype, cdir in CANONICAL_DIRS.items():
                        if item.name.upper().rstrip("S") == atype or item.name.upper() == cdir.upper():
                            canonical = cdir
                            break
                    violations["folder_canonical"].append({
                        "dir": item.name,
                        "canonical": canonical or "PRD|ADR|EPICS|SPEC|INTENTS",
                        "files": [f.name for f in item.iterdir() if f.is_file()],
                    })
                    break

    # ---- Scan par dossier canonique ----
    for artifact_dir_name in ARTIFACT_DIRS:
        artifact_dir = repo / artifact_dir_name
        if not artifact_dir.exists():
            continue

        artifact_type = artifact_dir_name.rstrip("S")
        if artifact_type not in ARTIFACT_NAMING:
            continue

        naming_pattern = ARTIFACT_NAMING[artifact_type]
        valid_statuses = ARTIFACT_STATUSES[artifact_type]
        index_file = ARTIFACT_INDEX_FILES.get(artifact_type)

        # Index manquant
        if index_file and not (artifact_dir / index_file).exists():
            violations["index_missing"].append({
                "dir": artifact_dir_name,
                "expected": index_file,
            })

        # -- Pre-scan: lire statuts pour F2 et F4 --
        file_statuses = {}  # fname -> status
        for item in artifact_dir.iterdir():
            if not item.is_file() or item.name.startswith(".") or item.name == index_file:
                continue
            if naming_pattern.match(item.name):
                content = item.read_text(encoding="utf-8")
                fm = _parse_frontmatter(content)
                file_statuses[item.name] = fm.get("status", "")

        # -- F2: detecter les doublons de numero (actifs seulement) --
        # Un F2 reel = au moins 2 fichiers du meme numero avec statut actif
        # Paire (actif + superseded/deprecated) = F2-PIPELINE, ignore
        number_map = {}  # num -> [filenames]
        for fname, status in file_statuses.items():
            if fname == index_file:
                continue
            m = naming_pattern.match(fname)
            if m:
                num = m.group("num")
                number_map.setdefault(num, []).append((fname, status))

        for num, entries in number_map.items():
            if len(entries) > 1:
                active_entries = [
                    (fname, status) for fname, status in entries
                    if status not in INACTIVE_STATUSES
                ]
                inactive_entries = [
                    (fname, status) for fname, status in entries
                    if status in INACTIVE_STATUSES
                ]
                if len(active_entries) > 1:
                    # Vrai F2 : plusieurs actifs avec le meme numero
                    violations["duplicate_numbers"].append({
                        "artifact_dir": artifact_dir_name,
                        "number": f"{artifact_type}-{num}",
                        "files": [fname for fname, _ in entries],
                        "active_files": [fname for fname, _ in active_entries],
                        "inactive_files": [fname for fname, _ in inactive_entries],
                        "error": (
                            f"{len(active_entries)} fichiers ACTIFS portent le meme numero"
                            f" (+ {len(inactive_entries)} stub(s) inactif(s))"
                        ),
                    })
                elif len(active_entries) == 1 and inactive_entries:
                    # F2-PIPELINE : 1 actif + stubs superseded/deprecated -> normal, ignore
                    pass
                # Si tous inactifs (edge case) -> ignore

        # -- Construire la liste des fichiers actifs/stubs pour F4 --
        active_files = set()
        stub_files = set()
        all_fms = {}  # fname -> frontmatter
        for item in sorted(artifact_dir.iterdir()):
            if not item.is_file() or item.name.startswith(".") or item.name == index_file:
                continue
            content = item.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            all_fms[item.name] = fm
            status = fm.get("status", "")
            if status in INACTIVE_STATUSES:
                stub_files.add(item.name)
            else:
                active_files.add(item.name)

        # -- POST: index_sync --
        if index_file and (artifact_dir / index_file).exists():
            index_content = (artifact_dir / index_file).read_text(encoding="utf-8")
            missing_in_index = []
            for fname in active_files:
                expected_id = _id_from_filename(fname, artifact_type)
                if fname not in index_content and (not expected_id or expected_id not in index_content):
                    missing_in_index.append(fname)
            placeholder_in_index = re.findall(
                r"(PRD-NNN|ADR-NNN|EPIC-NNN|SPEC-NNN|INTENT-NNN)",
                index_content, re.IGNORECASE
            )
            if missing_in_index or placeholder_in_index:
                violations["index_sync"].append({
                    "index": f"{artifact_dir_name}/{index_file}",
                    "missing_entries": missing_in_index,
                    "placeholder_ids": list(set(placeholder_in_index)),
                    "error": (
                        f"{len(missing_in_index)} fichier(s) actif(s) absent(s) de l'index"
                        + (f", {len(set(placeholder_in_index))} placeholder(s) detecte(s)" if placeholder_in_index else "")
                    ),
                })

        # -- Scan fichier par fichier --
        for item in artifact_dir.iterdir():
            if not item.is_file() or item.name.startswith(".") or item.name == index_file:
                continue

            fname = item.name

            # 1. Check nommage
            if not naming_pattern.match(fname):
                violations["naming"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "pattern": naming_pattern.pattern,
                })
                continue

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

            # 3. F1 -- Check frontmatter_id
            fm_id = str(fm.get("id", "")).strip()
            expected_id = _id_from_filename(fname, artifact_type)
            if ID_PLACEHOLDERS.match(fm_id):
                violations["frontmatter_id"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "current_id": fm_id,
                    "expected_id": expected_id,
                    "error": f"id placeholder '{fm_id}' -> attendu '{expected_id}'",
                })
            elif expected_id and fm_id != expected_id:
                violations["frontmatter_id"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "current_id": fm_id,
                    "expected_id": expected_id,
                    "error": f"id '{fm_id}' != attendu '{expected_id}'",
                })

            # 4. F1 -- Check frontmatter_repo
            fm_repo = str(fm.get("repo", "")).strip()
            if fm_repo.lower() in ("unknown", "", "none", "null", "n/a"):
                violations["frontmatter_repo"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "current_repo": fm_repo,
                    "error": f"repo: '{fm_repo}' invalide -- doit etre gerivdb/<nom_repo>",
                })

            # 5. Check statut
            status = fm.get("status", "")
            if status and valid_statuses and status not in valid_statuses:
                violations["status"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "status": status,
                    "valid": ", ".join(sorted(valid_statuses)),
                })

            # 6. Check stub superseded
            if status == "superseded" and not _is_stub_superseded(content):
                violations["stubs"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "error": "fichier superseded qui n'est pas un stub",
                })

            # 7. F4 -- Check superseded_chain
            superseded_by = fm.get("superseded_by")
            if superseded_by:
                sb = str(superseded_by).strip()
                target_file = None
                for candidate in artifact_dir.iterdir():
                    if candidate.is_file() and candidate.name != index_file:
                        cid = _id_from_filename(candidate.name, artifact_type)
                        if cid == sb or candidate.name == sb or candidate.stem == sb:
                            target_file = candidate.name
                            break
                if target_file is None:
                    violations["superseded_chain"].append({
                        "file": f"{artifact_dir_name}/{fname}",
                        "superseded_by": sb,
                        "error": f"superseded_by '{sb}' : fichier cible introuvable",
                    })
                elif target_file in stub_files:
                    target_fm = all_fms.get(target_file, {})
                    target_status = target_fm.get("status", "?")
                    violations["superseded_chain"].append({
                        "file": f"{artifact_dir_name}/{fname}",
                        "superseded_by": sb,
                        "target_file": target_file,
                        "target_status": target_status,
                        "error": f"superseded_by '{sb}' pointe un stub ({target_status}) -- chaine invalide",
                    })

            # 8. Check mirrors
            source_repo = fm.get("source_repo")
            if source_repo and not fm.get("source_path"):
                violations["mirrors"].append({
                    "file": f"{artifact_dir_name}/{fname}",
                    "error": "source_repo present mais source_path manquant",
                })

    return violations


def fix_artifacts(repo_path: str, violations: dict) -> int:
    """
    Corrige automatiquement les violations artefacts simples.
    F1 (frontmatter_id, frontmatter_repo) sont corriges si la valeur attendue est deterministe.
    F4 (superseded_chain) : signalement uniquement -- correction manuelle requise.
    """
    repo = Path(repo_path)
    fixed = 0

    # Creer les index manquants
    for v in violations.get("index_missing", []):
        artifact_dir = repo / v["dir"]
        index_path = artifact_dir / v["expected"]
        if not index_path.exists():
            lines = [
                f"# {v['expected']} -- Index des {v['dir']} de ce repo",
                "",
                "> Index genere automatiquement. Ne pas editer a la main.",
                "> Pour regenerer : `python rss_lint.py --repo . --index rebuild`",
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
                f"*Derniere mise a jour : auto-genere*",
            ]
            index_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"  [FIX] Index cree: {v['dir']}/{v['expected']}")
            fixed += 1

    # F1 -- Corriger frontmatter_id (placeholder -> ID derive du nom de fichier)
    for v in violations.get("frontmatter_id", []):
        file_path = repo / v["file"]
        if not file_path.exists():
            continue
        expected_id = v.get("expected_id")
        if not expected_id:
            print(f"  [SKIP] frontmatter_id: ID attendu inconnu pour {v['file']}")
            continue
        content = file_path.read_text(encoding="utf-8")
        current_id = v.get("current_id", "")
        new_content = re.sub(
            r"(^id:\s*)" + re.escape(current_id) + r"(\s*$)",
            r"\g<1>" + expected_id + r"\g<2>",
            content,
            count=1,
            flags=re.MULTILINE
        )
        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"  [FIX] frontmatter_id: {v['file']} '{current_id}' -> '{expected_id}'")
            fixed += 1
        else:
            print(f"  [SKIP] frontmatter_id: remplacement echoue pour {v['file']} (verifier manuellement)")

    # F1 -- Signaler frontmatter_repo (correction manuelle requise car valeur inconnue automatiquement)
    for v in violations.get("frontmatter_repo", []):
        print(f"  [MANUAL] frontmatter_repo: {v['file']} -- corriger repo: -> gerivdb/<nom_repo>")

    # F4 -- Signaler superseded_chain (correction manuelle requise)
    for v in violations.get("superseded_chain", []):
        print(f"  [MANUAL] superseded_chain: {v['file']} -- {v['error']}")

    # F3 -- Signaler folder_canonical (migration manuelle ou via F3-PIPELINE)
    for v in violations.get("folder_canonical", []):
        print(f"  [MANUAL] folder_canonical: {v['dir']}/ -> {v['canonical']}/ ({len(v['files'])} fichier(s))")

    # F2 -- Signaler duplicate_numbers (correction manuelle requise)
    for v in violations.get("duplicate_numbers", []):
        print(f"  [MANUAL] duplicate_numbers: {v['number']} -> actifs: {', '.join(v.get('active_files', v['files']))}")

    return fixed



# ============================================================
# SOT Ref check (ADR-008)
# ============================================================

# Fichiers registre a scanner pour sot_ref
SOT_REF_TARGET_FILES = [
    "known_repositories.yaml",
    "citizens.yaml",
]

SOT_REF_REGISTRY_DIRS = [
    "registries",
    "config/registries",
]

# Patterns de blocs qui indiquent une reference externe necessitant sot_ref
SOT_REF_EXTERNAL_PATTERNS = [
    re.compile(r"\bENV-REGISTRY\b"),
    re.compile(r"\bENV\d+-"),
    re.compile(r"\bSOT-"),
    re.compile(r"\bONTOLOGY\b"),
    re.compile(r"\bTOPOS\b"),
    re.compile(r"\bgerivdb/"),
    re.compile(r"source_repo\s*:"),
    re.compile(r"upstream\s*:"),
]


def _is_external_entity(block: dict) -> bool:
    """Heuristique: determine si un bloc YAML reference une entite avec SOT externe."""
    if not isinstance(block, dict):
        return False
    # Si le bloc a un champ source_repo ou upstream, c'est externe
    if "source_repo" in block or "upstream" in block:
        return True
    # Si le bloc reference un repo externe connu
    block_str = str(block)
    for pat in SOT_REF_EXTERNAL_PATTERNS:
        if pat.search(block_str):
            return True
    return False


def check_sot_ref(repo_path: str) -> list:
    """
    LINT_SOT_REF_MISSING -- verifie que tout bloc registre avec description
    et reference externe inclut un champ sot_ref.

    Cible :
      - known_repositories.yaml
      - citizens.yaml
      - registries/*.yaml (et config/registries/*.yaml)

    Retourne une liste de violations :
      {"file": str, "block": str, "error": str}
    """
    repo = Path(repo_path)
    violations = []

    # Cibles a scanner
    target_files = []
    for fname in SOT_REF_TARGET_FILES:
        fpath = repo / fname
        if fpath.exists():
            target_files.append(fpath)

    for reg_dir_name in SOT_REF_REGISTRY_DIRS:
        reg_dir = repo / reg_dir_name
        if reg_dir.exists() and reg_dir.is_dir():
            for item in reg_dir.glob("*.yaml"):
                target_files.append(item)
            for item in reg_dir.glob("*.yml"):
                target_files.append(item)

    for fpath in target_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = _yaml.safe_load(f)
        except (_yaml.YAMLError, OSError):
            continue

        if data is None:
            continue

        rel_path = str(fpath.relative_to(repo))

        # known_repositories.yaml et citizens.yaml sont des listes de blocs
        if isinstance(data, list):
            for idx, block in enumerate(data):
                if not isinstance(block, dict):
                    continue
                block_name = block.get("full_name", block.get("name", f"block[{idx}]"))
                has_description = bool(block.get("description", "").strip()) if isinstance(block.get("description"), str) else False
                has_sot_ref = "sot_ref" in block
                is_external = _is_external_entity(block)

                if has_description and is_external and not has_sot_ref:
                    violations.append({
                        "file": rel_path,
                        "block": block_name,
                        "error": f"description sans sot_ref (entite externe: {block_name})",
                    })

        # registries/*.yaml sont des dicts avec des blocs nommes
        elif isinstance(data, dict):
            for key, value in data.items():
                if not isinstance(value, dict):
                    continue
                # Si le contenu est une liste de blocs
                if isinstance(value, list):
                    for idx, block in enumerate(value):
                        if not isinstance(block, dict):
                            continue
                        block_name = block.get("full_name", block.get("name", f"{key}[{idx}]"))
                        has_description = bool(block.get("description", "").strip()) if isinstance(block.get("description"), str) else False
                        has_sot_ref = "sot_ref" in block
                        is_external = _is_external_entity(block)

                        if has_description and is_external and not has_sot_ref:
                            violations.append({
                                "file": rel_path,
                                "block": block_name,
                                "error": f"description sans sot_ref (entite externe: {block_name})",
                            })
                # Si le contenu est lui-meme un bloc avec description
                has_description = bool(value.get("description", "").strip()) if isinstance(value.get("description"), str) else False
                has_sot_ref = "sot_ref" in value
                is_external = _is_external_entity(value)

                if has_description and is_external and not has_sot_ref:
                    violations.append({
                        "file": rel_path,
                        "block": str(key),
                        "error": f"description sans sot_ref (entite externe: {key})",
                    })

    return violations


# ============================================================
# Git Engineering checks
# ============================================================

def check_git_engineering(repo_path: str) -> dict:
    """
    Verifie la conformite des fichiers Git Engineering dans git-engineering/.

    Checks inclus :
      - dir_present    : le repertoire git-engineering/ existe
      - required_files : les 6 fichiers requis sont presents
      - max_lines      : aucun fichier ne depasse GIT_ENG_MAX_LINES
      - adr_reference  : chaque fichier reference ADR-007 et INTENT-077
      - no_real_names  : pas de noms de repo reels dans les exemples
      - no_frontmatter : pas de frontmatter YAML (conventions pures)
    """
    repo = Path(repo_path)
    violations = {
        "dir_missing": False,
        "missing_files": [],
        "extra_files": [],
        "max_lines": [],
        "missing_adr_ref": [],
        "missing_intent_ref": [],
        "real_repo_names": [],
        "unexpected_frontmatter": [],
    }

    ge_dir = repo / GIT_ENG_DIR
    if not ge_dir.exists():
        violations["dir_missing"] = True
        return violations

    # Fichiers requis presents
    for fname in sorted(GIT_ENG_VALID_FILES):
        if not (ge_dir / fname).exists():
            violations["missing_files"].append(fname)

    # Fichiers supplementaires (non attendus)
    if ge_dir.exists():
        for item in sorted(ge_dir.iterdir()):
            if item.is_file() and item.name not in GIT_ENG_VALID_FILES:
                violations["extra_files"].append(item.name)

    # Checks par fichier
    for fname in sorted(GIT_ENG_VALID_FILES):
        fpath = ge_dir / fname
        if not fpath.exists():
            continue

        file_content = fpath.read_text(encoding="utf-8")

        # Check max lines
        lines = file_content.split("\n")
        if len(lines) > GIT_ENG_MAX_LINES:
            violations["max_lines"].append({
                "file": fname,
                "lines": len(lines),
                "max": GIT_ENG_MAX_LINES,
            })

        # Check references ADR-007 et INTENT-077
        if "ADR-007" not in file_content:
            violations["missing_adr_ref"].append(fname)
        if "INTENT-077" not in file_content:
            violations["missing_intent_ref"].append(fname)

        # Check pas de frontmatter YAML (conventions pures)
        if file_content.strip().startswith("---"):
            # Verifier si c'est un vrai frontmatter YAML (pas juste une ligne horizontale)
            end = file_content.find("---", 3)
            if end > 3:
                block = file_content[3:end].strip()
                if block and ":" in block:
                    violations["unexpected_frontmatter"].append(fname)

        # Check pas de noms de repo reels
        for pattern, desc in [
            (r"gerivdb/(CTULU|TRIX|NEXUS|WAZAA|BRAIN|FLUENCE|REPO-STANDARDS|GOVERNANCE-HUB)", "nom de repo reel"),
            (r"D:\\DO\\WEB\\TOOLS\\L[0-5]", "chemin absolu Windows"),
        ]:
            matches = re.findall(pattern, file_content)
            if matches:
                violations["real_repo_names"].append({
                    "file": fname,
                    "matches": list(set(matches)),
                    "desc": desc,
                })

    return violations


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
        title = fm.get("title", "--")
        status = fm.get("status", "--")
        created = fm.get("created", "--")
        row = f"| {fid} | [{item.name}]({item.name}) | {title} | {status} | {created} |"

        if status in ("superseded", "deprecated", "done"):
            archive_rows.append(row)
        else:
            active_rows.append(row)

    lines = [
        f"# {index_file} -- Index des {artifact_dir_name} de ce repo",
        "",
        "> Index genere automatiquement. Ne pas editer a la main.",
        "> Pour regenerer : `python rss_lint.py --repo . --index rebuild`",
        "",
        "## Actifs",
        "",
        "| ID | Fichier | Titre | Statut | Date |",
        "|----|---------|-------|--------|------|",
    ]
    lines.extend(active_rows if active_rows else ["| -- | -- | -- | -- | -- |"])

    lines.extend([
        "",
        "## Archives",
        "",
        "| ID | Fichier | Titre | Statut | Date |",
        "|----|---------|-------|--------|------|",
    ])
    lines.extend(archive_rows if archive_rows else ["| -- | -- | -- | -- | -- |"])

    lines.extend([
        "",
        f"*Derniere mise a jour : auto-genere*",
    ])

    index_path.write_text("\n".join(lines), encoding="utf-8")
    return True




# ============================================================
# REPO.yaml generation (EPIC-016/EPIC-017)
# ============================================================

def _detect_strate(repo_path: str) -> str:
    """Détecte la strate du repo depuis le chemin local."""
    path_lower = repo_path.replace("\\", "/").lower()
    if "/l0-" in path_lower or "/l0/" in path_lower:
        return "L0"
    elif "/l1-" in path_lower or "/l1/" in path_lower:
        return "L1"
    elif "/l2-" in path_lower or "/l2/" in path_lower:
        return "L2"
    elif "/l3-" in path_lower or "/l3/" in path_lower:
        return "L3"
    elif "/l4-" in path_lower or "/l4/" in path_lower:
        return "L4"
    elif "/l5-" in path_lower or "/l5/" in path_lower:
        return "L5"
    return "L4"


def _detect_profil(repo_path: str) -> str:
    """Détecte le profil RSS-v2 du repo."""
    strate = _detect_strate(repo_path)
    strate_num = int(strate[1])
    if strate_num <= 2:
        return "CRITICAL"
    elif strate_num == 3:
        return "TOOL"
    elif strate_num <= 7:
        return "CITIZEN"
    else:
        return "ARCHIVE"


def generate_repo_yaml(repo_path: str) -> dict:
    """
    Génère un REPO.yaml pour le repo donné.
    Retourne un dict représentant le REPO.yaml.
    """
    repo = Path(repo_path)
    if not repo.exists():
        raise FileNotFoundError(f"Repo path not found: {repo_path}")

    name = os.path.basename(os.path.abspath(repo_path)) if repo.name in (".", "", None) else repo.name
    strate = _detect_strate(repo_path)
    profil = _detect_profil(repo_path)

    # Lister les dossiers présents
    dirs_present = []
    for item in sorted(repo.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            dirs_present.append(item.name)
        elif item.name == "README.md":
            dirs_present.append("README.md")

    # Vérifier les dossiers manquants selon le profil
    profile_config = REPO_YAML_PROFILES.get(profil, REPO_YAML_PROFILES["CITIZEN"])
    required = profile_config["required_dirs"]
    dirs_missing = [d for d in required if d not in dirs_present]

    # Calculer le hash de structure
    import hashlib
    structure_str = ",".join(sorted(dirs_present))
    structure_hash = "sha256:" + hashlib.sha256(structure_str.encode()).hexdigest()[:16]

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d")

    return {
        "repo": f"gerivdb/{name}",
        "strate": strate,
        "profil": profil,
        "rss_version": "2.1",
        "structure_hash": structure_hash,
        "last_audited": now,
        "conformite": "PASS" if not dirs_missing else "WARN",
        "dossiers_presents": dirs_present,
        "dossiers_manquants": dirs_missing,
        "fichiers_requis_absents": [d for d in dirs_missing if d.endswith(".md") or d.startswith(".")],
        "crosslinks": [],
        "auteur": "gerivdb",
        "do_not_edit": True,
    }


def write_repo_yaml(repo_path: str, repo_yaml: dict) -> str:
    """Écrit REPO.yaml dans le repo. Retourne le chemin du fichier écrit."""
    import yaml
    repo = Path(repo_path)
    yaml_path = repo / "REPO.yaml"

    content = yaml.dump(repo_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
    yaml_path.write_text(content, encoding="utf-8")
    return str(yaml_path)


# ============================================================
# SOT Ref check (ADR-008) — FIN
# ============================================================


# ============================================================
# Profile-based checks (RSS-v2 §6)
# ============================================================

def check_profile_conformity(repo_path: str, profil: str = None) -> dict:
    """
    Vérifie la conformité du repo selon son profil RSS-v2 (§6).
    
    Checks :
      - required_dirs présents
      - forbidden_items absents
      - max_depth respecté
      - citizens.yaml présent (si profil CRITICAL/TOOL/CITIZEN)
      - REPO.yaml présent (si profil CRITICAL/TOOL/CITIZEN)
      - CROSSLINKS/ conforme au profil
    """
    repo = Path(repo_path)
    violations = {
        "missing_dirs": [],
        "forbidden_items": [],
        "depth_exceeded": [],
        "missing_files": [],
        "crosslinks_violation": False,
    }

    # Détecter le profil si non fourni
    if profil is None:
        # Vérifier d'abord si le profil est forcé dans .rssignore
        rssignore_path = Path(repo_path) / ".rssignore"
        forced_profil = None
        if rssignore_path.exists():
            for line in rssignore_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("profile:"):
                    forced_profil = line.split(":", 1)[1].strip().upper()
                    break
        if forced_profil:
            profil = forced_profil
        else:
            profil = _detect_profil(repo_path)

    profile_config = REPO_YAML_PROFILES.get(profil, REPO_YAML_PROFILES["CITIZEN"])

    # Vérifier les dossiers requis
    present_dirs = [d.name for d in repo.iterdir() if d.is_dir()]
    present_files = [f.name for f in repo.iterdir() if f.is_file()]
    all_present = present_dirs + present_files
    for req_dir in profile_config["required_dirs"]:
        if req_dir not in all_present:
            violations["missing_dirs"].append(req_dir)

    # Véricher les fichiers interdits à la racine
    for item in repo.iterdir():
        if item.is_file():
            for forbidden_pat in profile_config.get("forbidden_items", []):
                if forbidden_pat.startswith("*"):
                    import fnmatch
                    if fnmatch.fnmatch(item.name, forbidden_pat):
                        violations["forbidden_items"].append(item.name)
                elif item.name == forbidden_pat:
                    violations["forbidden_items"].append(item.name)

    # Vérifier la profondeur
    max_depth = profile_config.get("max_depth", 4)
    for root, dirs, files in os.walk(repo_path, topdown=True):
        rel_root = Path(root).relative_to(repo)
        parts = rel_root.parts if str(rel_root) != "." else ()
        if parts and (parts[0].startswith(".git") or parts[0].startswith(".kilo") or
                      parts[0] in ("node_modules", ".venv", "__pycache__")):
            dirs.clear()
            continue
        if len(parts) > max_depth:
            violations["depth_exceeded"].append({
                "path": str(rel_root),
                "depth": len(parts),
                "max": max_depth,
            })

    # Vérifier citizens.yaml (obligatoire pour CRITICAL/TOOL/CITIZEN)
    if profil in ("CRITICAL", "TOOL", "CITIZEN"):
        if not (repo / "citizens.yaml").exists():
            violations["missing_files"].append("citizens.yaml")

    # Vérifier REPO.yaml (obligatoire pour CRITICAL/TOOL/CITIZEN)
    if profil in ("CRITICAL", "TOOL", "CITIZEN"):
        if not (repo / "REPO.yaml").exists():
            violations["missing_files"].append("REPO.yaml")

    # Vérifier CROSSLINKS/ selon profil
    has_crosslinks = (repo / "CROSSLINKS").exists()
    if profil == "CRITICAL" and not has_crosslinks:
        violations["crosslinks_violation"] = True
    elif profil == "TOOL" and has_crosslinks:
        # CROSSLINKS interdit pour TOOL
        violations["crosslinks_violation"] = True

    return violations


# ============================================================
# BLO push (EPIC-017)
# ============================================================

def push_to_blo(repo_path: str, repo_yaml: dict, dry_run: bool = False) -> dict:
    """
    Pousse REPO.yaml vers BLO/WAL/{repo}/REPO.yaml via GitHub API.
    Retourne {"success": bool, "message": str, "url": str}.
    """
    import yaml
    import urllib.request
    import urllib.error
    import json as _json

    repo_name = Path(repo_path).name
    wal_path = BLO_WAL_PATH.format(repo=repo_name)

    # Construire le contenu
    content = yaml.dump(repo_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
    content_bytes = content.encode("utf-8")

    # Encoder en base64
    import base64
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")

    # Préparer la requête GitHub API
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return {"success": False, "message": "GITHUB_TOKEN non défini", "url": ""}

    url = f"https://api.github.com/repos/{BLO_WAL_REPO}/contents/{wal_path}"

    # Vérifier si le fichier existe déjà (pour obtenir le SHA)
    sha = None
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        })
        resp = urllib.request.urlopen(req)
        existing = _json.loads(resp.read())
        sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return {"success": False, "message": f"Erreur GitHub API: {e.code} {e.reason}", "url": ""}

    # Créer ou mettre à jour
    payload = {
        "message": f"chore: update REPO.yaml for {repo_name} (auto rss_lint)",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha

    if dry_run:
        return {"success": True, "message": f"[DRY RUN] Push vers {BLO_WAL_REPO}/{wal_path}", "url": f"https://github.com/{BLO_WAL_REPO}/blob/main/{wal_path}"}

    try:
        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="PUT", headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req)
        result = _json.loads(resp.read())
        return {"success": True, "message": "Pushé avec succès", "url": result.get("content", {}).get("html_url", "")}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {"success": False, "message": f"Erreur push: {e.code} {e.reason} {error_body[:200]}", "url": ""}


def batch_repos(repos_root: str, push_blo: bool = False) -> dict:
    """
    Audit batch de tous les repos dans repos_root.
    Retourne un résumé par repo.
    """
    import yaml as _yaml
    root = Path(repos_root)
    results = {}
    repos = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]

    for repo in sorted(repos, key=lambda x: x.name):
        name = repo.name
        try:
            yaml_data = generate_repo_yaml(str(repo))
            results[name] = {
                "status": "ok",
                "conformite": yaml_data["conformite"],
                "strate": yaml_data["strate"],
                "profil": yaml_data["profil"],
                "missing": yaml_data["dossiers_manquants"],
            }

            # Écrire REPO.yaml localement
            write_repo_yaml(str(repo), yaml_data)

            # Push BLO si demandé
            if push_blo:
                push_result = push_to_blo(str(repo), yaml_data, dry_run=True)
                results[name]["blo"] = push_result.get("message", "ok")

        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}

    return results

# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="RSS-v2 -- Gate de conformite")
    parser.add_argument("--repo", default=".", nargs="?", help="Chemin du repo a verifier (défaut: .). Non requis avec --batch.")
    parser.add_argument("--fix", action="store_true", help="Corriger automatiquement")
    parser.add_argument("--strict", action="store_true", help="Mode strict (WARN = FAIL)")
    parser.add_argument("--depth", type=int, choices=[2, 4], default=None,
                        help="Profondeur max (2=simple, 4=complexe). Auto-detecte si omis.")
    parser.add_argument("--check-git-noise", action="store_true",
                        help="Verifier le bruit git")
    parser.add_argument("--check-gitignore", action="store_true",
                        help="Verifier la couverture du .gitignore")
    parser.add_argument("--check-filesystem", action="store_true",
                        help="Verifier l'integrite du filesystem")
    parser.add_argument("--repo-type", type=str, default="default",
                        choices=["core", "cli", "mcp", "docs", "plugin", "tool", "infra", "default"],
                        help="Type de repo pour les seuils git noise")
    parser.add_argument("--check-artifacts", action="store_true",
                        help="Verifier la conformite des artefacts (PRD, ADR, EPIC, SPEC) -- checks de base")
    parser.add_argument("--check-governance", action="store_true",
                        help="Verifier la gouvernance artefacts (F1/F2/F3/F4/POST) -- checks complets")
    parser.add_argument("--check-git-engineering", action="store_true",
                        help="Verifier la conformite des conventions Git Engineering (git-engineering/)")
    parser.add_argument("--check-sot-ref", action="store_true",
                         help="Verifier la presence de sot_ref sur blocs registre externe (ADR-008)")
    parser.add_argument("--check-profile", action="store_true",
                         help="Verifier la conformite au profil RSS-v2 (§6) — required_dirs, forbidden_items, depth")
    parser.add_argument("--all-checks", action="store_true",
                         help="Activer toutes les verifications")
    parser.add_argument("--generate-repo-yaml", action="store_true",
                        help="Generer REPO.yaml pour le repo (EPIC-017)")
    parser.add_argument("--push-blo", action="store_true",
                        help="Push REPO.yaml vers BLO/WAL/ (EPIC-017)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mode dry-run (pas de push réel)")
    parser.add_argument("--batch", type=str, default=None, metavar="REPOS_ROOT",
                        help="Audit batch de tous les repos dans REPOS_ROOT (EPIC-017)")
    parser.add_argument("--index", choices=["rebuild"], default=None,
                        help="Reconstruire les index d'artefacts")
    parser.add_argument("--artifact-dir", type=str, default=None,
                        help="Dossier d'artefact cible pour --index (PRD, ADR, EPICS, SPEC). Tous si omis.")
    parser.add_argument("--scope", type=str, default=None,
                        help="Limiter le scan aux dossiers specifies (ex: ADR,PRD,EPICS). Tous si omis.")

    args = parser.parse_args()

    if args.all_checks:
        args.check_git_noise = True
        args.check_gitignore = True
        args.check_filesystem = True
        args.check_artifacts = True
        args.check_governance = True
        args.check_git_engineering = True
        args.check_sot_ref = True
        args.check_profile = True
        args.generate_repo_yaml = True

    # --check-governance implique --check-artifacts
    if args.check_governance:
        args.check_artifacts = True

    rssignore_patterns = load_rssignore(Path(args.repo))
    depth = args.depth or get_depth(Path(args.repo), rssignore_patterns)

    print(f"\n{'='*60}")
    print(f"RSS-v2 -- Gate de conformite")
    print(f"Repo: {args.repo}")
    print(f"Profondeur: {depth} niveaux")
    if args.repo_type != "default":
        print(f"Type: {args.repo_type}")
    print(f"{'='*60}\n")

    skip_filesystem = any(p.strip() == "skip-filesystem" for p in rssignore_patterns)
    skip_depth = any(p.strip() == "skip-depth-check" for p in rssignore_patterns)
    if skip_filesystem:
        args.check_filesystem = False
        print("[INFO] .rssignore: skip-filesystem active")
    if skip_depth:
        args.check_filesystem = False
        depth = 4
        print("[INFO] .rssignore: skip-depth-check active")

    # -- Index rebuild --
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

    # -- Git Noise --
    git_noise_result = None
    if args.check_git_noise:
        git_noise_result = check_git_noise(args.repo, args.repo_type)
        sev = git_noise_result.get("severity", "PASS")
        count = git_noise_result.get("count", 0)
        print(f"[{sev}] Git noise: {count} untracked files")
        if git_noise_result.get("files"):
            for f in git_noise_result["files"][:5]:
                print(f"   {f}")
            if count > 5:
                print(f"   ... et {count - 5} autres")

    # -- Gitignore --
    gitignore_result = None
    if args.check_gitignore:
        gitignore_result = check_gitignore_coverage(args.repo, args.repo_type)
        sev = gitignore_result.get("severity", "PASS")
        missing = gitignore_result.get("missing", [])
        print(f"[{sev}] .gitignore coverage: {len(missing)} patterns manquants")
        for m in missing:
            print(f"   manquant: {m}")

    # -- Filesystem --
    fs_result = None
    if args.check_filesystem:
        fs_result = check_filesystem_integrity(args.repo, rssignore_patterns)
        sev = fs_result.get("severity", "PASS")
        print(f"[{sev}] Filesystem: {fs_result['junction_count']} junctions, {fs_result['orphan_count']} orphelins")
        for j in fs_result.get("junctions", [])[:5]:
            print(f"   junction: {j}")
        for o in fs_result.get("orphan_files", [])[:5]:
            print(f"   orphelin: {o}")

    # -- Artifact checks (base + gouvernance) --
    artifact_violations = None
    if args.check_artifacts:
        artifact_violations = check_artifacts(args.repo)

        base_total = (
            len(artifact_violations["naming"]) +
            len(artifact_violations["frontmatter"]) +
            len(artifact_violations["index_missing"]) +
            len(artifact_violations["mirrors"]) +
            len(artifact_violations["stubs"]) +
            len(artifact_violations["status"])
        )
        gov_total = (
            len(artifact_violations["frontmatter_id"]) +
            len(artifact_violations["frontmatter_repo"]) +
            len(artifact_violations["duplicate_numbers"]) +
            len(artifact_violations["folder_canonical"]) +
            len(artifact_violations["superseded_chain"]) +
            len(artifact_violations["index_sync"])
        )
        artifact_total = base_total + gov_total

        if artifact_total == 0:
            print("[PASS] Artefacts de gouvernance: conformes RSS-v2")
        else:
            # -- Affichage checks de base --
            if artifact_violations["naming"]:
                print(f"[FAIL] Nommage artefacts ({len(artifact_violations['naming'])}):")
                for v in artifact_violations["naming"]:
                    print(f"   {v['file']} -> attendu: {v['pattern']}")
            if artifact_violations["frontmatter"]:
                print(f"[FAIL] Frontmatter manquant ({len(artifact_violations['frontmatter'])}):")
                for v in artifact_violations["frontmatter"]:
                    print(f"   {v['file']}: {v['error']}")
            if artifact_violations["status"]:
                print(f"[FAIL] Statuts invalides ({len(artifact_violations['status'])}):")
                for v in artifact_violations["status"]:
                    print(f"   {v['file']}: '{v['status']}' -> attendu: {v['valid']}")
            if artifact_violations["stubs"]:
                print(f"[FAIL] Stubs superseded invalides ({len(artifact_violations['stubs'])}):")
                for v in artifact_violations["stubs"]:
                    print(f"   {v['file']}: {v['error']}")
            if artifact_violations["mirrors"]:
                print(f"[FAIL] Mirrors non declares ({len(artifact_violations['mirrors'])}):")
                for v in artifact_violations["mirrors"]:
                    print(f"   {v['file']}: {v['error']}")
            if artifact_violations["index_missing"]:
                print(f"[FAIL] Index manquants ({len(artifact_violations['index_missing'])}):")
                for v in artifact_violations["index_missing"]:
                    print(f"   {v['dir']}/{v['expected']}")

            # -- Affichage checks gouvernance (F1/F2/F3/F4/POST) --
            if args.check_governance:
                if artifact_violations["frontmatter_id"]:
                    print(f"[FAIL] F1 frontmatter_id ({len(artifact_violations['frontmatter_id'])}):")
                    for v in artifact_violations["frontmatter_id"]:
                        print(f"   {v['file']}: {v['error']}")
                if artifact_violations["frontmatter_repo"]:
                    print(f"[FAIL] F1 frontmatter_repo ({len(artifact_violations['frontmatter_repo'])}):")
                    for v in artifact_violations["frontmatter_repo"]:
                        print(f"   {v['file']}: {v['error']}")
                if artifact_violations["duplicate_numbers"]:
                    print(f"[FAIL] F2 duplicate_numbers ({len(artifact_violations['duplicate_numbers'])}):")
                    for v in artifact_violations["duplicate_numbers"]:
                        print(f"   {v['artifact_dir']}/{v['number']}: {v['error']}")
                        print(f"      actifs: {', '.join(v.get('active_files', v['files']))}")
                        if v.get("inactive_files"):
                            print(f"      stubs inactifs: {', '.join(v['inactive_files'])}")
                if artifact_violations["folder_canonical"]:
                    print(f"[FAIL] F3 folder_canonical ({len(artifact_violations['folder_canonical'])}):")
                    for v in artifact_violations["folder_canonical"]:
                        print(f"   {v['dir']}/ -> devrait etre {v['canonical']}/")
                        if v["files"]:
                            print(f"      contient: {', '.join(v['files'][:5])}")
                if artifact_violations["superseded_chain"]:
                    print(f"[FAIL] F4 superseded_chain ({len(artifact_violations['superseded_chain'])}):")
                    for v in artifact_violations["superseded_chain"]:
                        print(f"   {v['file']}: {v['error']}")
                if artifact_violations["index_sync"]:
                    print(f"[FAIL] POST index_sync ({len(artifact_violations['index_sync'])}):")
                    for v in artifact_violations["index_sync"]:
                        print(f"   {v['index']}: {v['error']}")
                        for mf in v.get("missing_entries", [])[:5]:
                            print(f"      absent: {mf}")
                        for ph in v.get("placeholder_ids", []):
                            print(f"      placeholder: {ph}")

        # Fix artefacts
        if args.fix and artifact_total > 0:
            print(f"\nCorrection automatique artefacts...")
            fixed = fix_artifacts(args.repo, artifact_violations)
            print(f"{fixed} correction(s) appliquee(s) (le reste requiert intervention manuelle)")

    # -- Git Engineering checks --
    git_eng_violations = None
    if args.check_git_engineering:
        git_eng_violations = check_git_engineering(args.repo)

        ge_total = (
            (1 if git_eng_violations["dir_missing"] else 0) +
            len(git_eng_violations["missing_files"]) +
            len(git_eng_violations["extra_files"]) +
            len(git_eng_violations["max_lines"]) +
            len(git_eng_violations["missing_adr_ref"]) +
            len(git_eng_violations["missing_intent_ref"]) +
            len(git_eng_violations["real_repo_names"]) +
            len(git_eng_violations["unexpected_frontmatter"])
        )

        if ge_total == 0:
            print("[PASS] Git Engineering: conventions conformes")
        else:
            if git_eng_violations["dir_missing"]:
                print("[FAIL] Git Engineering: repertoire git-engineering/ absent")
            if git_eng_violations["missing_files"]:
                print(f"[FAIL] Git Engineering: fichiers manquants ({len(git_eng_violations['missing_files'])}):")
                for mf in git_eng_violations["missing_files"]:
                    print(f"   manquant: {mf}")
            if git_eng_violations["extra_files"]:
                print(f"[WARN] Git Engineering: fichiers non attendus ({len(git_eng_violations['extra_files'])}):")
                for ef in git_eng_violations["extra_files"]:
                    print(f"   supplementaire: {ef}")
            if git_eng_violations["max_lines"]:
                print(f"[FAIL] Git Engineering: depassement {GIT_ENG_MAX_LINES} lignes ({len(git_eng_violations['max_lines'])}):")
                for v in git_eng_violations["max_lines"]:
                    print(f"   {v['file']}: {v['lines']} lignes (max {v['max']})")
            if git_eng_violations["missing_adr_ref"]:
                print(f"[FAIL] Git Engineering: reference ADR-007 manquante ({len(git_eng_violations['missing_adr_ref'])}):")
                for mf in git_eng_violations["missing_adr_ref"]:
                    print(f"   {mf}")
            if git_eng_violations["missing_intent_ref"]:
                print(f"[FAIL] Git Engineering: reference INTENT-077 manquante ({len(git_eng_violations['missing_intent_ref'])}):")
                for mf in git_eng_violations["missing_intent_ref"]:
                    print(f"   {mf}")
            if git_eng_violations["real_repo_names"]:
                print(f"[FAIL] Git Engineering: noms de repo reels detectes ({len(git_eng_violations['real_repo_names'])}):")
                for v in git_eng_violations["real_repo_names"]:
                    print(f"   {v['file']}: {', '.join(v['matches'])} ({v['desc']})")
            if git_eng_violations["unexpected_frontmatter"]:
                print(f"[FAIL] Git Engineering: frontmatter YAML inattendu ({len(git_eng_violations['unexpected_frontmatter'])}):")
                for mf in git_eng_violations["unexpected_frontmatter"]:
                    print(f"   {mf} (les conventions Git Eng sont des fichiers purs, pas d'artefacts RSS-v2)")

    # -- SOT Ref check (ADR-008) --
    sot_ref_violations = None
    if args.check_sot_ref:
        sot_ref_violations = check_sot_ref(args.repo)
        sot_ref_total = len(sot_ref_violations)
        if sot_ref_total == 0:
            print("[PASS] sot_ref: tous les blocs registre externe sont conformes (ADR-008)")
        else:
            sev = "FAIL" if args.strict else "WARN"
            print(f"[{sev}] LINT_SOT_REF_MISSING: {sot_ref_total} bloc(s) sans sot_ref")
            for v in sot_ref_violations:
                print(f"   {v['file']}: {v['block']} -- {v['error']}")

    # -- Profile conformity check (RSS-v2 §6) --
    profile_violations = None
    if args.check_profile:
        # Vérifier si profil forcé dans .rssignore
        rssignore_path = Path(args.repo) / ".rssignore"
        forced_profil = None
        if rssignore_path.exists():
            for _line in rssignore_path.read_text(encoding="utf-8").splitlines():
                _line = _line.strip()
                if _line.startswith("profile:"):
                    forced_profil = _line.split(":", 1)[1].strip().upper()
                    break
        profile_violations = check_profile_conformity(args.repo, profil=forced_profil)
        profil_detecte = forced_profil if forced_profil else _detect_profil(args.repo)
        strate_detectee = _detect_strate(args.repo)
        total_profile = (
            len(profile_violations["missing_dirs"]) +
            len(profile_violations["forbidden_items"]) +
            len(profile_violations["depth_exceeded"]) +
            len(profile_violations["missing_files"])
        )
        if total_profile == 0 and not profile_violations["crosslinks_violation"]:
            print(f"[PASS] Profil {profil_detecte} (strate {strate_detectee}): conforme RSS-v2 §6")
        else:
            sev = "FAIL" if args.strict else "WARN"
            print(f"[{sev}] Profil {profil_detecte} (strate {strate_detectee}): {total_profile} violation(s)")
            for d in profile_violations["missing_dirs"]:
                print(f"   dossier manquant: {d}")
            for f in profile_violations["forbidden_items"]:
                print(f"   fichier interdit: {f}")
            for d in profile_violations["depth_exceeded"]:
                print(f"   profondeur dépassée: {d['path']} ({d['depth']} > {d['max']})")
            for f in profile_violations["missing_files"]:
                print(f"   fichier requis manquant: {f}")
            if profile_violations["crosslinks_violation"]:
                print(f"   CROSSLINKS: non conforme au profil {profil_detecte}")

    # -- Violations RSS-v2 standard --
    if violations["forbidden_root"]:
        print(f"[FAIL] Fichiers interdits a la racine ({len(violations['forbidden_root'])}):")
        for v in violations["forbidden_root"]:
            print(f"   {v['file']} -> devrait etre dans {v['destination']}")
    if violations["missing_dirs"]:
        print(f"[FAIL] Dossiers obligatoires manquants ({len(violations['missing_dirs'])}):")
        for d in violations["missing_dirs"]:
            print(f"   {d}")
    if violations["artefacts"]:
        print(f"[FAIL] Artefacts de run ({len(violations['artefacts'])}):")
        for a in violations["artefacts"]:
            print(f"   {a}")
    if violations["depth_exceeded"]:
        print(f"[FAIL] Profondeur depassee ({len(violations['depth_exceeded'])}):")
        for v in violations["depth_exceeded"]:
            print(f"   {v['path']} (profondeur {v['depth']} > max {v['max']})")
    if violations["config_misplaced"]:
        print(f"[WARN] Fichiers de config a la racine ({len(violations['config_misplaced'])}):")
        for v in violations["config_misplaced"]:
            print(f"   {v['file']} -> suggere: {v['destination']}")

    if args.fix and total_violations > 0:
        print(f"\nCorrection automatique RSS-v2...")
        fixed = fix_violations(args.repo, violations, depth)
        print(f"\n{fixed} correction(s) appliquee(s)")
    elif total_violations > 0:
        print(f"\n{total_violations} violation(s) RSS-v2 detectee(s) -- utilisez --fix pour corriger")

    # -- Statut final --
    artifact_failures = (
        artifact_violations is not None and (
            len(artifact_violations["naming"]) > 0 or
            len(artifact_violations["frontmatter"]) > 0 or
            len(artifact_violations["index_missing"]) > 0 or
            len(artifact_violations["mirrors"]) > 0 or
            len(artifact_violations["stubs"]) > 0 or
            len(artifact_violations["status"]) > 0 or
            (args.check_governance and (
                len(artifact_violations["frontmatter_id"]) > 0 or
                len(artifact_violations["frontmatter_repo"]) > 0 or
                len(artifact_violations["duplicate_numbers"]) > 0 or
                len(artifact_violations["folder_canonical"]) > 0 or
                len(artifact_violations["superseded_chain"]) > 0 or
                len(artifact_violations["index_sync"]) > 0
            ))
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
        or (git_eng_violations is not None and (
            git_eng_violations["dir_missing"] or
            len(git_eng_violations["missing_files"]) > 0 or
            len(git_eng_violations["max_lines"]) > 0 or
            len(git_eng_violations["missing_adr_ref"]) > 0 or
            len(git_eng_violations["missing_intent_ref"]) > 0 or
            len(git_eng_violations["real_repo_names"]) > 0 or
            len(git_eng_violations["unexpected_frontmatter"]) > 0
        ))
        or (sot_ref_violations is not None and len(sot_ref_violations) > 0 and args.strict)
        or (profile_violations is not None and (
            len(profile_violations["missing_dirs"]) > 0 or
            len(profile_violations["missing_files"]) > 0 or
            len(profile_violations["forbidden_items"]) > 0 or
            profile_violations["crosslinks_violation"]
        ))
    )

    has_warns = (
        len(violations["config_misplaced"]) > 0 or
        (git_noise_result and git_noise_result.get("severity") == "WARN") or
        (gitignore_result and gitignore_result.get("severity") == "WARN") or
        (fs_result and fs_result.get("severity") == "WARN") or
        (sot_ref_violations is not None and len(sot_ref_violations) > 0 and not args.strict)
        or (profile_violations is not None and len(profile_violations["depth_exceeded"]) > 0)
    )

    # -- Generate REPO.yaml & Push BLO (avant exit) --
    if args.generate_repo_yaml:
        import yaml as _yaml
        print(f"\n[GEN] Génération REPO.yaml pour: {args.repo}")
        try:
            yaml_data = generate_repo_yaml(args.repo)
            yaml_path = write_repo_yaml(args.repo, yaml_data)
            print(f"[OK] REPO.yaml généré: {yaml_path}")
            print(f"   repo: {yaml_data['repo']}")
            print(f"   strate: {yaml_data['strate']}, profil: {yaml_data['profil']}")
            print(f"   conformite: {yaml_data['conformite']}")
            if yaml_data["dossiers_manquants"]:
                print(f"   dossiers_manquants: {', '.join(yaml_data['dossiers_manquants'])}")
        except Exception as e:
            print(f"[FAIL] Erreur génération: {e}")

    if args.push_blo:
        import yaml as _yaml
        print(f"\n[PUSH] Push REPO.yaml vers BLO/WAL/ pour: {args.repo}")
        try:
            yaml_data = generate_repo_yaml(args.repo)
            is_dry = getattr(args, 'dry_run', False)
            if is_dry:
                result = push_to_blo(args.repo, yaml_data, dry_run=True)
            else:
                result = push_to_blo(args.repo, yaml_data, dry_run=False)
            status = "OK" if result["success"] else "FAIL"
            print(f"[{status}] {result['message']}")
            if result.get("url"):
                print(f"   URL: {result['url']}")
        except Exception as e:
            print(f"[FAIL] Erreur push: {e}")

    # -- Statut final --
    if has_failures or (args.strict and has_warns):
        print(f"\n[FAIL] Repo non conforme RSS-v2")
        sys.exit(1)
    elif has_warns:
        print(f"\n[WARN] Violations mineures -- repo fonctionnel mais non standardise")
        sys.exit(0)
    else:
        print(f"\n[PASS] Repo conforme RSS-v2")
        sys.exit(0)


if __name__ == "__main__":
    main()
