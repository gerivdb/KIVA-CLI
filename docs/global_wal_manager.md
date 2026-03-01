# Global WAL Manager - Complete Reference

## Overview

The **Global WAL (Write-Ahead Log) Manager** provides comprehensive cross-repository event tracking with IntentHash¹¹ chain validation and φ-CPS drift monitoring for the ECOS H0 ecosystem.

### Key Features

- ✅ **Cross-repo event persistence** - SQLite-based event storage
- ✅ **IntentHash¹¹ L0-L1-L2 chain** - Cryptographic event continuity
- ✅ **φ-CPS drift tracking** - Automatic threshold monitoring
- ✅ **Base-3 ternary validation** - UNKNOWN/VALID/INVALID semantic states
- ✅ **Automatic rollback detection** - Auto-trigger on drift > 5%
- ✅ **Complete audit trail** - JSON/CSV export capabilities
- ✅ **CLI integration** - Full command-line interface

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ECOS H0 Operations                   │
│  (ProjectManager, CLI, DaemonManager, etc.)             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ append_event()
                   ▼
┌─────────────────────────────────────────────────────────┐
│              Global WAL Manager                         │
│  ┌────────────────────────────────────────────┐        │
│  │  Event Processing                           │        │
│  │  - Generate IntentHash (SHA256)            │        │
│  │  - Validate parent chain (L0→L1→L2)        │        │
│  │  - Calculate φ-CPS delta                   │        │
│  │  - Check drift threshold (5%)              │        │
│  └────────────────────────────────────────────┘        │
│                   │                                      │
│                   ▼                                      │
│  ┌────────────────────────────────────────────┐        │
│  │  SQLite Database                            │        │
│  │  - wal_events table                        │        │
│  │  - rollback_points table                   │        │
│  │  - Indexes: timestamp, repo, intent_hash   │        │
│  └────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                   │
                   │ query_events() / export_audit()
                   ▼
┌─────────────────────────────────────────────────────────┐
│              Consumers                                   │
│  - CLI (ecos wal query)                                 │
│  - Audit reports (JSON/CSV)                             │
│  - Monitoring dashboards                                │
│  - Rollback orchestration                               │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

### wal_events Table

```sql
CREATE TABLE wal_events (
    event_id TEXT PRIMARY KEY,           -- Unique event ID (evt_<hex>)
    timestamp TEXT NOT NULL,             -- ISO 8601 UTC timestamp
    operation TEXT NOT NULL,             -- Operation type (e.g., SCAFFOLD_PROJECT)
    repo TEXT NOT NULL,                  -- Repository name (e.g., KIVA-CLI)
    intent_hash TEXT NOT NULL,           -- IntentHash¹¹ (0x<16-char HEX>)
    parent_intent_hash TEXT,             -- Parent IntentHash (for L1/L2)
    phi_cps_delta REAL NOT NULL,         -- φ-CPS delta (+/-)
    phi_cps_current REAL NOT NULL,       -- Cumulative φ-CPS
    validation_state TEXT NOT NULL,      -- UNKNOWN/VALID/INVALID
    status TEXT NOT NULL,                -- PENDING/SUCCESS/FAILED
    commit_sha TEXT,                     -- Git commit SHA (if applicable)
    metadata TEXT,                       -- JSON metadata
    error_message TEXT,                  -- Error details (if FAILED)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX idx_timestamp ON wal_events(timestamp);
CREATE INDEX idx_repo ON wal_events(repo);
CREATE INDEX idx_intent_hash ON wal_events(intent_hash);
CREATE INDEX idx_operation ON wal_events(operation);
```

### rollback_points Table

```sql
CREATE TABLE rollback_points (
    rollback_id TEXT PRIMARY KEY,        -- Unique rollback ID
    timestamp TEXT NOT NULL,             -- ISO 8601 UTC timestamp
    phi_cps_snapshot REAL NOT NULL,      -- φ-CPS snapshot at rollback
    event_count INTEGER NOT NULL,        -- Total events at rollback
    reason TEXT,                         -- Rollback reason
    metadata TEXT                        -- JSON metadata
);
```

## IntentHash¹¹ Specification

### Format

```
0x<16-character HEX>

Example: 0x9A4E7C2F1D8B3605
```

### Generation Algorithm

```python
import hashlib
from datetime import datetime

def generate_intent_hash(
    operation: str,
    repo: str,
    parent_hash: Optional[str] = None
) -> str:
    # Combine inputs
    data = f"{operation}|{repo}|{parent_hash or 'L0'}|{datetime.now().isoformat()}"
    
    # SHA256 hash
    hash_obj = hashlib.sha256(data.encode())
    
    # Take first 8 bytes (16 hex chars)
    intent_hash = "0x" + hash_obj.hexdigest()[:16].upper()
    
    return intent_hash
```

### Chain Levels

| Level | Description | Parent Hash |
|-------|-------------|-------------|
| **L0** | Genesis event (no parent) | `None` |
| **L1** | Child of L0 event | L0 IntentHash |
| **L2** | Child of L1 event | L1 IntentHash |
| **L2+** | Continued chain | Previous IntentHash |

### Chain Validation

```python
wal = GlobalWALManager()

# L0 event (genesis)
event1 = wal.append_event(
    operation="INIT_PROJECT",
    repo="KIVA-CLI",
    phi_cps_delta=0.018
)
# ✅ parent_intent_hash = None

# L1 event (child of L0)
event2 = wal.append_event(
    operation="ADD_TESTS",
    repo="KIVA-CLI",
    phi_cps_delta=0.012,
    parent_intent_hash=event1.intent_hash
)
# ✅ parent_intent_hash = event1.intent_hash

# Validate chain
is_valid, message = wal.validate_chain(
    intent_hash=event2.intent_hash,
    parent_intent_hash=event1.intent_hash
)
# ✅ is_valid = True
# ✅ message = "Chain validated: 0x9A4E... → 0x6B3D..."
```

## φ-CPS Drift Tracking

### Formula

```
φ_current = φ_baseline + Σ(φ_delta_i)

relative_drift = (φ_current - φ_baseline) / φ_baseline

threshold_exceeded = relative_drift > 0.05  # 5%
```

### Drift Thresholds

| Status | Relative Drift | Action |
|--------|----------------|--------|
| ✅ **Healthy** | < 3% | Normal operations |
| ⚠️ **Warning** | 3% - 5% | Monitor closely |
| 🛑 **Critical** | > 5% | Auto-rollback triggered |

### Drift Monitoring Example

```python
wal = GlobalWALManager()

# Check current drift
drift = wal.get_drift()

print(f"Baseline φ-CPS: {drift['baseline_phi']:.4f}")
print(f"Current φ-CPS: {drift['current_phi']:.4f}")
print(f"Drift: {drift['relative_drift']:.2%}")
print(f"Threshold exceeded: {drift['threshold_exceeded']}")

if drift['threshold_exceeded']:
    # Create rollback point
    rollback_id = wal.create_rollback_point(
        reason="AUTO_DRIFT_THRESHOLD_EXCEEDED",
        metadata=drift
    )
    print(f"Rollback point created: {rollback_id}")
```

## CLI Commands

### ecos wal append

Append new event to Global WAL.

```bash
# Basic usage
ecos wal append --operation SCAFFOLD_PROJECT \
                --repo KIVA-CLI \
                --phi-delta 0.018

# With commit SHA + parent hash
ecos wal append --operation DEPLOY_DOCKER \
                --repo my-api \
                --phi-delta 0.012 \
                --commit-sha abc123def456 \
                --parent-hash 0x9A4E7C2F1D8B3605

# With metadata
ecos wal append --operation TEST_RUN \
                --repo KIVA-CLI \
                --phi-delta 0.005 \
                --metadata '{"coverage": 85, "tests_passed": 120}'

# Failed event
ecos wal append --operation BUILD_FAILED \
                --repo my-api \
                --phi-delta 0.0 \
                --status FAILED \
                --validation INVALID
```

**Options:**
- `--operation, -o`: Operation type (required)
- `--repo, -r`: Repository name (required)
- `--phi-delta`: φ-CPS delta (required)
- `--commit-sha`: Git commit SHA
- `--parent-hash`: Parent IntentHash (for L1/L2)
- `--validation`: UNKNOWN | VALID | INVALID (default: VALID)
- `--status`: PENDING | SUCCESS | FAILED (default: SUCCESS)
- `--metadata`: JSON metadata string

### ecos wal query

Query WAL events with filters.

```bash
# All events (last 20)
ecos wal query

# By repository
ecos wal query --repo KIVA-CLI --limit 10

# By operation
ecos wal query --operation DEPLOY_DOCKER --hours 24

# By status
ecos wal query --status FAILED

# Combined filters
ecos wal query --repo my-api \
               --operation SCAFFOLD_PROJECT \
               --hours 48 \
               --limit 50
```

**Options:**
- `--repo, -r`: Filter by repository
- `--operation, -o`: Filter by operation type
- `--status`: Filter by PENDING | SUCCESS | FAILED
- `--hours`: Last N hours
- `--limit, -n`: Max results (default: 20)

### ecos wal drift

Check φ-CPS drift metrics.

```bash
ecos wal drift
```

**Output:**
```
📈 φ-CPS DRIFT METRICS
════════════════════════════════════════════════════════════

📊 BASELINE:
   φ-CPS baseline: 4.269
   Events since baseline: 15

📈 CURRENT:
   φ-CPS current: 4.319
   Absolute drift: +0.050
   Relative drift: 1.17%

🎯 THRESHOLD:
   Threshold: 5%
   Status: ✅ WITHIN LIMITS

✅ φ-CPS drift is healthy
```

### ecos wal chain

Verify IntentHash chain continuity.

```bash
# L0 event (no parent)
ecos wal chain 0x9A4E7C2F1D8B3605

# L1 event (with parent)
ecos wal chain 0x6B3D8A9E4F2C7105 \
              --parent 0x9A4E7C2F1D8B3605
```

**Output:**
```
🔗 INTENTHASH CHAIN VERIFICATION
────────────────────────────────────────────────────────────

✅ Chain validated: 0x9A4E7C2F1D8B3605 → 0x6B3D8A9E4F2C7105

📊 EVENT DETAILS:
   Operation: DEPLOY_DOCKER
   Repo: my-api
   φ-CPS: 4.281
   Validation: VALID

🔗 PARENT EVENT:
   Operation: SCAFFOLD_PROJECT
   φ-CPS: 4.269
```

### ecos wal rollback

Create rollback point (snapshot).

```bash
# Simple rollback
ecos wal rollback --reason "Before major deployment"

# With metadata
ecos wal rollback --reason drift_exceeded \
                  --metadata '{"auto_triggered": true, "drift": 0.057}'
```

**Output:**
```
🔄 Creating rollback point
────────────────────────────────────────────────────────────

✅ Rollback point created!

📊 ROLLBACK METADATA:
   🆔 Rollback ID: evt_a3f8e9c2d1b4567
   📈 φ-CPS snapshot: 4.319
   📝 Reason: Before major deployment

📈 Current drift: 1.17%
```

### ecos wal export

Export audit trail to file.

```bash
# JSON export (default)
ecos wal export audit.json

# CSV export
ecos wal export audit.csv --format csv
```

**JSON Output Structure:**
```json
{
  "export_timestamp": "2026-03-01T00:54:00Z",
  "total_events": 42,
  "drift_metrics": {
    "baseline_phi": 4.269,
    "current_phi": 4.319,
    "relative_drift": 0.0117,
    "threshold_exceeded": false
  },
  "events": [
    {
      "event_id": "evt_9a4e7c2f1d8b3605",
      "timestamp": "2026-03-01T00:45:00Z",
      "operation": "SCAFFOLD_PROJECT",
      "repo": "KIVA-CLI",
      "intent_hash": "0x9A4E7C2F1D8B3605",
      "phi_cps_delta": 0.018,
      "phi_cps_current": 4.269,
      "validation_state": "VALID",
      "status": "SUCCESS"
    }
  ]
}
```

## Integration Patterns

### Automatic Event Tracking (ProjectManager)

```python
from tools.core.project_manager import ProjectManager
from tools.core.global_wal_manager import get_global_wal

class EnhancedProjectManager(ProjectManager):
    def __init__(self):
        super().__init__()
        self.wal = get_global_wal()
    
    def scaffold(self, name: str, framework: str, **kwargs):
        # Execute operation
        result = super().scaffold(name, framework, **kwargs)
        
        # Append to WAL
        self.wal.append_event(
            operation=f"SCAFFOLD_{framework.upper()}",
            repo="KIVA-CLI",
            phi_cps_delta=0.018,
            metadata={
                "project_name": name,
                "framework": framework,
                "validation": result.get("validation")
            }
        )
        
        return result
```

### Batch Operations

```python
wal = get_global_wal()

# Store parent hash for chain
parent_hash = None

for project in projects:
    event = wal.append_event(
        operation="BATCH_SCAFFOLD",
        repo="KIVA-CLI",
        phi_cps_delta=0.015,
        parent_intent_hash=parent_hash,
        metadata={"project": project.name}
    )
    
    # Update parent for next event
    parent_hash = event.intent_hash
```

### Rollback Orchestration

```python
def safe_deploy_with_rollback():
    wal = get_global_wal()
    
    # Create rollback point before deploy
    rollback_id = wal.create_rollback_point(
        reason="PRE_DEPLOY_SNAPSHOT",
        metadata={"environment": "production"}
    )
    
    try:
        # Execute deployment
        result = deploy_project()
        
        # Log success
        wal.append_event(
            operation="DEPLOY_SUCCESS",
            repo="my-api",
            phi_cps_delta=0.025
        )
        
    except Exception as e:
        # Log failure
        wal.append_event(
            operation="DEPLOY_FAILED",
            repo="my-api",
            phi_cps_delta=0.0,
            status=EventStatus.FAILED,
            error_message=str(e)
        )
        
        # Trigger rollback
        print(f"Rollback to: {rollback_id}")
        raise
```

## Best Practices

### 1. Consistent Operation Naming

Use consistent, descriptive operation names:

```python
# ✅ Good
SCAFFOLD_PROJECT, DEPLOY_DOCKER, RUN_TESTS, UPDATE_CONFIG

# ❌ Bad
scaffold, deploy, test, update
```

### 2. Meaningful φ-CPS Deltas

Assign φ-CPS deltas based on operation complexity:

| Operation Type | Suggested Delta | Reasoning |
|----------------|-----------------|----------|
| Scaffold project | +0.015 - +0.025 | Medium complexity |
| Deploy to Docker | +0.010 - +0.020 | Medium complexity |
| Run tests | +0.005 - +0.010 | Low complexity |
| Update config | +0.003 - +0.007 | Low complexity |
| Major refactor | +0.030 - +0.050 | High complexity |

### 3. Chain Continuity

Always maintain IntentHash chain for related operations:

```python
# ✅ Good - Continuous chain
event1 = wal.append_event(operation="INIT", ...)
event2 = wal.append_event(operation="BUILD", parent_intent_hash=event1.intent_hash)
event3 = wal.append_event(operation="TEST", parent_intent_hash=event2.intent_hash)

# ❌ Bad - Broken chain
event1 = wal.append_event(operation="INIT", ...)
event2 = wal.append_event(operation="BUILD", ...)  # No parent!
event3 = wal.append_event(operation="TEST", ...)   # No parent!
```

### 4. Proactive Rollback Points

Create rollback points before risky operations:

```python
# Before major deployment
wal.create_rollback_point(reason="PRE_DEPLOY_PROD")

# Before schema migration
wal.create_rollback_point(reason="PRE_DB_MIGRATION")

# Before bulk operations
wal.create_rollback_point(reason="PRE_BATCH_PROCESS")
```

### 5. Regular Audits

Export audit trails regularly:

```bash
# Daily export
ecos wal export audits/$(date +%Y-%m-%d)-audit.json

# Weekly CSV export
ecos wal export audits/$(date +%Y-W%V)-audit.csv --format csv
```

## Troubleshooting

### Drift Threshold Exceeded

**Symptom:** `⚠️ φ-CPS DRIFT THRESHOLD EXCEEDED!`

**Actions:**
1. Review recent operations:
   ```bash
   ecos wal query --limit 20
   ```

2. Create rollback point:
   ```bash
   ecos wal rollback --reason drift_exceeded
   ```

3. Analyze drift:
   ```bash
   ecos wal drift
   ```

4. If necessary, prepare baseline reset:
   ```bash
   ecos phi prepare-reset  # (If command available)
   ```

### Broken IntentHash Chain

**Symptom:** `❌ Parent IntentHash not found`

**Actions:**
1. Query events to find valid parent:
   ```bash
   ecos wal query --limit 100
   ```

2. Verify chain manually:
   ```bash
   ecos wal chain <intent_hash> --parent <parent_hash>
   ```

3. If chain is broken, start new L0 event:
   ```python
   # New L0 (genesis) event
   wal.append_event(
       operation="CHAIN_RESTART",
       repo="KIVA-CLI",
       phi_cps_delta=0.0,
       parent_intent_hash=None  # L0 event
   )
   ```

### Database Locked

**Symptom:** `sqlite3.OperationalError: database is locked`

**Actions:**
1. Check for concurrent WAL operations
2. Ensure proper connection closing
3. If persistent, backup and recreate:
   ```bash
   # Backup
   cp ~/.kiva/global_wal.db ~/.kiva/global_wal.db.backup
   
   # Export to JSON
   ecos wal export wal_backup.json
   
   # Remove and recreate (will auto-initialize)
   rm ~/.kiva/global_wal.db
   ```

## FAQ

**Q: What happens if I lose the WAL database?**

A: The WAL database is local and can be recreated. However, you'll lose historical event tracking. Regular exports to JSON/CSV provide backup.

**Q: Can I have multiple WAL databases?**

A: Yes, specify custom `db_path` when initializing:
```python
wal = GlobalWALManager(db_path=Path("/custom/path/wal.db"))
```

**Q: How do I reset φ-CPS baseline?**

A: Create a rollback point. Future drift calculations will use this as the new baseline:
```bash
ecos wal rollback --reason "NEW_BASELINE"
```

**Q: What's the difference between L0, L1, L2 events?**

A:
- **L0**: Genesis event (no parent) - Start of a new chain
- **L1**: Direct child of L0 - First operation after genesis
- **L2+**: Continued chain - Subsequent operations

**Q: Can I query events across multiple repos?**

A: Yes, omit `--repo` filter:
```bash
ecos wal query --operation DEPLOY_DOCKER --limit 50
```

## See Also

- [ProjectManager CLI](./project_manager_cli.md)
- [ECOS_ROOT.json Specification](../ECOS_ROOT.json)
- [φ-CPS Tracking Guide](./phi_cps_tracking.md) (if available)
- [IntentHash Specification](./intent_hash_spec.md) (if available)
