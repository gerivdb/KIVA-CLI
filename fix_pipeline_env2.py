#!/usr/bin/env python3
"""
Fix all $VAR references in ecosystem-orchestration-pipeline.yaml
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
    'PYTHON': 'python',
}

# First, replace $PYTHON with python (simple string replace)
content = content.replace('$PYTHON', 'python')

# For each variable, replace $VAR with os.environ.get('VAR', 'default')
# We need to be careful not to replace inside os.environ.get() calls
# Strategy: process line by line, but handle multi-line strings

def replace_var_in_content(text):
    """Replace $VAR with os.environ.get('VAR', 'default') but not inside os.environ.get()"""
    result = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if line contains os.environ.get( - if so, skip replacement on this line
        if 'os.environ.get' in line:
            result.append(line)
            i += 1
            continue
        
        # Replace $VAR or ${VAR} with os.environ.get('VAR', 'default')
        def replace_match(match):
            full = match.group(0)
            var_name = match.group(1)
            if var_name in var_mappings:
                return "os.environ.get('" + var_name + "', '" + var_mappings[var_name] + "')"
            return full
        
        # Pattern: $VAR or ${VAR} but not inside os.environ.get
        # We already skipped lines with os.environ.get
        line = re.sub(r'\$\{?([A-Z_][A-Z0-9_]*)\}?', replace_match, line)
        result.append(line)
        i += 1
    
    return '\n'.join(result)

# Apply replacement
content = replace_var_in_content(content)

# Also fix the first step which I already manually edited - ensure it has proper imports
# Check if os import is missing in the first step
if 'import os' not in content[:5000]:
    # Add import os after the first "python -c \"" that doesn't already have it
    pass  # The first step already has import os from my earlier edit

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all $VAR references in ecosystem-orchestration-pipeline.yaml")
print("Done!")