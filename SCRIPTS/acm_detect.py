#!/usr/bin/env python3
"""
ACM Detection Script for KIVA-CLI

Detects Atomic Cycle Models in repository dependencies.

IntentHash: 0xACM_SCRIPT_20260718
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

from kiva_cli.core.dag3.acm_detector import ACMDetector, CycleSeverity


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ACM Detector")
    parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    parser.add_argument("--output", "-o", default="", help="Output JSON file")
    parser.add_argument("--validate-merge", "-v", nargs=2, metavar=("BRANCH", "TARGET"),
                        help="Validate merge candidate")
    parser.add_argument("--json", action="store_true", help="JSON output")
    
    args = parser.parse_args()
    
    detector = ACMDetector(repo_path=args.repo_path)
    
    if args.validate_merge:
        branch, target = args.validate_merge
        is_valid, message = detector.validate_merge_candidate(branch, target)
        print(f"[ACM] {branch} -> {target}: {'VALID' if is_valid else 'INVALID'}")
        print(f"[ACM] {message}")
        return 0 if is_valid else 1
    
    result = detector.detect_cycles()
    
    print(f"[ACM] Cycles: {result.has_cycles}, Severity: {result.severity.name}")
    print(f"[ACM] phi-CPS impact: {result.phi_cps_impact:.3f}")
    if result.has_cycles:
        for i, cycle in enumerate(result.cycles[:5]):
            print(f"  Cycle {i+1}: {' -> '.join(cycle)}")
    
    if result.recommendations:
        for rec in result.recommendations:
            print(f"  {rec}")
    
    if args.output:
        detector.export_analysis(args.output)
    
    return 1 if result.has_cycles and result.severity == CycleSeverity.HIGH else 0


if __name__ == "__main__":
    sys.exit(main())