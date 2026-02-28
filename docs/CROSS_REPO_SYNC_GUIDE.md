# Cross-Repo Sync Guide

**Version**: 1.0.0  
**Last Updated**: 2026-02-28  
**Ecosystem**: ecosystem-1  
**Mode**: H0 Autonomous

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Usage](#usage)
5. [CLI Reference](#cli-reference)
6. [API Reference](#api-reference)
7. [GitHub Actions](#github-actions)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [φ-CPS Validation](#phi-cps-validation)

---

## Overview

The Cross-Repo Sync system enables automated synchronization of ecosystem metadata, WAL database, and metrics across the 11 repositories in ecosystem-1.

### Key Features

- **ECOS_ROOT.json Synchronization**: Central manifest replication
- **WAL Database Sync**: SQLite database backup and distribution
- **Repository Metrics**: Git statistics collection and aggregation
- **φ-CPS Validation**: Consistency checks across repositories
- **Automated Reports**: Markdown and JSON output generation
- **CI/CD Integration**: GitHub Actions workflow automation
- **Multi-Repo Orchestration**: Parallel operations with dependency management

### Benefits

- ✅ **Consistency**: All repos share same ecosystem state
- ✅ **Traceability**: Every operation logged in WAL
- ✅ **Automation**: Daily sync via GitHub Actions
- ✅ **Monitoring**: φ-CPS drift detection
- ✅ **Resilience**: Auto-rollback on validation failures
- ✅ **Scalability**: Supports 50+ repositories

---

## Architecture

### System Components

```
┌───────────────────────────────────────────────────────────┐
│                    KIVA-CLI (Source)                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ECOS_ROOT.json (Manifest)                          │  │
│  │  - 11 repos metadata                                │  │
│  │  - Global metrics                                   │  │
│  │  - φ-CPS tracking                                   │  │
│  │  - Recent events                                    │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  global_wal.db (WAL Database)                       │  │
│  │  - Event log (SQLite)                               │  │
│  │  - IntentHash chain                                 │  │
│  │  - φ-CPS deltas                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  scripts/cross_repo_sync.py                         │  │
│  │  - Sync orchestrator                                │  │
│  │  - Multi-repo operations                            │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────┬───────────────────────────────────────────┘
                │
                │ Daily Sync (02:00 UTC)
                │ GitHub Actions
                │
                ↓
┌───────────────┴───────────────────────────────────────────┐
│                  Target Repositories                      │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  ECOYSTEM    │  │  DevTools    │  │  BRAIN       │   │
│  │  (Core)      │  │  (Utility)   │  │  (Knowledge) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  CANDIDATOR  │  │  FLUENCE     │  │  ...         │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└───────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Trigger**: GitHub Actions schedule, push event, or manual
2. **Checkout**: Clone KIVA-CLI, ECOYSTEM, DevTools
3. **Validate**: Check ECOS_ROOT.json syntax
4. **Sync**: Execute cross_repo_sync.py
5. **Commit**: Push changes to target repos
6. **Metrics**: Generate dashboard
7. **Validate**: Check φ-CPS drift
8. **Alert**: Create issue if threshold exceeded
9. **Artifacts**: Upload reports (30-day retention)

---

## Components

### 1. ECOS_ROOT.json

**Location**: `ECOS_ROOT.json`  
**Purpose**: Central ecosystem manifest  
**Format**: JSON (11 KB)

**Structure**:
```json
{
  "manifest_version": "1.0.0",
  "ecosystem_id": "ecosystem-1",
  "phi_cps_genesis": 4.092,
  "phi_cps_current": 4.226,
  "repositories": [ /* 11 repos */ ],
  "global_metrics": { /* aggregates */ },
  "validation_rules": { /* base-3, φ-CPS */ },
  "managers": { /* 6 managers */ },
  "recent_events": [ /* event log */ ],
  "next_steps": [ /* roadmap */ ]
}
```

### 2. global_wal.db

**Location**: `~/.kiva/global_wal.db`  
**Purpose**: Write-Ahead Log for all ecosystem events  
**Format**: SQLite3

**Schema**:
```sql
CREATE TABLE wal_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  event_type TEXT NOT NULL,
  entity_id TEXT,
  action TEXT NOT NULL,
  intent_hash TEXT NOT NULL,
  phi_delta REAL DEFAULT 0.0,
  description TEXT,
  status TEXT DEFAULT 'SUCCESS'
);
```

### 3. cross_repo_sync.py

**Location**: `scripts/cross_repo_sync.py`  
**Purpose**: Cross-repo synchronization orchestrator  
**Size**: 415 lines (14.1 KB)

**Operations**:
- `ecos_root`: Sync ECOS_ROOT.json
- `wal`: Sync WAL database
- `metrics`: Update repo metrics
- `validate`: Check φ-CPS consistency
- `full`: Execute all operations

### 4. ecosystem_sync.yml

**Location**: `.github/workflows/ecosystem_sync.yml`  
**Purpose**: GitHub Actions CI/CD workflow  
**Size**: 214 lines (9.8 KB)

**Schedule**: Daily at 02:00 UTC  
**Triggers**: Push to main, manual dispatch

---

## Usage

### Quick Start

```bash
# Clone KIVA-CLI
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Full sync workflow
python scripts/cross_repo_sync.py \
  --root .. \
  --source KIVA-CLI \
  --operation full
```

### Common Workflows

#### 1. Sync ECOS_ROOT.json Only

```bash
python scripts/cross_repo_sync.py \
  --root /path/to/repos \
  --operation ecos_root
```

#### 2. Sync WAL Database Only

```bash
python scripts/cross_repo_sync.py \
  --root /path/to/repos \
  --operation wal
```

#### 3. Validate φ-CPS Consistency

```bash
python scripts/cross_repo_sync.py \
  --root /path/to/repos \
  --operation validate
```

#### 4. Generate Sync Report

```bash
python scripts/cross_repo_sync.py \
  --operation full \
  --output sync_report.md
```

---

## CLI Reference

### cross_repo_sync.py

**Synopsis**:
```
python scripts/cross_repo_sync.py [OPTIONS]
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--root` | str | `..` | Root directory containing repos |
| `--source` | str | `KIVA-CLI` | Source repository name |
| `--operation` | str | `full` | Operation: full, ecos_root, wal, validate |
| `--output` | str | None | Output file for sync report |
| `--target-repos` | str | `all` | Comma-separated repo names or "all" |
| `--dry-run` | flag | False | Preview changes without executing |
| `--verbose` | flag | False | Enable verbose logging |

**Examples**:

```bash
# Full sync with custom root
python scripts/cross_repo_sync.py --root ~/projects --operation full

# Sync specific repos only
python scripts/cross_repo_sync.py \
  --operation ecos_root \
  --target-repos ECOYSTEM,DevTools

# Dry run to preview changes
python scripts/cross_repo_sync.py --operation full --dry-run

# Verbose output with report
python scripts/cross_repo_sync.py \
  --operation full \
  --verbose \
  --output sync_report.md
```

---

## API Reference

### CrossRepoSync Class

**Import**:
```python
from scripts.cross_repo_sync import CrossRepoSync
```

**Constructor**:
```python
syncer = CrossRepoSync(
    root_dir: Path,
    repos_config: Dict[str, str]
)
```

**Methods**:

#### sync_ecos_root()

```python
def sync_ecos_root(
    self,
    source_repo: str,
    target_repos: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Sync ECOS_ROOT.json to target repos."""
```

**Returns**:
```python
{
    "success": True,
    "synced_repos": ["ECOYSTEM", "DevTools"],
    "timestamp": "2026-02-28T18:00:00Z"
}
```

#### sync_wal_database()

```python
def sync_wal_database(
    self,
    source_repo: str,
    target_repos: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Sync WAL database to target repos."""
```

**Returns**:
```python
{
    "success": True,
    "database_size": 512000,
    "events_count": 150,
    "synced_repos": ["ECOYSTEM"]
}
```

#### update_repo_metrics()

```python
def update_repo_metrics(
    self,
    target_repos: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Update repository metrics."""
```

**Returns**:
```python
{
    "success": True,
    "updated_repos": 11,
    "total_commits": 20,
    "metrics": { /* per-repo stats */ }
}
```

#### validate_phi_cps_consistency()

```python
def validate_phi_cps_consistency(
    self
) -> Dict[str, Any]:
    """Validate φ-CPS consistency."""
```

**Returns**:
```python
{
    "success": True,
    "phi_genesis": 4.092,
    "phi_current": 4.226,
    "drift": 0.134,
    "drift_acceptable": True,
    "repos_checked": 11
}
```

#### execute_full_sync()

```python
def execute_full_sync(
    self,
    source_repo: str
) -> Dict[str, Any]:
    """Execute full sync workflow."""
```

**Returns**:
```python
{
    "success": True,
    "operations": [
        {"type": "ecos_root", "status": "SUCCESS"},
        {"type": "wal", "status": "SUCCESS"},
        {"type": "metrics", "status": "SUCCESS"},
        {"type": "validate", "status": "SUCCESS"}
    ],
    "duration_seconds": 12.5
}
```

### Example Usage

```python
from pathlib import Path
from scripts.cross_repo_sync import CrossRepoSync

# Initialize
repos = {
    "KIVA-CLI": "KIVA-CLI",
    "ECOYSTEM": "ECOYSTEM",
    "DevTools": "DevTools"
}

syncer = CrossRepoSync(Path(".."), repos)

# Sync ECOS_ROOT.json
result = syncer.sync_ecos_root("KIVA-CLI")
print(f"Synced to {len(result['synced_repos'])} repos")

# Validate φ-CPS
validation = syncer.validate_phi_cps_consistency()
if validation['drift_acceptable']:
    print("φ-CPS drift within threshold")
else:
    print(f"WARNING: Drift {validation['drift']:.4f} exceeds 0.05")

# Full sync
full_result = syncer.execute_full_sync("KIVA-CLI")
for op in full_result['operations']:
    print(f"{op['type']}: {op['status']}")
```

---

## GitHub Actions

### Workflow Configuration

**File**: `.github/workflows/ecosystem_sync.yml`

### Triggers

1. **Schedule**: Daily at 02:00 UTC
   ```yaml
   schedule:
     - cron: '0 2 * * *'
   ```

2. **Push Events**: Changes to sync files
   ```yaml
   push:
     branches: [main]
     paths:
       - 'ECOS_ROOT.json'
       - 'scripts/cross_repo_sync.py'
       - '.github/workflows/ecosystem_sync.yml'
   ```

3. **Manual Dispatch**: On-demand execution
   ```yaml
   workflow_dispatch:
     inputs:
       operation:
         type: choice
         options: [full, ecos_root, wal, validate]
   ```

### Manual Trigger

1. Navigate to: `Actions` → `Ecosystem Cross-Repo Sync`
2. Click: `Run workflow`
3. Select:
   - **Branch**: `main`
   - **Operation**: `full` (or specific)
   - **Target repos**: `all` (or comma-separated)
4. Click: `Run workflow`

### View Results

1. **Job Summary**: Check run page for markdown summary
2. **Artifacts**: Download `sync-report-{run_number}`
3. **Logs**: View detailed step logs
4. **Issues**: Auto-created on drift/failure

---

## Troubleshooting

### Common Issues

#### Issue: "ECOS_ROOT.json not found"

**Cause**: Missing manifest file  
**Solution**:
```bash
# Check file exists
ls -la ECOS_ROOT.json

# If missing, sync from source
git pull origin main
```

#### Issue: "Permission denied" when syncing

**Cause**: Insufficient git permissions  
**Solution**:
```bash
# Check SSH key
ssh -T git@github.com

# Or use HTTPS with token
git config credential.helper store
```

#### Issue: "φ-CPS drift exceeds threshold"

**Cause**: Cumulative drift > 0.05  
**Solution**:
1. Review recent events in ECOS_ROOT.json
2. Validate IntentHash chain integrity
3. Check for semantic inconsistencies
4. Run comprehensive audit:
   ```bash
   python scripts/cross_repo_sync.py --operation validate
   ```

#### Issue: "WAL database locked"

**Cause**: Concurrent access to SQLite DB  
**Solution**:
```bash
# Wait for lock release (auto after 5s)
# Or force unlock:
fuser -k ~/.kiva/global_wal.db
```

#### Issue: "GitHub Actions workflow failed"

**Cause**: Various (rate limit, permissions, errors)  
**Solution**:
1. Check workflow logs
2. Review auto-created issue
3. Verify GitHub token permissions:
   - `contents: write`
   - `issues: write`
4. Re-run workflow manually

### Debug Mode

```bash
# Enable verbose logging
python scripts/cross_repo_sync.py --operation full --verbose

# Dry run to preview
python scripts/cross_repo_sync.py --operation full --dry-run

# Check ECOS_ROOT syntax
python -c "import json; json.load(open('ECOS_ROOT.json'))"
```

---

## Best Practices

### 1. Regular Sync Schedule

- **Automated**: Daily at 02:00 UTC via GitHub Actions
- **Manual**: After major changes to ECOS_ROOT.json
- **Emergency**: On φ-CPS drift alerts

### 2. Validation Before Sync

```bash
# Always validate before full sync
python scripts/cross_repo_sync.py --operation validate

# If validation passes, proceed
if [ $? -eq 0 ]; then
  python scripts/cross_repo_sync.py --operation full
fi
```

### 3. Incremental Sync

```bash
# Sync components separately for large ecosystems
python scripts/cross_repo_sync.py --operation ecos_root
python scripts/cross_repo_sync.py --operation wal
python scripts/cross_repo_sync.py --operation validate
```

### 4. Monitor φ-CPS Drift

```bash
# Check current drift
python -c "
import json
ecos = json.load(open('ECOS_ROOT.json'))
genesis = ecos['phi_cps_genesis']
current = ecos['phi_cps_current']
drift = abs(current - genesis)
print(f'Drift: {drift:.4f} (threshold: 0.05)')
"
```

### 5. Backup Before Sync

```bash
# Backup critical files
cp ECOS_ROOT.json ECOS_ROOT.json.bak
cp ~/.kiva/global_wal.db ~/.kiva/global_wal.db.bak

# Sync
python scripts/cross_repo_sync.py --operation full

# Verify success, then remove backups
rm *.bak
```

### 6. Review Sync Reports

```bash
# Generate detailed report
python scripts/cross_repo_sync.py \
  --operation full \
  --output sync_report_$(date +%Y%m%d).md

# Review
cat sync_report_*.md
```

---

## φ-CPS Validation

### Drift Calculation

```python
φ_drift = abs(φ_current - φ_genesis)

# Threshold check
if φ_drift > 0.05:
    # ALERT: Drift exceeds 5%
    create_drift_alert_issue()
else:
    # OK: Drift within acceptable range
    pass
```

### Validation Process

1. **Extract φ values** from ECOS_ROOT.json
2. **Calculate drift**: `Δφ = |φ_current - φ_genesis|`
3. **Check threshold**: Compare to 0.05
4. **Validate consistency**: All repos use same φ_genesis
5. **Check chain**: Verify IntentHash¹¹ integrity
6. **Report**: Generate validation report

### Auto-Rollback

```python
if phi_drift > 0.05:
    # Rollback to last known good state
    git revert HEAD
    
    # Create incident ticket
    create_issue(
        title="⚠️ φ-CPS Drift Threshold Exceeded",
        body=f"Drift: {phi_drift:.4f} > 0.05",
        labels=["φ-CPS", "drift-alert", "automated"]
    )
    
    # Log to WAL
    wal.append_event(
        event_type="rollback",
        reason="phi_drift_exceeded",
        phi_delta=-phi_drift
    )
```

### Manual Audit

```bash
# Comprehensive φ-CPS audit
python scripts/ecosystem_metrics_dashboard.py \
  --root .. \
  --format json \
  | jq '.phi_cps_analysis'

# Expected output:
# {
#   "phi_genesis": 4.092,
#   "phi_current": 4.226,
#   "delta_total": 0.134,
#   "delta_percent": 3.27,
#   "drift_acceptable": true
# }
```

---

## Support

**Documentation**: [KIVA-CLI README](../README.md)  
**Issues**: [GitHub Issues](https://github.com/gerivdb/KIVA-CLI/issues)  
**Workflow Logs**: [GitHub Actions](https://github.com/gerivdb/KIVA-CLI/actions)

**Emergency Contact**:
- Check auto-created issues for drift/failure alerts
- Review workflow run summaries
- Consult WAL database for event history

---

**Generated by**: ECOS-AUTO H0 Autonomous System  
**Mode**: NO-HITL (Zero Human Interaction)  
**Version**: 1.0.0  
**Last Updated**: 2026-02-28
