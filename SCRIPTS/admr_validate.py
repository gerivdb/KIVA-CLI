#!/usr/bin/env python3
"""
ADMR Validation Script for KIVA-CLI

Validates merge requests using Adjunction-driven constraints.

IntentHash: 0xADMR_SCRIPT_20260718
"""

import sys
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        import io as _io
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add KIVA-CLI to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kiva_cli.core.dag3.admr_validator import ADMRValidator, ADMRStatus


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ADMR Validator")
    parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    parser.add_argument("--source", "-s", required=True, help="Source branch name")
    parser.add_argument("--target", "-t", default="main", help="Target branch name")
    parser.add_argument("--output", "-o", default="", help="Output JSON file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    
    args = parser.parse_args()
    
    validator = ADMRValidator(repo_path=args.repo_path)
    result = validator.validate(args.source, args.target)
    
    print(f"[ADMR] Status: {result.status.value}")
    print(f"[ADMR] phi-CPS impact: {result.phi_cps_impact:.3f}")
    
    if result.violations:
        print(f"[ADMR] Violations: {len(result.violations)}")
        for v in result.violations[:5]:
            print(f"  [{v.severity.upper()}] {v.message}")
    
    if result.recommendations:
        for rec in result.recommendations:
            print(f"  {rec}")
    
    if args.output:
        import json
        output_data = {
            "status": result.status.value,
            "violations": [
                {"type": v.constraint_type.value, "message": v.message, "severity": v.severity}
                for v in result.violations
            ],
            "phi_cps_impact": result.phi_cps_impact,
            "hitl_required": result.hitl_required
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    
    return 0 if result.status == ADMRStatus.APPROVED else 1


if __name__ == "__main__":
    sys.exit(main())