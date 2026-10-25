"""The supplied Hmong recordings and user-provided excerpt words."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'assets' / 'hmong'
HMONG_ENGINES = frozenset({'f5_hmong', 'hmong_native'})


def active_engine():
    """Choose new renders only; saved jobs retain their recorded engine."""
    backend = os.getenv('HMOOB_BACKEND', 'f5').lower()
    if backend not in {'f5', 'native'}:
        raise ValueError('HMOOB_BACKEND chỉ nhận f5 hoặc native.')
    return 'hmong_native' if backend == 'native' else 'f5_hmong'


def references():
    return json.loads((ROOT / 'voices.json').read_text(encoding='utf-8'))


def all_references():
    """Resolve canonical preset IDs, keeping the two original metadata keys stable."""
    result = {'hmong-' + gender: item for gender, item in references().items()}
    extra = ROOT / 'additional-voices.json'
    if extra.is_file():
        result.update(json.loads(extra.read_text(encoding='utf-8')))
    return result


def is_builtin_voice_id(ident):
    return isinstance(ident, str) and ident in all_references()


def reference_text_required(ident, engine):
    """Only the original verified presets require words in native audio mode."""
    return engine != 'hmong_native' or ident in {'hmong-male', 'hmong-female'}


def default_preset_id(engine=None):
    engine = engine or active_engine()
    return ('hmong-female-3' if engine == 'hmong_native'
            and is_builtin_voice_id('hmong-female-3') else 'hmong-male')


def reference(ident):
    if not is_builtin_voice_id(ident):
        raise ValueError('Không tìm thấy giọng Hmong mặc định.')
    item = all_references()[ident]
    path = ROOT / item['reference_file']
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['reference_sha256']:
        raise ValueError('Đoạn giọng mẫu không đạt kiểm tra SHA256; hãy giải nén lại gói đầy đủ.')
    return path, item['reference']['text']


def reference_fingerprint(ident):
    """Bind resumable preset jobs to verified audio and the exact given words."""
    path, text = reference(ident)
    identity = {'version': 1, 'audio_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'transcript': text}
    payload = json.dumps(identity, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def source(ident):
    if not is_builtin_voice_id(ident):
        raise ValueError('Không tìm thấy giọng Hmong mặc định.')
    item = all_references()[ident]
    path = ROOT / item['file']
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('Tệp MP3 gốc không đạt SHA256; hãy giải nén lại bản đầy đủ.')
    return path


def presets():
    return [
        {'id': 'hmong-' + gender, 'name': item['name'], 'engine': active_engine(),
         'speaker': 'hmong-' + gender, 'languages': ['mww'],
         'description': 'Mẫu của bạn · ' + item['user_filename'] + ' · lời mẫu do bạn cung cấp',
         'source_filename': item['user_filename'], 'source_sha256': item['sha256'],
         'reference_text_verified': bool(item.get('reference_text_verified', False)),
         'sample_url': '/api/hmong/presets/hmong-' + gender + '/sample'}
        for gender in ('male', 'female')
        for item in [references()[gender]]
    ] + ([
        {'id': ident, 'name': item['name'], 'engine': 'hmong_native',
         'speaker': ident, 'languages': ['mww'], 'builtin': True,
         'category': 'preset', 'description': 'Mẫu của bạn · ' + item['user_filename'] + ' · lấy chất giọng từ âm thanh',
         'source_filename': item['user_filename'], 'source_sha256': item['sha256'],
         'reference_text_verified': False, 'reference_conditioning': 'audio',
         'requires_transcript': False,
         'sample_url': '/api/hmong/presets/' + ident + '/sample'}
        for ident, item in all_references().items()
        if ident not in {'hmong-male', 'hmong-female'}
    ] if active_engine() == 'hmong_native' else [])
