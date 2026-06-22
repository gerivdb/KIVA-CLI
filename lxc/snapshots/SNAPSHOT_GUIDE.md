# LXC Snapshot Management Guide

## Overview

Automated snapshot management for LXC containers using ZFS or native LXC snapshots.

## Snapshot Types

### 1. Hourly Snapshots
- **Frequency**: Every hour
- **Retention**: Last 24 snapshots
- **Use case**: Recent point-in-time recovery

### 2. Daily Snapshots
- **Frequency**: Daily at 02:00
- **Retention**: Last 7 snapshots
- **Use case**: Short-term backup

### 3. Weekly Snapshots
- **Frequency**: Sunday at 03:00
- **Retention**: Last 4 snapshots
- **Use case**: Medium-term backup

### 4. Monthly Snapshots
- **Frequency**: 1st of month at 04:00
- **Retention**: Last 12 snapshots
- **Use case**: Long-term backup, compliance

## Usage

### Create Manual Snapshot

```bash
./lxc/snapshots/snapshot-manager.sh create kiva-cli manual
```

### Create Scheduled Snapshot

```bash
# Hourly
./lxc/snapshots/snapshot-manager.sh create brain hourly

# Daily
./lxc/snapshots/snapshot-manager.sh create fluence daily

# Weekly
./lxc/snapshots/snapshot-manager.sh create candidator weekly

# Monthly
./lxc/snapshots/snapshot-manager.sh create geribooking monthly
```

### List Snapshots

```bash
./lxc/snapshots/snapshot-manager.sh list kiva-cli
```

Output:
```
NAME                                    USED  CREATION
lxc-pool/kiva-cli@hourly-20260228-1400  50M   2026-02-28 14:00
lxc-pool/kiva-cli@hourly-20260228-1500  45M   2026-02-28 15:00
lxc-pool/kiva-cli@daily-20260228-0200   2G    2026-02-28 02:00
```

### Restore Snapshot

```bash
./lxc/snapshots/snapshot-manager.sh restore kiva-cli hourly-20260228-1500
```

**Warning**: This will:
1. Stop the container
2. Rollback to snapshot state
3. Restart the container

All changes after snapshot will be lost!

### Verify Snapshot Integrity

```bash
./lxc/snapshots/snapshot-manager.sh verify kiva-cli hourly-20260228-1500
```

### Cleanup Old Snapshots

```bash
# Automatic cleanup based on retention policy
./lxc/snapshots/snapshot-manager.sh cleanup kiva-cli
```

## Automation with Cron

Add to `/etc/cron.d/lxc-snapshots`:

```cron
# Hourly snapshots for critical containers
0 * * * * root /path/to/snapshot-manager.sh create kiva-cli hourly >> /var/log/lxc/snapshots.log 2>&1
0 * * * * root /path/to/snapshot-manager.sh create brain hourly >> /var/log/lxc/snapshots.log 2>&1
0 * * * * root /path/to/snapshot-manager.sh create fluence hourly >> /var/log/lxc/snapshots.log 2>&1

# Daily snapshots for all containers
0 2 * * * root /path/to/snapshot-manager.sh create kiva-cli daily >> /var/log/lxc/snapshots.log 2>&1
0 2 * * * root /path/to/snapshot-manager.sh create ecoystem daily >> /var/log/lxc/snapshots.log 2>&1
# ... (add all 11 containers)

# Weekly cleanup
0 3 * * 0 root /path/to/snapshot-manager.sh cleanup kiva-cli >> /var/log/lxc/snapshots.log 2>&1
# ... (add all 11 containers)

# Monthly snapshots
0 4 1 * * root /path/to/snapshot-manager.sh create kiva-cli monthly >> /var/log/lxc/snapshots.log 2>&1
# ... (add all 11 containers)
```

## ZFS Advanced Features

### Clone Snapshot

```bash
# Create writable clone from snapshot
zfs clone lxc-pool/kiva-cli@daily-20260228-0200 lxc-pool/kiva-cli-clone

# Use clone for testing
lxc-start -n kiva-cli-clone
```

### Send Snapshot to Remote

```bash
# Initial full send
zfs send lxc-pool/kiva-cli@daily-20260228-0200 | ssh backup-server zfs receive backup-pool/kiva-cli

# Incremental send
zfs send -i @daily-20260228-0200 lxc-pool/kiva-cli@daily-20260301-0200 | ssh backup-server zfs receive backup-pool/kiva-cli
```

### Compression

```bash
# Enable compression on pool
zfs set compression=lz4 lxc-pool/kiva-cli

# Check compression ratio
zfs get compressratio lxc-pool/kiva-cli
```

## Disaster Recovery

### Full System Restore

1. Boot from rescue media
2. Install ZFS
3. Import pool: `zpool import lxc-pool`
4. List snapshots: `zfs list -t snapshot`
5. Rollback: `zfs rollback lxc-pool/kiva-cli@<snapshot>`
6. Start containers: `lxc-start -n kiva-cli`

### Partial Data Restore

```bash
# Mount snapshot read-only
mkdir /mnt/snapshot
mount -t zfs lxc-pool/kiva-cli@daily-20260228-0200 /mnt/snapshot

# Copy specific files
cp /mnt/snapshot/path/to/file /destination/

# Unmount
umount /mnt/snapshot
```

## Monitoring

### Check Snapshot Space Usage

```bash
zfs list -t snapshot -o name,used,refer
```

### Alert on High Snapshot Usage

```bash
#!/bin/bash
THRESHOLD=50  # GB

USAGE=$(zfs list -t snapshot -o used -Hp | awk '{s+=$1} END {print s/1024/1024/1024}')

if (( $(echo "$USAGE > $THRESHOLD" | bc -l) )); then
    echo "WARNING: Snapshot usage ($USAGE GB) exceeds threshold ($THRESHOLD GB)"
    # Send alert
fi
```

## Troubleshooting

### Snapshot Creation Fails

```bash
# Check ZFS pool health
zpool status

# Check available space
zfs list -o space

# Check for errors
dmesg | grep -i zfs
```

### Rollback Hangs

```bash
# Force stop container
lxc-stop -n <container> -k

# Verify no processes
lxc-info -n <container>

# Retry rollback
zfs rollback lxc-pool/<container>@<snapshot>
```

## Best Practices

1. **Test restores regularly**: Verify snapshots are usable
2. **Monitor space usage**: Snapshots consume disk space
3. **Document before major changes**: Create named snapshot before updates
4. **Automate cleanup**: Run retention policy regularly
5. **Off-site backups**: Send snapshots to remote location

## References

- [ZFS Snapshots](https://docs.oracle.com/cd/E19253-01/819-5461/gbciq/index.html)
- [LXC Snapshots](https://linuxcontainers.org/lxc/manpages/man1/lxc-snapshot.1.html)
