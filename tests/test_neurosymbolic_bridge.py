#!/usr/bin/env python3
"""Tests round-trip O4 — Neurosymbolic Bridge.

Vérifie que le bridge BRAIN → NEXUS produit des verdicts corrects
et respecte le SLA < 200ms.

Usage:
    python -m pytest tests/test_neurosymbolic_bridge.py -v
    python tests/test_neurosymbolic_bridge.py
"""

import json
import sys
import time
import unittest
from pathlib import Path

# Ajout du path NEXUS pour imports
NEXUS_ROOT = Path(__file__).resolve().parent.parent
if str(NEXUS_ROOT) not in sys.path:
    sys.path.insert(0, str(NEXUS_ROOT))

from nexus.bridge.neurosymbolic import NeurosymbolicBridge, SIGNAL_TYPES, VERDICT_TYPES


class TestNeurosymbolicBridge(unittest.TestCase):
    """Tests du bridge neurosymbolique."""

    @classmethod
    def setUpClass(cls):
        cls.bridge = NeurosymbolicBridge()

    # --- Tests de base ---

    def test_ontology_context_loaded(self):
        """Le contexte JSON-LD doit être chargé (ou fallback)."""
        self.assertTrue(self.bridge.ontology.is_loaded())

    def test_all_signal_types_handled(self):
        """Tous les types de signaux doivent produire un verdict."""
        for signal_type in SIGNAL_TYPES:
            signal = {"type": signal_type, "content": {}, "source": "test"}
            verdict = self.bridge.process_signal(signal)
            self.assertIn("verdict", verdict)
            self.assertIn(verdict["verdict"], VERDICT_TYPES)

    def test_unknown_signal_type(self):
        """Un type inconnu doit produire UNKNOWN."""
        signal = {"type": "foobar", "content": {}, "source": "test"}
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "UNKNOWN")

    # --- Tests par type de signal ---

    def test_intent_valid(self):
        """Intent avec hash valide → ACCEPT."""
        signal = {
            "type": "intent",
            "content": {"intent_hash": "0xABC123", "action": "update_status"},
            "source": "BRAIN",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ACCEPT")

    def test_intent_missing_hash(self):
        """Intent sans hash → REVIEW."""
        signal = {
            "type": "intent",
            "content": {"action": "update_status"},
            "source": "BRAIN",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "REVIEW")

    def test_intent_sensitive_action(self):
        """Intent avec action sensible → ESCALATE."""
        signal = {
            "type": "intent",
            "content": {"intent_hash": "0xABC", "action": "set_conflict"},
            "source": "BRAIN",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ESCALATE")

    def test_anomaly_critical(self):
        """Anomalie critique → ESCALATE."""
        signal = {"type": "anomaly", "content": {"severity": "critical"}, "source": "GOV"}
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ESCALATE")

    def test_anomaly_low(self):
        """Anomalie basse → ACCEPT."""
        signal = {"type": "anomaly", "content": {"severity": "low"}, "source": "GOV"}
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ACCEPT")

    def test_drift_above_threshold(self):
        """Drift au-dessus du seuil → REVIEW."""
        signal = {
            "type": "drift",
            "content": {"phi_cps_delta": 0.08, "threshold": 0.05},
            "source": "phi-cps",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "REVIEW")

    def test_drift_critical(self):
        """Drift critique (2x seuil) → ESCALATE."""
        signal = {
            "type": "drift",
            "content": {"phi_cps_delta": 0.15, "threshold": 0.05},
            "source": "phi-cps",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ESCALATE")

    def test_drift_normal(self):
        """Drift normal → ACCEPT."""
        signal = {
            "type": "drift",
            "content": {"phi_cps_delta": 0.01, "threshold": 0.05},
            "source": "phi-cps",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ACCEPT")

    def test_conflict(self):
        """Conflit inter-repo → ESCALATE."""
        signal = {
            "type": "conflict",
            "content": {"repositories": ["NEXUS", "BRAIN"]},
            "source": "sync",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ESCALATE")

    def test_certification_valid(self):
        """Certification valide → ACCEPT."""
        signal = {
            "type": "certification",
            "content": {"cert_level": "L_STANDARD"},
            "source": "UAE",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ACCEPT")

    def test_certification_unknown(self):
        """Certification inconnue → REVIEW."""
        signal = {
            "type": "certification",
            "content": {"cert_level": "L_UNKNOWN"},
            "source": "UAE",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "REVIEW")

    def test_query(self):
        """Requête état → ACCEPT."""
        signal = {"type": "query", "content": {"repo": "NEXUS"}, "source": "agent"}
        verdict = self.bridge.process_signal(signal)
        self.assertEqual(verdict["verdict"], "ACCEPT")

    # --- Tests de structure du verdict ---

    def test_verdict_has_required_fields(self):
        """Chaque verdict doit avoir les champs requis."""
        signal = {"type": "query", "content": {}, "source": "test"}
        verdict = self.bridge.process_signal(signal)
        required = ["verdict", "severity", "reason", "signal", "timestamp", "verdict_hash", "latency_ms", "sla_met", "ontology_context_loaded"]
        for field in required:
            self.assertIn(field, verdict, f"Champ manquant: {field}")

    def test_verdict_hash_format(self):
        """Le verdict hash doit être au format 0xHEX."""
        signal = {"type": "query", "content": {}, "source": "test"}
        verdict = self.bridge.process_signal(signal)
        self.assertTrue(verdict["verdict_hash"].startswith("0x"))
        self.assertEqual(len(verdict["verdict_hash"]), 18)  # 0x + 16 hex

    # --- Tests de performance (SLA < 200ms) ---

    def test_sla_single_signal(self):
        """Un seul signal doit être traité en < 200ms."""
        signal = {
            "type": "intent",
            "content": {"intent_hash": "0xPERF", "action": "update_status"},
            "source": "perf-test",
        }
        verdict = self.bridge.process_signal(signal)
        self.assertLess(verdict["latency_ms"], 200.0,
                        f"SLA violé: {verdict['latency_ms']:.2f}ms")

    def test_sla_batch_100(self):
        """100 signaux doivent tous respecter le SLA."""
        signals = [
            {"type": "drift", "content": {"phi_cps_delta": 0.01 * i, "threshold": 0.05}, "source": f"batch-{i}"}
            for i in range(100)
        ]
        violations = 0
        for signal in signals:
            verdict = self.bridge.process_signal(signal)
            if not verdict["sla_met"]:
                violations += 1
        self.assertEqual(violations, 0, f"{violations}/100 signaux ont violé le SLA")

    def test_stats(self):
        """Les stats doivent être cohérentes."""
        bridge = NeurosymbolicBridge()
        for i in range(10):
            bridge.process_signal({"type": "query", "content": {}, "source": "stats-test"})
        stats = bridge.get_stats()
        self.assertEqual(stats["total_signals"], 10)
        self.assertGreaterEqual(stats["avg_latency_ms"], 0)
        self.assertGreaterEqual(stats["max_latency_ms"], stats["min_latency_ms"])

    # --- Tests de résolution sémantique ---

    def test_resolve_term(self):
        """La résolution de termes via le contexte doit fonctionner."""
        iri = self.bridge.ontology.resolve_term("name")
        # Même en fallback, "name" doit être résolu
        self.assertIsNotNone(iri)

    def test_resolve_unknown_term(self):
        """Un terme inconnu retourne None."""
        iri = self.bridge.ontology.resolve_term("xyz_nonexistent")
        self.assertIsNone(iri)


if __name__ == "__main__":
    unittest.main(verbosity=2)
