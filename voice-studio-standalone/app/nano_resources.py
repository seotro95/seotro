"""Bound Nano processes and ONNX threads to resources this process can use."""
import math
import os
from pathlib import Path


MAX_NANO_WORKERS = 8
MAX_NANO_THREADS = 8
# A loaded Nano runtime includes Python, torch imports and ONNX scratch buffers.
# Keep headroom for the server, audio export and other desktop applications.
NANO_WORKER_BYTES = 1024 ** 3
RESERVED_BYTES = 768 * 1024 ** 2


def cpu_budget():
    count = getattr(os, 'process_cpu_count', os.cpu_count)() or 1
    try:
        count = min(count, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    try:
        quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()
        if quota != 'max':
            count = min(count, max(1, math.floor(int(quota) / int(period))))
    except (OSError, ValueError, ZeroDivisionError):
        pass
    return max(1, count)


def available_memory():
    available = None
    try:
        import psutil
        available = psutil.virtual_memory().available
    except ImportError:
        pass
    try:
        maximum = Path('/sys/fs/cgroup/memory.max').read_text().strip()
        if maximum != 'max':
            remaining = max(0, int(maximum) - int(Path('/sys/fs/cgroup/memory.current').read_text()))
            available = remaining if available is None else min(available, remaining)
    except (OSError, ValueError):
        pass
    return available


def resource_policy(*, cpus=None, memory=None):
    cpus = cpu_budget() if cpus is None else max(1, cpus)
    memory = available_memory() if memory is None else memory
    memory_workers = 2 if memory is None else max(1, (memory - RESERVED_BYTES) // NANO_WORKER_BYTES)
    maximum = max(1, min(MAX_NANO_WORKERS, cpus, memory_workers))
    return {'cpu_budget': cpus, 'available_memory_bytes': memory, 'max_workers': maximum,
            'recommended_workers': maximum, 'recommended_threads': 1}


def nano_resources(workers=0, threads=0, *, cpus=None, memory=None):
    """0 workers selects automatic concurrency; explicit requests remain bounded."""
    policy = resource_policy(cpus=cpus, memory=memory)
    cpus = policy['cpu_budget']
    threads = int(threads)
    threads = max(1, min(MAX_NANO_THREADS, threads if threads > 0 else policy['recommended_threads'], cpus))
    cpu_workers = max(1, cpus // threads)
    limit = min(policy['max_workers'], cpu_workers)
    requested = int(workers)
    selected = limit if requested <= 0 else min(requested, limit)
    return {**policy, 'workers': max(1, selected), 'threads': threads}


def resolve_nano_settings(job):
    """Keep old explicit choices, resolve 0/auto and enforce runtime bounds."""
    if job.get('engine') != 'vieneu_nano':
        return dict(job)
    requested_workers = int(job.get('nano_requested_parallel', job.get('nano_parallel', 1)))
    requested_threads = int(job.get('nano_requested_threads', job.get('nano_threads', 2)))
    resources = nano_resources(requested_workers, requested_threads)
    return {**job, 'nano_parallel': resources['workers'], 'nano_threads': resources['threads'],
            'nano_requested_parallel': requested_workers, 'nano_requested_threads': requested_threads,
            'nano_resources': resources}
