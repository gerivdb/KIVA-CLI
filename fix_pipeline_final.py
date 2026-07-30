#!/usr/bin/env python3
"""Fix $VAR references in ecosystem-orchestration-pipeline.yaml correctly"""

import re

file_path = r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI\.kiva\pipelines\ecosystem-orchestration-pipeline.yaml"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define all environment variable defaults
var_defaults = {
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
}

# Process the content line by line to preserve YAML structure
lines = content.split('\n')
result = []
in_python_block = False
block_indent = 0

for line in lines:
    # Check if we're entering a python -c block
    if re.search(r'^\s*(?:python|PYTHON)\s+-c\s+"', line) or re.search(r'^\s*\$PYTHON\s+-c\s+"', line):
        # Replace $PYTHON with python at the start of command
        line = re.sub(r'^\s*\$PYTHON\s+-c\s+', '        python -c ', line)
        # If line has just the opening quote, track that we're in a python block
        if line.rstrip().endswith('"'):
            in_python_block = True
        else:
            in_python_block = True
    
    elif in_python_block:
        # Inside python block - replace $VAR with os.environ.get('VAR', 'default')
        # But be careful with f-string variables like {GATEWAY_HOST}
        def replace_var(match):
            var_name = match.group(1)
            if var_name in ['OUTPUT_DIR', 'ECOS_ROOT', 'TOPOS_REGISTRY', 'KNOWN_REPOS', 
                           'ECOS_CLI_PATH', 'CTULU_PATH', 'TRIX_PATH', 'GOVERNANCE_HUB',
                           'BRIDGES_YAML', 'GATEWAY_HOST', 'GATEWAY_PORT']:
                return "os.environ.get('" + match.group(1) + "', '" + var_defaults.get(match.group(1), '') + "')"
            return match.group(0)
        
        # Replace $VAR and ${VAR} patterns
        new_line = re.sub(r'\$\{?([A-Z_][A-Z0-9_]*)\}?', 
                          lambda m: "os.environ.get('" + m.group(1) + "', '" + var_defaults.get(m.group(1), '') + "')" 
                          if m.group(1) in ['OUTPUT_DIR', 'ECOS_ROOT', 'TOPOS_REGISTRY', 'KNOWN_REPOS', 
                                           'ECOS_CLI_PATH', 'CTULU_PATH', 'TRIX_PATH', 'GOVERNANCE_HUB',
                                           'BRIDGES_YAML', 'GATEWAY_HOST', 'GATEWAY_PORT', 'PYTHON'] 
                          else m.group(0), 
                          line)
        
        # Also fix Path() calls that have the os.environ.get inside quotes
        # Path('os.environ.get(...') -> Path(os.environ.get(...))
        line = re.sub(r"Path\('os\.environ\.get\([^)]+\)", 
                      lambda m: m.group(0).replace("Path('os.environ.get", "Path(os.environ.get").replace("')", ')'), 
                      line)
        
        # Check if python block ends
        if line.strip().endswith('"') and not line.strip().startswith('#'):
            # Check if this is the closing quote of the python -c block
            if not line.strip().startswith(' ') or line.strip() == '"':
                # This might be the end, but need to be careful
                pass
    
    result.append(line)

# Also fix the $PYTHON at the start of commands
content = '\n'.join(result)

# Replace $PYTHON -c with python -c at command start
content = re.sub(r'^\s*\$PYTHON\s+-c\s+', '        python -c ', content, flags=re.MULTILINE)

# Fix any remaining $PYTHON references
content = content.replace('$PYTHON', 'python')

# Replace $GATEWAY_HOST and $GATEWAY_PORT in f-strings with os.environ.get
# These appear in f-strings like f'http://{GATEWAY_HOST}:{GATEWAY_PORT}/...'
# They should become f'http://{os.environ.get(\"GATEWAY_HOST\", \"127.0.0.1\")}:{os.environ.get(\"GATEWAY_PORT\", \"18000\")}/...'

# This is complex - let's do a more targeted approach
# For now, just write the result and we'll test

# Also need to fix the Path() calls that have os.environ.get inside quotes
# Path('os.environ.get(...)') -> Path(os.environ.get(...))

# Write the modified content
with open(r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI\.kiva\pipelines\ecosystem-orchestration-pipeline.yaml", 'w', encoding='utf-8') as f:
    f.write('\n'.join(content.split('\n')))

print("Fixed $VAR references")
print("Done!")