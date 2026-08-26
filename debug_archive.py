from pathlib import Path
import shutil
from datetime import datetime

src = Path('D:/DO/WEB/TOOLS/reports/ecosystem-orchestration')
dest = src / datetime.now().strftime('%Y-%m-%d')
dest.mkdir(parents=True, exist_ok=True)

print(f"Source: {src}")
print(f"Dest: {dest}")

moved = 0
latest_name = None
for f in src.glob('*.json'):
    print(f'Checking: {f.name}')
    if not f.name.endswith('-latest.json'):
        print(f'  -> Moving {f.name}')
        shutil.move(str(f), dest / f.name)
        moved += 1
        latest_name = f.name

print(f'Moved: {moved} files to {dest}')
print(f'Latest name: {latest_name}')

# Clean up old symlink
latest = src / 'ecosystem_orchestration-latest.json'
if latest.exists() or latest.is_symlink():
    latest.unlink()
    print('Unlinked old symlink')

# Create new symlink
if latest_name:
    target = dest.name / latest_name
    print(f'Creating symlink to: {target}')
    latest.symlink_to(target)
    print(f'New symlink target: {latest.readlink()}')
    print(f'Target absolute: {(src / target).resolve()}')
    print(f'Target exists: {(src / target).exists()}')