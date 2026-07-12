#!/usr/bin/env python3
"""
Sync forks from upstream.
Respects fork_source.sync_frequency and conflict_strategy.
"""
import subprocess
import yaml
import sys
import json
from pathlib import Path

def sync_fork(repo_config):
    repo_name = repo_config["name"]
    local_path = repo_config["local_path"]
    fork_source = repo_config.get("fork_source")
    
    if not fork_source:
        return {"repo": repo_name, "status": "skipped", "reason": "no fork_source"}
    
    if not Path(local_path).exists():
        return {"repo": repo_name, "status": "error", "reason": f"local_path {local_path} not found"}
    
    # Add upstream remote if missing
    remotes = subprocess.run(["git", "remote", "-v"], cwd=local_path, capture_output=True, text=True).stdout
    if "upstream" not in remotes:
        upstream_url = f"https://github.com/{fork_source['owner']}/{fork_source['repo']}.git"
        result = subprocess.run(["git", "remote", "add", "upstream", upstream_url], cwd=local_path, capture_output=True, text=True)
        if result.returncode != 0:
            return {"repo": repo_name, "status": "error", "reason": f"add upstream failed: {result.stderr}"}
    
    # Fetch upstream
    result = subprocess.run(["git", "fetch", "upstream"], cwd=local_path, capture_output=True, text=True)
    if result.returncode != 0:
        return {"repo": repo_name, "status": "error", "reason": f"fetch failed: {result.stderr}"}
    
    # Check if upstream has new commits
    local_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=local_path, capture_output=True, text=True).stdout.strip()
    upstream_sha = subprocess.run(["git", "rev-parse", f"upstream/{fork_source['branch']}"], cwd=local_path, capture_output=True, text=True).stdout.strip()
    
    if local_sha == upstream_sha:
        return {"repo": repo_name, "status": "up_to_date"}
    
    # Try merge
    merge_result = subprocess.run(["git", "merge", f"upstream/{fork_source['branch']}"], cwd=local_path, capture_output=True, text=True)
    
    if merge_result.returncode == 0:
        # Push merged result
        subprocess.run(["git", "push", "origin", "main"], cwd=local_path, check=True)
        return {"repo": repo_name, "status": "merged", "from_sha": local_sha, "to_sha": upstream_sha}
    
    # Conflict
    conflict_strategy = fork_source.get("conflict_strategy", "hitl")
    if conflict_strategy == "hitl":
        # Create issue in GOVERNANCE-HUB
        issue_title = f"[FORK SYNC CONFLICT] {repo_name} - upstream merge failed"
        issue_body = f"Auto-merge of upstream/{fork_source['branch']} into {repo_name} failed.\n\n```\n{merge_result.stdout}\n{merge_result.stderr}\n```\n\nResolve locally then close issue."
        subprocess.run([
            "gh", "issue", "create",
            "--repo", "gerivdb/GOVERNANCE-HUB",
            "--title", issue_title,
            "--body", issue_body,
            "--label", "fork-conflict,needs-hitl"
        ], capture_output=True)
        # Abort merge
        subprocess.run(["git", "merge", "--abort"], cwd=local_path)
        return {"repo": repo_name, "status": "conflict", "issue_created": True}
    
    return {"repo": repo_name, "status": "error", "reason": "conflict, no resolution strategy"}

def main():
    KNOWN_REPOS = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml")
    
    with open(KNOWN_REPOS) as f:
        data = yaml.safe_load(f)
    
    all_repos = []
    for tier in ["P0_REPOS", "P1_REPOS", "P2_REPOS", "P3_REPOS"]:
        all_repos.extend(data.get(tier, []))
    
    forked_repos = [r for r in all_repos if r.get("fork_source") and r.get("status") == "ACTIVE"]
    
    results = []
    for repo in forked_repos:
        result = sync_fork(repo)
        results.append(result)
        print(f"[FORK-SYNC] {repo['name']}: {result['status']}")
    
    # Write report
    Path("fork-sync-report.json").write_text(json.dumps(results, indent=2))
    
    conflicts = [r for r in results if r.get("status") == "conflict"]
    if conflicts:
        print(f"[WARN] {len(conflicts)} conflicts requiring HITL")
        sys.exit(1)
    
    print("[OK] All forks synced")
    sys.exit(0)

if __name__ == "__main__":
    main()