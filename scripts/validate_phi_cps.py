"""
φ-CPS Validation Script - Run comprehensive checks
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.core.pipeline_manager import PipelineManager
from tools.core.global_wal_manager import GlobalWALManager
import json

def validate_phi_cps_stability():
    """Validate current φ-CPS state and recommendations"""
    
    # Load ECOS_ROOT.json
    with open('ECOS_ROOT.json', 'r') as f:
        manifest = json.load(f)
    
    phi_baseline = manifest['phi_cps_baseline']
    phi_current = manifest['phi_cps_current']
    phi_delta = manifest['phi_cps_delta']
    threshold = manifest['phi_cps_threshold']
    
    print("=" * 80)
    print("φ-CPS VALIDATION REPORT")
    print("=" * 80)
    print(f"Baseline: {phi_baseline}")
    print(f"Current:  {phi_current}")
    print(f"Delta:    {phi_delta:+.3f}")
    print(f"Threshold: {threshold}")
    print()
    
    # Calculate drift percentage
    drift_pct = (phi_delta / threshold - 1.0) * 100
    
    if phi_delta <= threshold:
        status = "✅ OK"
        recommendation = "Safe to continue implementations"
    elif phi_delta <= threshold * 1.5:
        status = "⚠️  WARNING"
        recommendation = "Reduce implementation scope or run integration tests"
    else:
        status = "🔴 CRITICAL"
        recommendation = "HALT all implementations. Run full validation suite."
    
    print(f"Status: {status}")
    print(f"Drift: {drift_pct:+.1f}% from threshold")
    print(f"Recommendation: {recommendation}")
    print()
    
    # Component breakdown
    print("Component Contributions:")
    for repo in manifest['repositories']:
        if repo.get('phi_cps_contribution', 0) > 0:
            print(f"  {repo['name']}: +{repo['phi_cps_contribution']:.3f}")
    print()
    
    # Recent operations
    print("Recent Operations:")
    for op in manifest['recent_operations'][-5:]:
        print(f"  [{op['status']}] {op['operation']}: +{op['phi_cps_delta']:.3f}")
    print()
    
    return phi_delta <= threshold

if __name__ == "__main__":
    is_valid = validate_phi_cps_stability()
    sys.exit(0 if is_valid else 1)
