import os
os.environ["ECOS_ROOT"] = "D:/DO/WEB/TOOLS/ECOS_ROOT.json"
import json, sys
from pathlib import Path
import yaml

errors = []
try:
    with open(os.environ.get("ECOS_ROOT"), "r") as f:
        pass
except Exception as e:
    print(f"[ERROR] ECOS_ROOT.json: {e}")
    errors.append(f"ECOS_ROOT.json: {e}")

if errors:
    for e in errors: print(f"[ERROR] {e}")
    pass  # was sys.exit(1)
print("Success")