"""Keep each default voice's transcript and normalized audio together."""
from pathlib import Path
import json
import math
import os
import re
import tempfile
import uuid

from fastapi import HTTPException
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
VOICE_IDS = ('hmong-white-female', 'hmong-white-male')


class ReferenceSettings(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)


def directory():
    return Path(os.getenv('HMONG_STUDIO_DATA_DIR', str(BASE / '.data'))) / 'references'


def original(voice):
    if voice not in VOICE_IDS:
        raise HTTPException(404, 'Không tìm thấy mẫu giọng nam/nữ.')
    return BASE / 'static' / 'voices' / f'{voice}.mp3'


def _duration(path):
    try:
        import soundfile
        info = soundfile.info(str(path))
        duration = info.frames / info.samplerate
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('duration')
        return duration
    except (ImportError, OSError, RuntimeError, ValueError, ZeroDivisionError):
        raise HTTPException(503, 'Không đọc được mẫu giọng. Mở lại MO_HMONG_NHANH.bat để cài thư viện âm thanh và kiểm tra tệp MP3 gốc.') from None


def _extract(source, destination, start, end):
    """Decode the packaged MP3 with libsndfile; no external FFmpeg install needed."""
    try:
        import numpy as np
        import soundfile
        from scipy.signal import resample_poly
        with soundfile.SoundFile(str(source)) as audio:
            rate = audio.samplerate
            first, last = round(start * rate), round(end * rate)
            audio.seek(first)
            samples = audio.read(last - first, dtype='float32', always_2d=True)
        if not samples.size or not np.isfinite(samples).all():
            raise ValueError('invalid sample')
        mono = samples.mean(axis=1)
        if rate != 24000:
            factor = math.gcd(rate, 24000)
            mono = resample_poly(mono, 24000 // factor, rate // factor)
        soundfile.write(str(destination), mono, 24000, subtype='PCM_16', format='WAV')
    except (ImportError, OSError, RuntimeError, ValueError):
        raise HTTPException(503, 'Không trích xuất được đoạn mẫu. Mở lại MO_HMONG_NHANH.bat để kiểm tra thư viện và chọn lại đoạn giọng.') from None


def settings(voice):
    duration = _duration(original(voice))
    default = {'text': '', 'start': 0, 'end': min(8, duration), 'duration': duration}
    try:
        saved = json.loads((directory() / f'{voice}.json').read_text(encoding='utf-8'))
        selection = ReferenceSettings.model_validate(saved)
        filename = saved.get('sample', '')
        if (not selection.text.strip() or not 3 <= selection.end - selection.start <= 8
                or selection.end > duration or not isinstance(filename, str)
                or not re.fullmatch(re.escape(voice) + r'-[0-9a-f]{32}\.wav', filename)
                or not (directory() / filename).is_file()):
            return default
        return {**selection.model_dump(), 'duration': duration, 'sample': filename}
    except (OSError, ValueError, TypeError):
        return default


def save(voice, selection):
    duration = _duration(original(voice))
    if (not selection.text.strip() or not 3 <= selection.end - selection.start <= 8
            or selection.end > duration):
        raise HTTPException(422, 'Chọn đoạn mẫu dài 3–8 giây trong bản gốc và nhập đúng lời của đoạn này.')
    root = directory()
    root.mkdir(parents=True, exist_ok=True)
    filename = f'{voice}-{uuid.uuid4().hex}.wav'
    destination = root / filename
    # Publish metadata last. Workers always read a complete, immutable audio/transcript pair.
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        sample = Path(temporary) / 'reference.wav'
        _extract(original(voice), sample, selection.start, selection.end)
        from cloning_engine import _validate_reference, CloningError
        try:
            _validate_reference(sample)
        except CloningError as exc:
            raise HTTPException(422, str(exc)) from None
        data = {**selection.model_dump(), 'text': selection.text.strip(), 'sample': filename}
        metadata = Path(temporary) / 'settings.json'
        metadata.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        sample.replace(destination)
        metadata.replace(root / f'{voice}.json')
    return {**data, 'duration': duration}


def selected(voice):
    saved = settings(voice)
    if not saved['text'].strip() or not saved.get('sample'):
        raise HTTPException(422, 'Chọn đoạn 3–8 giây, nhập và lưu đúng lời mẫu của giọng đang chọn trước khi tạo voice.')
    return directory() / saved['sample'], saved['text']
