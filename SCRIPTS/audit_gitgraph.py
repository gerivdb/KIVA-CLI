#!/usr/bin/env python3
"""
Audit gitgraph - Vérifie la cohérence de l'historique Git
"""
import subprocess
import sys
from collections import Counter

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def get_commit_history():
    """Get commit history from main"""
    output, code = run_cmd("git log --oneline main -20")
    if code != 0 or not output:
        return []
    return [line.split(' ', 1) for line in output.split('\n') if line.strip()]

def get_remote_history():
    """Get commit history from origin/main"""
    output, code = run_cmd("git log --oneline origin/main -20")
    if code != 0 or not output:
        return []
    return [line.split(' ', 1) for line in output.split('\n') if line.strip()]

def check_duplicates(commits):
    """Check for duplicate commits"""
    hashes = [c[0] for c in commits if c]
    counts = Counter(hashes)
    duplicates = {h: c for h, c in counts.items() if c > 1}
    return duplicates

def check_merge_commits(commits):
    """Check for proper merge commits"""
    merges = [c for c in commits if c[0].startswith('Merge')]
    return merges

def main():
    print("[GITGRAPH] Auditing commit history...")
    
    # Get local history
    local_commits = get_commit_history()
    print(f"[GITGRAPH] Local main: {len(local_commits)} recent commits")
    
    # Get remote history  
    remote_commits = get_remote_history()
    print(f"[GITGRAPH] Remote origin/main: {len(remote_commits)} recent commits")
    
    # Check for divergence
    local_hashes = set(c[0] for c in local_commits if c)
    remote_hashes = set(c[0] for c in remote_commits if c)
    
    missing_in_remote = local_hashes - remote_hashes
    missing_in_local = remote_hashes - local_hashes
    
    if missing_in_remote:
        print(f"[GITGRAPH] WARNING: {len(missing_in_remote)} commits in local but not in remote")
        for h in list(missing_in_remote)[:5]:
            print(f"  Missing in remote: {h}")
    
    if missing_in_local:
        print(f"[GITGRAPH] WARNING: {len(missing_in_local)} commits in remote but not in local")
        for h in list(missing_in_local)[:5]:
            print(f"  Missing in local: {h}")
    
    # Check for duplicates
    duplicates = check_duplicates(local_commits)
    if duplicates:
        print(f"[GITGRAPH] WARNING: Found {len(duplicates)} duplicate commits")
        for h, count in duplicates.items():
            print(f"  Duplicate: {h} ({count} times)")
    
    # Check merge commits
    merges = check_merge_commits(local_commits)
    print(f"[GITGRAPH] Found {len(merges)} merge commits in recent history")
    
    # Summary
    if not missing_in_remote and not missing_in_local and not duplicates:
        print("[GITGRAPH] [OK] Git graph is clean and consistent")
        return 0
    else:
        print("[GITGRAPH] [WARN] Git graph has issues - recommend git pull --rebase")
        return 1

if __name__ == "__main__":
    sys.exit(main())