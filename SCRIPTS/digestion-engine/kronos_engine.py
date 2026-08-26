#!/usr/bin/env python3
"""
KRONOS - Qualificateur des Signaux
Consomme les signaux MUD d'IRIS pour prendre des décisions de citoyenisation/expulsion.
"""

import json
import sys
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class KronosRules:
    """Règles de qualification KRONOS"""
    citizen_threshold: Dict = None
    expulsion_threshold: Dict = None
    
    def __post_init__(self):
        if self.citizen_threshold is None:
            self.citizen_threshold = {
                "min_activity_score": 0.7,
                "min_commits_per_month": 5,
                "min_releases_per_month": 1,
                "min_active_issues": 3,
                "min_contributors": 2
            }
        if self.expulsion_threshold is None:
            self.expulsion_threshold = {
                "max_activity_score": 0.3,
                "max_commits_per_month": 2,
                "max_releases_per_month": 0.5,
                "max_active_issues": 1,
                "max_no_releases_days": 180
            }


class KronosEngine:
    """Moteur de qualification KRONOS"""
    
    def __init__(self, rules: KronosRules = None):
        self.rules = rules or KronosRules()
    
    def qualify(self, mud_signal: Dict) -> Dict:
        """
        Qualifie un signal MUD et retourne le verdict.
        
        Returns:
            Dict with verdict, score, and reason
        """
        health = mud_signal.get("health_indicators", {})
        signals = mud_signal.get("signals", {})
        
        activity_score = health.get("activity_score", 0)
        
        # Calculate composite score
        score = self._calculate_composite_score(mud_signal)
        
        # Determine verdict
        verdict = self._determine_verdict(mud_signal, score)
        
        return {
            "verdict": verdict,
            "score": round(score, 3),
            "reason": self._get_reason(verdict, mud_signal),
            "repo": mud_signal.get("repo"),
            "timestamp": mud_signal.get("timestamp"),
            "health_indicators": health
        }
    
    def _calculate_composite_score(self, mud_signal: Dict) -> float:
        """Calculate composite score from all health indicators"""
        health = mud_signal.get("health_indicators", {})
        signals = mud_signal.get("signals", {})
        
        # Weighted composite score
        activity = health.get("activity_score", 0) * 0.4
        stability = health.get("stability_score", 0) * 0.2
        community = health.get("community_score", 0) * 0.4
        
        return activity + stability + community
    
    def _determine_verdict(self, mud_signal: Dict, score: float) -> str:
        """Determine citizenship verdict based on score and thresholds"""
        health = mud_signal.get("health_indicators", {})
        signals = mud_signal.get("signals", {})
        
        activity_score = health.get("activity_score", 0)
        
        # Check citizen threshold
        if (activity_score >= self.rules.citizen_threshold["min_activity_score"] and
            signals.get("commits", {}).get("count", 0) >= self.rules.citizen_threshold["min_commits_per_month"]):
            return "CITIZEN"
        
        # Check expulsion threshold
        if (activity_score <= self.rules.expulsion_threshold["max_activity_score"] and
            signals.get("commits", {}).get("count", 0) <= self.rules.expulsion_threshold["max_commits_per_month"]):
            return "EXPULSION"
        
        # Default to monitor
        return "MONITOR"
    
    def _get_reason(self, verdict: str, mud_signal: Dict) -> str:
        """Get human-readable reason for verdict"""
        if verdict == "CITIZEN":
            return "Activity score above citizen threshold"
        elif verdict == "EXPULSION":
            return "Activity score below expulsion threshold"
        else:
            return "Activity score in monitoring range"


def main():
    """Read MUD signal from stdin, output verdict to stdout"""
    kronos = KronosEngine()
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            mud_signal = json.loads(line)
            verdict = kronos.qualify(mud_signal)
            print(json.dumps(verdict))
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)


if __name__ == "__main__":
    main()