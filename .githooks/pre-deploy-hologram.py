#!/usr/bin/env python
# pre-deploy hologram v6 — KIVA-CLI hook
# IntentHash: 0xHOOK_HOLO_DEPLOY_20260911
# ERR_120 : deploy pre-validation hook for hologram API

import sys
import os

def main():
    """Run hologram CI validation before deploy."""
    os.chdir(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    ret = os.system(
        'powershell -File "D:\\DO\\WEB\\TOOLS\\L0-CANON\\GOVERNANCE-HUB\\scripts\\hologram-ci.ps1" -SkipAuth'
    )
    if ret != 0:
        print("[HOOK] hologram-ci validation FAILED — aborting deploy")
        sys.exit(1)
    print("[HOOK] hologram-ci validation PASSED — proceed with deploy")
    sys.exit(0)

if __name__ == "__main__":
    main()
