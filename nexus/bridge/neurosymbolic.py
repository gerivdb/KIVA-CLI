#!/usr/bin/env python3
"""NEXUS Neurosymbolic Bridge — O4.

Bridge entre signaux BRAIN (neuronaux) et verdicts NEXUS (symboliques).
Utilise le contexte JSON-LD de ONTOLOGY pour l'alignement sémantique.

Round-trip cible : BRAIN signal → NEXUS verdict < 200ms.

Usage:
    python -m nexus.bridge.neurosymbolic --signal '{"type": "intent", "content": "..."}'
    python -m nexus.bridge.neurosymbolic --verify
"""

from __future__ import annotations

import json
import hashlib
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
NEXUS_ROOT = Path(__file__).resolve().parent.parent.parent  # nexus/bridge/ -> NEXUS/
ONTOLOGY_ROOT = Path(r"D:\DO\WEB\TOOLS\ONTOLOGY")
CONTEXT_JSONLD = ONTOLOGY_ROOT / "context.jsonld"
SCHEMA_DIR = ONTOLOGY_ROOT / "schema"

# ---------------------------------------------------------------------------
# Chargement du contexte JSON-LD
# ---------------------------------------------------------------------------

class OntologyContext:
    """Charge et expose le contexte JSON-LD de ONTOLOGY."""

    _instance: Optional["OntologyContext"] = None
    _context: dict = {}
    _loaded: bool = False

    def __new__(cls) -> "OntologyContext":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self) -> bool:
        """Charge le contexte JSON-LD depuis ONTOLOGY/context.jsonld."""
        if self._loaded:
            return True
        try:
            if CONTEXT_JSONLD.exists():
                self._context = json.loads(CONTEXT_JSONLD.read_text(encoding="utf-8"))
                self._loaded = True
                return True
            # Fallback: contexte minimal inline
            self._context = self._minimal_context()
            self._loaded = True
            return True
        except Exception:
            self._context = self._minimal_context()
            self._loaded = True
            return False

    @staticmethod
    def _minimal_context() -> dict:
        """Contexte minimal de fallback si context.jsonld indisponible."""
        return {
            "@context": {
                "ontology": "https://github.com/gerivdb/ONTOLOGY#",
                "nexus": "https://github.com/gerivdb/NEXUS#",
                "name": "rdfs:label",
                "description": "rdfs:comment",
                "intent_hash": "ontology:intentHash",
                "nexus_status": "nexus:status",
                "Repo": "ontology:Repository",
                "Agent": "ontology:Agent",
                "Bridge": "ontology:Bridge",
            }
        }

    @property
    def context(self) -> dict:
        if not self._loaded:
            self.load()
        return self._context

    def resolve_term(self, term: str) -> Optional[str]:
        """Résout un terme court en IRI complète via le contexte."""
        ctx = self.context.get("@context", {})
        return ctx.get(term)

    def is_loaded(self) -> bool:
        return self._loaded


# ---------------------------------------------------------------------------
# Types de signaux BRAIN
# ---------------------------------------------------------------------------

SIGNAL_TYPES = {
    "intent": "Signal d'intention agent",
    "anomaly": "Détection d'anomalie",
    "drift": "Dérive φ-CPS",
    "conflict": "Conflit inter-repo",
    "certification": "Certification niveau agent",
    "query": "Requête état NEXUS",
}

# ---------------------------------------------------------------------------
# Verdicts NEXUS
# ---------------------------------------------------------------------------

VERDICT_TYPES = {
    "ACCEPT": {"code": "ACCEPT", "severity": 0, "description": "Signal conforme"},
    "REVIEW": {"code": "REVIEW", "severity": 1, "description": "Revue HITL recommandée"},
    "ESCALATE": {"code": "ESCALATE", "severity": 2, "description": "Escalade HITL obligatoire"},
    "REJECT": {"code": "REJECT", "severity": 3, "description": "Signal rejeté"},
    "UNKNOWN": {"code": "UNKNOWN", "severity": -1, "description": "Type de signal inconnu"},
}


# ---------------------------------------------------------------------------
# Bridge principal
# ---------------------------------------------------------------------------

class NeurosymbolicBridge:
    """Bridge BRAIN → NEXUS.

    Transforme un signal BRAIN (JSON brut) en verdict NEXUS (structuré)
    en utilisant le contexte JSON-LD de ONTOLOGY pour l'alignement sémantique.
    """

    def __init__(self):
        self.ontology = OntologyContext()
        self.ontology.load()
        self._stats = {"total": 0, "latency_ms": []}

    def process_signal(self, signal: dict) -> dict:
        """Traite un signal BRAIN et produit un verdict NEXUS.

        Args:
            signal: Dict avec au minimum {"type": str, "content": any}

        Returns:
            Dict avec verdict structuré.
        """
        t0 = time.monotonic()

        signal_type = signal.get("type", "unknown")
        content = signal.get("content", {})
        source = signal.get("source", "unknown")

        # 1. Classification du signal
        if signal_type not in SIGNAL_TYPES:
            verdict = self._make_verdict("UNKNOWN", signal, "Type de signal inconnu")
        elif signal_type == "intent":
            verdict = self._process_intent(content, source)
        elif signal_type == "anomaly":
            verdict = self._process_anomaly(content, source)
        elif signal_type == "drift":
            verdict = self._process_drift(content, source)
        elif signal_type == "conflict":
            verdict = self._process_conflict(content, source)
        elif signal_type == "certification":
            verdict = self._process_certification(content, source)
        elif signal_type == "query":
            verdict = self._process_query(content, source)
        else:
            verdict = self._make_verdict("UNKNOWN", signal, f"Non géré: {signal_type}")

        # 2. Calcul latence
        latency_ms = (time.monotonic() - t0) * 1000
        verdict["latency_ms"] = round(latency_ms, 2)
        self._stats["total"] += 1
        self._stats["latency_ms"].append(latency_ms)

        # 3. Vérification SLA (< 200ms)
        verdict["sla_met"] = latency_ms < 200.0

        return verdict

    def _process_intent(self, content: dict, source: str) -> dict:
        """Traite un signal d'intention."""
        intent_hash = content.get("intent_hash", "")
        action = content.get("action", "")

        # Résolution sémantique via le contexte
        action_iri = self.ontology.resolve_term(action)

        if not intent_hash:
            return self._make_verdict("REVIEW", {"content": content, "source": source},
                                      "Intent hash manquant — revue HITL")

        if action in ("create_tracking", "update_status", "set_field"):
            return self._make_verdict("ACCEPT", {"content": content, "source": source},
                                      f"Intent valide → {action_iri or action}")
        elif action in ("set_conflict", "escalate"):
            return self._make_verdict("ESCALATE", {"content": content, "source": source},
                                      f"Action sensible → {action_iri or action}")
        else:
            return self._make_verdict("REVIEW", {"content": content, "source": source},
                                      f"Action inconnue → {action}")

    def _process_anomaly(self, content: dict, source: str) -> dict:
        """Traite un signal d'anomalie."""
        severity = content.get("severity", "low")

        if severity in ("critical", "high"):
            return self._make_verdict("ESCALATE", {"content": content, "source": source},
                                      f"Anomalie {severity} — escalade HITL")
        elif severity == "medium":
            return self._make_verdict("REVIEW", {"content": content, "source": source},
                                      f"Anomalie {severity} — revue recommandée")
        else:
            return self._make_verdict("ACCEPT", {"content": content, "source": source},
                                      f"Anomalie {severity} — logué")

    def _process_drift(self, content: dict, source: str) -> dict:
        """Traite un signal de dérive φ-CPS."""
        delta = content.get("phi_cps_delta", 0.0)
        threshold = content.get("threshold", 0.05)

        if abs(delta) > threshold * 2:
            return self._make_verdict("ESCALATE", {"content": content, "source": source},
                                      f"Drift critique: {delta:+.4f} (seuil: {threshold:+.4f})")
        elif abs(delta) > threshold:
            return self._make_verdict("REVIEW", {"content": content, "source": source},
                                      f"Drift détecté: {delta:+.4f} (seuil: {threshold:+.4f})")
        else:
            return self._make_verdict("ACCEPT", {"content": content, "source": source},
                                      f"Drift normal: {delta:+.4f}")

    def _process_conflict(self, content: dict, source: str) -> dict:
        """Traite un signal de conflit inter-repo."""
        repos = content.get("repositories", [])
        return self._make_verdict("ESCALATE", {"content": content, "source": source},
                                  f"Conflit inter-repo: {', '.join(repos)} — HITL obligatoire")

    def _process_certification(self, content: dict, source: str) -> dict:
        """Traite un signal de certification agent."""
        cert_level = content.get("cert_level", "L_GENESIS")

        if cert_level in ("L_GENESIS", "L_STANDARD", "L_APOGEE"):
            return self._make_verdict("ACCEPT", {"content": content, "source": source},
                                      f"Certification valide: {cert_level}")
        else:
            return self._make_verdict("REVIEW", {"content": content, "source": source},
                                      f"Niveau inconnu: {cert_level}")

    def _process_query(self, content: dict, source: str) -> dict:
        """Traite un signal de requête état NEXUS."""
        return self._make_verdict("ACCEPT", {"content": content, "source": source},
                                  "Requête état — pas d'action requise")

    def _make_verdict(self, verdict_code: str, signal: dict, reason: str) -> dict:
        """Construit un verdict structuré."""
        v = VERDICT_TYPES.get(verdict_code, VERDICT_TYPES["UNKNOWN"])
        ts = datetime.now(timezone.utc).isoformat()
        raw = json.dumps(signal, ensure_ascii=False, default=str)
        vhash = "0x" + hashlib.sha256(f"{verdict_code}::{raw}::{ts}".encode()).hexdigest()[:16].upper()

        return {
            "verdict": v["code"],
            "severity": v["severity"],
            "reason": reason,
            "signal": signal,
            "timestamp": ts,
            "verdict_hash": vhash,
            "ontology_context_loaded": self.ontology.is_loaded(),
        }

    def get_stats(self) -> dict:
        """Retourne les statistiques du bridge."""
        latencies = self._stats["latency_ms"]
        return {
            "total_signals": self._stats["total"],
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "max_latency_ms": round(max(latencies), 2) if latencies else 0,
            "min_latency_ms": round(min(latencies), 2) if latencies else 0,
            "sla_violations": sum(1 for l in latencies if l >= 200.0),
            "ontology_loaded": self.ontology.is_loaded(),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Point d'entrée CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="NEXUS Neurosymbolic Bridge")
    parser.add_argument("--signal", type=str, help="Signal JSON à traiter")
    parser.add_argument("--verify", action="store_true", help="Vérification round-trip")
    parser.add_argument("--stats", action="store=True", help="Afficher statistiques")
    args = parser.parse_args()

    bridge = NeurosymbolicBridge()

    if args.verify:
        _run_verification(bridge)
        return

    if args.signal:
        try:
            signal = json.loads(args.signal)
        except json.JSONDecodeError as exc:
            print(json.dumps({"error": f"JSON invalide: {exc}"}, ensure_ascii=False))
            sys.exit(1)
        verdict = bridge.process_signal(signal)
        print(json.dumps(verdict, indent=2, ensure_ascii=False, default=str))
        return

    if args.stats:
        print(json.dumps(bridge.get_stats(), indent=2))
        return

    # Mode par défaut: vérification
    _run_verification(bridge)


def _run_verification(bridge: NeurosymbolicBridge) -> None:
    """Exécute le test de round-trip O4."""
    print("=" * 60)
    print("  NEXUS Neurosymbolic Bridge — Round-trip verification")
    print("=" * 60)

    test_signals = [
        {"type": "intent", "content": {"intent_hash": "0xABC", "action": "update_status"}, "source": "BRAIN"},
        {"type": "anomaly", "content": {"severity": "critical"}, "source": "GOV-ENGINE"},
        {"type": "drift", "content": {"phi_cps_delta": 0.12, "threshold": 0.05}, "source": "phi-cps-check"},
        {"type": "conflict", "content": {"repositories": ["NEXUS", "BRAIN"]}, "source": "sync"},
        {"type": "certification", "content": {"cert_level": "L_STANDARD"}, "source": "UAE"},
        {"type": "query", "content": {"repo": "NEXUS"}, "source": "agent"},
        {"type": "unknown", "content": {}, "source": "test"},
    ]

    all_sla_met = True
    for signal in test_signals:
        verdict = bridge.process_signal(signal)
        sla = "✅" if verdict["sla_met"] else "❌"
        if not verdict["sla_met"]:
            all_sla_met = False
        print(f"\n  Signal: {signal['type']:<15} → Verdict: {verdict['verdict']:<10} "
              f"Latency: {verdict['latency_ms']:>7.2f}ms  SLA: {sla}")
        print(f"    Reason: {verdict['reason']}")

    stats = bridge.get_stats()
    print(f"\n{'=' * 60}")
    print(f"  Stats: {stats['total_signals']} signals | "
          f"Avg: {stats['avg_latency_ms']:.2f}ms | "
          f"Max: {stats['max_latency_ms']:.2f}ms | "
          f"SLA violations: {stats['sla_violations']}")
    print(f"  Ontology context loaded: {stats['ontology_loaded']}")
    print(f"  SLA < 200ms: {'✅ PASS' if all_sla_met else '❌ FAIL'}")
    print(f"{'=' * 60}")

    sys.exit(0 if all_sla_met else 1)


if __name__ == "__main__":
    main()
