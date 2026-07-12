#!/usr/bin/env python3
"""
Deploy git hooks to all ACTIVE repos.
"""
import subprocess
import sys
import json
import base64
from pathlib import Path

def deploy_hook(repo, hook_name, content_b64):
    result = subprocess.run([
        "gh", "api", f"repos/{repo}/contents/.githooks/{hook_name}",
        "-X", "PUT",
        "-f", f"message=ci(hooks): deploy {hook_name} [skip ci]",
        "-f", f"content={content_b64}",
        "-f", "branch=main"
    ], capture_output=True, text=True)
    return result.returncode == 0

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Source .githooks directory")
    parser.add_argument("--target-repos", required=True, help="JSON array of repo full_names")
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    
    import os
    os.environ["GITHUB_TOKEN"] = args.token
    
    target_repos = json.loads(args.target_repos)
    source_dir = Path(args.source)
    
    hook_files = [f for f in source_dir.iterdir() 
                  if f.is_file() and not f.name.startswith("README") and f.suffix in [".sh", ".ps1", ""]]
    
    print(f"[DEPLOY-HOOKS] Deploying {len(hook_files)} hooks to {len(target_repos)} repos...")
    
    for repo in target_repos:
        print(f"  [DEPLOY] {repo}...")
        for hook in hook_files:
            content_b64 = base64.b64encode(hook.read_bytes()).decode().strip()
            if deploy_hook(repo, hook.name, content_b64):
                print(f"    ✓ {hook.name}")
            else:
                print(f"    ✗ {hook.name}")
        print(f"  [OK] {repo}")

if __name__ == "__main__":
    main()