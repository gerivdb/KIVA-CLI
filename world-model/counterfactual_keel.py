#!/usr/bin/env python3
"""Counterfactual Keel — PRD-048.

Moteur de raisonnement contrefactuel pour NEXUS.
Génère des scénarios "What if?" et évalue leur impact sur l'écosystème.

Usage:
    python -m world-model.counterfactual_keel --scenario "What if O3 was delayed?"
    python -m world-model.counterfactual_keel --list-scenarios
    python -m world-model.counterfactual_keel --evaluate --scenario-id 0xABC
"""

from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

NEXUS_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = NEXUS_ROOT / ".nexus" / "counterfactual_scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

# Scénaires prédéfinés NEXUS v3
PREDEFINED_SCENARIOS = [
    {
        "id": "0xCF001",
        "question": "What if O3 (API v3) was delayed by 30 days?",
        "impact_areas": ["O4_neurosymbolic_bridge", "ADR_072", "KIVA_CLI"],
        "severity": "HIGH",
    },
    {
        "id": "0xCF002",
        "question": "What if O4 (neurosymbolic bridge) was rejected?",
        "impact_areas": ["CDIM", "world_model", "context_jsonld"],
        "severity": "CRITICAL",
    },
    {
        "id": "0xCF003",
        "question": "What if GOV-ENGINE scan frequency was reduced to daily?",
        "impact_areas": ["drift_detection", "issue_response_time"],
        "severity": "MEDIUM",
    },
    {
        "id": "0xCF004",
        "question": "What if context.jsonld was not created?",
        "impact_areas": ["O4_bridge", "CDIM_integration", "jsonld_protocol"],
        "severity": "HIGH",
    },
    {
        "id": "0xCF005",
        "question": "What if BDCP mode was accidentally disabled?",
        "impact_areas": ["network_anonymity", "token_quota", "security"],
        "severity": "CRITICAL",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_scenario(scenario: dict) -> dict:
    """Évalue l'impact d'un scénario contrefactuel."""
    impact_areas = scenario.get("impact_areas", [])
    severity = scenario.get("severity", "LOW")

    # Calculer un score d'impact
    severity_scores = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.8, "CRITICAL": 1.0}
    base_score = severity_scores.get(severity, 0.1)
    area_score = min(0.3, len(impact_areas) * 0.1)
    total_impact = min(1.0, base_score + area_score)

    # Générer des recommendations
    recommendations = []
    if total_impact > 0.7:
        recommendations.append("IMMEDIATE: Escalate to HITL — critical impact detected")
    if "O4" in str(impact_areas) or "neurosymbolic" in str(impact_areas):
        recommendations.append("Review neurosymbolic bridge dependencies")
    if "BDCP" in str(impact_areas) or "security" in str(impact_areas):
        recommendations.append("Verify BDCP clapet status before proceeding")
    if "GOV-ENGINE" in str(impact_areas) or "drift" in str(impact_areas):
        recommendations.append("Adjust scan frequency or force manual scan")
    if not recommendations:
        recommendations.append("Standard monitoring sufficient")

    return {
        "scenario_id": scenario.get("id", "UNKNOWN"),
        "question": scenario.get("question", ""),
        "severity": severity,
        "impact_score": round(total_impact, 2),
        "impact_areas": impact_areas,
        "recommendations": recommendations,
        "evaluated_at": _now_iso(),
    }


def list_scenarios() -> list[dict]:
    """Liste tous les scénarios disponibles."""
    return PREDEFINED_SCENARIOS


def save_evaluation(evaluation: dict) -> Path:
    """Sauvegarde une évaluation."""
    scenario_id = evaluation.get("scenario_id", "unknown")
    path = SCENARIOS_DIR / f"eval_{scenario_id}.json"
    path.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Counterfactual Keel")
    parser.add_argument("--scenario", type=str, help="Question contrefactuelle")
    parser.add_argument("--scenario-id", type=str, help="ID du scénario à évaluer")
    parser.add_argument("--list-scenarios", action="store_true", help="Lister les scénarios")
    parser.add_argument("--evaluate", action="store_true", help="Évaluer un scénario")
    parser.add_argument("--all", action="store_true", help="Évaluer tous les scénarios")
    args = parser.parse_args()

    if args.list_scenarios:
        scenarios = list_scenarios()
        for s in scenarios:
            print(f"  {s['id']} [{s['severity']}] {s['question']}")
        return

    if args.all:
        results = []
        for scenario in PREDEFINED_SCENARIOS:
            result = evaluate_scenario(scenario)
            save_evaluation(result)
            results.append(result)
            icon = "🔴" if result["impact_score"] > 0.7 else ("🟡" if result["impact_score"] > 0.4 else "🟢")
            print(f"  {icon} {result['scenario_id']}: impact={result['impact_score']} — {scenario['question'][:60]}...")
        print(f"\n{len(results)} scenarios evaluated. Saved to {SCENARIOS_DIR}")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if args.evaluate:
        # Chercher par ID ou par question
        target = None
        if args.scenario_id:
            target = next((s for s in PREDEFINED_SCENARIOS if s["id"] == args.scenario_id), None)
        elif args.scenario:
            target = next((s for s in PREDEFINED_SCENARIOS if args.scenario.lower() in s["question"].lower()), None)
            if not target:
                # Créer un scénario ad-hoc
                target = {
                    "id": f"0xADHOC_{hashlib.sha256(args.scenario.encode()).hexdigest()[:8].upper()}",
                    "question": args.scenario,
                    "impact_areas": ["unknown"],
                    "severity": "MEDIUM",
                }
        if not target:
            print("Scenario not found. Use --list-scenarios to see available IDs.")
            sys.exit(1)

        result = evaluate_scenario(target)
        path = save_evaluation(result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\nSaved: {path}")
        return

    # Par défaut: lister
    scenarios = list_scenarios()
    for s in scenarios:
        print(f"  {s['id']} [{s['severity']}] {s['question']}")


if __name__ == "__main__":
    main()
