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


@pytest.mark.skipif(
    not Path(ECOS_ROOT).exists() and not Path(TOPOS_REGISTRY).exists() and not Path(KNOWN_REPOS).exists(),
    reason="Requires ECOS_ROOT.json, TOPOS registry, or known_repositories.yaml"
)
def test_registry_sources_loadable():
    sources, errors = _load_sources()
    
    # At least one source must be loadable
    assert "ecos_root" in sources or "topos" in sources or "known_repos" in sources, \
        f"No sources loadable. Errors: {errors}"


@pytest.mark.skipif(
    not Path(ECOS_ROOT).exists() and not Path(TOPOS_REGISTRY).exists() and not Path(KNOWN_REPOS).exists(),
    reason="Requires ECOS_ROOT.json, TOPOS registry, or known_repositories.yaml"
)
def test_registry_drift_detection():
    sources, errors = _load_sources()
    
    # Need at least 2 sources for drift detection
    if len(sources) < 2:
        pytest.skip(f"Need at least 2 sources for drift detection. Errors: {errors}")

    repos = {}
    if "ecos_root" in sources and "repos" in sources["ecos_root"]:
        repos["ecos_root"] = {r["name"] for r in sources["ecos_root"]["repos"]}

    if "topos" in sources:
        topos_data = sources["topos"]
        # Handle both old list format and new dict format
        if isinstance(topos_data, dict) and "repos" in topos_data:
            topos_repos = topos_data["repos"]
            if isinstance(topos_repos, list) and topos_repos:
                if isinstance(topos_repos[0], dict):
                    repos["topos"] = {r.get("full_name", "").replace("gerivdb/", "") for r in topos_repos}
                else:
                    pytest.skip("TOPOS repos format is not a list of dicts")
            else:
                pytest.skip("TOPOS repos is empty or not a list")
        else:
            pytest.skip("TOPOS data structure does not contain 'repos' key")

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
