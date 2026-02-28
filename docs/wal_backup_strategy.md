# WAL Database Backup Strategy

## Overview

Automated backup and restore system for KIVA-CLI Global WAL database, ensuring data durability and disaster recovery capabilities.

## Configuration

### Backup Locations

1. **Local Backups**
   - Path: `~/.kiva/backups/wal`
   - Retention: 30 days
   - Compression: gzip (level 9)

2. **Remote Backups (GitHub)**
   - Repository: `gerivdb/ECOYSTEM`
   - Path: `backups/wal`
   - Retention: 90 days
   - Compression: gzip (level 9)

### Backup Types

#### Full Backup
- **Frequency**: Daily at 02:00 UTC
- **Retention**: 7 backups
- **Content**: Complete database snapshot
- **Compression**: Level 9
- **Size**: ~50-200 MB compressed

#### Incremental Backup
- **Frequency**: Hourly
- **Retention**: 24 backups
- **Content**: New entries only
- **Compression**: Level 6
- **Size**: ~5-20 MB compressed

#### Snapshot Backup
- **Frequency**: Weekly (Sunday 02:00 UTC)
- **Retention**: 4 backups
- **Content**: Complete database state with indexes
- **Compression**: Level 9
- **Size**: ~100-300 MB compressed

## Usage

### Create Manual Backup

```bash
# Full backup
python wal_backup_manager.py --type full

# Incremental backup
python wal_backup_manager.py --type incremental
```

### Restore from Backup

```bash
# Restore from local backup
python wal_backup_manager.py --restore --backup-id wal_backup_full_20260228_020000 --source local

# Restore from GitHub
python wal_backup_manager.py --restore --backup-id wal_backup_full_20260228_020000 --source github
```

### Automated Schedule (GitHub Actions)

```yaml
name: WAL Database Backup

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 02:00 UTC
    - cron: '0 */1 * * *'  # Hourly
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Create WAL Backup
        run: |
          python scripts/wal_backup_manager.py --type full
          
      - name: Upload to ECOYSTEM
        run: |
          # Upload backup to ECOYSTEM repository
          python scripts/wal_backup_manager.py --upload
```

## Restore Procedures

### Point-in-Time Recovery

1. Identify target recovery timestamp
2. Download appropriate backup from GitHub
3. Verify backup integrity (automatic)
4. Restore database with rollback protection
5. Validate φ-CPS consistency

### Disaster Recovery

1. **Local Disk Failure**
   - Download latest backup from GitHub
   - Restore to new database location
   - Verify all tables and indexes

2. **Data Corruption**
   - Stop all KIVA-CLI processes
   - Create backup of corrupted database
   - Restore from last known good backup
   - Replay incremental backups if available

3. **Complete Data Loss**
   - Clone ECOYSTEM repository
   - Extract latest snapshot backup
   - Restore to standard location
   - Rebuild WAL indexes

## Monitoring

### Backup Success Rate
- Target: 99.5%
- Alert if < 95% in 7-day window

### Backup Duration
- Full backup: < 5 minutes
- Incremental: < 1 minute
- Alert if exceeds 2x target

### Storage Usage
- Local: Monitor < 80% capacity
- GitHub: Track repo size growth
- Alert at 80% threshold

## Validation

### Automatic Restore Testing
- **Frequency**: Weekly (Saturday 03:00 UTC)
- **Sample Size**: Latest 3 backups
- **Verification**: Schema + data consistency
- **Report**: GitHub issue if failures detected

### Integrity Checks
- **Frequency**: Daily with backup
- **Checks**: 
  - SHA256 checksum
  - SQLite PRAGMA integrity_check
  - Table count verification
  - Record count validation

## Troubleshooting

### Backup Fails
1. Check disk space (`df -h`)
2. Verify database not locked
3. Review backup logs
4. Retry with `--force` flag

### Restore Fails
1. Verify backup checksum
2. Check database permissions
3. Ensure no active connections
4. Review restore logs

### GitHub Upload Fails
1. Check GitHub API rate limits
2. Verify authentication token
3. Check repository permissions
4. Retry with exponential backoff

## Best Practices

1. **Test Restores Regularly**: Monthly restore validation
2. **Monitor Backup Size**: Track growth trends
3. **Rotate Credentials**: Update tokens quarterly
4. **Document Recovery**: Keep runbooks updated
5. **Audit Access**: Review backup access logs

## φ-CPS Impact

Expected φ-CPS delta: **+0.002**

Rationale:
- Data durability: +0.001 (reduces data loss risk)
- Recovery capability: +0.001 (enables quick restoration)
- Monitoring: +0.0005 (proactive issue detection)
- Automation: -0.0005 (complexity overhead)

## Integration

### ECOS CLI Commands

```bash
# Create backup
ecos wal backup --type full

# Restore backup
ecos wal restore --backup-id <id>

# List backups
ecos wal backups list

# Verify backup
ecos wal backup verify --backup-id <id>
```

### GitHub Actions Integration

Automatic integration with `ecosystem_sync.yml` workflow:
- Pre-sync: Create backup
- Post-sync: Verify integrity
- On-failure: Restore from backup

## Next Steps

1. ✅ Implement backup script
2. ✅ Create documentation
3. ⏳ Add GitHub Actions workflow
4. ⏳ Implement ECOS CLI commands
5. ⏳ Setup monitoring dashboard
6. ⏳ Create restore runbooks
