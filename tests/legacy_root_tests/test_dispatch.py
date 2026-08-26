import os, re, sys
from pathlib import Path

# CTULU
sys.path.insert(0, 'D:/DO/WEB/TOOLS/L4-TOOLS/CTULU/pipelines/plix-ternary-router')
from plix_ternary_router import TernaryRouter, TernarySignal, SignalType, TRIT_ADVANCE, TRIT_NEUTRAL

router = TernaryRouter(Path('D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml'))
ctulu_count = len(router.registry)

test_signal = TernarySignal(
    source=SignalType.IRIS,
    vector=[TRIT_ADVANCE, TRIT_ADVANCE, TRIT_NEUTRAL, TRIT_ADVANCE, TRIT_NEUTRAL],
    confidence=[0.8, 0.7, 0.5, 0.6, 0.4],
    metadata={'target_type': 'auto', 'source_name': 'VERIFICATION'}
)
result = router.project(test_signal)

print(f'CTULU registry: {ctulu_count}')
print(f'CTULU projected: {result.projected_index} ({result.symbol})')
print(f'CTULU targets: {len(result.target_repos)}')

# TRIX
dispatch_file = Path('D:/DO/WEB/TOOLS/L4-TOOLS/TRIX/src/dispatch.zig')
content = dispatch_file.read_text()
start = content.find('const map = .{')
if start != -1:
    brace_count = 0
    map_content = ''
    for i, c in enumerate(content[start:]):
        if c == '{': brace_count += 1
        elif c == '}':
            brace_count -= 1
            if brace_count == 0:
                map_content = content[start:start+i+1]
                break
    commands = re.findall(r'\{\s*"([^"]+)",\s*\.(\w+)', map_content)
    real_commands = [cmd for cmd in commands if not cmd[1].startswith('EPIC-') and cmd[1] != '/']
    trix_count = len(real_commands)
    print(f'TRIX commands: {trix_count}')
    print(f'Sample: {sorted([c[0] for c in real_commands])[:10]}')

# Piano
if 'PianoState' in content and 'to_dispatch_index' in content:
    print(f'Piano: 243 entries (3^5)')