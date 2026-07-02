#!/usr/bin/env python3
"""
Register BDCP-CORE as a citizen in KIVA ecosystem.
Manual registration script - creates citizen entry for BDCP-CORE.
"""

from pathlib import Path
from datetime import datetime

def register_bdcp_core():
    """Generate citizen registration JSON for BDCP-CORE."""
    citizen_entry = {
        "citizen_id": "ctz_bdcp_core_001",
        "intent_hash": "0xBDCP_CITIZEN_REG_20260702",
        "name": "BDCP-CORE",
        "entity_type": "LIBRARY",
        "repo": "gerivdb/BDCP-CORE",
        "local_path": "D:\\DO\\WEB\\TOOLS\\L2-PLATFORM\\BDCP-CORE",
        "layer": ["N1", "N3"],
        "stratum": "L2-PLATFORM",
        "phi_cps": 0.03,  # Base level (L2)
        "created_at": datetime.utcnow().isoformat(),
    }
    
    output = Path("D:/DO/WEB/TOOLS/L2-PLATFORM/BDCP-CORE/citizen_registration.json")
    import json
    output.write_text(json.dumps(citizen_entry, indent=2))
    
    print(f"Citizen registration created: {output}")
    print(f"citizen_id: {citizen_entry['citizen_id']}")

if __name__ == "__main__":
    register_bdcp_core()