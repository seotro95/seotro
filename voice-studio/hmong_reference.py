"""Decode local uploads and pair bounded Hmong references with their exact words.

Only byte-identical project originals receive automatic cropping/text prefill.
The stored words are editable project metadata, not a verified transcription.
Other recordings need the user's transcript of the selected interval; no ASR or
text guessing is performed here.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import subprocess
import wave

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
AUDIO_SUFFIXES = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm'}


class ReferenceError(ValueError):
    pass


def validate_upload(filename, content):
    if Path(filename or '').suffix.lower() not in AUDIO_SUFFIXES:
        raise ReferenceError('Chọn tệp MP3, WAV, M4A, FLAC, OGG hoặc WEBM.')
    if not content:
        raise ReferenceError('Mẫu âm thanh chưa có dữ liệu.')
    if len(content) > MAX_UPLOAD_BYTES:
        raise ReferenceError('Mẫu không được vượt quá 20 MB.')


def decode_upload(source, target):
    """Bound decoding to 31 seconds, sufficient to reject originals over 30 s."""
    result = subprocess.run([
        'ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-i', str(source), '-t', '31', '-vn', '-ac', '1', '-ar', '24000',
        '-codec:a', 'pcm_s16le', '-y', str(target),
    ], capture_output=True, timeout=45, check=False)
    if result.returncode or not Path(target).is_file():
        raise ReferenceError('Không đọc được âm thanh. Hãy dùng bản thu WAV/MP3 rõ tiếng.')
    try:
        with wave.open(str(target), 'rb') as audio:
            duration = audio.getnframes() / audio.getframerate()
        if not 3 <= duration <= 30.001:
            raise ReferenceError('Mẫu gốc cần dài từ 3 đến 30 giây; chọn đoạn 3–8 giây để nhân bản Hmong.')
        import numpy as np
        import soundfile as sf
        samples, _ = sf.read(str(target), dtype='float32')
        if not np.isfinite(samples).all() or not np.any(np.abs(samples) > 0.0001):
            raise ReferenceError('Mẫu giọng chỉ có im lặng hoặc âm thanh không hợp lệ. Hãy thu lại lời nói rõ tiếng.')
        return duration
    except (wave.Error, EOFError) as exc:
        raise ReferenceError('Không đọc được âm thanh. Hãy dùng bản thu WAV/MP3 rõ tiếng.') from exc


def known_source(content):
    from hmong_assets import references
    fingerprint = hashlib.sha256(content).hexdigest()
    for gender, item in references().items():
        if item.get('sha256') == fingerprint:
            return 'hmong-' + gender, item
    return None, None


def describe_reference(content, duration):
    preset, item = known_source(content)
    selected = item['reference'] if item else {'start': 0, 'end': min(duration, 8), 'text': ''}
    return {
        'duration': duration,
        'known_preset': preset,
        'reference_start': selected['start'],
        'reference_end': selected['end'],
        'transcript': selected['text'],
        'transcript_verified': False,
        'transcript_source': 'project_prefill' if item else 'manual',
        'automatic': item is not None,
        'requires_transcript': item is None,
        'requires_selection': item is None and duration > 8.001,
    }


def select_reference(content, duration, transcript, start=None, end=None):
    """Resolve a crop and editable project prefill without replacing user words."""
    info = describe_reference(content, duration)
    exact_known_interval = (info['automatic'] and not isinstance(start, bool) and not isinstance(end, bool)
                            and start == info['reference_start'] and end == info['reference_end'])
    known_interval = info['automatic'] and ((start is None and end is None) or exact_known_interval)
    automatic = (known_interval and isinstance(transcript, str)
                 and transcript.strip() in {'', info['transcript']})
    if (start is None) != (end is None):
        raise ReferenceError('Chọn đủ mốc bắt đầu và kết thúc của đoạn giọng mẫu.')
    if known_interval:
        start, end = info['reference_start'], info['reference_end']
        if automatic:
            transcript = info['transcript']
    elif start is None:
        if duration > 8.001:
            raise ReferenceError('Mẫu dài hơn 8 giây. Chọn đoạn 3–8 giây, nghe lại và nhập đúng lời của đoạn đã chọn.')
        start, end = 0.0, duration
    if (isinstance(start, bool) or isinstance(end, bool)
            or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
            or not math.isfinite(start) or not math.isfinite(end)
            or start < 0 or end > duration + 0.001 or not 3 <= end - start <= 8.001):
        raise ReferenceError('Đoạn mẫu cần dài 3–8 giây và nằm trong âm thanh gốc.')
    if not isinstance(transcript, str) or not transcript.strip():
        raise ReferenceError('Nhập đúng lời Hmong của đoạn mẫu đã chọn; tool không tự đoán lời mẫu.')
    return {
        'source_sha256': hashlib.sha256(content).hexdigest(),
        'source_duration': duration,
        'reference_start': float(start),
        'reference_end': float(end),
        'transcript': transcript.strip(),
        'automatic_reference': automatic,
        'known_preset': info['known_preset'],
    }


def crop_reference(decoded, target, start, end):
    """Crop normalized PCM without another encoder or a lost audio generation."""
    with wave.open(str(decoded), 'rb') as source:
        rate = source.getframerate()
        source.setpos(round(start * rate))
        expected_frames = round(end * rate) - round(start * rate)
        content = source.readframes(expected_frames)
        if len(content) != expected_frames * 2:
            raise ReferenceError('Đoạn chọn vượt âm thanh thực tế; chọn lại mốc kết thúc.')
    with wave.open(str(target), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(content)
    # Validate the actual selected interval, not just the full original.
    import numpy as np
    samples = np.frombuffer(content, dtype='<i2')
    if not np.any(np.abs(samples.astype('int32')) > 3):
        Path(target).unlink(missing_ok=True)
        raise ReferenceError('Đoạn đã chọn chỉ có im lặng. Chọn đoạn có một người nói rõ lời.')
    return expected_frames / rate
