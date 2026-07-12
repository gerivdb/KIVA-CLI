#!/usr/bin/env python3
"""
Bootstrap complet d'un repo ACTIVE en < 5 min.
Usage: python bootstrap_repo.py --repo gerivdb/NEW-REPO
"""
import subprocess, sys, time, json, tempfile, base64
from pathlib import Path

REUSABLE_WORKFLOWS = [
    ("rss-lint.yml", "gerivdb/KIVA-CLI/.github/workflows/rss-v2-reusable.yml@gov-workflows/v1",
     {"repo_path": ".", "checks": "all", "depth": "auto"}),
    ("vyoa-verify.yml", "gerivdb/KIVA-CLI/.github/workflows/vyoa-verify-reusable.yml@gov-workflows/v1",
     {"action": "commit", "args": ""}),
    ("branch-gate.yml", "gerivdb/KIVA-CLI/.github/workflows/branch-gate.yml@gov-workflows/v1",
     {}),
]

HOOKS_SOURCE = Path("D:/DO/WEB/TOOLS/L4-TOOLS/REPO-STANDARDS/.githooks")
HOOK_FILES = ["pre-commit", "pre-push", "commit-msg", "post-commit", "post-push", "post-merge", "rules.sh"]

PROTECTION_CONTEXTS = [
    "RSS-v2 Linter",
    "BRGS — Branch Ownership Check",
    "BRANCH-GOVERNOR — Branch Naming Check",
    "VYOA Verify"
]

def run(cmd, check=True, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result

def deploy_workflow(repo, name, reusable_ref, inputs):
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
    b64 = base64.b64encode(content.encode()).decode()
    run(f'gh api repos/{repo}/contents/.github/workflows/{name} -X PUT '
        f'-f "message=ci: bootstrap {name} [skip ci]" -f "content={b64}" -f "branch=main"')

def deploy_hooks(repo):
    for hook in HOOK_FILES:
        src = Path("D:/DO/WEB/TOOLS/L4-TOOLS/REPO-STANDARDS/.githooks") / hook
        if not src.exists():
            continue
        b64 = base64.b64encode(src.read_bytes()).decode()
        run(f'gh api repos/{repo}/contents/.githooks/{hook} -X PUT '
            f'-f "message=ci(hooks): bootstrap {hook} [skip ci]" -f "content={b64}" -f "branch=main"')

def wait_for_status_checks(repo, contexts, timeout=180):
    print(f"[WAIT] Waiting for status checks: {contexts}")
    start = time.time()
    while time.time() - start < timeout:
        result = run(f'gh api repos/{repo}/commits/main/check-runs --jq ".check_runs[].name"', check=False)
        existing = set(result.stdout.strip().split('\n')) if result.returncode == 0 else set()
        missing = [c for c in contexts if c not in existing]
        if not missing:
            print(f"[OK] All status checks present")
            return True
        print(f"  ... missing: {missing} ({int(time.time()-start)}s)")
        time.sleep(10)
    raise TimeoutError(f"Status checks not ready after {timeout}s: {missing}")

def configure_protection(repo):
    import json
    payload = {
        "required_status_checks": {"strict": True, "contexts": PROTECTION_CONTEXTS},
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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        run(f'gh api repos/{repo}/branches/main/protection -X PUT --input {f.name}')

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Full repo name (owner/name)")
    args = parser.parse_args()
    
    print(f"[BOOTSTRAP] {args.repo}")
    start = time.time()
    
    try:
        # 1. Workflows
        print("[1/5] Deploying workflows...")
        for name, ref, inputs in REUSABLE_WORKFLOWS:
            deploy_workflow(args.repo, name, ref, inputs)
        
        # 2. Hooks
        print("[2/5] Deploying hooks...")
        deploy_hooks(args.repo)
        
        # 3. Rules.sh (assume generated)
        print("[3/5] BRGS rules.sh deployed with hooks")
        
        # 4. Wait for status checks
        print("[4/5] Waiting for status checks...")
        wait_for_status_checks(args.repo, PROTECTION_CONTEXTS)
        
        # 5. Branch protection
        print("[5/5] Configuring branch protection...")
        configure_protection(args.repo)
        
        elapsed = time.time() - start
        print(f"[BOOTSTRAP COMPLETE] {args.repo} in {elapsed:.1f}s")
        
    except Exception as e:
        print(f"[BOOTSTRAP FAILED] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()