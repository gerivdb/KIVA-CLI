# LXC I/O Throttling Guide

## Overview

This guide explains how to configure and manage I/O throttling for LXC containers in the KIVA-CLI ecosystem.

## Throttling Mechanisms

### 1. cgroup blkio Controller

```bash
# Set read BPS limit (200MB/s for brain)
lxc-cgroup -n brain blkio.throttle.read_bps_device "8:0 209715200"

# Set write BPS limit (150MB/s for brain)
lxc-cgroup -n brain blkio.throttle.write_bps_device "8:0 157286400"

# Set read IOPS limit (20K for brain)
lxc-cgroup -n brain blkio.throttle.read_iops_device "8:0 20000"

# Set write IOPS limit (15K for brain)
lxc-cgroup -n brain blkio.throttle.write_iops_device "8:0 15000"

# Set I/O weight (1000 for highest priority)
lxc-cgroup -n brain blkio.weight 1000
```

### 2. I/O Scheduler Selection

```bash
# CFQ (Complete Fair Queuing) for high-priority containers
echo cfq > /sys/block/sda/queue/scheduler

# Deadline for medium/low-priority containers
echo deadline > /sys/block/sda/queue/scheduler
```

## Container-Specific Configurations

See `lxc/security/security_io_config.json` for complete settings.

### Example: Applying to brain container

```bash
#!/bin/bash
CONTAINER="brain"
DEVICE="8:0"  # /dev/sda

# Read: 200M/s = 209715200 bytes/s
lxc-cgroup -n $CONTAINER blkio.throttle.read_bps_device "$DEVICE 209715200"

# Write: 150M/s = 157286400 bytes/s
lxc-cgroup -n $CONTAINER blkio.throttle.write_bps_device "$DEVICE 157286400"

# Read IOPS: 20000
lxc-cgroup -n $CONTAINER blkio.throttle.read_iops_device "$DEVICE 20000"

# Write IOPS: 15000
lxc-cgroup -n $CONTAINER blkio.throttle.write_iops_device "$DEVICE 15000"

# I/O weight: 1000 (highest)
lxc-cgroup -n $CONTAINER blkio.weight 1000

echo "✅ I/O limits applied to $CONTAINER"
```

## Monitoring I/O Usage

```bash
# Real-time I/O monitoring
iotop -o

# Container-specific I/O stats
lxc-cgroup -n <container> blkio.throttle.io_service_bytes

# ZFS I/O stats
zpool iostat -v 1
```

## Troubleshooting

### High I/O wait times

1. Check current limits:
```bash
lxc-cgroup -n <container> blkio.throttle.read_bps_device
lxc-cgroup -n <container> blkio.throttle.write_bps_device
```

2. Temporarily increase limits for testing:
```bash
lxc-cgroup -n <container> blkio.throttle.read_bps_device "8:0 400000000"
```

3. Monitor impact:
```bash
iotop -o -P
```

### I/O starvation for low-priority containers

Adjust blkio.weight to provide more bandwidth:

```bash
# Increase from 200 to 400
lxc-cgroup -n <container> blkio.weight 400
```

## Best Practices

1. **Start conservative**: Begin with lower limits and increase as needed
2. **Monitor regularly**: Use iotop and zpool iostat to track usage
3. **Balance priorities**: Ensure critical services (brain, fluence) have adequate bandwidth
4. **Test under load**: Simulate production workloads to validate limits
5. **Document changes**: Update `security_io_config.json` with any modifications

## References

- [Linux cgroup blkio Documentation](https://www.kernel.org/doc/Documentation/cgroup-v1/blkio-controller.txt)
- [I/O Schedulers Comparison](https://wiki.archlinux.org/title/Improving_performance#Input/output_schedulers)
