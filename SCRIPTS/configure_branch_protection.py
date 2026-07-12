#!/usr/bin/env python3
"""
Configure branch protection via GitHub API.
"""
import subprocess
import sys
import json
import argparse
import tempfile

REQUIRED_CONTEXTS = [
    "RSS-v2 Linter",
    "BRGS — Branch Ownership Check",
    "BRANCH-GOVERNOR — Branch Naming Check",
    "VYOA Verify"
]

PROTECTION_PAYLOAD = {
    "required_status_checks": {
        "strict": True,
        "contexts": REQUIRED_CONTEXTS
    },
    "enforce_admins": True,
    "required_pull_request_reviews": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False
    },
    "restrictions": None,
    "allow_force_pushes": False,
    "allow_deletions": False,
    "block_creations": False
}

def configure_protection(repo, checks):
    required = [c.strip() for c in checks.split(",")]
    payload = PROTECTION_PAYLOAD.copy()
    payload["required_status_checks"]["contexts"] = required
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        temp_file = f.name
    
    cmd = [
        "gh", "api", f"repos/{repo}/branches/main/protection",
        "-X", "PUT", "--input", temp_file,
        "-H", "Accept: application/vnd.github+json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", required=True)
    parser.add_argument("--checks", required=True)
    parser.add_argument("--token", required=False)
    args = parser.parse_args()

    repos = json.loads(args.repos)
    print(f"[PROTECTION] Configuring {len(repos)} repos")
    
    for repo in repos:
        ok, err = configure_protection(repo, args.checks)
        print(f"  {repo}: {'OK' if ok else f'FAIL ({err})'}")
    
    print("[DONE]")

if __name__ == "__main__":
    main()