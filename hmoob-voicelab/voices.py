"""Built-in reference recordings and independently saved reference transcripts."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

BASE = Path(__file__).resolve().parent


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         suffix='.pending', delete=False) as output:
            temporary = Path(output.name)
            json.dump(value, output, ensure_ascii=False)
            output.flush()
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class Voices:
    def __init__(self, data, assets=None):
        self.data = Path(data)
        self.assets = Path(assets or BASE / 'assets')
        self.metadata = json.loads((self.assets / 'voices.json').read_text(encoding='utf-8'))

    def sample(self, ident):
        if ident not in ('female', 'male'):
            raise ValueError('Không tìm thấy giọng mẫu.')
        return self.assets / self.metadata[ident]['file']

    def get(self, ident):
        self.sample(ident)
        record = self.metadata[ident]
        reference = {'start': 0, 'end': min(8, record['duration']), 'text': ''}
        path = self.data / 'references' / f'{ident}.json'
        if path.is_file():
            reference = self.validate(ident, json.loads(path.read_text(encoding='utf-8')))
        return {'id': ident, 'name': record['name'], 'duration': record['duration'],
                'sample_url': f'/api/voices/{ident}/sample', 'reference': reference,
                'reference_ready': bool(reference['text'].strip())}

    def all(self):
        return [self.get(ident) for ident in ('female', 'male')]

    def validate(self, ident, settings):
        self.sample(ident)
        if not isinstance(settings, dict):
            raise ValueError('Thiết lập mẫu không hợp lệ.')
        start, end, text = (settings.get(key) for key in ('start', 'end', 'text'))
        if (any(isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) for value in (start, end))
                or start < 0 or not 3 <= end - start <= 8
                or end > self.metadata[ident]['duration'] + .001):
            raise ValueError('Chọn đoạn rõ lời dài 3–8 giây nằm trong mẫu gốc.')
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            raise ValueError('Nhập đúng lời khớp đoạn mẫu, tối đa 2.000 ký tự.')
        try:
            text.encode('utf-8')
        except UnicodeError:
            raise ValueError('Lời mẫu chứa ký tự Unicode không hợp lệ.') from None
        return {'start': float(start), 'end': float(end), 'text': text.strip()}

    def save(self, ident, settings):
        value = self.validate(ident, settings)
        atomic_json(self.data / 'references' / f'{ident}.json', value)
        return self.get(ident)

    def snapshot(self, ident, destination):
        """Freeze audio and transcript together so later edits cannot alter a job."""
        voice = self.get(ident)
        reference = self.validate(ident, voice['reference'])
        source = self.sample(ident)
        if hashlib.sha256(source.read_bytes()).hexdigest() != self.metadata[ident]['sha256']:
            raise ValueError('Tệp giọng mẫu khác bản gốc. Kiểm tra hoặc khôi phục gói tool.')
        try:
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(reference['start']),
                            '-i', str(source), '-t', str(reference['end'] - reference['start']),
                            '-map', '0:a:0', '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le',
                            '-y', str(destination)], check=True, capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            raise ValueError('Không trích xuất được mẫu giọng. Kiểm tra FFmpeg và tệp gốc.') from None
        return reference
