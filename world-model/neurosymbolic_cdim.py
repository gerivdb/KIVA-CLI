#!/usr/bin/env python3
"""Neurosymbolic CDIM Protocol — PRD-050.

Protocole d'échange JSON-LD entre le neurosymbolic bridge (O4)
et le module CDIM. Produit des verdicts structurés au format JSON-LD.

Usage:
    python -m world-model.neurosymbolic_cdim --signal '{"type": "intent", ...}'
    python -m world-model.neurosymbolic_cdim --round-trip
"""

from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

NEXUS_ROOT = Path(__file__).resolve().parent.parent

# Imports depuis les modules CDIM
sys.path.insert(0, str(Path(__file__).resolve().parent))
from world_model_verse import WorldModelVerse
from causal_consolidation import phi1_causal_chain_detection, phi4_counterfactual_propagation, phi6_drift_causal_attribution
from counterfactual_keel import evaluate_scenario, PREDEFINED_SCENARIOS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_jsonld(verdict: dict, signal: dict) -> dict:
    """Enveloppe un verdict dans un document JSON-LD."""
    return {
        "@context": "https://github.com/gerivdb/ONTOLOGY",
        "@type": "nexus:Verdict",
        "verdict": verdict.get("verdict", "UNKNOWN"),
        "severity": verdict.get("severity", -1),
        "signal": signal,
        "reason": verdict.get("reason", ""),
        "timestamp": _now_iso(),
        "verdictHash": verdict.get("verdict_hash", "0x0"),
        "phiCpsScore": verdict.get("phi_cps_score", 0.0),
        "slaMet": verdict.get("sla_met", True),
        "cdimAnnotations": {
            "worldModelRef": "world-model/world_model_verse.py",
            "causalRef": "world-model/causal_consolidation.py",
            "counterfactualRef": "world-model/counterfactual_keel.py",
        },
    }


def process_signal_neurosymbolic(signal: dict) -> dict:
    """Traite un signal BRAIN via le neurosymbolic bridge + CDIM."""
    from nexus.bridge.neurosymbolic import NeurosymbolicBridge
    bridge = NeurosymbolicPipeline()
    return bridge.process_signal(signal)


class NeurosymbolicPipeline:
    """Pipeline complet: signal → neurosymbolic → CDIM → JSON-LD verdict."""

    def __init__(self):
        self.wm = WorldModelVerse()

    def process_signal(self, signal: dict) -> dict:
        """Pipeline complet."""
        # Étape 1: Neurosymbolic base
        from nexus.bridge.neurosymbolic import NeurosymbolicBridge
        base = NeurosymbolicBridge()
        verdict = base.process_signal(signal)

        # Étape 2: Causal consolidation (φ6) si drift détecté
        if signal.get("type") == "drift":
            drift_report = {
                "drift_items": [{
                    "type": "SIGNAL_DRIFT",
                    "severity": "HIGH" if verdict.get("severity", 0) > 1 else "MEDIUM",
                    "description": verdict.get("reason", ""),
                }]
            }
            causal = phi6_drift_causal_attribution(drift_report)
            verdict["cdim_causal"] = causal

        # Étape 3: Counterfactual pour les signaux d'intention
        if signal.get("type") == "intent":
            hypothesis = signal.get("content", {}).get("action", "unknown")
            cf = evaluate_scenario({
                "id": f"0xNS_{hashlib.sha256(json.dumps(signal).encode()).hexdigest()[:8].upper()}",
                "question": f"What if intent '{hypothesis}' failed?",
                "impact_areas": ["nexus_status", "workflow"],
                "severity": "MEDIUM",
            })
            verdict["cdim_counterfactual"] = cf

        # Étape 4: World Model state
        state = self.wm.capture_state(signal.get("source", "NEXUS"))
        verdict["world_model_state"] = state

        # Étape 5: Enveloppe JSON-LD
        jsonld = _make_jsonld(verdict, signal)
        verdict["jsonld"] = jsonld

        return verdict


def run_round_trip_test() -> dict:
        """Test round-trip complet: signal → CDIM → JSON-LD."""
        test_signals = [
            {"type": "intent", "content": {"intent_hash": "0xRT001", "action": "update_status"}, "source": "BRAIN"},
            {"type": "drift", "content": {"phi_cps_delta": 0.12, "threshold": 0.05}, "source": "phi-cps-check"},
            {"type": "anomaly", "content": {"severity": "critical"}, "source": "GOV-ENGINE"},
        ]

        pipeline = NeurosymbolicPipeline()
        results = []
        all_pass = True

        for signal in test_signals:
            verdict = pipeline.process_signal(signal)
            sla_met = verdict.get("sla_met", False)
            has_jsonld = "jsonld" in verdict
            passed = sla_met and has_jsonld
            if not passed:
                all_pass = False
            results.append({
                "signal_type": signal["type"],
                "verdict": verdict.get("verdict"),
                "sla_met": sla_met,
                "has_jsonld": has_jsonld,
                "passed": passed,
            })

        return {
            "test": "neurosymbolic_cdim_round_trip",
            "results": results,
            "all_passed": all_pass,
            "timestamp": _now_iso(),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Neurosymbolic CDIM Protocol")
    parser.add_argument("--signal", type=str, help="JSON signal to process")
    parser.add_argument("--round-trip", action="store_true", help="Run round-trip test")
    args = parser.parse_args()

    if args.round_trip:
        result = run_round_trip_test()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["all_passed"] else 1)

    if args.signal:
        try:
            signal = json.loads(args.signal)
        except json.JSONDecodeError as exc:
            print(json.dumps({"error": f"Invalid JSON: {exc}"}, ensure_ascii=False))
            sys.exit(1)
    else:
        signal = {"type": "query", "content": {"repo": "NEXUS"}, "source": "test"}

    pipeline = NeurosymbolicPipeline()
    result = pipeline.process_signal(signal)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
