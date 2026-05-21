#!/usr/bin/env python3
import json, math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
from pathlib import Path

class PhiCPSLevel(Enum):
    GENESIS = 4.092
    EMERGENT = 4.398
    CONSCIOUS = 4.701
    AUTONOMOUS = 5.000

class PhiCPSManager:
    """ECOS-CLI φ-CPS Management & Calculation System"""

    PHI_GENESIS_CURRENT = 4.092
    PHI_CURRENT = 4.239
    PHI_THRESHOLD = 0.05

    WEIGHTS = {
        "complexity": 0.25, "autonomy": 0.20, "adaptability": 0.20,
        "reliability": 0.15, "efficiency": 0.10, "evolution": 0.10,
    }

    def __init__(self, ecos_root_path: Optional[str] = None):
        self.ecos_root_path = ecos_root_path or "ECOS_ROOT.json"
        self.ecos_root_data = self._load_ecos_root()

    def _load_ecos_root(self) -> Dict:
        try:
            if Path(self.ecos_root_path).exists():
                with open(self.ecos_root_path, 'r') as f: return json.load(f)
        except Exception: pass
        return {
            "phi_cps_genesis": self.PHI_GENESIS_CURRENT,
            "phi_cps_current": self.PHI_CURRENT,
            "phi_cps_frozen": True,
            "repositories": []
        }

    def calculate_phi_cps(self, metrics: Dict[str, Any]) -> float:
        phi_score = self.PHI_GENESIS_CURRENT
        for m, w in self.WEIGHTS.items():
            if m in metrics:
                val = self._normalize_metric(metrics[m])
                phi_score += w * val * 0.5
        return min(phi_score, 5.0)

    def _normalize_metric(self, value: Any) -> float:
        if isinstance(value, bool): return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            if value >= 100: return min(value / 100.0, 1.0)
            if value >= 10: return min(value / 10.0, 1.0)
            return min(max(float(value), 0.0), 1.0)
        return 0.5

    def get_metrics(self) -> Dict:
        return {
            "genesis": self.ecos_root_data.get("phi_cps_genesis", self.PHI_GENESIS_CURRENT),
            "current": self.ecos_root_data.get("phi_cps_current", self.PHI_CURRENT),
            "threshold": self.PHI_THRESHOLD,
            "frozen": self.ecos_root_data.get("phi_cps_frozen", False)
        }

    def check_drift(self) -> Tuple[bool, float, str]:
        m = self.get_metrics()
        drift = m["current"] - m["genesis"]
        exceeds = drift > m["threshold"]
        msg = "CRITICAL: Reset required" if exceeds else "Drift OK"
        return exceeds, drift, msg

    def assess_maturity_level(self, phi_score: float) -> PhiCPSLevel:
        for level in sorted(PhiCPSLevel, key=lambda x: x.value, reverse=True):
            if phi_score >= level.value: return level
        return PhiCPSLevel.GENESIS
