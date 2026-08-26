#!/usr/bin/env python3
"""Validate atoms_registry.yaml structure and references."""

import sys
import hashlib
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] pyyaml is required: pip install pyyaml")
    sys.exit(1)


REGISTRY_PATH = Path("atoms_registry.yaml")
ATOMS_DIR = Path("atoms")


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def validate() -> bool:
    if not REGISTRY_PATH.exists():
        print(f"[ERROR] Registry not found: {REGISTRY_PATH}")
        return False

    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "atoms" not in data:
        print("[ERROR] Invalid registry root: missing 'atoms' key")
        return False

    atoms = data["atoms"]
    if not isinstance(atoms, list):
        print("[ERROR] 'atoms' must be a list")
        return False

    errors = []
    paths = set()
    all_ids = set()

    for idx, entry in enumerate(atoms, start=1):
        if not isinstance(entry, dict):
            errors.append(f"[ERROR] Atom #{idx}: not a mapping")
            continue

        path = entry.get("path")
        if not path:
            errors.append(f"[ERROR] Atom #{idx}: missing 'path'")
            continue

        abs_path = Path(path)
        if not abs_path.exists():
            errors.append(f"[ERROR] Atom #{idx}: file not found: {path}")
        else:
            expected_hash = sha1_file(abs_path)
            actual_hash = entry.get("hash", "")
            if actual_hash != expected_hash:
                errors.append(
                    f"[ERROR] Atom #{idx}: hash mismatch for {path}: "
                    f"registry={actual_hash}, file={expected_hash}"
                )

        depends_on = entry.get("depends_on", [])
        if not isinstance(depends_on, list):
            errors.append(f"[ERROR] Atom #{idx}: 'depends_on' must be a list")
            depends_on = []

    if errors:
        for e in errors:
            print(e)
        print(f"[KO] Registry validation failed: {len(errors)} error(s)")
        return False

    print(f"[OK] Registry validation passed: {len(atoms)} atom(s) checked")
    return True


if __name__ == "__main__":
    result = validate()
    sys.exit(0 if result else 1)
