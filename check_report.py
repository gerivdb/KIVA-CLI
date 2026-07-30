import json
from pathlib import Path

output_dir = Path('D:/DO/WEB/TOOLS/reports/ecosystem-orchestration')
date_dir = output_dir / '2026-07-29'

if date_dir.exists():
    for f in date_dir.glob('*.json'):
        print(f'{f.name}: {f.stat().st_size} bytes')
        if 'ecosystem' in f.name:
            data = json.loads(f.read_text())
            status = data.get('status')
            print(f'  status: {status}')
            if 'steps' in data:
                for step_name, step_data in data['steps'].items():
                    print(f'  step: {step_name}')
                    if 'dispatch' in step_name:
                        for k, v in step_data.items():
                            print(f'    {k}: {v}')