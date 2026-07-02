#!/usr/bin/env python3
"""
Register BDCP-CORE as a citizen in KIVA ecosystem.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from tools.core.citizen_manager import CitizenManager, EntityLevel, EntityValidationState, EntityLifecycle, EntityType

def register_bdcp_core():
    manager = CitizenManager()
    
    citizen = manager.register_entity(
        name="BDCP-CORE",
        entity_type=EntityType.LIBRARY,
        repo="gerivdb/BDCP-CORE",
        local_path="D:\\DO\\WEB\\TOOLS\\L2-PLATFORM\\BDCP-CORE",
        layer=["N1", "N3"],
        stratum="L2-PLATFORM",
    )
    
    print(f"Citizen registered: {citizen.citizen_id}")
    print(f"IntentHash: {citizen.intent_hash}")
    return citizen.citizen_id

if __name__ == "__main__":
    register_bdcp_core()