#!/usr/bin/env python3
"""
Verify gitignore - Nettoie les fichiers non trackés et corrompus
"""
import subprocess
import sys
import re
from pathlib import Path

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def get_untracked_files():
    """Get list of untracked files"""
    output, code = run_cmd("git ls-files --others --exclude-standard")
    if code != 0 or not output:
        return []
    return [f for f in output.split('\n') if f.strip()]

def is_corrupted_filename(filename):
    """Detect if filename contains corrupted characters"""
    # Look for common corruption patterns
    patterns = [
        r'\\x[0-9a-fA-F]{2}',  # Hex escape sequences
        r'\\([0-9]{3})',      # Octal escape sequences
        r'[^\x00-\x7F]',      # Non-ASCII characters (potential UTF-8 corruption)
    ]
    for pattern in patterns:
        if re.search(pattern, filename):
            return True
    return False

def get_corrupted_files():
    """Find files with corrupted names"""
    output, code = run_cmd("git status --porcelain")
    if code != 0 or not output:
        return []
    
    corrupted = []
    for line in output.split('\n'):
        if not line.strip():
            continue
        # Extract filename from porcelain output
        parts = line.split(' ', 1)
        if len(parts) > 1:
            filename = parts[1].strip('"\'')
            if is_corrupted_filename(filename):
                corrupted.append(filename)
    return corrupted

def remove_corrupted_file(filepath):
    """Remove a corrupted file"""
    try:
        Path(filepath).unlink()
        return True
    except Exception as e:
        print(f"  ✗ Failed to remove {filepath}: {e}")
        return False

def main():
    print("[GITIGNORE] Checking untracked files...")
    
    # Get untracked files
    untracked = get_untracked_files()
    print(f"[GITIGNORE] Found {len(untracked)} untracked files")
    
    # Find corrupted files
    corrupted = get_corrupted_files()
    if corrupted:
        print(f"[GITIGNORE] WARNING: Found {len(corrupted)} corrupted files")
        for f in corrupted:
            print(f"  ⚠ Corrupted: {f}")
    
    # Remove corrupted files
    removed = 0
    for filepath in corrupted:
        if remove_corrupted_file(filepath):
            print(f"  ✓ Removed corrupted: {filepath}")
            removed += 1
    
    # Report
    print(f"[GITIGNORE] Total removed: {removed}")
    
    # Check if there are files to add to .gitignore
    if untracked:
        print(f"[GITIGNORE] Consider adding to .gitignore:")
        for f in untracked[:10]:  # Show first 10
            print(f"  {f}")
        if len(untracked) > 10:
            print(f"  ... and {len(untracked) - 10} more")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())