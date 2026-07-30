#!/usr/bin/env python3
"""Extract dependencies from ATOM-*.md files and update atoms_registry.yaml"""
import re
import sys
import yaml
from pathlib import Path

ATOM_DIR = Path("atoms")
REGISTRY_FILE = Path("atoms_registry.yaml")

def extract_dependencies(content):
    """Extract depends_on from YAML front matter or Markdown body."""
    # Simple regex for depends_on: [...] or depends_on: ATOM-XXX
    match = re.search(r'depends_on:\s*(\[.*?\]|ATOM-\d+)', content, re.IGNORECASE)
    if match:
        raw = match.group(1)
        if raw.startswith('['):
            return [x.strip() for x in raw.strip('[]').split(',') if x.strip()]
        return [raw.strip()]
    return []

def build_registry():
    registry = {}
    for md_file in ATOM_DIR.glob("ATOM-*.md"):
        content = md_file.read_text(encoding='utf-8')
        deps = extract_dependencies(content)
        # Use existing hash from registry if unchanged, else compute?
        # For now, we just report deps; we'll update registry later.
        registry[md_file.name] = {
            "path": str(md_file),
            "depends_on": deps
        }
    return registry

def main():
    dry = "--dry-run" in sys.argv
    write = "--write" in sys.argv
    registry = build_registry()
    if dry:
        print("Dependencies found:")
        for name, data in registry.items():
            print(f"  {name}: {data['depends_on']}")
        return
    if write:
        # Load existing registry, update deps, preserve hash/description
        existing = {}
        if REGISTRY_FILE.exists():
            existing = yaml.safe_load(REGISTRY_FILE.read_text(encoding='utf-8')) or {}
        for name, data in registry.items():
            if name in existing:
                existing[name]["depends_on"] = data["depends_on"]
            else:
                existing[name] = data
        REGISTRY_FILE.write_text(yaml.dump(existing, sort_keys=False, allow_unicode=True), encoding='utf-8')
        print(f"Updated {REGISTRY_FILE} with {len(existing)} entries")
    else:
        print("Use --dry-run to preview, --write to update registry.")

if __name__ == "__main__":
    main()