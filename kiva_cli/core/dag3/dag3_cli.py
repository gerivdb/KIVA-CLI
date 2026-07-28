#!/usr/bin/env python3
"""
DAG3 CLI - DAG-3 Manager CLI

Orchestrates ACM and ADMR validation for merge requests.

IntentHash: 0xDAG3_CLI_20260718
"""

import sys
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kiva_cli.core.dag3 import DAG3Manager


def main():
    """CLI entry point for DAG3 validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DAG3 Manager — Validate merges with ACM + ADMR"
    )
    parser.add_argument(
        "--repo-path", "-r", 
        default=".", 
        help="Repository path"
    )
    parser.add_argument(
        "--source", "-s", 
        required=True, 
        help="Source branch name"
    )
    parser.add_argument(
        "--target", "-t", 
        default="main", 
        help="Target branch name"
    )
    parser.add_argument(
        "--output", "-o", 
        default="", 
        help="Output JSON file"
    )
    parser.add_argument(
        "--pre-check", 
        action="store_true", 
        help="Run pre-merge check with detailed output"
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    manager = DAG3Manager(repo_path=args.repo_path)
    
    if args.pre_check:
        report = manager.pre_merge_check(args.source, args.target)
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"[DAG3] Pre-merge check result: {report['status']}")
            print(f"[DAG3] φ-CPS impact: {report['phi_cps_impact']:.3f}")
            print(f"[DAG3] ACM cycles: {report['acm_cycles']}")
            print(f"[DAG3] ADMR violations: {report['admr_violations']}")
            
            if report["recommendations"]:
                print("[DAG3] Recommendations:")
                for rec in report["recommendations"]:
                    print(f"  {rec}")
        
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"[DAG3] Report exported to {args.output}")
        
        return 0 if report["status"] == "approved" else 1
    
    result = manager.validate_merge(args.source, args.target)
    
    if args.json:
        output = {
            "status": result.overall_status,
            "phi_cps_impact": result.phi_cps_impact,
            "acm_cycles": len(result.acm_result.cycles) if result.acm_result.has_cycles else 0,
            "acm_severity": result.acm_result.severity.name if result.acm_result.has_cycles else "NONE",
            "admr_violations": len(result.admr_result.violations),
            "admr_status": result.admr_result.status.value,
            "recommendations": result.recommendations,
            "timestamp": result.timestamp
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"[DAG3] Validation: {result.overall_status}")
        print(f"[DAG3] φ-CPS impact: {result.phi_cps_impact:.3f}")
        
        if result.acm_result.has_cycles:
            print(f"[DAG3] ACM cycles: {len(result.acm_result.cycles)}")
            for cycle in result.acm_result.cycles[:3]:
                print(f"  Cycle: {' -> '.join(cycle)}")
        
        if result.admr_result.violations:
            print(f"[DAG3] ADMR violations: {len(result.admr_result.violations)}")
        
        if result.recommendations:
            print("[DAG3] Recommendations:")
            for rec in result.recommendations:
                print(f"  {rec}")
    
    if args.output:
        manager.export_report(args.source, args.target, args.output)
        print(f"[DAG3] Report exported to {args.output}")
    
    return 0 if "approved" in result.overall_status else 1


if __name__ == "__main__":
    sys.exit(main())