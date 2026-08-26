from pathlib import Path

output_dir = Path('D:/DO/WEB/TOOLS/reports/ecosystem-orchestration')
print('Dir exists:', output_dir.exists())
for item in output_dir.iterdir():
    if item.is_symlink():
        print(f'  {item.name}: symlink -> {item.readlink()}')
    elif item.is_dir():
        print(f'  {item.name}: dir')
        for f in item.glob('*.json'):
            print(f'    {f.name}')
    elif item.is_file():
        print(f'  {item.name}: file ({item.suffix})')