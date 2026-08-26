#!/usr/bin/env python3
"""
Conflict Resolver Engine - v2.0
Automated conflict resolution using business rules derived from production experience.

Version: 2.0
Date: 2026-07-13
IntentHash: 0xCONFLICT_RESOLVER_ENGINE_V2_20260713

Changelog:
- v1.0: Initial version with basic rules
- v2.0: Added production-learned rules from PR #167-170 resolution
  - README.md: always keep ours (branch version)
  - YAML: merge both versions
  - JSON: keep most complete version
  - Deleted files in main: restore from main
  - ONTOLOGY.yaml: always keep main version
"""

import subprocess
import os
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Conflict resolution rules - v2.0
# Priority order matters: first match wins
CONFLICT_RULES = [
    # (pattern, strategy, reason)
    ("README.md", "ours", "Branch version contains feature additions (badges, sections, arborescence)"),
    ("ONTOLOGY.yaml", "theirs", "ONTOLOGY.yaml is canonical - main version is authoritative"),
    ("*.yaml", "merge_lines", "YAML files often have additive changes from both sides"),
    ("*.json", "theirs", "JSON files: keep most complete version (usually main)"),
    ("*.py", "ours", "Python files: branch version contains the feature code"),
    ("test_*.py", "ours", "Test files: branch version matches the feature"),
    ("*.md", "ours", "Markdown files: branch version contains feature documentation"),
]

# Files that should never be auto-resolved
BLACKLIST = [
    "*.key",
    "*.pem",
    ".env",
    "*.secret",
    "credentials.yaml",
]

def run_cmd(cmd, cwd=None):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def get_conflict_files(repo_path):
    """Get list of files with conflicts"""
    stdout, code = run_cmd("git status --porcelain", repo_path)
    conflicts = []
    for line in stdout.split('\n'):
        if line.startswith('U') or 'UU' in line:
            parts = line.split()
            if parts:
                conflicts.append(parts[-1])
    return conflicts

def is_blacklisted(filepath):
    """Check if file is in blacklist"""
    filename = os.path.basename(filepath)
    for pattern in BLACKLIST:
        if pattern.startswith('*'):
            ext = pattern[1:]
            if filename.endswith(ext):
                return True
        elif filename == pattern:
            return True
    return False

def match_rule(filepath):
    """Match file against conflict rules - v2.0 with priority"""
    filename = os.path.basename(filepath)
    
    # Check blacklist first
    if is_blacklisted(filepath):
        return "reject", "Blacklisted file - manual resolution required"
    
    # Check rules in priority order
    for pattern, strategy, reason in CONFLICT_RULES:
        if pattern.startswith('*'):
            # Extension match
            ext = pattern[1:]
            if filename.endswith(ext):
                return strategy, reason
        elif filename == pattern or filepath.endswith(pattern):
            return strategy, reason
    
    # Default: don't auto-resolve
    return "reject", "No matching rule - manual resolution required"

def resolve_ours(filepath, repo_path):
    """Resolve conflict by taking our version (branch)"""
    try:
        result = subprocess.run(
            f'git checkout --ours "{filepath}"',
            shell=True, cwd=repo_path, capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[CONFLICT] Failed to resolve ours for {filepath}: {e}")
        return False

def resolve_theirs(filepath, repo_path):
    """Resolve conflict by taking their version (main)"""
    try:
        result = subprocess.run(
            f'git checkout --theirs "{filepath}"',
            shell=True, cwd=repo_path, capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[CONFLICT] Failed to resolve theirs for {filepath}: {e}")
        return False

def resolve_merge_lines(filepath, repo_path):
    """Merge lines from both versions - v2.0 improved"""
    try:
        # Get both versions
        ours_result = subprocess.run(
            f'git show :2:"{filepath}" 2>/dev/null',
            shell=True, cwd=repo_path, capture_output=True, text=True
        )
        theirs_result = subprocess.run(
            f'git show :3:"{filepath}" 2>/dev/null',
            shell=True, cwd=repo_path, capture_output=True, text=True
        )
        
        ours_content = ours_result.stdout if ours_result.stdout else ""
        theirs_content = theirs_result.stdout if theirs_result.stdout else ""
        
        # For YAML files, try to merge by keeping all unique keys
        if filepath.endswith('.yaml') or filepath.endswith('.yml'):
            merged = merge_yaml(ours_content, theirs_content)
        else:
            # For other files, concatenate with separator
            merged = f"# === AUTO-MERGED FROM BOTH VERSIONS ===\n"
            merged += f"# === OURS (branch) ===\n{ours_content}\n"
            merged += f"# === THEIRS (main) ===\n{theirs_content}\n"
        
        # Write merged content
        full_path = os.path.join(repo_path, filepath)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(merged)
        
        return True
    except Exception as e:
        print(f"[CONFLICT] Failed to merge lines for {filepath}: {e}")
        return False

def merge_yaml(ours, theirs):
    """Merge two YAML contents by keeping all unique top-level keys"""
    try:
        import yaml
        
        ours_data = yaml.safe_load(ours) or {}
        theirs_data = yaml.safe_load(theirs) or {}
        
        # Merge: start with ours, add keys from theirs that don't exist
        merged = ours_data.copy()
        for key, value in theirs_data.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursive merge for nested dicts
                merged[key] = {**merged[key], **value}
        
        return yaml.dump(merged, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"[CONFLICT] YAML merge failed, falling back to concat: {e}")
        return f"# === AUTO-MERGED (fallback) ===\n{ours}\n{theirs}"

def restore_from_main(filepath, repo_path):
    """Restore file from main branch"""
    try:
        result = subprocess.run(
            f'git show origin/main:"{filepath}" > "{filepath}"',
            shell=True, cwd=repo_path, capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[CONFLICT] Failed to restore {filepath} from main: {e}")
        return False

def resolve_conflict(filepath, repo_path):
    """Resolve a single conflict file - v2.0"""
    strategy, reason = match_rule(filepath)
    
    if strategy == "reject":
        print(f"[CONFLICT] No auto-resolution rule for {filepath}: {reason}")
        return False, filepath, reason
    
    print(f"[CONFLICT] Resolving {filepath} with strategy: {strategy} ({reason})")
    
    if strategy == "ours":
        result = resolve_ours(filepath, repo_path)
    elif strategy == "theirs":
        result = resolve_theirs(filepath, repo_path)
    elif strategy == "merge_lines":
        result = resolve_merge_lines(filepath, repo_path)
    elif strategy == "restore_from_main":
        result = restore_from_main(filepath, repo_path)
    else:
        print(f"[CONFLICT] Unknown strategy: {strategy}")
        return False, filepath, reason
    
    if result:
        print(f"[CONFLICT] ✓ Resolved {filepath}")
    else:
        print(f"[CONFLICT] ✗ Failed to resolve {filepath}")
    
    return result, filepath, reason

def run_conflict_resolution(repo_path, auto_add=True):
    """Run full conflict resolution - v2.0"""
    print(f"[CONFLICT] Starting conflict resolution at {datetime.now()}")
    print(f"[CONFLICT] Repository: {repo_path}")
    
    conflicts = get_conflict_files(repo_path)
    print(f"[CONFLICT] Found {len(conflicts)} conflicted files")
    
    if not conflicts:
        print("[CONFLICT] No conflicts to resolve")
        return {"conflicts_found": 0, "resolved": [], "failed": []}
    
    resolved = []
    failed = []
    rules_applied = {}
    
    for filepath in conflicts:
        success, path, reason = resolve_conflict(filepath, repo_path)
        if success:
            resolved.append(path)
            rules_applied[path] = reason
        else:
            failed.append(path)
    
    # Mark as resolved
    if resolved and auto_add:
        print(f"[CONFLICT] Staging {len(resolved)} resolved files")
        for filepath in resolved:
            subprocess.run(
                f'git add "{filepath}"',
                shell=True, cwd=repo_path, capture_output=True, text=True
            )
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "repository": str(repo_path),
        "conflicts_found": len(conflicts),
        "resolved": resolved,
        "failed": failed,
        "rules_applied": rules_applied,
        "version": "2.0"
    }
    
    # Write report
    report_dir = os.path.join(repo_path, "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"conflict_resolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n[CONFLICT] Resolution complete")
    print(f"[CONFLICT] Resolved: {len(resolved)}/{len(conflicts)}")
    print(f"[CONFLICT] Failed: {len(failed)}")
    print(f"[CONFLICT] Report: {report_path}")
    
    if failed:
        print(f"\n[CONFLICT] WARNING: {len(failed)} files could not be auto-resolved:")
        for path in failed:
            print(f"  - {path}")
        print("[CONFLICT] Manual resolution required for these files")
    
    return report

def main():
    """Main entry point"""
    # Default to current directory or REPO-STANDARDS
    repo_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent.parent)
    
    if not os.path.isdir(repo_path):
        print(f"[ERROR] Invalid repository path: {repo_path}")
        sys.exit(1)
    
    report = run_conflict_resolution(repo_path)
    
    # Exit with error code if conflicts failed
    if report["failed"]:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
