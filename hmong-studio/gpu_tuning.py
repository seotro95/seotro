"""Persist only locally measured GPU precision choices for this model snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

BASE = Path(__file__).resolve().parent
REVISION = '5663e0df2589c2ca2403cd327a52702c3ff96e8f'
PRECISIONS = ('float32', 'float16')
SCHEMA = 1


def settings_path():
    return BASE / '.data' / 'runtime' / 'gpu-tuning.json'


def hardware_key(torch):
    if not torch.cuda.is_available():
        return None
    properties = torch.cuda.get_device_properties(torch.cuda.current_device())
    name = properties.name
    memory = properties.total_memory
    major, minor = properties.major, properties.minor
    if (not isinstance(name, str) or not name or len(name) > 256
            or isinstance(memory, bool) or not isinstance(memory, int) or memory <= 0
            or any(isinstance(n, bool) or not isinstance(n, int) or n < 0
                   for n in (major, minor))):
        raise ValueError('Thông tin GPU không hợp lệ; chưa lưu cấu hình tốc độ.')
    identity = {'name': name, 'total_memory': memory, 'capability': [major, minor],
                'torch': str(torch.__version__), 'cuda': str(torch.version.cuda)}
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def _measurements(results):
    if not isinstance(results, list) or not 1 <= len(results) <= 2:
        raise ValueError('Cần kết quả đo GPU thật trước khi lưu cấu hình.')
    measured = []
    seen = set()
    for result in results:
        if not isinstance(result, dict):
            raise ValueError('Kết quả đo GPU không hợp lệ.')
        precision = result.get('precision')
        elapsed, duration = result.get('elapsed_seconds'), result.get('speech_seconds')
        if (precision not in PRECISIONS or precision in seen
                or any(isinstance(n, bool) or not isinstance(n, (int, float))
                       or not math.isfinite(n) or n <= 0 for n in (elapsed, duration))):
            raise ValueError('Kết quả đo GPU không hợp lệ.')
        seen.add(precision)
        ratio = elapsed / duration
        if not math.isfinite(ratio) or ratio <= 0:
            raise ValueError('Tốc độ đo GPU không hợp lệ.')
        row = {'precision': precision, 'elapsed_seconds': float(elapsed),
               'speech_seconds': float(duration), 'real_time_factor': ratio}
        measured.append(row)
    return measured


def _winner(results):
    return min(results, key=lambda row: row['real_time_factor'])['precision']


def load_choice(path, torch):
    """Ignore stale/malformed settings; never infer a one-hour performance claim."""
    path = Path(path)
    try:
        key = hardware_key(torch)
        if key is None or path.stat().st_size > 64 * 1024:
            return None
        record = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(record, dict) or record.get('schema') != SCHEMA
                or record.get('revision') != REVISION or record.get('hardware') != key
                or record.get('precision') not in PRECISIONS):
            return None
        measurements = _measurements(record.get('results'))
        return record['precision'] if _winner(measurements) == record['precision'] else None
    except (OSError, ValueError, TypeError, AttributeError, RuntimeError):
        return None


def save_choice(path, torch, precision, results):
    measured = _measurements(results)
    key = hardware_key(torch)
    if key is None or precision not in PRECISIONS or precision != _winner(measured):
        raise ValueError('Chỉ lưu chế độ GPU có tốc độ tốt nhất đã đo thành công.')
    record = {'schema': SCHEMA, 'revision': REVISION, 'hardware': key,
              'precision': precision, 'results': measured,
              'created_at': datetime.now(timezone.utc).isoformat(),
              'one_hour_verified': False}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.gpu-tuning-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
