#!/usr/bin/env python3
"""
Wait for GitHub Actions status checks to appear on main branch.
"""
import subprocess
import sys
import time
import json

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", required=True, help="JSON array of repo full_names")
    parser.add_argument("--checks", required=True, help="Comma-separated list of check names")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    
    repos = json.loads(args.repos)
    required_checks = [c.strip() for c in args.checks.split(",")]
    start = time.time()
    
    print(f"[WAIT] Waiting for {len(required_checks)} checks on {len(repos)} repos...")
    
    while time.time() - start < args.timeout:
        all_ready = True
        for repo in repos:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/commits/main/check-runs", "--jq", ".check_runs[].name"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                all_ready = False
                continue
            
            existing = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
            missing = [c for c in required_checks if c not in existing]
            
            if missing:
                all_ready = False
                print(f"  {repo}: missing {missing}")
            else:
                print(f"  {repo}: all checks present")
        
        if all_ready:
            print("[OK] All status checks present")
            sys.exit(0)
        
        print(f"  ... waiting ({int(time.time()-start)}s)")
        time.sleep(10)
    
    print("[TIMEOUT] Status checks not ready")
    sys.exit(1)

if __name__ == "__main__":
    main()