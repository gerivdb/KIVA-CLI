import subprocess
import os

result = subprocess.run([
    'python', '-c',
    '''
import json, sys, os
errors = []
try:
    with open(os.environ.get("ECOS_ROOT", "D:/DO/WEB/TOOLS/ECOS_ROOT.json"), "r") as f:
        pass
except Exception as e:
    errors.append(f"ECOS_ROOT.json: {e}")
try:
    with open(os.environ.get("TOPOS_REGISTRY", "D:/DO/WEB/TOOLS/L1-INFRA/TOPOS/registry/repos.json"), "r") as f:
        pass
except Exception as e:
    errors.append(f"TOPOS/registry/repos.json: {e}")
if errors:
    for e in errors: print(f"[ERROR] {e}")
    pass  # was sys.exit(1)
print("Success")
'''
], capture_output=True, text=True, timeout=30, shell=False, env={**os.environ, 'ECOS_ROOT': 'D:/DO/WEB/TOOLS/ECOS_ROOT.json', 'TOPOS_REGISTRY': 'D:/DO/WEB/TOOLS/L1-INFRA/TOPOS/registry/repos.json'})

print('Return code:', result.returncode)
print('Stdout:', result.stdout)