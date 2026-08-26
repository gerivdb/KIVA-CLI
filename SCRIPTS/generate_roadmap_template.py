#!/usr/bin/env python3
"""
scripts/generate_roadmap_template.py — RSS-v3 ROADMAPS/ template generator v2.

Crée le dossier ROADMAPS/ avec les 5 fichiers template standard :
  - blockers.yaml
  - dependencies.yaml
  - history.yaml
  - milestones.yaml
  - vector.yaml

Schéma v2 (RSS-v3.1) — ajoute :
  - dimensions d0-d7 (VECTUS-03)
  - vision_layer (HOLOVISION / VISION FRACTALE / OMNIVISION)
  - thought_commits (vectorisation temporelle longue)

Optionnellement, fait automatiquement le git add + commit.

Usage:
    python generate_roadmap_template.py <repo_path> [--commit] [--push]
    python generate_roadmap_template.py <repo_path> --v1  # rétrocompatibilité

Exemple:
    python generate_roadmap_template.py /path/to/my/repo --commit
    python generate_roadmap_template.py . --commit --push
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE_VERSION = "2.0"
TEMPLATE_INTENT_HASH = "0XROADMAP_TEMPLATE_V2_20260626"
TEMPLATE_VERSION_V1 = "1.0"
TEMPLATE_INTENT_HASH_V1 = "0XROADMAP_TEMPLATE_V1_20260626"


def generate_blockers_yaml(repo_name: str, version: str = None, intent_hash: str = None) -> str:
    v = version or TEMPLATE_VERSION
    ih = intent_hash or TEMPLATE_INTENT_HASH
    return f"""type: ROADMAP_BLOCKERS
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
blockers: []
severity_critical: 0
severity_high: 0
severity_medium: 0
"""


def generate_dependencies_yaml(repo_name: str, version: str = None, intent_hash: str = None) -> str:
    v = version or TEMPLATE_VERSION
    ih = intent_hash or TEMPLATE_INTENT_HASH
    return f"""type: ROADMAP_DEPENDENCIES
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
dependencies: []
"""


def generate_history_yaml(repo_name: str, version: str = None, intent_hash: str = None) -> str:
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')
    v = version or TEMPLATE_VERSION
    ih = intent_hash or TEMPLATE_INTENT_HASH
    if v == TEMPLATE_VERSION:
        # v2 schema — history.yaml est append-only, structure amendments[]
        return f"""type: ROADMAP_HISTORY
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
amendments:
  - date: '{now}'
    event: init
    description: ROADMAPS/ directory initialized (RSS-v3 v2 — VECTUS-03)
    actor: generate_roadmap_template.py
    causal_ref: ''
    significance: 0.0
    delta_vector: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
"""
    else:
        # v1 legacy
        return f"""type: ROADMAP_HISTORY
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
entries:
  - timestamp: '{now}'
    action: init
    description: ROADMAPS/ directory initialized (RSS-v3 standard)
    author: generate_roadmap_template.py
"""


def generate_milestones_yaml(repo_name: str, version: str = None, intent_hash: str = None) -> str:
    v = version or TEMPLATE_VERSION
    ih = intent_hash or TEMPLATE_INTENT_HASH
    if v == TEMPLATE_VERSION:
        return f"""type: ROADMAP_MILESTONES
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
milestones: []
dimension_targets: {{}}
"""
    else:
        return f"""type: ROADMAP_MILESTONES
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
milestones: []
"""


def generate_vector_yaml(repo_name: str, strate: str = "UNKNOWN", version: str = None, intent_hash: str = None) -> str:
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')
    v = version or TEMPLATE_VERSION
    ih = intent_hash or TEMPLATE_INTENT_HASH
    if v == TEMPLATE_VERSION:
        # v2 schema — VECTUS-03 dimensions + triple vision + thought_commits
        return f"""type: ROADMAP_VECTOR
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
strate: {strate}
vector:
  horizon: 90d
  direction: []
  velocity_observed: 0.0
  mass: 0.5
  last_amended: '{now}'
  _inferred: true
  _inference_source: generate_roadmap_template.py (mass deploy v2)
  dimensions:
    d0_stabilisation: 0.0
    d1_extension: 0.0
    d2_integration: 0.0
    d3_formalisation: 0.0
    d4_deprecation: 0.0
    d5_performance: 0.0
    d6_gouvernance: 0.0
    d7_experimentation: 0.0
  vision_layer:
    holovision: ''
    fractale_strate: ''
    omnivision_role: ''
  thought_commits: []
"""
    else:
        # v1 legacy
        return f"""type: ROADMAP_VECTOR
version: '{v}'
intent_hash: {ih}
date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d')}'
repo: {repo_name}
strate: {strate}
vector:
  horizon: 90d
  direction: []
  velocity_observed: 0.0
  mass: 0.5
  last_amended: '{now}'
  _inferred: true
  _inference_source: generate_roadmap_template.py (mass deploy)
"""


def deploy_roadmaps(repo_path: str, commit: bool = False, push: bool = False, use_v1: bool = False) -> dict:
    """Crée ROADMAPS/ dans le repo cible et optionnellement commit.
    
    Args:
        repo_path: Chemin vers le repo cible
        commit: Faire git add + commit
        push: Push après commit
        use_v1: Utiliser le schéma v1 (rétrocompatibilité)
    """
    repo = Path(repo_path).resolve()
    result = {"repo": str(repo), "files_created": [], "committed": False, "pushed": False, "errors": [], "schema_version": "v1" if use_v1 else "v2"}

    if not repo.exists():
        result["errors"].append(f"Chemin inexistant: {repo}")
        return result

    # Détecter le nom du repo depuis git remote ou dossier
    repo_name = repo.name
    try:
        os.chdir(str(repo))
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10
        )
        if remote.returncode == 0 and remote.stdout.strip():
            url = remote.stdout.strip()
            if "/" in url:
                repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    except Exception:
        pass

    # Détecter la strate depuis le chemin
    strate = "UNKNOWN"
    parts = str(repo).split(os.sep)
    for p in parts:
        if p.startswith("L") and len(p) >= 2 and p[1].isdigit():
            strate = p
            break

    # Sélection du schéma
    if use_v1:
        v = TEMPLATE_VERSION_V1
        ih = TEMPLATE_INTENT_HASH_V1
    else:
        v = TEMPLATE_VERSION
        ih = TEMPLATE_INTENT_HASH

    roadmaps_dir = repo / "ROADMAPS"
    roadmaps_dir.mkdir(exist_ok=True)

    files = {
        "blockers.yaml": generate_blockers_yaml(repo_name, v, ih),
        "dependencies.yaml": generate_dependencies_yaml(repo_name, v, ih),
        "history.yaml": generate_history_yaml(repo_name, v, ih),
        "milestones.yaml": generate_milestones_yaml(repo_name, v, ih),
        "vector.yaml": generate_vector_yaml(repo_name, strate, v, ih),
    }

    for filename, content in files.items():
        fpath = roadmaps_dir / filename
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")
            result["files_created"].append(str(fpath.relative_to(repo)))

    # Git add + commit si demandé
    if commit and result["files_created"]:
        try:
            os.chdir(str(repo))
            subprocess.run(
                ["git", "add", "ROADMAPS/"],
                check=True, capture_output=True, text=True, timeout=15
            )
            schema_tag = "v1" if use_v1 else "v2"
            commit_msg = f"feat(rss-v3.{schema_tag[1:]}): add ROADMAPS directory (template {schema_tag})"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True, capture_output=True, text=True, timeout=15
            )
            result["committed"] = True

            if push:
                subprocess.run(
                    ["git", "push"],
                    check=True, capture_output=True, text=True, timeout=30
                )
                result["pushed"] = True
        except subprocess.CalledProcessError as e:
            result["errors"].append(f"Erreur git: {e}")
        except subprocess.TimeoutExpired:
            result["errors"].append("Timeout git")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="RSS-v3 ROADMAPS/ template generator v2 (VECTUS-03)"
    )
    parser.add_argument(
        "repo_path", type=str, default=".",
        help="Chemin vers le repo cible (défaut: .)"
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Faire le git add + commit après création"
    )
    parser.add_argument(
        "--push", action="store_true",
        help="Push après commit (implique --commit)"
    )
    parser.add_argument(
        "--v1", action="store_true",
        help="Utiliser le schéma v1 (rétrocompatibilité)"
    )
    args = parser.parse_args()

    if args.push:
        args.commit = True

    result = deploy_roadmaps(args.repo_path, commit=args.commit, push=args.push, use_v1=args.v1)

    schema = result.get("schema_version", "v2")
    print(f"[ROADMAPS] repo={result['repo']} schema={schema}")
    print(f"  files_created={len(result['files_created'])}")
    for f in result["files_created"]:
        print(f"    + {f}")
    if result["committed"]:
        print(f"  [COMMIT] feat(rss-v3.{schema[1:]}): add ROADMAPS directory (template {schema})")
    if result["pushed"]:
        print(f"  [PUSH] pushed to remote")
    if result["errors"]:
        print(f"  [ERRORS]")
        for e in result["errors"]:
            print(f"    ! {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
