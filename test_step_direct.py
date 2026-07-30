import os
import subprocess

result = subprocess.run([
    'python', '-c',
    '''
import os
import json
import sys
from pathlib import Path
import yaml

output_dir = Path(os.environ.get("OUTPUT_DIR"))
output_dir.mkdir(parents=True, exist_ok=True)

errors = []
warnings = []

sources = {}
try:
    with open(os.environ.get("ECOS_ROOT"), "r") as f:
        sources["ecos_root"] = json.load(f)
except Exception as e:
    errors.append(f"ECOS_ROOT.json: {e}")

try:
    with open(os.environ.get("TOPOS_REGISTRY"), "r") as f:
        sources["topos"] = json.load(f)
except Exception as e:
    errors.append(f"TOPOS/registry/repos.json: {e}")

try:
    with open(os.environ.get("KNOWN_REPOS"), "r") as f:
        sources["known_repos"] = __import__("yaml").safe_load(f)
except Exception as e:
    errors.append(f"known_repositories.yaml: {e}")

if errors:
    for e in errors: print(f"[ERROR] {e}")
    sys.exit(1)

print("All sources loaded successfully")
'''
], capture_output=True, text=True, timeout=30, env={**os.environ, "OUTPUT_DIR": "D:/DO/WEB/TOOLS/reports/ecosystem-orchestration", "ECOS_ROOT": "D:/DO/WEB/TOOLS/ECOS_ROOT.json", "TOPOS_REGISTRY": "D:/DO/WEB/TOOLS/L1-INFRA/TOPOS/registry/repos.json", "KNOWN_REPOS": "D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml"})

print('Return code:', result.returncode)
print('Stdout:', result.stdout)
print('Stderr:', result.stderr)