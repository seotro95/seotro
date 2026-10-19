"""Local reference library. A reference is not a trained voice model."""
from pathlib import Path
from datetime import datetime, timezone
import io
import json
import os
import re
import subprocess
import tempfile
import uuid
import wave
from fastapi import HTTPException

DATA = Path(os.getenv('HMONG_STUDIO_DATA_DIR', str(Path(__file__).parent / '.data'))) / 'clones'


def _directory(voice_id):
    if not re.fullmatch(r'custom-[0-9a-f]{32}', voice_id):
        raise HTTPException(404, 'Không tìm thấy mẫu giọng.')
    return DATA / voice_id


def get(voice_id):
    folder = _directory(voice_id)
    try:
        return json.loads((folder / 'voice.json').read_text(encoding='utf-8')), folder / 'reference.wav'
    except (OSError, ValueError):
        raise HTTPException(404, 'Không tìm thấy mẫu giọng.') from None


def list_voices():
    if not DATA.exists():
        return []
    result = []
    for folder in sorted(DATA.glob('custom-*')):
        try:
            meta, _ = get(folder.name)
            result.append(meta)
        except HTTPException:
            continue
    return result


def create(raw, name, transcript):
    name, transcript = name.strip(), transcript.strip()
    if not name or not transcript:
        raise HTTPException(422, 'Nhập tên giọng và bản chép đúng lời trong mẫu.')
    if not raw:
        raise HTTPException(422, 'Chọn tệp âm thanh trước.')
    try:
        # Pipe-only input prevents media references from opening local files or URLs.
        process = subprocess.run(['ffmpeg', '-v', 'error', '-protocol_whitelist', 'pipe',
            '-i', 'pipe:0', '-t', '61', '-ac', '1', '-ar', '24000', '-f', 'wav', 'pipe:1'],
            input=raw, capture_output=True, timeout=30, check=True)
        with wave.open(io.BytesIO(process.stdout), 'rb') as wav:
            frames = wav.readframes(61 * 24000)
        duration = len(frames) / 48000
        if not 3 <= duration <= 60:
            raise HTTPException(422, 'Mẫu giọng cần dài từ 3 đến 60 giây.')
        import array
        samples = array.array('h', frames)
        if not samples or max(abs(x) for x in samples) < 32:
            raise HTTPException(422, 'Mẫu gần như im lặng. Chọn bản thu có tiếng nói rõ.')
    except (subprocess.SubprocessError, OSError, wave.Error, EOFError):
        raise HTTPException(422, 'Không đọc được mẫu. Cần FFmpeg và tệp WAV/MP3/M4A hợp lệ.') from None
    DATA.mkdir(parents=True, exist_ok=True)
    voice_id = 'custom-' + uuid.uuid4().hex
    metadata = {'id': voice_id, 'name': name, 'transcript': transcript, 'dialect': 'mww',
                'duration': round(duration, 3), 'consent_at': datetime.now(timezone.utc).isoformat(),
                'reference': f'/api/clones/{voice_id}/sample'}
    with tempfile.TemporaryDirectory(dir=DATA) as temp:
        folder = Path(temp)
        with wave.open(str(folder / 'reference.wav'), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(frames)
        (folder / 'voice.json').write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
        # Publish only a complete pair; the temporary directory is then cleaned up.
        target = DATA / voice_id
        target.mkdir()
        (folder / 'reference.wav').replace(target / 'reference.wav')
        (folder / 'voice.json').replace(target / 'voice.json')
    return metadata


def delete(voice_id):
    get(voice_id)
    folder = _directory(voice_id)
    (folder / 'voice.json').unlink(missing_ok=True)
    (folder / 'reference.wav').unlink(missing_ok=True)
    folder.rmdir()
