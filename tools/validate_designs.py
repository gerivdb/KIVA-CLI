"""Validation des designs KG-L (GF-15) — KIVA-CLI.

IntentHash: 0xPRD_MOC_VOLTX_PHASE2_KG_L_ENGINE_20260905
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_registry(root: Path) -> Path | None:
    candidates = [
        root / "known_repositories.yaml",
        root.parents[1] / "L0-CANON" / "GOVERNANCE-HUB" / "known_repositories.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _export_kg_l(registry_path: Path, output_path: Path) -> int:
    try:
        import yaml
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[KG-L-GF15] FAILED — yaml load: {exc}")
        return 1

    entries = []
    for repo in registry.get("P0_REPOS", registry.get("repositories", [])):
        entries.append({
            "id": repo.get("name"),
            "name": repo.get("name"),
            "sources": ["known_repositories"],
            "layer": repo.get("layer", repo.get("strata", "")),
            "status": repo.get("status", "ACTIVE"),
            "local_path": repo.get("local_path"),
            "remote": repo.get("remote", repo.get("url", "")),
            "role": repo.get("role", ""),
            "intent_hash": repo.get("intent_hash", ""),
            "logical_layers": repo.get("logical_layers", []),
            "entity_type": repo.get("entity_type", "REPO"),
        })

    graph = {
        "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "count": len(entries),
        "nodes": entries,
    }

    output_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[KG-L-GF15] exported {len(entries)} nodes -> {output_path}")
    return 0


def validate_designs(scope: str = "kg-l") -> int:
    if scope != "kg-l":
        print(f"[KG-L-GF15] unknown scope={scope}")
        return 1

    root = Path(__file__).resolve().parents[1]
    registry = _find_registry(root)
    if registry is None:
        print("[KG-L-GF15] missing registry")
        return 1

    output = root / "KG-L" / "docs" / "ecosystem_kg_full.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if _export_kg_l(registry, output) != 0:
        return 1

    print("[KG-L-GF15] PASSED")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KG-L validate_designs")
    parser.add_argument("--scope", default="kg-l")
    args = parser.parse_args()
    sys.exit(validate_designs(args.scope))
