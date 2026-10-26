"""Respect CPU affinity and container quotas without changing inference quality."""
from __future__ import annotations

import os
from pathlib import Path


def _quota_limit(root=Path('/sys/fs/cgroup')):
    """Read common cgroup v2/v1 CPU quotas; absent files mean no known quota."""
    limits = []
    try:
        quota, period = (root / 'cpu.max').read_text().split()
        if quota != 'max' and int(quota) > 0 and int(period) > 0:
            limits.append(max(1, int(quota) // int(period)))
    except (OSError, ValueError):
        pass
    for folder in (root, root / 'cpu', root / 'cpu,cpuacct'):
        try:
            quota = int((folder / 'cpu.cfs_quota_us').read_text())
            period = int((folder / 'cpu.cfs_period_us').read_text())
            if quota > 0 and period > 0:
                limits.append(max(1, quota // period))
        except (OSError, ValueError):
            pass
    return min(limits) if limits else None


def cpu_thread_count():
    """Cap work at usable cores, including an explicit HMONG_CPU_THREADS value."""
    available = max(1, os.cpu_count() or 1)
    try:
        available = min(available, max(1, len(os.sched_getaffinity(0))))
    except (AttributeError, OSError):
        pass
    quota = _quota_limit()
    if quota is not None:
        available = min(available, quota)
    try:
        requested = int(os.getenv('HMONG_CPU_THREADS', '4'))
    except ValueError:
        requested = 4
    return max(1, min(requested, available))
