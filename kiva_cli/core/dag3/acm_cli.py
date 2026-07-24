#!/usr/bin/env python3
"""
ACM CLI - Atomic Cycle Model Detection CLI

IntentHash: 0xACM_CLI_20260718
"""

import sys
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kiva_cli.core.dag3.acm_detector import ACMDetector, CycleSeverity


def main():
    """CLI entry point for ACM detection."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="ACM Detector — Detect atomic cycles in dependency graphs"
    )
    parser.add_argument(
        "--repo-path", "-r", 
        default=".", 
        help="Repository path to analyze"
    )
    parser.add_argument(
        "--output", "-o", 
        default="", 
        help="Output JSON file for analysis"
    )
    parser.add_argument(
        "--validate-merge", "-v", 
        nargs=2, 
        metavar=("BRANCH", "TARGET"),
        help="Validate merge candidate"
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    detector = ACMDetector(repo_path=args.repo_path)
    
    if args.validate_merge:
        branch, target = args.validate_merge
        is_valid, message = detector.validate_merge_candidate(branch, target)
        
        if args.json:
            output = {
                "valid": is_valid,
                "message": message,
                "branch": branch,
                "target": target
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"[ACM-VALIDATE] {branch} -> {target}: {'VALID' if is_valid else 'INVALID'}")
            print(f"[ACM-VALIDATE] {message}")
        
        return 0 if is_valid else 1
    
    result = detector.detect_cycles()
    
    if args.json:
        output = {
            "has_cycles": result.has_cycles,
            "cycles": result.cycles,
            "severity": result.severity.name,
            "affected_nodes": list(result.affected_nodes),
            "recommendations": result.recommendations,
            "phi_cps_impact": result.phi_cps_impact
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"[ACM] Cycles detected: {result.has_cycles}")
        if result.has_cycles:
            print(f"[ACM] Severity: {result.severity.name}")
            print(f"[ACM] Affected nodes: {len(result.affected_nodes)}")
            for i, cycle in enumerate(result.cycles[:5]):
                print(f"[ACM] Cycle {i+1}: {' -> '.join(cycle)}")
            print(f"[ACM] φ-CPS impact: {result.phi_cps_impact:.3f}")
        
        if result.recommendations:
            print("[ACM] Recommendations:")
            for rec in result.recommendations:
                print(f"  {rec}")
    
    if args.output:
        detector.export_analysis(args.output)
        print(f"[ACM] Analysis exported to {args.output}")
    
    return 1 if result.has_cycles and result.severity == CycleSeverity.HIGH else 0


if __name__ == "__main__":
    sys.exit(main())