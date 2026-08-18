"""Legacy registry sync verification.

This module was originally a standalone script under the repo root.
It is retained here for regression checks, but no longer exits the
interpreter on missing sources.
"""

import json
import os
from pathlib import Path

import yaml
import pytest


ECOS_ROOT = os.environ.get(
    "ECOS_ROOT",
    r"D:\DO\WEB\TOOLS\ECOS_ROOT.json",
)
TOPOS_REGISTRY = os.environ.get(
    "TOPOS_REGISTRY",
    r"D:\DO\WEB\TOOLS\L1-INFRA\TOPOS\registry\repos.json",
)
KNOWN_REPOS = os.environ.get(
    "KNOWN_REPOS",
    r"D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB\known_repositories.yaml",
)
OUTPUT_DIR = Path(
    os.environ.get(
        "OUTPUT_DIR",
        r"D:\DO\WEB\TOOLS\reports\ecosystem-orchestration",
    )
)


def _load_sources():
    sources = {}
    errors = []

    try:
        with open(ECOS_ROOT, "r", encoding="utf-8") as f:
            sources["ecos_root"] = json.load(f)
    except Exception as e:
        errors.append(f"ECOS_ROOT.json: {e}")

    try:
        with open(TOPOS_REGISTRY, "r", encoding="utf-8") as f:
            sources["topos"] = json.load(f)
    except Exception as e:
        errors.append(f"TOPOS/registry/repos.json: {e}")

    try:
        with open(KNOWN_REPOS, "r", encoding="utf-8") as f:
            sources["known_repos"] = yaml.safe_load(f)
    except Exception as e:
        errors.append(f"known_repositories.yaml: {e}")

    return sources, errors


def test_registry_sources_loadable():
    sources, errors = _load_sources()
    for e in errors:
        pytest.fail(e, pytrace=False)

    assert "ecos_root" in sources or "topos" in sources or "known_repos" in sources


def test_registry_drift_detection():
    sources, errors = _load_sources()
    for e in errors:
        pytest.fail(e, pytrace=False)

    repos = {}
    if "ecos_root" in sources and "repos" in sources["ecos_root"]:
        repos["ecos_root"] = {r["name"] for r in sources["ecos_root"]["repos"]}

    if "topos" in sources and "repos" in sources["topos"]:
        repos["topos"] = {
            r["full_name"].replace("gerivdb/", "") for r in sources["topos"]["repos"]
        }

    if "known_repos" in sources and "repositories" in sources["known_repos"]:
        repos["known_repos"] = {
            r["name"] for r in sources["known_repos"]["repositories"]
        }

    all_names = set()
    for v in repos.values():
        all_names.update(v)

    missing = []
    for name in sorted(all_names):
        present = {k: name in v for k, v in repos.items()}
        if not all(present.values()):
            missing.append(
                {
                    "repo": name,
                    "absent_from": [k for k, v in present.items() if not v],
                }
            )

    assert not missing, missing
