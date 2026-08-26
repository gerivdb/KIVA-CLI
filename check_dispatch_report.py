from pathlib import Path
import json

output_dir = Path('D:/DO/WEB/TOOLS/reports/ecosystem-orchestration')
date_dir = output_dir / '2026-07-29'
if date_dir.exists():
    for f in date_dir.glob('*.json'):
        print(f'{f.name}: {f.stat().st_size} bytes')
        data = json.loads(f.read_text())
        if 'step' in data and data['step'] == 'verify-dispatch-tables':
            print('  ctulu_registry_count:', data.get('ctulu_registry_count'))
            print('  trix_commands_count:', data.get('trix_commands_count'))
            print('  piano_model_count:', data.get('piano_model_count'))
            print('  warnings:', data.get('warnings'))