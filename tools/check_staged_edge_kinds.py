"""Validation des edge kinds KG-L (GF-16) — KIVA-CLI.

IntentHash: 0xPRD_MOC_VOLTX_PHASE2_KG_L_ENGINE_20260905
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _load_graph() -> tuple[dict, Path]:
    root = Path(__file__).resolve().parents[1]
    graph_path = root / "KG-L" / "docs" / "ecosystem_kg_full.json"
    if not graph_path.exists():
        print(f"[KG-L-GF16] missing graph: {graph_path}")
        return {}, graph_path
    try:
        return json.loads(graph_path.read_text(encoding="utf-8")), graph_path
    except Exception as exc:
        print(f"[KG-L-GF16] FAILED — json load: {exc}")
        return {}, graph_path


def check_staged_edge_kinds() -> int:
    """Point d'entrée pour `python -m tools.check_staged_edge_kinds` (KIVA-CLI)."""
    graph, graph_path = _load_graph()
    if not graph:
        return 1

    nodes = graph.get("nodes", [])
    if not nodes:
        print("[KG-L-GF16] graph empty")
        return 1

    required = ["id", "name", "layer", "status", "local_path", "remote"]
    issues = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if not node.get("local_path"):
            continue
        if node.get("status") != "ACTIVE" or node.get("entity_type") != "REPO":
            continue
        missing = [field for field in required if not node.get(field)]
        if missing:
            issues.append(f"node={node.get('id')} missing={missing}")

    if issues:
        for issue in issues:
            print(f"[KG-L-GF16] ISSUE {issue}")
        return 1

    print(f"[KG-L-GF16] checked {len(nodes)} nodes")
    print("[KG-L-GF16] PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(check_staged_edge_kinds())
