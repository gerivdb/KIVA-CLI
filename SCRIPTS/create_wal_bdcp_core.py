#!/usr/bin/env python3
"""
Create WAL entry for BDCP-CORE creation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from tools.core.global_wal_manager import GlobalWALManager, EventType, Severity

def create_wal_entry():
    manager = GlobalWALManager()
    
    event_id = manager.append_event(
        event_type=EventType.COMPONENT_IMPLEMENTATION,
        ecosystem_id="ECOSYSTEM-1",
        repositories=["BDCP-CORE"],
        phi_cps_baseline=3.697,
        phi_cps_current=3.697,
        parent_intent_hash=None,
        severity=Severity.INFO,
        description="Creation of BDCP-CORE package for zero-trust traffic enforcement",
    )
    
    manager.add_operation(
        event_id=event_id,
        operation_type="CREATE_REPO",
        repository="BDCP-CORE",
        status=manager.ValidationState.SUCCESS,
        path="D:\\DO\\WEB\\TOOLS\\L2-PLATFORM\\BDCP-CORE",
        commit_sha="b30147d",  # Last commit SHA
        duration_ms=15000,
    )
    
    print(f"✅ WAL entry created: {event_id}")

if __name__ == "__main__":
    create_wal_entry()