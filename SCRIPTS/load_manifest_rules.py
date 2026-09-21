#!/usr/bin/env python3
"""Load branch routing rules from manifest YAML for KIVA-CLI pre-push hook."""
from __future__ import annotations

import json
import os
import sys

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_manifest_rules(manifest_path: str, repo_name: str) -> dict:
    """Return rules dict for the given repo from manifest YAML."""
    if not os.path.isfile(manifest_path):
        return {}

    if yaml is None:
        print("PyYAML unavailable; cannot load manifest rules.", file=sys.stderr)
        return {}

    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    repos = manifest.get("branch_routing", {}).get("repositories", {})
    cfg = repos.get(repo_name, {})

    return {
        "forbidden_paths": cfg.get("forbidden_paths", []),
        "allowed_prefixes": cfg.get("allowed_branch_prefixes", []),
        "redirect_map": cfg.get("redirect_map", {}),
    }


if __name__ == "__main__":
    manifest_path = sys.argv[1] if len(sys.argv) > 1 else ""
    repo_name = sys.argv[2] if len(sys.argv) > 2 else ""
    rules = load_manifest_rules(manifest_path, repo_name)
    print(json.dumps(rules))
