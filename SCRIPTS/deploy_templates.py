#!/usr/bin/env python3
"""
Deploy governance workflow templates to all ACTIVE repos.
"""
import subprocess
import sys
import json
from pathlib import Path

TEMPLATES = {
    "rss-lint.yml": "gerivdb/KIVA-CLI/.github/workflows/rss-v2-reusable.yml@gov-workflows/v1",
    "vyoa-verify.yml": "gerivdb/KIVA-CLI/.github/workflows/vyoa-verify-reusable.yml@gov-workflows/v1",
    "branch-gate.yml": "gerivdb/KIVA-CLI/.github/workflows/branch-gate.yml@gov-workflows/v1",
}

def make_workflow(name, reusable_ref, inputs):
    inputs_yaml = "\n".join(f"      {k}: {v}" for k,v in inputs.items())
    content = f"""name: {name.replace('.yml','')}
on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
jobs:
  {name.replace('.yml','').replace('-','_')}:
    uses: {reusable_ref}
    with:
{inputs_yaml}
    secrets: inherit
"""
    return base64.b64encode(content.encode()).decode()

def deploy_workflow(repo, name, reusable_ref, inputs):
    b64 = make_workflow(name, reusable_ref, inputs)
    result = subprocess.run([
        "gh", "api", f"repos/{repo}/contents/.github/workflows/{name}",
        "-X", "PUT",
        "-f", f"message=ci: deploy governance template {name} [skip ci]",
        "-f", f"content={b64}",
        "-f", "branch=main"
    ], capture_output=True, text=True)
    return result.returncode == 0

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="REPO-STANDARDS/.github/workflows")
    parser.add_argument("--target-repos", required=True, help="JSON array of repo full_names")
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    
    import os
    os.environ["GITHUB_TOKEN"] = args.token
    
    target_repos = json.loads(args.target_repos)
    print(f"[DEPLOY] Deploying templates to {len(target_repos)} repos...")
    
    for repo in target_repos:
        print(f"  [DEPLOY] {repo}...")
        success = True
        for name, ref in TEMPLATES.items():
            inputs = {"repo_path": ".", "checks": "all", "depth": "auto"} if name == "rss-lint.yml" else \
                     {"action": "commit", "args": ""} if name == "vyoa-verify.yml" else \
                     {}
            if not deploy_workflow(repo, name, ref, inputs):
                print(f"    ✗ {name}")
                success = False
            else:
                print(f"    ✓ {name}")
        if success:
            print(f"  [OK] {repo}")
        else:
            print(f"  [FAIL] {repo}")

if __name__ == "__main__":
    import base64
    main()