import subprocess, json
result = subprocess.run(['gh', 'api', 'repos/gerivdb/KIVA-CLI/actions/workflows'], capture_output=True, text=True)
data = json.loads(result.stdout)
for w in data['workflows']:
    if 'ecosystem' in w['name'].lower():
        print(f"ID: {w['id']}, Name: {w['name']}, State: {w['state']}")