import os
os.environ["ECOS_ROOT"] = "D:/DO/WEB/TOOLS/ECOS_ROOT.json"
os.environ["TOPOS_REGISTRY"] = "D:/DO/WEB/TOOLS/L1-INFRA/TOPOS/registry/repos.json"
os.environ["KNOWN_REPOS"] = "D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml"
os.environ["OUTPUT_DIR"] = "D:/DO/WEB/TOOLS/reports/ecosystem-orchestration"

import json, sys
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
        sources["known_repos"] = yaml.safe_load(f)
except Exception as e:
    errors.append(f"known_repositories.yaml: {e}")

print(f"Errors: {errors}")
print(f"Sources keys: {list(sources.keys())}")

if errors:
    for e in errors: print(f"[ERROR] {e}")
    sys.exit(1)

repos = {}
if "ecos_root" in sources and "repos" in sources["ecos_root"]:
    repos["ecos_root"] = {r["name"] for r in sources["ecos_root"]["repos"]}

if "topos" in sources and "repos" in sources["topos"]:
    repos["topos"] = {r["full_name"].replace("gerivdb/", "") for r in sources["topos"]["repos"]}

if "known_repos" in sources and "repositories" in sources["known_repos"]:
    repos["known_repos"] = {r["name"] for r in sources["known_repos"]["repositories"]}

all_names = set()
for k, v in repos.items():
    all_names.update(v)

for name in sorted(all_names):
    present = {k: name in v for k, v in repos.items()}
    if not all(present.values()):
        missing = [k for k, v in present.items() if not v]
        warnings.append(f"[REGISTRY_DRIFT] Repo \"{name}\" absent de: {missing}")

if warnings:
    for w in warnings: print(w)
    print("[WARN] Drift detecte entre registres")
else:
    print(f"[OK] Registres coherents: {len(all_names)} repos synchronises")

output_dir = Path(os.environ.get("OUTPUT_DIR"))
output_dir.mkdir(parents=True, exist_ok=True)
report = {
    "step": "verify-registry-sync",
    "repos_per_source": {k: len(v) for k, v in repos.items()},
    "total_unique": len(all_names),
    "warnings": warnings,
    "timestamp": __import__("datetime").datetime.now().isoformat()
}
with open(output_dir / "step1_registry.json", "w") as f:
    json.dump(report, f, indent=2)
print("[OK] step1_registry.json created")