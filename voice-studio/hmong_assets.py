"""The two project-approved, transcribed Hmong reference clips."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'assets' / 'hmong'


def references():
    return json.loads((ROOT / 'voices.json').read_text(encoding='utf-8'))


def reference(ident):
    if ident not in {'hmong-female', 'hmong-male'}:
        raise ValueError('Không tìm thấy giọng Hmong mặc định.')
    item = references()[ident.removeprefix('hmong-')]
    path = ROOT / item['reference_file']
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['reference_sha256']:
        raise ValueError('Đoạn giọng mẫu không đạt kiểm tra SHA256; hãy giải nén lại gói đầy đủ.')
    return path, item['reference']['text']


def presets():
    return [
        {'id': 'hmong-' + gender, 'name': item['name'], 'engine': 'f5_hmong',
         'speaker': 'hmong-' + gender, 'languages': ['mww'],
         'description': 'F5-Hmong · mẫu và lời tham chiếu đã lưu trong dự án',
         'sample_url': '/api/hmong/presets/hmong-' + gender + '/sample'}
        for gender, item in references().items()
    ]
