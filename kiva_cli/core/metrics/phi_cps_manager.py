"""
ECOS-CLI φ-CPS Management System
Coherence metric tracking with baseline reset preparation

IntentHash: 0x69C0965C49825C93BDDF
Generated: 2026-02-28T22:00:31.548491
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


class PhiCPSManager:
    """Manage φ-CPS metrics and baseline resets"""
    
    # Constants from ECOS_ROOT.json
    PHI_GENESIS_CURRENT = 4.092
    PHI_CURRENT = 4.239
    PHI_THRESHOLD = 0.05
    
    def __init__(self, ecos_root_path: Optional[str] = None):
        self.ecos_root_path = ecos_root_path or "ECOS_ROOT.json"
        self.ecos_root_data = self._load_ecos_root()
    
    def _load_ecos_root(self) -> Dict:
        """Load ECOS_ROOT.json configuration"""
        try:
            with open(self.ecos_root_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "phi_cps_genesis": self.PHI_GENESIS_CURRENT,
                "phi_cps_current": self.PHI_CURRENT,
                "phi_cps_frozen": True,
                "repositories": []
            }
    
    def get_metrics(self) -> Dict:
        """Get current φ-CPS metrics"""
        return {
            "genesis": self.ecos_root_data.get("phi_cps_genesis", self.PHI_GENESIS_CURRENT),
            "current": self.ecos_root_data.get("phi_cps_current", self.PHI_CURRENT),
            "threshold": self.PHI_THRESHOLD,
            "frozen": self.ecos_root_data.get("phi_cps_frozen", False),
            "warning": self.ecos_root_data.get("phi_cps_warning")
        }
    
    def get_detailed_metrics(self) -> Dict:
        """Get detailed φ-CPS metrics with history"""
        metrics = self.get_metrics()
        drift = metrics["current"] - metrics["genesis"]
        
        return {
            **metrics,
            "drift": drift,
            "drift_percentage": (drift / metrics["genesis"] * 100),
            "drift_exceeds_threshold": drift > metrics["threshold"],
            "repositories": self._get_repo_metrics(),
            "global_metrics": self.ecos_root_data.get("global_metrics", {})
        }
    
    def _get_repo_metrics(self) -> List[Dict]:
        """Get per-repository φ-CPS metrics"""
        repos = []
        for repo in self.ecos_root_data.get("repositories", []):
            repos.append({
                "name": repo["name"],
                "phi_cps": repo.get("phi_cps", self.PHI_GENESIS_CURRENT),
                "phi_delta_total": repo.get("phi_delta_total", 0.0),
                "status": repo.get("status", "UNKNOWN")
            })
        return repos
    
    def check_drift(self) -> Tuple[bool, float, str]:
        """
        Check if φ-CPS drift exceeds threshold
        
        Returns:
            (exceeds: bool, drift: float, recommendation: str)
        """
        metrics = self.get_metrics()
        drift = metrics["current"] - metrics["genesis"]
        exceeds = drift > metrics["threshold"]
        
        recommendation = (
            "CRITICAL: Ecosystem-wide baseline reset required"
            if exceeds
            else "Drift within acceptable range"
        )
        
        return exceeds, drift, recommendation
    
    def prepare_baseline_reset(self, preview: bool = True) -> Dict:
        """
        Prepare ecosystem-wide φ-CPS baseline reset
        
        Args:
            preview: If True, generate plan only. If False, execute reset.
        
        Returns:
            Reset plan with migration steps
        """
        current_genesis = self.ecos_root_data.get("phi_cps_genesis", self.PHI_GENESIS_CURRENT)
        new_genesis = self.ecos_root_data.get("phi_cps_current", self.PHI_CURRENT)
        
        # Calculate impact on all repos
        affected_repos = []
        for repo in self.ecos_root_data.get("repositories", []):
            current_phi = repo.get("phi_cps", current_genesis)
            current_delta = repo.get("phi_delta_total", 0.0)
            
            # After reset, new delta = 0 (baseline alignment)
            affected_repos.append({
                "name": repo["name"],
                "phi_cps_before": current_phi,
                "phi_delta_before": current_delta,
                "phi_cps_after": new_genesis,  # All repos aligned to new baseline
                "phi_delta_after": 0.0,  # Reset cumulative delta
                "action": "UPDATE_ECOS_ROOT"
            })
        
        # Migration plan
        migration_plan = [
            {
                "step": 1,
                "action": "Backup ECOS_ROOT.json",
                "command": "cp ECOS_ROOT.json ECOS_ROOT.json.backup",
                "critical": True
            },
            {
                "step": 2,
                "action": "Update phi_cps_genesis",
                "value": new_genesis,
                "field": "phi_cps_genesis"
            },
            {
                "step": 3,
                "action": "Reset all repo phi_delta_total to 0.0",
                "affected_repos": len(affected_repos)
            },
            {
                "step": 4,
                "action": "Update manifest_version",
                "value": "2.0.0",
                "field": "manifest_version"
            },
            {
                "step": 5,
                "action": "Set phi_cps_frozen to false",
                "field": "phi_cps_frozen",
                "value": False
            },
            {
                "step": 6,
                "action": "Commit ECOS_ROOT.json v2.0.0",
                "commit_message": "[ECOS-AUTO] φ-CPS Baseline Reset v2.0.0"
            },
            {
                "step": 7,
                "action": "Sync to ECOYSTEM repo",
                "target": "gerivdb/ECOYSTEM"
            },
            {
                "step": 8,
                "action": "Log WAL event",
                "event_type": "baseline_reset"
            }
        ]
        
        # Generate ECOS_ROOT.json v2.0.0 preview
        ecos_root_v2 = self.ecos_root_data.copy()
        ecos_root_v2["manifest_version"] = "2.0.0"
        ecos_root_v2["phi_cps_genesis"] = new_genesis
        ecos_root_v2["phi_cps_current"] = new_genesis
        ecos_root_v2["phi_cps_frozen"] = False
        ecos_root_v2["phi_cps_warning"] = None
        ecos_root_v2["last_updated"] = datetime.now().isoformat() + "Z"
        
        # Reset all repo deltas
        for repo in ecos_root_v2.get("repositories", []):
            repo["phi_cps"] = new_genesis
            repo["phi_delta_total"] = 0.0
        
        # Update global metrics
        if "global_metrics" in ecos_root_v2:
            ecos_root_v2["global_metrics"]["cumulative_phi_delta"] = 0.0
            ecos_root_v2["global_metrics"]["avg_phi_cps"] = new_genesis
        
        return {
            "preview": preview,
            "current_genesis": current_genesis,
            "new_genesis": new_genesis,
            "drift_resolved": new_genesis - current_genesis,
            "affected_repos": affected_repos,
            "migration_plan": migration_plan,
            "ecos_root_v2_preview": ecos_root_v2,
            "warning": "PREVIEW ONLY - Execute in Phase 7 with full ecosystem backup",
            "estimated_duration_minutes": 5,
            "requires_approval": True
        }
    
    def calculate_phi_delta(
        self,
        semantic_weight: float,
        confidence: float
    ) -> float:
        """
        Calculate φ-CPS delta for new implementation
        
        Formula: Δφ = semantic_weight × confidence
        
        Args:
            semantic_weight: Semantic importance (0.0-1.0)
            confidence: Implementation confidence (0.0-1.0)
        
        Returns:
            φ-CPS delta value
        """
        return semantic_weight * confidence
    
    def validate_phi_increment(
        self,
        proposed_delta: float
    ) -> Tuple[bool, str]:
        """
        Validate if φ-CPS increment is allowed
        
        Args:
            proposed_delta: Proposed Δφ value
        
        Returns:
            (allowed: bool, reason: str)
        """
        metrics = self.get_metrics()
        current_drift = metrics["current"] - metrics["genesis"]
        projected_drift = current_drift + proposed_delta
        
        if metrics.get("frozen"):
            return False, f"φ-CPS is frozen (drift {current_drift:.3f} > threshold {metrics['threshold']})"
        
        if projected_drift > metrics["threshold"]:
            return False, f"Projected drift {projected_drift:.3f} would exceed threshold {metrics['threshold']}"
        
        return True, f"φ-CPS increment allowed (projected drift: {projected_drift:.3f})"
