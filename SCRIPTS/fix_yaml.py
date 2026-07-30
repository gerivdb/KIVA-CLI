import re

filepath = r'D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB\known_repositories.yaml'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: in role: lines, escape single quotes by doubling them
lines = content.split('\n')
fixed = []
for line in lines:
    if 'role:' in line and "'" in line:
        # Pattern: role: 'value with apostrophe'
        match = re.match(r'^(\s*role:\s*)\'(.*)\'(\s*)$', line)
        if match:
            prefix = match.group(1)
            value = match.group(2)
            suffix = match.group(3)
            # Double apostrophes in value
            value_fixed = value.replace("'", "''")
            line = f"{prefix}'{value_fixed}'{suffix}"
    fixed.append(line)

result = '\n'.join(fixed)
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(result)

print('Fixed role quotes')
