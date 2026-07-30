#!/usr/bin/env python3
"""Anti-Anachronism Validator - DETECTE et BLOCKE les anomalies temporelles."""

import json
import sys
from pathlib import Path
from datetime import datetime


def check_path_resolution(script_path: Path) -> dict:
    """Vérifie que les scripts n'utilisent pas __file__ traversal erroné."""
    content = script_path.read_text()
    
    # Pattern dangereux : __file__.parent.parent.parent (ou moins)
    if "__file__.parent.parent" in content and "__file__.parent.parent.parent.parent" not in content:
        return {"status": "BLOCKED", "reason": "Incomplete __file__ traversal"}
    
    return {"status": "OK", "reason": "Path resolution safe"}


def check_registry_drift(registry_path: Path, repo_name: str) -> dict:
    """Vérifie que le repo existe dans known_repositories.yaml."""
    import yaml
    
    phases = ["P0_REPOS", "P1_REPOS", "P2_REPOS", "P3_REPOS", "P4_REPOS", "P5_REPOS"]
    
    for phase in phases:
        for entry in registry.get(phase, []):
            if entry.get("name") == repo_name:
                return {"status": "OK", "local_path": entry.get("local_path")}
    
    return {"status": "BLOCKED", "reason": f"{repo_name} not in registry"}


def check_import_valid(module_path: Path) -> dict:
    """Vérifie que le module Python importe correctement."""
    # Test basique : fichier syntaxiquement valide
    import py_compile
    try:
        py_compile.compile(str(module_path), doraise=True)
        return {"status": "OK"}
    except py_compile.PyCompileError as e:
        return {"status": "BLOCKED", "reason": str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Anti-Anachronism Validator")
    parser.add_argument("--check-path", help="Check script path resolution")
    parser.add_argument("--check-registry", help="Check repo in registry")
    parser.add_argument("--check-import", help="Check Python module import")
    args = parser.parse_args()
    
    if args.check_path:
        result = check_path_resolution(Path(args.check_path))
    elif args.check_registry:
        result = check_registry_drift(
            Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml"),
            args.check_registry
        )
    elif args.check_import:
        result = check_import_valid(Path(args.check_import))
    else:
        result = {"status": "ERROR", "reason": "No check specified"}
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "OK" else 1)


if __name__ == "__main__":
    main()