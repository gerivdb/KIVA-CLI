import yaml
import os
from pathlib import Path

impl = yaml.safe_load(Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\KG-L\kilocode\guards\design_enforcement\design_implementations.yaml").read_text(encoding="utf-8"))
designs = impl.get("designs", {})
enforcement_dir = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\KG-L\kilocode\guards\design_enforcement")

missing = []
for d, info in designs.items():
    if info.get("implemented"):
        # Convert design ID to valid filename
        filename = d.replace("/", "-").replace(".", "-") + ".py"
        filepath = enforcement_dir / filename
        if not filepath.exists():
            # Also check exact match
            exact = enforcement_dir / f"{d}.py"
            if not exact.exists():
                print(f"MISSING: {d} -> looked for {filename} and {d}.py")

print("Done")