from pathlib import Path
import json

src = Path('.')
for f in src.glob('step*.json'):
    print(f'  {f.name}: {f.stat().st_size} bytes')
    data = json.loads(f.read_text())
    print(f'    step: {data.get("step")}, warnings: {data.get("warnings")}')