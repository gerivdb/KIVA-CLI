import json
from pathlib import Path

output_dir = Path('D:/DO/WEB/TOOLS/reports/ecosystem-orchestration')
symlink = output_dir / 'ecosystem_orchestration-latest.json'

if symlink.is_symlink():
    target = symlink.readlink()
    print('Symlink target:', target)
    print('Target absolute:', target.absolute())
    print('Target exists:', target.exists())
    if target.exists():
        data = json.loads(target.read_text())
        print('Report keys:', list(data.keys()))
        if 'steps' in data:
            steps_list = list(data['steps'].keys())
            print('Steps:', steps_list)
            for step_name, step_data in data['steps'].items():
                if 'dispatch' in step_name:
                    print('Dispatch step found!')
                    for k, v in step_data.items():
                        print(f'  {k}: {v}')