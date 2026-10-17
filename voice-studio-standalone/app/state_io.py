"""Atomic JSON snapshots with bounded retry for Windows sharing locks."""
import json
import os
from pathlib import Path
import tempfile
import time


def write_json_atomic(path, data, *, best_effort=False):
    """Progress may be skipped; project, result and job records must be durable."""
    path=Path(path)
    payload=json.dumps(data,ensure_ascii=False)
    temporary=None
    try:
        fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
        temporary=Path(name)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            stream.write(payload)
        attempts=8 if best_effort else 12
        for attempt in range(attempts):
            try:
                temporary.replace(path)
                return True
            except PermissionError:
                if attempt==attempts-1:raise
                time.sleep(min(.01*2**attempt,.08))
    except OSError:
        if not best_effort:raise
        return False
    finally:
        if temporary is not None:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass


def write_progress(path, data):
    return write_json_atomic(path,data,best_effort=True)


def read_progress(path):
    try:
        value=json.loads(Path(path).read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):
        return {}
