#!/usr/bin/env python3
"""
[ECOS-AUTO] WAL Entry Creator for KIVA-CLI Bootstrap

Creates global WAL entry documenting KIVA-CLI repository creation.
Integrates with global_wal_manager.py from ECOYSTEM.

Usage:
    python scripts/create_wal_entry.py
    
Requirements:
    - ECOYSTEM repo in sibling directory
    - global_wal_manager.py accessible
    - Write access to ecosystem-1/global_wal.db
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
import uuid

# Import from ECOYSTEM (assume accessible)
try:
    ecoystem_path = Path(__file__).parent.parent.parent / "ECOYSTEM" / "tools" / "core"
    from global_wal_manager import GlobalWALManager, CrossRepoEvent
except ImportError as e:
    print(f"❌ Cannot import global_wal_manager: {e}")
    print(f"   Expected path: {ecoystem_path}")
    sys.exit(1)

def generate_intent_hash(data: str) -> str:
    """Generate IntentHash¹¹ sha3-256"""
    return f"IntentHash¹¹:sha3-256:{hashlib.sha3_256(data.encode()).hexdigest()}"

def create_kiva_cli_bootstrap_entry():
    """Create WAL entry for KIVA-CLI repo creation"""
    
    # Initialize Global WAL Manager
    ecosystem_root = Path(__file__).parent.parent.parent  # Assume repos in same parent
    wal = GlobalWALManager(ecosystem_root)
    
    print(f"🔍 Ecosystem root: {ecosystem_root}")
    print(f"🔍 Global WAL DB: {wal.db_path}")
    
    # Prepare event metadata
    event_data = {
        "repo": "gerivdb/KIVA-CLI",
        "action": "repository_creation",
        "timestamp": "2026-02-28T06:02:00+01:00",
        "issues_created": 3,
        "ci_workflows": 6,
        "ecos_root_registered": True,
        "notion_sync": "PENDING",
        "github_issue_urls": [
            "https://github.com/gerivdb/KIVA-CLI/issues/1",
            "https://github.com/gerivdb/KIVA-CLI/issues/2",
            "https://github.com/gerivdb/KIVA-CLI/issues/3"
        ],
        "scripts_created": ["scripts/create_wal_entry.py"],
        "validation_status": "base-3:VALID"
    }
    
    # Generate IntentHash chain
    pre_hash = GlobalWALManager.GENESIS_HASH  # First event for KIVA-CLI
    post_data = json.dumps(event_data, sort_keys=True)
    post_hash = generate_intent_hash(post_data)
    
    print(f"\n🔗 IntentHash Chain:")
    print(f"   Pre:  {pre_hash}")
    print(f"   Post: {post_hash[:48]}...")
    
    # Create CrossRepoEvent
    event = CrossRepoEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        source_repos=["ECOYSTEM", "KIVA-CLI"],
        intent_hash_pre=pre_hash,
        intent_hash_post=post_hash,
        delta_phi=0.001,  # Minimal impact (repo registration)
        operation="repo_bootstrap",
        metadata=event_data,
        raft_index=0,
        raft_term=0
    )
    
    # Append to global WAL
    try:
        success = wal.append_cross_repo_event(event)
        if success:
            print(f"\n✅ [ECOS-AUTO] WAL Entry Created")
            print(f"   Event ID: {event.event_id}")
            print(f"   Operation: {event.operation}")
            print(f"   Δφ-CPS: +{event.delta_phi:.3f}")
            print(f"   Global WAL: {wal.db_path}")
            print(f"\n📊 Verification:")
            print(f"   cd {ecosystem_root}/ECOYSTEM")
            print(f"   python tools/core/global_wal_manager.py --root .. --list")
            return event
        else:
            print(f"❌ [ECOS-AUTO] WAL Entry Failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ [ECOS-AUTO] WAL Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("="*60)
    print("🚀 KIVA-CLI Bootstrap WAL Entry Creator")
    print("="*60)
    create_kiva_cli_bootstrap_entry()
    print("="*60)
