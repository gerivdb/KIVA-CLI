#!/usr/bin/env python3
"""
Fix environment variable references in ecosystem-orchestration-pipeline.yaml
Replace shell $VAR syntax with Python os.environ.get('VAR', 'default')
"""

import re
from pathlib import Path

file_path = Path("D:/DO/WEB/TOOLS/L1-INFRA/KIVA-CLI/.kiva/pipelines/ecosystem-orchestration-pipeline.yaml")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define variable mappings with defaults
var_mappings = {
    'OUTPUT_DIR': 'D:/DO/WEB/TOOLS/reports/ecosystem-orchestration',
    'ECOS_ROOT': 'D:/DO/WEB/TOOLS/ECOS_ROOT.json',
    'TOPOS_REGISTRY': 'D:/DO/WEB/TOOLS/L1-INFRA/TOPOS/registry/repos.json',
    'KNOWN_REPOS': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml',
    'BRIDGES_YAML': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/BRIDGES.yaml',
    'CTULU_PATH': 'D:/DO/WEB/TOOLS/L4-TOOLS/CTULU',
    'TRIX_PATH': 'D:/DO/WEB/TOOLS/L4-TOOLS/TRIX',
    'ECOS_CLI_PATH': 'D:/DO/WEB/TOOLS/L1-INFRA/ECOS-CLI',
    'GOVERNANCE_HUB': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB',
    'GATEWAY_HOST': '127.0.0.1',
    'GATEWAY_PORT': '18000',
}

# For each variable, replace $VAR or ${VAR} with os.environ.get('VAR', 'default')
for var_name, default_val in var_mappings.items():
    # Pattern to match $VAR or ${VAR} in Python string context
    pattern = r'\$\{?' + re.escape(var_name) + r'\}?'
    replacement = "os.environ.get('" + var_name + "', '" + default_val + "')"
    content = re.sub(pattern, replacement, content)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed environment variable references in ecosystem-orchestration-pipeline.yaml")
print("Done!")