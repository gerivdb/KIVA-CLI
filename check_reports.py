from pathlib import Path
import json

output_dir = Path('D:/DO/WEB/TOOLS/reports/ecosystem-orchestration')
for f in output_dir.glob('**/*.json'):
    if 'latest' not in f.name and 'bdcp' not in f.name:
        print(f'{f.relative_to(output_dir)}: {f.stat().st_size} bytes')
        if f.stat().st_size > 100:
            data = json.loads(f.read_text())
            print('  Status: ' + str(data.get('status', 'N/A')))
            if 'steps' in data:
                print('  Steps: ' + str(list(data['steps'].keys())))
            elif 'warnings' in data:
                print('  Warnings: ' + str(len(data['warnings'])))