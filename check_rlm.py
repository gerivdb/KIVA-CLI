import yaml
from pathlib import Path

impl = yaml.safe_load(Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\KG-L\kilocode\guards\design_enforcement\design_implementations.yaml").read_text(encoding="utf-8"))
designs = impl.get("designs", {})

for d in ["rlm243", "rlm-243"]:
    if d in designs:
        info = designs[d]
        print(f"{d}: implemented={info.get('implemented')}")

# Check files
from pathlib import Path
enforcement_dir = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\KG-L\kilocode\guards\design_enforcement")
for d in ["rlm243", "rlm-243"]:
    f = enforcement_dir / f"{d}.py"
    print(f"{d}.py exists: {f.exists()}")