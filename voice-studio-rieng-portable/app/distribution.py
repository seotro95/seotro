"""Non-secret package profile; absent on existing full installations."""
import json
from pathlib import Path


def distribution_profile(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent.parent
    try:
        path = root / 'DISTRIBUTION.json'
        if path.stat().st_size > 4096:
            return 'standard'
        record = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(record, dict) and type(record.get('schema')) is int and record['schema'] == 1:
            if record.get('profile') == 'compact-19':
                return 'compact-19'
    except (OSError, ValueError, UnicodeError):
        pass
    return 'standard'
