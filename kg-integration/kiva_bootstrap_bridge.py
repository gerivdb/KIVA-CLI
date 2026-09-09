#!/usr/bin/env python3
# kiva_bootstrap_bridge.py
# Génère un bootstrap state KG-L pour KIVA-CLI
# Utilise le lattice KG-L pour initialiser les intents KIVA

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

LATTICE_ROOT = os.environ.get("LATTICE_ROOT", "D:/lattice")
KG_EXPORT_DIR = os.path.join(LATTICE_ROOT, "L4", "kg_export")
KIVA_OUTPUT = r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI\kg-integration\kiva_bootstrap.json"


def parse_args():
    parser = argparse.ArgumentParser(description="KG-L to KIVA-CLI bootstrap")
    parser.add_argument("--generate", action="store_true", help="Generate bootstrap state")
    parser.add_argument("--latest", action="store_true", help="Use latest KG-L export")
    return parser.parse_args()


def generate_bootstrap() -> dict:
    """Génère le state de bootstrap KIVA depuis KG-L"""
    
    # Chercher le dernier export KG-L
    latest_kg = None
    latest_time = 0
    if os.path.exists(KG_EXPORT_DIR):
        for f in Path(KG_EXPORT_DIR).glob("*.kg.json"):
            ftime = f.stat().st_mtime
            if ftime > latest_time:
                latest_time = ftime
                latest_kg = str(f)

    if not latest_kg:
        # Use a default bootstrap graph
        graph = {
            "nodes": [
                {"id": "intent_root", "type": "concept", "value": "Moteur Narratif Souverain"},
                {"id": "voltx_pipeline", "type": "entity", "value": "VOLTX pipeline"},
                {"id": "lattice_bridge", "type": "entity", "value": "lattice synchronization"},
                {"id": "bootstrap_state", "type": "entity", "value": "bootstrap state for KIVA"}
            ],
            "edges": [
                {"source": "intent_root", "target": "voltx_pipeline", "relation": "engendre"},
                {"source": "voltx_pipeline", "target": "lattice_bridge", "relation": "synchronise"},
                {"source": "lattice_bridge", "target": "bootstrap_state", "relation": "produit"}
            ],
            "graph_hash": "kiva_bootstrap_default"
        }
    else:
        with open(latest_kg) as f:
            graph = json.load(f)
        print(f"[KIVA] Using KG-L export: {Path(latest_kg).name}")

    # Générer le state de bootstrap
    bootstrap = {
        "type": "kiva_bootstrap_state",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "graph_source": latest_kg or "default",
        "intents": [],
        "pipeline_config": {
            "lattice_root": LATTICE_ROOT,
            "kg_l_export": KG_EXPORT_DIR,
            "bootstrap_timeout_s": 5,
            "target_score": 110
        }
    }

    # Extraire les intents depuis le graphe
    for node in graph.get("nodes", []):
        if node.get("type") in ("concept", "entity"):
            bootstrap["intents"].append({
                "id": node["id"],
                "label": node.get("value", ""),
                "type": node["type"],
                "status": "pending",
                "priority": "medium"
            })

    # Extraire les connexions comme actions
    for edge in graph.get("edges", []):
        src = next((n for n in bootstrap["intents"] if n["id"] == edge["source"]), None)
        tgt = next((n for n in bootstrap["intents"] if n["id"] == edge["target"]), None)
        if src and tgt:
            src["actions"] = src.get("actions", [])
            src["actions"].append({
                "target": tgt["id"],
                "relation": edge["relation"],
                "pipeline_phase": edge.get("relation", "unknown")
            })

    os.makedirs(os.path.dirname(KIVA_OUTPUT) if os.path.dirname(KIVA_OUTPUT) else ".", exist_ok=True)
    with open(KIVA_OUTPUT, "w") as f:
        json.dump(bootstrap, f, indent=2)

    return {
        "status": "success",
        "output": KIVA_OUTPUT,
        "intents": len(bootstrap["intents"]),
        "graph_source": latest_kg or "default"
    }


def main():
    args = parse_args()
    
    if args.generate or args.latest:
        result = generate_bootstrap()
        print(f"[KIVA] Bootstrap generated: {result['intents']} intents")
        print(f"[KIVA] Output: {result['output']}")
        print(f"[KIVA] Source: {result['graph_source']}")
        sys.exit(0)
    
    print("[KIVA] Usage: --generate [--latest]")


if __name__ == "__main__":
    main()
