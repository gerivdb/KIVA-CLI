#!/usr/bin/env python3
"""
Validate meta-design.yaml against JSON Schema.
Usage: python scripts/validate_meta_design.py --schema schemas/meta-design.schema.json meta-design.yaml
"""
import sys
import json
import yaml
import argparse
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("[ERR] jsonschema non installé. Installez avec: pip install jsonschema pyyaml")
    sys.exit(1)


def load_yaml(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate(meta_path: Path, schema_path: Path) -> bool:
    try:
        meta = load_yaml(meta_path)
        schema = load_json(schema_path)
        jsonschema.validate(meta, schema)
        print(f"[OK] {meta_path} validé contre {schema_path}")
        return True
    except jsonschema.ValidationError as e:
        print(f"[ERR] Validation échouée: {e.message}")
        print(f"      Chemin: {' -> '.join(str(p) for p in e.path)}")
        return False
    except Exception as e:
        print(f"[ERR] Erreur: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Valider meta-design.yaml contre JSON Schema")
    parser.add_argument("--schema", required=True, help="Chemin vers le schéma JSON")
    parser.add_argument("file", help="Fichier meta-design.yaml à valider")
    args = parser.parse_args()

    meta_path = Path(args.file)
    schema_path = Path(args.schema)

    if not meta_path.exists():
        print(f"[ERR] Fichier introuvable: {meta_path}")
        return 1
    if not schema_path.exists():
        print(f"[ERR] Schéma introuvable: {schema_path}")
        return 1

    ok = validate(meta_path, schema_path)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())