from pathlib import Path
import json

src = Path('D:/DO/WEB/TOOLS/reports/ecosystem-orchestration')
for f in src.glob('*.json'):
    print(f'  {f.name}: {f.stat().st_size} bytes')
    if 'step' in f.name:
        data = json.loads(f.read_text())
        print(f'    step: {data.get("step")}, warnings: {data.get("warnings")}')