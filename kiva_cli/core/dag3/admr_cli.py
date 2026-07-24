#!/usr/bin/env python3
"""
ADMR CLI - Adjunction-driven Merge Request Validator CLI

IntentHash: 0xADMR_CLI_20260718
"""

import sys
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kiva_cli.core.dag3.admr_validator import ADMRValidator, ADMRStatus


def main():
    """CLI entry point for ADMR validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="ADMR Validator — Validate merge requests with adjunction analysis"
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
        "--json", 
        action="store_true", 
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    validator = ADMRValidator(repo_path=args.repo_path)
    result = validator.validate(args.source, args.target)
    
    if args.json:
        output = {
            "status": result.status.value,
            "branch": result.branch,
            "target": result.target,
            "phi_cps_impact": result.phi_cps_impact,
            "violations": [
                {
                    "type": v.constraint_type.value,
                    "message": v.message,
                    "severity": v.severity,
                    "affected_files": v.affected_files
                }
                for v in result.violations
            ],
            "hitl_required": result.hitl_required,
            "recommendations": result.recommendations,
            "timestamp": result.validation_timestamp
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"[ADMR] Validation result: {result.status.value}")
        print(f"[ADMR] Branch: {result.branch} -> {result.target}")
        print(f"[ADMR] φ-CPS impact: {result.phi_cps_impact:.3f}")
        
        if result.violations:
            print(f"[ADMR] Violations found: {len(result.violations)}")
            for v in result.violations[:5]:
                print(f"  [{v.severity.upper()}] {v.message}")
        
        if result.recommendations:
            print("[ADMR] Recommendations:")
            for rec in result.recommendations:
                print(f"  {rec}")
    
    if args.output:
        output_data = {
            "status": result.status.value,
            "branch": result.branch,
            "target": result.target,
            "violations": [
                {
                    "type": v.constraint_type.value,
                    "message": v.message,
                    "severity": v.severity,
                    "affected_files": v.affected_files
                }
                for v in result.violations
            ],
            "phi_cps_impact": result.phi_cps_impact,
            "hitl_required": result.hitl_required,
            "recommendations": result.recommendations,
            "timestamp": result.validation_timestamp
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2), encoding="utf-8")
        print(f"[ADMR] Results exported to {args.output}")
    
    return 0 if result.status == ADMRStatus.APPROVED else 1


if __name__ == "__main__":
    sys.exit(main())