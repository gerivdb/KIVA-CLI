#!/usr/bin/env python3
"""
Cleanup merged branches - Supprime les branches locales et distantes qui ont été mergées
"""
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def get_merged_branches():
    """Get list of merged branches"""
    output, code = run_cmd("git branch --merged main | grep -v '^* main$'")
    if code != 0 or not output:
        return []
    return [b.strip().lstrip('* ') for b in output.split('\n') if b.strip()]

def get_remote_merged_branches():
    """Get list of merged remote branches"""
    output, code = run_cmd("git branch -r --merged origin/main | grep -v 'origin/main$'")
    if code != 0 or not output:
        return []
    return [b.strip() for b in output.split('\n') if b.strip()]

def delete_local_branch(branch):
    """Delete a local branch"""
    _, code = run_cmd(f"git branch -d {branch}")
    return code == 0

def delete_remote_branch(repo, branch):
    """Delete a remote branch"""
    _, code = run_cmd(f"git push origin --delete {branch}")
    return code == 0

def main():
    print("[CLEANUP] Analyzing merged branches...")
    
    # Get local merged branches
    local_merged = get_merged_branches()
    print(f"[CLEANUP] Found {len(local_merged)} local merged branches")
    
    # Delete local branches
    deleted = 0
    for branch in local_merged:
        if delete_local_branch(branch):
            print(f"  ✓ Deleted local branch: {branch}")
            deleted += 1
        else:
            print(f"  ✗ Failed to delete: {branch}")
    
    # Get remote merged branches
    remote_merged = get_remote_merged_branches()
    print(f"[CLEANUP] Found {len(remote_merged)} remote merged branches")
    
    # Delete remote branches
    for branch in remote_merged:
        branch_name = branch.replace('origin/', '')
        if delete_remote_branch('origin', branch_name):
            print(f"  ✓ Deleted remote branch: {branch_name}")
            deleted += 1
        else:
            print(f"  ✗ Failed to delete remote: {branch_name}")
    
    print(f"[CLEANUP] Total deleted: {deleted}")
    return 0

if __name__ == "__main__":
    sys.exit(main())