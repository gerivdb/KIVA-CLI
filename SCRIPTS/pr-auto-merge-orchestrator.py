#!/usr/bin/env python3
"""
PR Auto-Merge Orchestrator - v2.0
Detect, create, review, resolve conflicts, and merge PRs automatically.

Version: 2.0
Date: 2026-07-13
IntentHash: 0xPR_AUTO_MERGE_ORCHESTRATOR_V2_20260713

Changelog:
- v1.0: Initial version with basic PR detection and merge
- v2.0: Added conflict resolution, force-push, re-verification cycle
  based on production experience resolving PRs #166-170
"""

import subprocess
import sys
import json
import os
import requests
from pathlib import Path
from datetime import datetime

def run_cmd(cmd, cwd=None):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def run_cmd_checked(cmd, cwd=None, description=""):
    """Run command and exit on failure"""
    print(f"[PR-AUTO-MERGE] {description}: {cmd}")
    stdout, code = run_cmd(cmd, cwd)
    if code != 0:
        print(f"[ERROR] Failed: {description}")
        print(f"  stdout: {stdout}")
        return None, code
    return stdout, code

def get_feature_branches(repo_path):
    """Get all feature branches not on main"""
    stdout, code = run_cmd('git branch -r | grep -E "feat/|fix/|docs/" | grep -v HEAD', repo_path)
    branches = []
    for line in stdout.split('\n'):
        line = line.strip()
        if line and 'origin/' in line:
            # Extract branch name
            branch = line.split()[-1] if ' ' in line else line
            if branch.startswith('origin/'):
                branch = branch[7:]  # Remove 'origin/'
            if branch and branch not in ['main', 'master']:
                branches.append(branch)
    return branches

def has_local_branch(branch_name, repo_path):
    """Check if local branch exists"""
    stdout, code = run_cmd(f"git show-ref --verify --quiet refs/heads/{branch_name}", repo_path)
    return code == 0

def has_unmerged_commits(branch, repo_path):
    """Check if branch has commits not on origin/main"""
    run_cmd("git fetch origin", repo_path)
    stdout, code = run_cmd(f"git log --oneline origin/main..{branch} 2>/dev/null", repo_path)
    lines = [l for l in stdout.split('\n') if l.strip()]
    return len(lines) > 0, lines

def _github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        token = _token_from_gh_keyring()
    if not token:
        raise RuntimeError("GITHUB_TOKEN/gh keyring requis pour créer/merger des PRs en BDCP")
    return token

def _github_headers():
    return {
        "Authorization": f"Bearer {_github_token()}",
        "Accept": "application/vnd.github+json",
    }

def _command_exists(cmd):
    """Check if a command exists"""
    stdout, code = run_cmd(f"command -v {cmd}")
    if code == 0:
        return True
    if cmd == "gh":
        for candidate in ["gh", "C:\\gh\\bin\\gh.exe", os.path.expandvars("%LOCALAPPDATA%\\Programs\\gh\\bin\\gh.exe")]:
            if os.path.exists(candidate):
                return True
    return False

def _gh_executable():
    """Return the full path to gh.exe, or 'gh' if in PATH."""
    candidates = [
        "gh",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\gh\bin\gh.exe"),
        r"C:\gh\bin\gh.exe",
    ]
    for candidate in candidates:
        if candidate == "gh":
            stdout, code = run_cmd("command -v gh")
            if code == 0 and stdout.strip():
                return stdout.strip()
        elif os.path.exists(candidate):
            return candidate
    return None

def _token_from_gh_keyring():
    """Fallback: read token from gh keyring when GITHUB_TOKEN/ GH_TOKEN are not set"""
    gh_exec = _gh_executable()
    if not gh_exec:
        return None
    stdout, code = run_cmd(f"{gh_exec} auth token")
    if code != 0:
        return None
    token = stdout.strip()
    return token if token else None

def get_pr_number(branch_name, repo):
    """Get PR number if exists via GitHub API"""
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {"head": f"{repo.split('/')[0]}:{branch_name}", "state": "open"}
    try:
        resp = requests.get(url, headers=_github_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data[0]["number"] if data else None
    except Exception as e:
        print(f"[WARN] get_pr_number failed: {e}")
        return None

def get_pr_status(pr_number, repo):
    """Get PR mergeability status via GitHub API"""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    try:
        resp = requests.get(url, headers=_github_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {
            "mergeable": data.get("mergeable", False),
            "mergeStateStatus": data.get("mergeable_state", "UNKNOWN"),
            "state": data.get("state", "UNKNOWN"),
        }
    except Exception as e:
        print(f"[WARN] get_pr_status failed: {e}")
        return {"mergeable": False, "mergeStateStatus": "UNKNOWN", "state": "UNKNOWN"}

def create_pr(branch, repo, title=None, body=None):
    """Create PR for branch via GitHub API - BDCP safe"""
    branch_name = branch.replace("origin/", "")

    if not title:
        slug = branch_name.replace("feat/", "").replace("fix/", "").replace("docs/", "")
        slug = slug.replace("-", " ").title()
        branch_type = branch_name.split("/")[0] if "/" in branch_name else "feat"
        title = f"{branch_type}: {slug}"

    if not body:
        body = f"Auto-generated PR from branch `{branch_name}`\n\n## Commits\n\n"
        stdout, _ = run_cmd(f"git log --oneline origin/main..{branch_name}", ".")
        for line in stdout.split("\n")[:10]:
            if line.strip():
                body += f"- {line.strip()}\n"
        body += "\n## IntentHash\n\n`0xAUTO_GENERATED`\n"

    url = f"https://api.github.com/repos/{repo}/pulls"
    payload = {"title": title, "body": body, "head": branch_name, "base": "main"}

    try:
        resp = requests.post(url, headers=_github_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"[PR-AUTO-MERGE] PR created successfully")
        return data.get("number")
    except Exception as e:
        print(f"[ERROR] Failed to create PR: {e}")
        return get_pr_number(branch_name, repo)

def merge_pr(pr_number, repo, repo_path=None, delete_branch=True, method="squash"):
    """Merge PR via GitHub API - BDCP safe"""
    print(f"[PR-AUTO-MERGE] Merging PR #{pr_number} via GitHub API")

    status = get_pr_status(pr_number, repo)
    if status.get("mergeable") is not True or status.get("mergeStateStatus") != "CLEAN":
        print(f"[ERROR] PR #{pr_number} is not mergeable!")
        print(f"  mergeable: {status.get('mergeable')}")
        print(f"  mergeStateStatus: {status.get('mergeStateStatus')}")
        return False

    merge_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    payload = {"merge_method": method}
    if not delete_branch:
        payload["delete_branch"] = False

    try:
        resp = requests.put(merge_url, headers=_github_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        print(f"[PR-AUTO-MERGE] PR #{pr_number} merged successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to merge PR #{pr_number}: {e}")
        return False

def checkout_branch(branch_name, repo_path):
    """Checkout branch locally, creating it from remote if needed"""
    if not has_local_branch(branch_name, repo_path):
        print(f"[PR-AUTO-MERGE] Creating local branch {branch_name} from origin/{branch_name}")
        stdout, code = run_cmd(f"git checkout -b {branch_name} origin/{branch_name}", repo_path)
        if code != 0:
            print(f"[ERROR] Failed to create local branch {branch_name}")
            return False
    else:
        print(f"[PR-AUTO-MERGE] Switching to existing branch {branch_name}")
        stdout, code = run_cmd(f"git checkout {branch_name}", repo_path)
        if code != 0:
            print(f"[ERROR] Failed to checkout {branch_name}")
            return False
    return True

def merge_main_into_branch(repo_path):
    """Merge origin/main into current branch - v2.0 with conflict detection"""
    print(f"[PR-AUTO-MERGE] Merging origin/main into current branch")
    
    # Fetch first
    run_cmd("git fetch origin", repo_path)
    
    # Try merge without commit
    stdout, code = run_cmd("git merge origin/main --no-commit --no-ff", repo_path)
    
    if code == 0:
        print(f"[PR-AUTO-MERGE] Merge clean (no conflicts)")
        return True, []
    
    # Check if there are conflicts
    conflicts_stdout, _ = run_cmd("git diff --name-only --diff-filter=U", repo_path)
    conflicts = [c for c in conflicts_stdout.split('\n') if c.strip()]
    
    if conflicts:
        print(f"[PR-AUTO-MERGE] Merge has {len(conflicts)} conflicts:")
        for c in conflicts:
            print(f"  - {c}")
        return False, conflicts
    
    # Other merge error
    print(f"[PR-AUTO-MERGE] Merge failed with code {code}")
    print(f"  stdout: {stdout}")
    return False, []

def resolve_conflicts(repo_path):
    """Run conflict resolution engine - v2.0"""
    print(f"[PR-AUTO-MERGE] Running conflict resolution engine")
    
    # Import and run conflict resolver
    conflict_script = Path(__file__).parent / "conflict_resolver_engine.py"
    if not conflict_script.exists():
        print(f"[ERROR] Conflict resolver not found: {conflict_script}")
        return False
    
    result = subprocess.run(
        [sys.executable, str(conflict_script), repo_path],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"[WARN] {result.stderr}")
    
    return result.returncode == 0

def commit_merge_resolution(branch_name, repo_path, conflicts):
    """Commit the merge resolution - v2.0"""
    print(f"[PR-AUTO-MERGE] Committing merge resolution")
    
    # Get current main commit hash
    main_hash, _ = run_cmd("git rev-parse origin/main", repo_path)
    
    # Commit message
    msg = f"merge: integrate origin/main into {branch_name}\n\n"
    if conflicts:
        msg += f"- Resolve conflicts in {', '.join(conflicts[:5])}"
        if len(conflicts) > 5:
            msg += f" and {len(conflicts) - 5} more"
        msg += "\n"
    msg += f"- Branch now up-to-date with main ({main_hash[:8]})\n"
    msg += "\nIntentHash: 0xAUTO_MERGE_RESOLUTION_20260713"
    
    # Commit
    stdout, code = run_cmd(f'git commit -m "{msg}"', repo_path)
    if code != 0:
        print(f"[ERROR] Failed to commit merge resolution")
        print(f"  stdout: {stdout}")
        return False
    
    print(f"[PR-AUTO-MERGE] Merge resolution committed")
    return True

def force_push_branch(branch_name, repo_path):
    """Force push branch with lease - v2.0"""
    print(f"[PR-AUTO-MERGE] Force pushing {branch_name} with lease")
    
    # Always use --force-with-lease for safety
    stdout, code = run_cmd(f"git push --force-with-lease origin {branch_name}", repo_path)
    
    if code != 0:
        print(f"[ERROR] Failed to force push {branch_name}")
        print(f"  stdout: {stdout}")
        return False
    
    print(f"[PR-AUTO-MERGE] Force push successful")
    return True

def merge_pr(pr_number, repo, repo_path=None, delete_branch=True, method='squash'):
    """Merge PR via GitHub API - BDCP safe"""
    print(f"[PR-AUTO-MERGE] Merging PR #{pr_number} via GitHub API")

    status = get_pr_status(pr_number, repo)
    if status.get("mergeable") is not True or status.get("mergeStateStatus") != "CLEAN":
        print(f"[ERROR] PR #{pr_number} is not mergeable!")
        print(f"  mergeable: {status.get('mergeable')}")
        print(f"  mergeStateStatus: {status.get('mergeStateStatus')}")
        return False

    merge_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    payload = {"merge_method": method}
    if not delete_branch:
        payload["delete_branch"] = False

    try:
        resp = requests.put(merge_url, headers=_github_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        print(f"[PR-AUTO-MERGE] PR #{pr_number} merged successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to merge PR #{pr_number}: {e}")
        return False

def _command_exists(cmd):
    """Check if a command exists"""
    stdout, code = run_cmd(f"command -v {cmd}")
    return code == 0

def sync_main(repo_path):
    """Sync main branch with remote - v2.0"""
    print(f"[PR-AUTO-MERGE] Syncing main with remote...")

    run_cmd("git fetch origin", repo_path)

    # Check if main is behind
    stdout, code = run_cmd("git rev-parse main", repo_path)
    local_main = stdout.strip()

    stdout, code = run_cmd("git rev-parse origin/main", repo_path)
    remote_main = stdout.strip()

    if local_main != remote_main:
        print(f"[PR-AUTO-MERGE] main is behind - syncing")
        run_cmd("git checkout main", repo_path)
        run_cmd("git pull origin main", repo_path)
        print(f"[PR-AUTO-MERGE] main synced")
    else:
        print(f"[PR-AUTO-MERGE] main is up-to-date")

    return True

def process_branch(branch, repo, repo_path, auto_merge=False):
    """Process a single branch - v2.0 with full workflow"""
    branch_name = branch.replace('origin/', '')
    
    print(f"\n[PR-AUTO-MERGE] Processing branch: {branch_name}")
    
    # Check if local branch exists
    if not has_local_branch(branch_name, repo_path):
        print(f"[PR-AUTO-MERGE] No local branch - skipping")
        return
    
    # Check if branch has unmerged commits
    has_commits, commits = has_unmerged_commits(branch, repo_path)
    if not has_commits:
        print(f"[PR-AUTO-MERGE] Branch is up-to-date with main - deleting")
        run_cmd(f"git branch -D {branch_name}", repo_path)
        return
    
    print(f"[PR-AUTO-MERGE] Branch has {len(commits)} unmerged commits")
    
    # Check if PR exists
    pr_num = get_pr_number(branch_name, repo)
    
    if pr_num is None:
        print(f"[PR-AUTO-MERGE] Creating PR for {branch_name}")
        pr_num = create_pr(branch, repo)
        if not pr_num:
            print(f"[PR-AUTO-MERGE] Failed to create PR for {branch_name}")
            return
        print(f"[PR-AUTO-MERGE] PR #{pr_num} created")
    else:
        print(f"[PR-AUTO-MERGE] PR #{pr_num} exists for {branch_name}")
    
    # Check if PR can be merged
    status = get_pr_status(pr_num, repo)
    
    if status['mergeable'] == 'MERGEABLE' and status['mergeStateStatus'] == 'CLEAN':
        if auto_merge:
            print(f"[PR-AUTO-MERGE] PR #{pr_num} is mergeable - merging")
            merge_pr(pr_num, repo)
        else:
            print(f"[PR-AUTO-MERGE] PR #{pr_num} is mergeable - run with --auto-merge to merge")
    else:
        print(f"[PR-AUTO-MERGE] PR #{pr_num} is not mergeable yet")
        print(f"  mergeable: {status['mergeable']}")
        print(f"  mergeStateStatus: {status['mergeStateStatus']}")
        
        # Try to resolve conflicts automatically
        if status['mergeStateStatus'] == 'DIRTY' or status['mergeable'] == 'CONFLICTING':
            print(f"[PR-AUTO-MERGE] Attempting automatic conflict resolution")
            
            # Checkout branch
            if not checkout_branch(branch_name, repo_path):
                return
            
            # Merge main
            success, conflicts = merge_main_into_branch(repo_path)
            
            if not success and conflicts:
                # Resolve conflicts
                if resolve_conflicts(repo_path):
                    # Commit resolution
                    if commit_merge_resolution(branch_name, repo_path, conflicts):
                        # Force push
                        if force_push_branch(branch_name, repo_path):
                            print(f"[PR-AUTO-MERGE] Branch updated - re-checking PR")
                            
                            # Re-check PR status
                            new_status = get_pr_status(pr_num, repo)
                            if new_status['mergeable'] == 'MERGEABLE' and new_status['mergeStateStatus'] == 'CLEAN':
                                if auto_merge:
                                    merge_pr(pr_num, repo)
                                else:
                                    print(f"[PR-AUTO-MERGE] PR #{pr_num} is now mergeable - run with --auto-merge to merge")
                            else:
                                print(f"[PR-AUTO-MERGE] PR #{pr_num} still not mergeable after resolution")
                                print(f"  mergeable: {new_status['mergeable']}")
                                print(f"  mergeStateStatus: {new_status['mergeStateStatus']}")
                        else:
                            print(f"[ERROR] Failed to force push {branch_name}")
                    else:
                        print(f"[ERROR] Failed to commit merge resolution")
                else:
                    print(f"[ERROR] Conflict resolution failed")
            elif not success:
                print(f"[ERROR] Merge failed for unknown reason")

def main():
    """Main entry point - v2.0"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PR Auto-Merge Orchestrator v2.0")
    parser.add_argument("--repo", required=True, help="Repo (owner/name)")
    parser.add_argument("--repo-path", help="Local repo path (default: current directory)")
    parser.add_argument("--auto-merge", action="store_true", help="Auto-merge passing PRs")
    parser.add_argument("--branch", help="Process specific branch only")
    args = parser.parse_args()
    
    repo_path = Path(args.repo_path) if args.repo_path else Path.cwd()
    
    print(f"[PR-AUTO-MERGE] v2.0 - PR Auto-Merge Orchestrator")
    print(f"[PR-AUTO-MERGE] Repository: {args.repo}")
    print(f"[PR-AUTO-MERGE] Path: {repo_path}")
    print(f"[PR-AUTO-MERGE] Auto-merge: {args.auto_merge}")
    
    # Sync main first
    sync_main(repo_path)
    
    # Get branches
    if args.branch:
        branches = [args.branch]
    else:
        branches = get_feature_branches(repo_path)
    
    print(f"[PR-AUTO-MERGE] Found {len(branches)} branches to process")
    
    # Process each branch
    for branch in branches:
        try:
            process_branch(branch, args.repo, repo_path, args.auto_merge)
        except Exception as e:
            print(f"[ERROR] Failed to process {branch}: {e}")
            continue
    
    print(f"\n[PR-AUTO-MERGE] Scan complete")

if __name__ == "__main__":
    main()
