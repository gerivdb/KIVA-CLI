# CitizenManager - Entity Lifecycle & Validation

## Overview

CitizenManager provides **L0-L5 hierarchical entity management** with base-3 ternary validation, base-4 lifecycle states, and φ-CPS tracking for the ECOS ecosystem. It enables systematic tracking, promotion, and validation of entities (citizens) across 16 repositories.

### Key Features

- **L0-L5 Entity Hierarchy**: Structured progression from genesis (L0) to critical production (L4) or legacy archive (L5)
- **Base-3 Ternary Validation**: `UNKNOWN` / `VALID` / `INVALID` semantic validation states
- **Base-4 Lifecycle States**: `GENESIS` / `ACTIVE` / `DEPRECATED` / `ARCHIVED` entity lifecycle
- **φ-CPS Tracking**: Cumulative coherence scoring per entity with automatic drift detection
- **IntentHash Chain**: Cryptographic event continuity (L0-L1-L2 levels)
- **Cross-Repo Sync**: Automatic entity discovery and synchronization across ecosystem-1 (16 repos)
- **Dependency Tracking**: Entity relationship graph with parent/child hierarchies
- **SQLite Persistence**: Local database with full audit trail (citizens.db)
- **CLI Integration**: 7 commands for complete entity lifecycle management
- **WAL Integration**: Automatic event logging to GlobalWALManager

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KIVA-CLI Ecosystem                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌────────────────────┐         │
│  │  CitizenManager  │◄────►│  GlobalWALManager  │         │
│  │  (L0-L5 Entities)│      │  (Event Tracking)  │         │
│  └────────┬─────────┘      └────────────────────┘         │
│           │                                                 │
│           │ register/promote/demote                         │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────┐          │
│  │          citizens.db (SQLite)                │          │
│  ├─────────────────────────────────────────────┤          │
│  │  • citizens (entities)                       │          │
│  │  • entity_relationships (deps)               │          │
│  │  • entity_history (audit trail)              │          │
│  └─────────────────────────────────────────────┘          │
│           ▲                                                 │
│           │ sync                                            │
│  ┌────────┴─────────────────────────────────┐             │
│  │  Cross-Repo Sync (scripts/cross_repo_sync.py)          │
│  │  • Scans ECOS_ROOT.json in 16 repos                     │
│  │  • Auto-registers missing entities                      │
│  │  • Detects lifecycle changes                            │
│  └─────────────────────────────────────────────────────────┘
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### `citizens` Table

| Column | Type | Description |
|--------|------|-------------|
| `citizen_id` | TEXT PRIMARY KEY | Unique ID (`ctz_<16hex>`) |
| `name` | TEXT | Entity name |
| `entity_type` | TEXT | Type (PROJECT/SERVICE/COMPONENT/TOOL/etc.) |
| `entity_level` | TEXT | L0-L5 hierarchy level |
| `lifecycle_state` | TEXT | GENESIS/ACTIVE/DEPRECATED/ARCHIVED |
| `validation_state` | TEXT | UNKNOWN/VALID/INVALID |
| `repo` | TEXT | Repository name |
| `phi_cps` | REAL | φ-CPS score |
| `intent_hash` | TEXT | IntentHash (0x + 16 hex chars) |
| `parent_citizen_id` | TEXT | Parent entity ID (hierarchical) |
| `metadata` | TEXT | JSON metadata |
| `dependencies` | TEXT | JSON array of dependent citizen IDs |
| `created_at` | TEXT | ISO 8601 timestamp |
| `updated_at` | TEXT | ISO 8601 timestamp |

### `entity_relationships` Table

| Column | Type | Description |
|--------|------|-------------|
| `relationship_id` | TEXT PRIMARY KEY | Unique ID |
| `source_citizen_id` | TEXT | Source entity |
| `target_citizen_id` | TEXT | Target entity |
| `relationship_type` | TEXT | DEPENDS_ON/PARENT_OF/etc. |
| `created_at` | TEXT | ISO 8601 timestamp |

### `entity_history` Table

| Column | Type | Description |
|--------|------|-------------|
| `history_id` | TEXT PRIMARY KEY | Unique ID |
| `citizen_id` | TEXT | Entity ID |
| `event_type` | TEXT | REGISTER/PROMOTE/DEMOTE/VALIDATE |
| `from_level` | TEXT | Previous level (if promotion/demotion) |
| `to_level` | TEXT | New level |
| `phi_cps_delta` | REAL | φ-CPS change |
| `intent_hash` | TEXT | Event IntentHash |
| `timestamp` | TEXT | ISO 8601 timestamp |
| `metadata` | TEXT | JSON event metadata |

---

## Entity Levels (L0-L5)

### Level Definitions

| Level | Name | Description | φ-CPS Base | Promotion Criteria |
|-------|------|-------------|------------|--------------------|
| **L0** | GENESIS | Unvalidated, just created | 0.005 | Basic validation passing |
| **L1** | VALIDATED | Basic validation passed | 0.010 | Deployed and operational |
| **L2** | OPERATIONAL | Deployed and functional | 0.015 | Stable production use |
| **L3** | PRODUCTION | Stable production use | 0.020 | Mission-critical status |
| **L4** | CRITICAL | Mission-critical entity | 0.030 | N/A (top level) |
| **L5** | LEGACY | Archived/deprecated | 0.002 | Demotion/archival |

### Promotion Path

```
L0_GENESIS → L1_VALIDATED → L2_OPERATIONAL → L3_PRODUCTION → L4_CRITICAL
                                                                    ↓
                                                              L5_LEGACY
```

**Promotion φ-CPS Deltas**:
- L0 → L1: +0.008
- L1 → L2: +0.010
- L2 → L3: +0.012
- L3 → L4: +0.015

**Demotion φ-CPS Deltas**: Negative of promotion delta

---

## Entity Types

| Type | Description | Typical Level |
|------|-------------|---------------|
| `PROJECT` | Complete project/application | L2-L4 |
| `SERVICE` | Microservice or API | L2-L4 |
| `COMPONENT` | Reusable component/module | L1-L3 |
| `TOOL` | Development tool/utility | L1-L3 |
| `LIBRARY` | Code library/package | L1-L3 |
| `FRAMEWORK` | Framework or scaffold | L2-L4 |
| `WORKFLOW` | Automated workflow | L1-L2 |
| `AGENT` | AI agent or automation | L1-L3 |

---

## Lifecycle States (Base-4)

| State | Description | Typical Actions |
|-------|-------------|----------------|
| `GENESIS` | Initial creation | Register, validate |
| `ACTIVE` | In active use/development | Promote, update |
| `DEPRECATED` | Marked for removal | Demote, migrate |
| `ARCHIVED` | Permanently archived | Archive to L5 |

---

## Validation States (Base-3 Ternary)

| State | Description | Usage |
|-------|-------------|-------|
| `UNKNOWN` | Not yet validated | Default for new entities |
| `VALID` | Validation passed | Tests passing, deployment successful |
| `INVALID` | Validation failed | Tests failing, deployment blocked |

---

## CLI Commands

### 1. `ecos citizen register`

Register new citizen (entity).

**Syntax**:
```bash
ecos citizen register --name <name> --type <type> --repo <repo> \
                      [--level <level>] [--metadata <json>]
```

**Examples**:

```bash
# Basic registration (L0 by default)
ecos citizen register --name my-api --type SERVICE --repo KIVA-CLI

# Register at specific level
ecos citizen register --name prod-service --type SERVICE --repo FLUENCE \
                      --level L3_PRODUCTION

# With metadata
ecos citizen register --name web-app --type PROJECT --repo BRAIN \
                      --metadata '{"framework": "react", "version": "18.2.0"}'

# Component with dependencies
ecos citizen register --name auth-module --type COMPONENT --repo ECOYSTEM \
                      --metadata '{"dependencies": ["ctz_abc123"]}'
```

### 2. `ecos citizen promote`

Promote entity to higher level.

**Syntax**:
```bash
ecos citizen promote <citizen_id> --level <target_level>
```

**Examples**:

```bash
# Promote L0 → L1
ecos citizen promote ctz_a1b2c3d4e5f67890 --level L1_VALIDATED

# Promote to production
ecos citizen promote ctz_abc123 --level L3_PRODUCTION

# Promote to critical
ecos citizen promote ctz_prod001 --level L4_CRITICAL
```

### 3. `ecos citizen demote`

Demote entity to lower level or archive.

**Syntax**:
```bash
ecos citizen demote <citizen_id> --level <target_level> --reason <reason>
```

**Examples**:

```bash
# Demote to operational
ecos citizen demote ctz_abc123 --level L2_OPERATIONAL \
                --reason "Performance issues detected"

# Archive to L5
ecos citizen demote ctz_old_proj --level L5_LEGACY \
                --reason "Project deprecated, archived"

# Downgrade to validated
ecos citizen demote ctz_test --level L1_VALIDATED \
                --reason "Regression in tests, rollback to L1"
```

### 4. `ecos citizen list`

List citizens with filters.

**Syntax**:
```bash
ecos citizen list [--repo <repo>] [--level <level>] [--state <state>] \
                  [--limit <n>] [--format <table|json>]
```

**Examples**:

```bash
# List all citizens (table format)
ecos citizen list

# Filter by repository
ecos citizen list --repo KIVA-CLI

# Filter by entity level
ecos citizen list --level L3_PRODUCTION

# Filter by lifecycle state
ecos citizen list --state ACTIVE

# Combine filters + JSON output
ecos citizen list --repo BRAIN --level L4_CRITICAL --format json

# Limit results
ecos citizen list --limit 10
```

### 5. `ecos citizen export`

Export citizen registry to file.

**Syntax**:
```bash
ecos citizen export <output_path> [--format <json|csv>]
```

**Examples**:

```bash
# Export to JSON
ecos citizen export citizens_registry.json

# Export to CSV
ecos citizen export citizens_registry.csv --format csv

# Export with timestamp
ecos citizen export registry_$(date +%Y%m%d).json
```

### 6. `ecos citizen validate`

Update entity validation state (base-3).

**Syntax**:
```bash
ecos citizen validate <citizen_id> --state <UNKNOWN|VALID|INVALID>
```

**Examples**:

```bash
# Mark as valid
ecos citizen validate ctz_abc123 --state VALID

# Mark as invalid
ecos citizen validate ctz_failing_tests --state INVALID

# Reset to unknown
ecos citizen validate ctz_new --state UNKNOWN
```

### 7. `ecos citizen sync`

Synchronize citizens across repositories.

**Syntax**:
```bash
ecos citizen sync [--repos <repo1,repo2,...>] [--dry-run]
```

**Examples**:

```bash
# Sync all ecosystem-1 repos (16 repos)
ecos citizen sync

# Sync specific repos
ecos citizen sync --repos KIVA-CLI,BRAIN,FLUENCE

# Dry-run (preview changes)
ecos citizen sync --dry-run

# Sync and check output
ecos citizen sync && ecos citizen list --limit 50
```

---

## Cross-Repo Synchronization

### Workflow

1. **Scan Repositories**: Iterate through ecosystem-1 repos (16 total)
2. **Locate ECOS_ROOT.json**: Find manifest in each repo
3. **Extract Entities**: Parse capabilities and metadata
4. **Register Missing**: Auto-register entities not in CitizenManager
5. **Update Existing**: Detect level/lifecycle changes and update
6. **Log Events**: Append sync events to GlobalWALManager
7. **Generate Report**: Summary of actions (registered/updated/skipped)

### Sync Script Usage

```bash
# Direct script execution
python scripts/cross_repo_sync.py

# With specific repos
python scripts/cross_repo_sync.py --repos KIVA-CLI,BRAIN,FLUENCE

# Dry-run mode
python scripts/cross_repo_sync.py --dry-run
```

### Sync Output Example

```
🔄 Cross-Repo Sync Started
   Mode: LIVE
   Repos: 11

📂 Scanning repo: KIVA-CLI
   ✅ Found 5 entit(ies)
      + Registered: KIVA-CLI
      + Registered: Global WAL Manager
      + Registered: ProjectManager
      ✓ Updated: CitizenManager
      - Skipped: TestFramework (no changes)

📂 Scanning repo: BRAIN
   ✅ Found 3 entit(ies)
      + Registered: BRAIN-API
      + Registered: Memory System
      + Registered: Context Analyzer

============================================================
CROSS-REPO SYNC SUMMARY
============================================================
Repos scanned:       11
Citizens found:      52
Citizens registered: 38
Citizens updated:    8
Citizens skipped:    6
============================================================
```

---

## Integration with GlobalWALManager

### Auto-Logging Events

CitizenManager automatically appends events to GlobalWALManager:

| Operation | WAL Event |
|-----------|----------|
| `register_citizen` | `CITIZEN_REGISTER` |
| `promote_entity` | `CITIZEN_PROMOTE` |
| `demote_entity` | `CITIZEN_DEMOTE` |
| `validate_entity` | `CITIZEN_VALIDATE` |

### Event Metadata

Each WAL event includes:
- `citizen_id`: Entity ID
- `name`: Entity name
- `entity_type`: Type (PROJECT/SERVICE/etc.)
- `entity_level`: Current level
- `from_level` / `to_level`: Level changes (promotion/demotion)
- `reason`: Demotion reason (if applicable)

### φ-CPS Tracking

φ-CPS deltas are automatically calculated and logged:
- Registration: +initial φ-CPS (based on level)
- Promotion: +promotion delta (0.008 to 0.015)
- Demotion: -promotion delta (negative)

---

## φ-CPS Calculation

### Initial φ-CPS by Level

```python
φ_initial = {
    "L0_GENESIS": 0.005,
    "L1_VALIDATED": 0.010,
    "L2_OPERATIONAL": 0.015,
    "L3_PRODUCTION": 0.020,
    "L4_CRITICAL": 0.030,
    "L5_LEGACY": 0.002
}
```

### Promotion Deltas

```python
φ_delta = {
    ("L0_GENESIS", "L1_VALIDATED"): 0.008,
    ("L1_VALIDATED", "L2_OPERATIONAL"): 0.010,
    ("L2_OPERATIONAL", "L3_PRODUCTION"): 0.012,
    ("L3_PRODUCTION", "L4_CRITICAL"): 0.015
}
```

### Cumulative φ-CPS

```python
φ_entity_final = φ_initial + Σ(φ_delta_promotions)
```

**Example**: Entity promoted L0 → L1 → L2 → L3
```
φ_final = 0.005 + 0.008 + 0.010 + 0.012 = 0.035
```

---

## Best Practices

### 1. Entity Naming

- Use descriptive, unique names
- Follow repo naming conventions
- Max length: 50 characters (for compatibility)
- Example: `kiva-api-service`, `brain-memory-module`

### 2. Promotion Strategy

- **L0 → L1**: After basic validation (tests passing)
- **L1 → L2**: After successful deployment to staging/dev
- **L2 → L3**: After 30 days stable operation + production deployment
- **L3 → L4**: Reserve for mission-critical, high-uptime services

### 3. Metadata Usage

```json
{
  "framework": "fastapi",
  "version": "1.2.3",
  "maintainer": "team-backend",
  "dependencies": ["postgres", "redis"],
  "deployment_url": "https://api.example.com"
}
```

### 4. Cross-Repo Sync Schedule

- **Daily**: Automated sync via cron/GitHub Actions
- **On-demand**: Before major deployments
- **Dry-run first**: Preview changes before applying

### 5. Lifecycle Transitions

- `GENESIS → ACTIVE`: After L1 validation
- `ACTIVE → DEPRECATED`: When replacement available
- `DEPRECATED → ARCHIVED`: After 90-day grace period
- `ARCHIVED → L5_LEGACY`: Permanent archival

---

## Troubleshooting

### Issue: Citizen not found after registration

**Cause**: Database path mismatch or transaction not committed

**Solution**:
```bash
# Check database location
ls -la ~/.kiva/citizens.db

# Verify registration
ecos citizen list --format json | jq '.[] | select(.name == "my-entity")'
```

### Issue: Promotion fails with "Invalid promotion" error

**Cause**: Attempting invalid level jump (e.g., L0 → L3)

**Solution**:
```bash
# Check current level
ecos citizen list --format json | jq '.[] | select(.citizen_id == "ctz_abc")'

# Promote incrementally
ecos citizen promote ctz_abc --level L1_VALIDATED
ecos citizen promote ctz_abc --level L2_OPERATIONAL
```

### Issue: Cross-repo sync finds 0 entities

**Cause**: ECOS_ROOT.json not found or repos not in search paths

**Solution**:
```bash
# Check repo paths
python scripts/cross_repo_sync.py --dry-run

# Manually verify ECOS_ROOT.json exists
find ~/repos -name "ECOS_ROOT.json" -type f
```

### Issue: φ-CPS not updating after promotion

**Cause**: WAL Manager not initialized or database lock

**Solution**:
```bash
# Check WAL database
ls -la ~/.kiva/global_wal.db

# Verify φ-CPS in registry
ecos citizen list --format json | jq '.[] | select(.citizen_id == "ctz_abc") | .phi_cps'
```

---

## FAQ

### Q1: What's the difference between entity_level and lifecycle_state?

**A**: `entity_level` (L0-L5) tracks **maturity/criticality** (validation, production-readiness). `lifecycle_state` (GENESIS/ACTIVE/DEPRECATED/ARCHIVED) tracks **operational status** (in-use vs. archived).

### Q2: Can I skip levels during promotion (e.g., L0 → L3)?

**A**: Current implementation allows this, but **best practice** is incremental promotion (L0 → L1 → L2 → L3). Future versions may enforce strict ordering.

### Q3: How do I bulk-register citizens?

**A**: Use cross-repo sync (`ecos citizen sync`) or write a custom script iterating over `CitizenManager.register_citizen()`.

### Q4: What happens to φ-CPS when an entity is demoted?

**A**: φ-CPS decreases by the negative of the promotion delta (e.g., L2 → L1 gives -0.010).

### Q5: Can I delete a citizen?

**A**: Currently no direct delete command. Archive to L5_LEGACY and set lifecycle to ARCHIVED. Future versions may add soft/hard delete.

### Q6: How does CitizenManager integrate with ProjectManager?

**A**: ProjectManager automatically registers entities when scaffolding projects. CitizenManager tracks their lifecycle independently.

### Q7: What's the maximum number of citizens supported?

**A**: SQLite database supports millions of rows. Practical limit depends on disk space (~1KB per citizen with metadata).

### Q8: How do I export citizens for a specific repo?

**A**: Use filters + export:
```bash
ecos citizen list --repo KIVA-CLI --format json > kiva_citizens.json
```

---

## Next Steps

1. **Register your first citizen**: `ecos citizen register --name my-project --type PROJECT --repo MY-REPO`
2. **Run cross-repo sync**: `ecos citizen sync --dry-run` (preview), then `ecos citizen sync` (apply)
3. **View registry**: `ecos citizen list` (table) or `ecos citizen list --format json` (JSON)
4. **Export for backup**: `ecos citizen export registry_backup.json`
5. **Integrate with CI/CD**: Add promotion steps to deployment pipelines

---

**CitizenManager Version**: 0.1.0  
**KIVA-CLI Version**: 0.3.0  
**Last Updated**: 2026-03-01  
**φ-CPS**: 4.398
