from pathlib import Path

paths = {
    'ECOS_ROOT': 'D:/DO/WEB/TOOLS/ECOS_ROOT.json',
    'TOPOS_REGISTRY': 'D:/DO/WEB/TOOLS/L1-INFRA/TOPOS/registry/repos.json',
    'KNOWN_REPOS': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml',
    'BRIDGES_YAML': 'D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/BRIDGES.yaml',
}

for name, path in paths.items():
    p = Path(path)
    exists = p.exists()
    print(name + ': ' + path + ' -> ' + ('EXISTS' if exists else 'MISSING'))