#!/usr/bin/env python3
"""World Model Verse — PRD-046.

World model φ-CPS aware pour NEXUS. Intègre le neurosymbolic bridge (O4)
et le causal consolidation (PRD-047) pour produire des prédictions
d'état écosystème.

Usage:
    python -m world-model.world_model_verse --predict --repo NEXUS
    python -m world-model.world_model_verse --state
"""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

NEXUS_ROOT = Path(__file__).resolve().parent.parent
STATES_DIR = NEXUS_ROOT / ".nexus" / "world_model_states"
STATES_DIR.mkdir(parents=True, exist_ok=True)


class WorldModelVerse:
    """World model φ-CPS aware."""

    def __init__(self):
        self.state: dict = {}
        self.phi_cps_score: float = 0.0
        self.last_updated: str = ""

    def capture_state(self, repo: str = "NEXUS") -> dict:
        """Capture l'état courant d'un repo."""
        ts = datetime.now(timezone.utc).isoformat()

        # Lire STATUS.yaml
        status_file = NEXUS_ROOT / ".nexus" / "STATUS.yaml"
        status = {}
        if status_file.exists():
            try:
                import yaml
                status = yaml.safe_load(status_file.read_text()) or {}
            except ImportError:
                for line in status_file.read_text().splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        status[k.strip()] = v.strip().strip('"')

        # Compter les fichiers trackés
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True, text=True, cwd=str(NEXUS_ROOT), timeout=10
            )
            tracked_files = result.stdout.strip().splitlines() if result.returncode == 0 else []
        except Exception:
            tracked_files = []

        # Calculer φ-CPS score (simplifié)
        adr_count = len(list((NEXUS_ROOT / "ADR").glob("ADR-*.md"))) if (NEXUS_ROOT / "ADR").exists() else 0
        workflow_count = len(list((NEXUS_ROOT / ".github" / "workflows").glob("*.yml"))) if (NEXUS_ROOT / ".github" / "workflows").exists() else 0
        self.phi_cps_score = min(1.0, (adr_count * 0.1 + workflow_count * 0.2 + len(tracked_files) * 0.001))

        self.state = {
            "repo": repo,
            "timestamp": ts,
            "nexus_status": status.get("nexus_status", "UNKNOWN"),
            "tracked_files": len(tracked_files),
            "adr_count": adr_count,
            "workflow_count": workflow_count,
            "phi_cps_score": round(self.phi_cps_score, 4),
            "conflict_flag": str(status.get("conflict_flag", "false")).lower() in ("true", "1"),
        }
        self.last_updated = ts
        return self.state

    def predict(self, repo: str = "NEXUS") -> dict:
        """Prédit l'état futur du repo."""
        current = self.capture_state(repo)
        state_hash = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()[:16]

        # Prédiction simple basée sur φ-CPS
        if current["phi_cps_score"] > 0.8:
            prediction = "STABLE"
            confidence = 0.9
        elif current["phi_cps_score"] > 0.5:
            prediction = "EVOLVING"
            confidence = 0.7
        else:
            prediction = "DRIFT_RISK"
            confidence = 0.5

        return {
            "current_state": current,
            "prediction": prediction,
            "confidence": confidence,
            "state_hash": f"0x{state_hash.upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def save_state(self) -> Path:
        """Sauvegarde l'état courant."""
        if not self.state:
            self.capture_state()
        state_file = STATES_DIR / f"state_{self.state.get('repo', 'unknown')}.json"
        state_file.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")
        return state_file

    def load_state(self, repo: str = "NEXUS") -> Optional[dict]:
        """Charge un état sauvegardé."""
        state_file = STATES_DIR / f"state_{repo}.json"
        if state_file.exists():
            self.state = json.loads(state_file.read_text())
            return self.state
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="World Model Verse")
    parser.add_argument("--predict", action="store_true", help="Prédire l'état futur")
    parser.add_argument("--state", action="store_true", help="Capturer l'état courant")
    parser.add_argument("--repo", default="NEXUS", help="Repo cible")
    args = parser.parse_args()

    wm = WorldModelVerse()

    if args.predict:
        result = wm.predict(args.repo)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.state:
        state = wm.capture_state(args.repo)
        path = wm.save_state()
        print(json.dumps(state, indent=2, ensure_ascii=False))
        print(f"\nState saved: {path}")
    else:
        # Par défaut: capture + prédiction
        state = wm.capture_state(args.repo)
        prediction = wm.predict(args.repo)
        print(json.dumps({"state": state, "prediction": prediction}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
