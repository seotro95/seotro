"""Small process-local WAV cache; it never writes scripts or samples to disk."""
from collections import OrderedDict


class RenderCache:
    def __init__(self, max_bytes=32 * 1024 * 1024, max_entries=128):
        self.max_bytes = max_bytes
        self.max_entries = max_entries
        self.owner = None
        self.entries = OrderedDict()
        self.bytes = 0

    def set_owner(self, owner):
        # Strong identity prevents object-id reuse and keeps different loaded
        # models (including replacement checkpoints) from sharing results.
        if self.owner is not owner:
            self.owner = owner
            self.entries.clear()
            self.bytes = 0

    def get(self, key):
        value = self.entries.get(key)
        if value is not None:
            self.entries.move_to_end(key)
        return value

    def put(self, key, value):
        if not isinstance(value, bytes) or len(value) > self.max_bytes:
            return
        previous = self.entries.pop(key, None)
        if previous is not None:
            self.bytes -= len(previous)
        self.entries[key] = value
        self.bytes += len(value)
        while self.bytes > self.max_bytes or len(self.entries) > self.max_entries:
            _, oldest = self.entries.popitem(last=False)
            self.bytes -= len(oldest)
