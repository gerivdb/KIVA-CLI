#!/usr/bin/env python3
"""
DAG-3 — Triadic Graph Engine for gerivdb Ecosystem

Main entry point for DAG-3 module.

IntentHash: 0xDAG3_MAIN_20260718
"""

import sys
from pathlib import Path

# Ensure KIVA-CLI is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kiva_cli.core.dag3 import (
    ACMDetector, ADMRValidator, DAG3Manager,
    CycleSeverity, ADMRStatus
)


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DAG-3 — Triadic Graph Engine for gerivdb Ecosystem"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # ACM command
    acm_parser = subparsers.add_parser("acm", help="Atomic Cycle Model detection")
    acm_parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    acm_parser.add_argument("--validate-merge", "-v", nargs=2, 
                            metavar=("BRANCH", "TARGET"), help="Validate merge")
    acm_parser.add_argument("--output", "-o", default="", help="Output JSON file")
    
    # ADMR command
    admr_parser = subparsers.add_parser("admr", help="Adjunction-driven Merge Request validation")
    admr_parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    admr_parser.add_argument("--source", "-s", required=True, help="Source branch")
    admr_parser.add_argument("--target", "-t", default="main", help="Target branch")
    admr_parser.add_argument("--output", "-o", default="", help="Output JSON file")
    
    # Validate command (full DAG3)
    validate_parser = subparsers.add_parser("validate", help="Full DAG-3 merge validation")
    validate_parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    validate_parser.add_argument("--source", "-s", required=True, help="Source branch")
    validate_parser.add_argument("--target", "-t", default="main", help="Target branch")
    validate_parser.add_argument("--output", "-o", default="", help="Output JSON file")
    validate_parser.add_argument("--pre-check", action="store_true", help="Pre-merge check")
    
    args = parser.parse_args()
    
    if args.command == "acm":
        detector = ACMDetector(repo_path=args.repo_path)
        if args.validate_merge:
            branch, target = args.validate_merge
            is_valid, message = detector.validate_merge_candidate(branch, target)
            print(f"[ACM] {branch} -> {target}: {'VALID' if is_valid else 'INVALID'}")
            print(f"[ACM] {message}")
            return 0 if is_valid else 1
        result = detector.detect_cycles()
        print(f"[ACM] Cycles: {result.has_cycles}, Severity: {result.severity.name}")
        for rec in result.recommendations:
            print(f"  {rec}")
        return 1 if result.has_cycles else 0
    
    elif args.command == "admr":
        validator = ADMRValidator(repo_path=args.repo_path)
        result = validator.validate(args.source, args.target)
        print(f"[ADMR] Status: {result.status.value}")
        print(f"[ADMR] φ-CPS impact: {result.phi_cps_impact:.3f}")
        for rec in result.recommendations:
            print(f"  {rec}")
        return 0 if result.status.value == "approved" else 1
    
    elif args.command == "validate":
        manager = DAG3Manager(repo_path=args.repo_path)
        if args.pre_check:
            report = manager.pre_merge_check(args.source, args.target)
            print(f"[DAG3] Status: {report['status']}")
            print(f"[DAG3] φ-CPS impact: {report['phi_cps_impact']:.3f}")
            for rec in report["recommendations"]:
                print(f"  {rec}")
            if args.output:
                import json
                Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 0 if report["status"] == "approved" else 1
        
        result = manager.validate_merge(args.source, args.target)
        print(f"[DAG3] Status: {result.overall_status}")
        print(f"[DAG3] φ-CPS impact: {result.phi_cps_impact:.3f}")
        for rec in result.recommendations:
            print(f"  {rec}")
        if args.output:
            manager.export_report(args.source, args.target, args.output)
        return 0 if "approved" in result.overall_status else 1
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())