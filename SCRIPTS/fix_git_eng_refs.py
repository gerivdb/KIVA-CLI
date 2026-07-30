# fix_git_eng_refs.py - Mettre à jour les références ADR-GIT-ENG-001 → ADR-007
import os

base = r"D:\DO\WEB\TOOLS\L4-TOOLS\REPO-STANDARDS\git-engineering"

for fname in os.listdir(base):
    if not fname.endswith(".md"):
        continue
    fpath = os.path.join(base, fname)
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "ADR-GIT-ENG-001" in content:
        content = content.replace("ADR-GIT-ENG-001", "ADR-007")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[FIX] {fname}")

print("[DONE]")
