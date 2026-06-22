#!/usr/bin/env python3
"""Causal Consolidation — PRD-047.

Implémente les opérations causales φ1, φ4, φ6 :
  φ1 — Causal chain detection (détection de chaînes causales)
  φ4 — Counterfactual propagation (propagation contrefactuelle)
  φ6 — Drift causal attribution (attribution causale de dérive)

Usage:
    python -m world-model.causal_consolidation --phi 1 --events events.json
    python -m world-model.causal_consolidation --phi 4 --hypothesis "What if ADR-072 rejected?"
    python -m world-model.causal_consolidation --phi 6 --drift-report report.json
"""

from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

NEXUS_ROOT = Path(__file__).resolve().parent.parent
CAUSAL_LOG = NEXUS_ROOT / ".nexus" / "causal_log.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_causal_event(phi: int, operation: str, input_data: dict, output_data: dict):
    """Log un événement causal."""
    CAUSAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": _now_iso(),
        "phi": phi,
        "operation": operation,
        "input": input_data,
        "output": output_data,
        "hash": hashlib.sha256(json.dumps(output_data, sort_keys=True).encode()).hexdigest()[:16],
    }
    with open(CAUSAL_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def phi1_causal_chain_detection(events: list[dict]) -> dict:
    """φ1 — Détecte les chaînes causales dans une liste d'événements."""
    chains = []
    for i, event in enumerate(events):
        causes = event.get("causes", [])
        effects = event.get("effects", [])
        if causes or effects:
            chain = {
                "event": event.get("id", f"event_{i}"),
                "causes": causes,
                "effects": effects,
                "causal_depth": len(causes),
            }
            chains.append(chain)

    # Détecter les chaînes complètes
    complete_chains = []
    for chain in chains:
        if chain["causes"] and chain["effects"]:
            complete_chains.append(chain)

    return {
        "phi": 1,
        "operation": "causal_chain_detection",
        "total_events": len(events),
        "chains_found": len(chains),
        "complete_chains": len(complete_chains),
        "chains": complete_chains[:10],  # Limiter à 10 pour la lisibilité
    }


def phi4_counterfactual_propagation(hypothesis: str, current_state: dict) -> dict:
    """φ4 — Propage un scénario contrefactuel."""
    # Évaluer l'impact de l'hypothèse sur l'état courant
    impact_score = 0.0
    affected_fields = []

    # Mots-clés d'impact
    high_impact = {"rejected", "deleted", "broken", "conflict", "drift", "failed"}
    medium_impact = {"changed", "updated", "modified", "moved", "deprecated"}

    hyp_lower = hypothesis.lower()
    for word in high_impact:
        if word in hyp_lower:
            impact_score += 0.3
    for word in medium_impact:
        if word in hyp_lower:
            impact_score += 0.15

    impact_score = min(1.0, impact_score)

    # Identifier les champs affectés
    for key in current_state:
        if isinstance(current_state[key], str):
            for word in high_impact | medium_impact:
                if word in current_state[key].lower():
                    affected_fields.append(key)

    return {
        "phi": 4,
        "operation": "counterfactual_propagation",
        "hypothesis": hypothesis,
        "impact_score": round(impact_score, 2),
        "affected_fields": list(set(affected_fields)),
        "recommendation": "HITL_REVIEW" if impact_score > 0.5 else "AUTO_ACCEPT",
    }


def phi6_drift_causal_attribution(drift_report: dict) -> dict:
    """φ6 — Attribue causally les dérives détectées."""
    drift_items = drift_report.get("drift_items", [])
    attributions = []

    for item in drift_items:
        drift_type = item.get("type", "UNKNOWN")
        severity = item.get("severity", "LOW")

        # Attribution causale simplifiée
        if drift_type == "ADR_WRONG_STATUS":
            cause = "ADR status not updated after acceptance"
            root = "Missing post-acceptance hook"
        elif drift_type == "ADR_NOT_INDEXED":
            cause = "ADR created but not added to index"
            root = "Incomplete ADR creation workflow"
        elif drift_type == "EPIC_OVERSIZE":
            cause = "EPIC grew beyond size limit"
            root = "No size enforcement on EPIC updates"
        elif drift_type == "STRUCTURE_VIOLATION":
            cause = "File placed in wrong location"
            root = "Missing pre-commit structure check"
        elif drift_type == "REPO_MISSING_SOT":
            cause = "Repo tracked without STATUS.yaml"
            root = "Incomplete tracking initialization"
        elif drift_type == "WORKFLOW_MISSING":
            cause = "Required workflow file missing"
            root = "Cleanup deleted tracked workflow"
        else:
            cause = "Unknown drift source"
            root = "Unattributed"

        attributions.append({
            "drift_type": drift_type,
            "severity": severity,
            "immediate_cause": cause,
            "root_cause": root,
            "file": item.get("file", "unknown"),
        })

    return {
        "phi": 6,
        "operation": "drift_causal_attribution",
        "total_drifts": len(drift_items),
        "attributions": attributions,
        "high_severity_count": sum(1 for a in attributions if a["severity"] == "HIGH"),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Causal Consolidation φ1/φ4/φ6")
    parser.add_argument("--phi", type=int, choices=[1, 4, 6], required=True, help="φ operation")
    parser.add_argument("--events", type=str, help="JSON events file (φ1)")
    parser.add_argument("--hypothesis", type=str, help="Counterfactual hypothesis (φ4)")
    parser.add_argument("--current-state", type=str, help="Current state JSON (φ4)")
    parser.add_argument("--drift-report", type=str, help="Drift report JSON (φ6)")
    args = parser.parse_args()

    if args.phi == 1:
        if not args.events:
            print("Error: --events required for φ1", file=sys.stderr)
            sys.exit(1)
        events = json.loads(Path(args.events).read_text())
        result = phi1_causal_chain_detection(events)
    elif args.phi == 4:
        if not args.hypothesis:
            print("Error: --hypothesis required for φ4", file=sys.stderr)
            sys.exit(1)
        current = {}
        if args.current_state:
            current = json.loads(Path(args.current_state).read_text())
        result = phi4_counterfactual_propagation(args.hypothesis, current)
    elif args.phi == 6:
        if not args.drift_report:
            print("Error: --drift-report required for φ6", file=sys.stderr)
            sys.exit(1)
        drift = json.loads(Path(args.drift_report).read_text())
        result = phi6_drift_causal_attribution(drift)
    else:
        result = {"error": "Invalid phi"}

    entry = _log_causal_event(args.phi, result.get("operation", "unknown"), vars(args), result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
