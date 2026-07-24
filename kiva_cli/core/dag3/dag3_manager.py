#!/usr/bin/env python3
"""
DAG3 Manager - Orchestrates ACM and ADMR validation

IntentHash: 0xDAG3_MANAGER_20260718
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timezone

from .acm_detector import ACMDetector, CycleDetectionResult, CycleSeverity
from .admr_validator import ADMRValidator, ADMRValidationResult, ADMRStatus


@dataclass
class DAG3ValidationResult:
    """Combined result from ACM and ADMR validation."""
    acm_result: CycleDetectionResult
    admr_result: ADMRValidationResult
    overall_status: str  # "approved", "rejected", "needs_hitl"
    phi_cps_impact: float
    recommendations: List[str]
    timestamp: str


class DAG3Manager:
    """
    DAG3 Manager - Orchestrates graph-based validation for merges.
    
    Combines ACM (Atomic Cycle Model) and ADMR (Adjunction-driven Merge Request)
    validation for comprehensive merge safety.
    
    Usage:
        manager = DAG3Manager(repo_path="/path/to/repo")
        result = manager.validate_merge("feature-branch", "main")
        if result.overall_status == "approved":
            print("Merge approved!")
    """

    def __init__(self, repo_path: str = ".", commit_range: str = ""):
        """
        Initialize DAG3 Manager.
        
        Args:
            repo_path: Path to the repository
            commit_range: Optional commit range for analysis
        """
        self.repo_path = Path(repo_path)
        self.acm_detector = ACMDetector(repo_path=str(self.repo_path))
        self.admr_validator = ADMRValidator(repo_path=str(self.repo_path), commit_range=commit_range)
        
    def validate_merge(self, source_branch: str, target_branch: str = "main") -> DAG3ValidationResult:
        """
        Validate a merge request using both ACM and ADMR.
        
        Args:
            source_branch: Source branch name
            target_branch: Target branch name
            
        Returns:
            DAG3ValidationResult with combined validation outcome
        """
        # Run ACM detection
        acm_result = self.acm_detector.detect_cycles()
        
        # Run ADMR validation
        admr_result = self.admr_validator.validate(source_branch, target_branch)
        
        # Combine results
        overall_status, recommendations, phi_cps_impact = self._combine_results(
            acm_result, admr_result
        )
        
        return DAG3ValidationResult(
            acm_result=acm_result,
            admr_result=admr_result,
            overall_status=overall_status,
            phi_cps_impact=phi_cps_impact,
            recommendations=recommendations,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def _combine_results(self, acm_result: CycleDetectionResult, 
                         admr_result: ADMRValidationResult) -> Tuple[str, List[str], float]:
        """Combine ACM and ADMR results into overall decision."""
        recommendations = []
        
        # Start with ADMR violations as primary signal
        if admr_result.status == ADMRStatus.REJECTED:
            return "rejected", admr_result.recommendations, admr_result.phi_cps_impact
        
        if admr_result.status == ADMRStatus.NEEDS_HITL:
            recommendations.extend(admr_result.recommendations)
        
        # Check ACM cycles
        if acm_result.has_cycles:
            if acm_result.severity == CycleSeverity.HIGH:
                recommendations.extend(acm_result.recommendations)
                if "rejected" not in recommendations:
                    return "rejected", recommendations, max(acm_result.phi_cps_impact, admr_result.phi_cps_impact)
            elif acm_result.severity == CycleSeverity.MEDIUM:
                recommendations.extend(acm_result.recommendations)
                if admr_result.status != ADMRStatus.APPROVED:
                    recommendations.append("[DAG3] Cycle severity medium - HITL recommended")
                    return "needs_hitl", recommendations, max(acm_result.phi_cps_impact, admr_result.phi_cps_impact)
            else:
                recommendations.extend(acm_result.recommendations)
        
        # Determine final status
        if admr_result.status == ADMRStatus.NEEDS_HITL or acm_result.has_cycles:
            if "rejected" not in recommendations:
                recommendations.append("[DAG3] Merge requires HITL approval due to constraints")
            return "needs_hitl", recommendations, max(acm_result.phi_cps_impact, admr_result.phi_cps_impact)
        
        if not recommendations:
            recommendations.append("[DAG3] All validations passed - merge approved")
        
        return "approved", recommendations, max(acm_result.phi_cps_impact, admr_result.phi_cps_impact)

    def pre_merge_check(self, source_branch: str, target_branch: str = "main") -> Dict:
        """
        Perform comprehensive pre-merge validation.
        
        Args:
            source_branch: Source branch name
            target_branch: Target branch name
            
        Returns:
            Dictionary with detailed validation results
        """
        result = self.validate_merge(source_branch, target_branch)
        
        return {
            "branch": f"{source_branch} -> {target_branch}",
            "status": result.overall_status,
            "phi_cps_impact": result.phi_cps_impact,
            "acm_cycles": len(result.acm_result.cycles) if result.acm_result.has_cycles else 0,
            "acm_severity": result.acm_result.severity.name if result.acm_result.has_cycles else "NONE",
            "admr_violations": len(result.admr_result.violations),
            "admr_status": result.admr_result.status.value,
            "recommendations": result.recommendations,
            "timestamp": result.timestamp
        }

    def export_report(self, source_branch: str, target_branch: str, 
                      output_path: str) -> None:
        """
        Export validation report to JSON file.
        
        Args:
            source_branch: Source branch name
            target_branch: Target branch name
            output_path: Path to output JSON file
        """
        report = self.pre_merge_check(source_branch, target_branch)
        
        Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")


def main():
    """CLI entry point for DAG3 validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DAG3 Manager - Validate merges with ACM+ADMR")
    parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    parser.add_argument("--source", "-s", required=True, help="Source branch name")
    parser.add_argument("--target", "-t", default="main", help="Target branch name")
    parser.add_argument("--output", "-o", default="", help="Output JSON file")
    parser.add_argument("--pre-check", action="store_true", help="Run pre-merge check")
    
    args = parser.parse_args()
    
    manager = DAG3Manager(repo_path=args.repo_path)
    
    if args.pre_check:
        report = manager.pre_merge_check(args.source, args.target)
        print(f"[DAG3] Pre-merge check result: {report['status']}")
        print(f"[DAG3] φ-CPS impact: {report['phi_cps_impact']:.3f}")
        print(f"[DAG3] ACM cycles: {report['acm_cycles']}")
        print(f"[DAG3] ADMR violations: {report['admr_violations']}")
        
        if report["recommendations"]:
            print("[DAG3] Recommendations:")
            for rec in report["recommendations"]:
                print(f"  {rec}")
    else:
        result = manager.validate_merge(args.source, args.target)
        
        print(f"[DAG3] Validation: {result.overall_status}")
        print(f"[DAG3] φ-CPS impact: {result.phi_cps_impact:.3f}")
        
        if result.recommendations:
            print("[DAG3] Recommendations:")
            for rec in result.recommendations:
                print(f"  {rec}")
    
    if args.output:
        manager.export_report(args.source, args.target, args.output)
        print(f"[DAG3] Report exported to {args.output}")
    
    return 0 if "approved" in result.overall_status else 1


if __name__ == "__main__":
    exit(main())