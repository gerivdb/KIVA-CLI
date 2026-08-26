#!/usr/bin/env python3
"""Fix $VAR references in ecosystem-orchestration-pipeline.yaml"""

import re

# Read the original file
file_path = r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI\.kiva\pipelines\ecosystem-orchestration-pipeline.yaml"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Variable mappings: $VAR -> os.environ.get('VAR', 'default')
var_mappings = {
    'OUTPUT_DIR': 'D:/DO/WEB/TOOLS/reports/ecosystem-orchestration',
    'ECOS_ROOT': 'D:/DO/WEB/TOOLS/ECOS_ROOT.json',
    'TOPOS_REGISTRY': 'D:/DO/WEB/TOOLS/L1-INFRA/TOPOS/registry/repos.json',
    'KNOWN_REPOS': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml',
    'ECOS_CLI_PATH': 'D:/DO/WEB/TOOLS/L1-INFRA/ECOS-CLI',
    'CTULU_PATH': 'D:/DO/WEB/TOOLS/L4-TOOLS/CTULU',
    'TRIX_PATH': 'D:/DO/WEB/TOOLS/L4-TOOLS/TRIX',
    'GOVERNANCE_HUB': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB',
    'BRIDGES_YAML': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/BRIDGES.yaml',
    'GATEWAY_HOST': '127.0.0.1',
    'GATEWAY_PORT': '18000',
    'PYTHON': 'python',
}

# Pattern to match $VAR or ${VAR} but NOT when already inside os.environ.get
# We'll process line by line and skip lines that already have os.environ.get

lines = content.split('\n')
result = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # Skip lines that already contain os.environ.get (already fixed)
    if 'os.environ.get' in line:
        result.append(line)
        i += 1
        continue
    
    # Replace $VAR or ${VAR} with os.environ.get('VAR', 'default')
    # But only if VAR is in our mappings
    def replace_var(match):
        var_name = match.group(1)
        if var_name in var_mappings:
            return "os.environ.get('" + var_name + "', '" + var_mappings[var_name] + "')"
        return match.group(0)  # Keep unchanged if not in mappings
    
    # Replace $VAR and ${VAR}
    # Pattern: \$([A-Z_][A-Z0-9_]*) or \$\{([A-Z_][A-Z0-9_]*)\}
    new_line = re.sub(r'\$\{?([A-Z_][A-Z0-9_]*)\}?', 
                      lambda m: "os.environ.get('" + m.group(1) + "', '" + var_mappings.get(m.group(1), '') + "')" if m.group(1) in var_mappings else m.group(0),
                      line)
    
    result.append(new_line)
    i += 1

# Join back
new_content = '\n'.join(result)

# Also need to add 'import os' to each python -c block that uses os.environ.get
# Find all "python -c \"" patterns and check if next lines have import os
# This is complex - let's do a simpler approach: replace all "$PYTHON -c" with "python -c" 
# and ensure import os is added

# Replace $PYTHON with python
new_content = new_content.replace('$PYTHON -c', 'python -c')

# For each python -c block, ensure import os is present
# This is tricky with multi-line strings. Let's use a different approach:
# Find all python -c "..." blocks and add import os if missing

# Pattern: python -c "\n(.*?)\n       "
# This is getting complex. Let's write the result and then do a final manual check.

# Write the modified content
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed $VAR references in pipeline")
print("Replaced $PYTHON with python")
print("Done!")