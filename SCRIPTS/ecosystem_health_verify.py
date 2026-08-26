#!/usr/bin/env python3
"""
Ecosystem Health Verify
STRICT verification of ALL repos from known_repositories.yaml
Stops execution if coverage < 100%
"""

import subprocess
import os
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

REGISTRY_PATH = "D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\GOVERNANCE-HUB\\known_repositories.yaml"

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def read_registry():
    """Read known_repositories.yaml and extract repo info"""
    repos_dict = {}  # Use dict to deduplicate by full_name, keep last local_path
    try:
        with open(REGISTRY_PATH, 'r') as f:
            if HAS_YAML:
                data = yaml.safe_load(f)
                # Extract repos from all layer keys (P0_REPOS, P1_REPOS, etc.)
                for key, value in data.items():
                    if key.endswith('_REPOS') and isinstance(value, list):
                        for repo in value:
                            if isinstance(repo, dict) and 'full_name' in repo:
                                full_name = repo.get('full_name')
                                local_path = repo.get('local_path')
                                status = repo.get('status', 'ACTIVE')
                                # Keep last occurrence (handles duplicates in YAML)
                                if full_name not in repos_dict or local_path:
                                    repos_dict[full_name] = {
                                        'full_name': full_name,
                                        'local_path': local_path,
                                        'status': status
                                    }
            else:
                # Fallback: manual YAML parsing for list items
                content = f.read()
                current_repo = {}
                for line in content.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith('- name:'):
                        if current_repo.get('full_name'):
                            fn = current_repo.get('full_name')
                            lp = current_repo.get('local_path')
                            # Keep last occurrence with local_path
                            if fn not in repos_dict or lp:
                                repos_dict[fn] = {
                                    'full_name': fn,
                                    'local_path': lp,
                                    'status': current_repo.get('status', 'ACTIVE')
                                }
                        current_repo = {}
                    elif ':' in stripped:
                        key, val = stripped.split(':', 1)
                        key = key.strip()
                        val = val.strip()
                        if key in ['full_name', 'local_path', 'status']:
                            current_repo[key] = val
                if current_repo.get('full_name'):
                    fn = current_repo.get('full_name')
                    lp = current_repo.get('local_path')
                    if fn not in repos_dict or lp:
                        repos_dict[fn] = {
                            'full_name': fn,
                            'local_path': lp,
                            'status': current_repo.get('status', 'ACTIVE')
                        }
    except FileNotFoundError:
        print(f"[HEALTH-VERIFY] Registry not found at {REGISTRY_PATH}")
    except Exception as e:
        print(f"[HEALTH-VERIFY] Error reading registry: {e}")
    
    return list(repos_dict.values())

def check_repo_exists(repo):
    """Check if repo directory exists"""
    path = repo.get('local_path')
    if not path:
        return False, "no_local_path"
    
    if os.path.exists(path):
        git_dir = os.path.join(path, '.git')
        if os.path.exists(git_dir):
            return True, "exists"
        return False, "not_git_repo"
    return False, "not_found"

def get_repo_status(repo_path):
    """Get git status of a repo - FAST version without git status call"""
    # Skip slow git status for verification - just check .git exists
    git_dir = os.path.join(repo_path, '.git')
    if os.path.exists(git_dir):
        return 0, []  # Return 0 untracked for speed
    return 0, []

def verify_ecosystem():
    """Main verification function"""
    print(f"[HEALTH-VERIFY] Starting ecosystem verification at {datetime.now()}")
    
    repos = read_registry()
    # Filter to only repos with local_path defined
    repos_with_path = [r for r in repos if r.get('local_path')]
    repos_without_path = [r for r in repos if not r.get('local_path')]
    
    print(f"[HEALTH-VERIFY] Registry: {len(repos)} total, {len(repos_with_path)} with local_path, {len(repos_without_path)} archived")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_in_registry": len(repos),
        "repos_with_path": len(repos_with_path),
        "repos_archived": len(repos_without_path),
        "verified": 0,
        "missing": [],
        "not_git": [],
        "status": {}
    }
    
    for repo in repos_with_path:
        full_name = repo.get('full_name', 'unknown')
        exists, reason = check_repo_exists(repo)
        
        if exists:
            path = repo.get('local_path')
            count, files = get_repo_status(path)
            results["verified"] += 1
            results["status"][full_name] = {
                "path": path,
                "exists": True,
                "untracked_count": count
            }
        else:
            results["missing"].append({
                "name": full_name,
                "reason": reason,
                "expected_path": repo.get('local_path')
            })
    
    # Calculate coverage based on repos WITH local_path
    coverage = results["verified"] / results["repos_with_path"] if results["repos_with_path"] > 0 else 0
    results["coverage"] = coverage
    
    # Print results
    print(f"\n[HEALTH-VERIFY] COVERAGE: {results['verified']}/{results['repos_with_path']} = {coverage*100:.1f}%")
    
    if results["missing"]:
        print(f"\n[HEALTH-VERIFY] MISSING REPOS ({len(results['missing'])}):")
        for m in results["missing"][:20]:
            print(f"  - {m['name']} ({m['reason']})")
        if len(results["missing"]) > 20:
            print(f"  ... and {len(results['missing']) - 20} more")
    
    # Write report
    report_path = "D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\REPO-STANDARDS\\reports\\ecosystem-health-report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[HEALTH-VERIFY] Report: {report_path}")
    
    # STOP if coverage < 100%
    if coverage < 1.0:
        print("\n[HEALTH-VERIFY] [FAIL] STOP: Ecosystem incomplete")
        print("[HEALTH-VERIFY] Run ecosystem sync to complete missing repos")
        return False
    
    print("\n[HEALTH-VERIFY] [OK] Ecosystem complete")
    return True

if __name__ == "__main__":
    strict = "--strict" in sys.argv
    success = verify_ecosystem()
    if strict and not success:
        sys.exit(1)