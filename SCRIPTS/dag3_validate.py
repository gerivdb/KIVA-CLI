#!/usr/bin/env python3
"""
DAG3 Manager Script for KIVA-CLI

Orchestrates ACM and ADMR validation for merge requests.

IntentHash: 0xDAG3_SCRIPT_20260718
"""

import sys
import json
from pathlib import Path

# Fix Windows console encoding for Unicode characters (e.g. φ)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        import io as _io
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add KIVA-CLI to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kiva_cli.core.dag3 import DAG3Manager


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DAG3 Manager")
    parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    parser.add_argument("--source", "-s", required=True, help="Source branch name")
    parser.add_argument("--target", "-t", default="main", help="Target branch name")
    parser.add_argument("--output", "-o", default="", help="Output JSON file")
    parser.add_argument("--pre-check", action="store_true", help="Pre-merge check mode")
    parser.add_argument("--json", action="store_true", help="JSON output")
    
    args = parser.parse_args()
    
    manager = DAG3Manager(repo_path=args.repo_path)
    
    if args.pre_check:
        report = manager.pre_merge_check(args.source, args.target)
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"[DAG3] Status: {report['status']}")
            print(f"[DAG3] phi-CPS impact: {report['phi_cps_impact']:.3f}")
            print(f"[DAG3] ACM cycles: {report['acm_cycles']}")
            print(f"[DAG3] ADMR violations: {report['admr_violations']}")
        
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        
        return 0 if report["status"] == "approved" else 1
    
    result = manager.validate_merge(args.source, args.target)
    
    print(f"[DAG3] Status: {result.overall_status}")
    print(f"[DAG3] phi-CPS impact: {result.phi_cps_impact:.3f}")
    
    if result.recommendations:
        for rec in result.recommendations:
            print(f"  {rec}")
    
    if args.output:
        manager.export_report(args.source, args.target, args.output)
    
    return 0 if "approved" in result.overall_status else 1


if __name__ == "__main__":
    sys.exit(main())