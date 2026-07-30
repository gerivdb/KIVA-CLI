#!/usr/bin/env python3
"""Validate ADR references in META-DESIGN.yaml"""
import sys
import yaml
import os
from pathlib import Path

def main():
    meta_path = Path("META-DESIGN.yaml")
    adr_dir = Path("ADR")
    
    if not meta_path.exists():
        print(f"[ERROR] {meta_path} not found")
        return 1
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find ADR references like ADR-XXX
    import re
    adr_refs = re.findall(r'ADR-(\d+)', content)
    
    missing = []
    for ref in set(adr_refs):
        adr_file = adr_dir / f"ADR-{int(ref):03d}-*.md"
        if not list(adr_dir.glob(f"ADR-{int(ref):03d}-*.md")):
            missing.append(f"ADR-{int(ref):03d}")
    
    if missing:
        print(f"[ERROR] Missing ADR files: {', '.join(missing)}")
        return 1
    
    print(f"[OK] All {len(set(adr_refs))} ADR references found in {adr_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())