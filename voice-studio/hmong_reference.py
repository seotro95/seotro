"""Decode local uploads and select bounded voice reference recordings.

Only byte-identical project originals receive automatic cropping/text prefill.
The stored words are editable project metadata, not a verified transcription.
F5 recordings need the exact words of the selected interval. Native OpenVoice
uses audio for speaker identity and can accept any reference language without a
transcript. Neither path performs ASR or guesses reference words.
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
    """Bound decoding, then prevent float codec overshoot from clipping PCM16.

    MP3 reconstruction can exceed full scale. A single constant attenuation
    preserves its waveform before integer conversion; this does not repair an
    already clipped recording or change its pitch.
    """
    import numpy as np
    import soundfile as sf
    target = Path(target)
    floating = target.with_name(target.name + '.float.wav')
    try:
        result = subprocess.run([
            'ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe',
            '-i', str(source), '-t', '31', '-vn', '-ac', '1', '-ar', '24000',
            '-codec:a', 'pcm_f32le', '-y', str(floating),
        ], capture_output=True, timeout=45, check=False)
        if result.returncode or not floating.is_file():
            raise ReferenceError('Không đọc được âm thanh. Hãy dùng bản thu WAV/MP3 rõ tiếng.')
        samples, rate = sf.read(str(floating), dtype='float32')
        duration = len(samples) / rate
        if not 3 <= duration <= 30.001:
            raise ReferenceError('Mẫu gốc cần dài từ 3 đến 30 giây; chọn đoạn 3–8 giây để nhân bản Hmong.')
        if not np.isfinite(samples).all() or not np.any(np.abs(samples) > 0.0001):
            raise ReferenceError('Mẫu giọng chỉ có im lặng hoặc âm thanh không hợp lệ. Hãy thu lại lời nói rõ tiếng.')
        peak = float(np.max(np.abs(samples)))
        if peak > 1:
            samples *= .95 / peak
        sf.write(str(target), samples, rate, format='WAV', subtype='PCM_16')
        return duration
    except (RuntimeError, wave.Error, EOFError) as exc:
        raise ReferenceError('Không đọc được âm thanh. Hãy dùng bản thu WAV/MP3 rõ tiếng.') from exc
    finally:
        floating.unlink(missing_ok=True)


def known_source(content):
    from hmong_assets import all_references
    fingerprint = hashlib.sha256(content).hexdigest()
    for ident, item in all_references().items():
        if item.get('sha256') == fingerprint:
            return ident, item
    return None, None


def suggest_audio_reference(decoded, duration):
    """Find a bounded interval with signal energy, without recognizing speech.

    Energy cannot distinguish a speaker from music or background noise. The
    user can listen to and replace these suggested bounds before saving.
    """
    import numpy as np
    import soundfile as sf
    samples, rate = sf.read(str(decoded), dtype='float32', always_2d=True)
    samples = samples.mean(axis=1)
    actual = len(samples) / rate
    if (not np.isfinite(samples).all() or not 3 <= actual <= 30.001
            or not math.isfinite(duration) or abs(duration - actual) > .002):
        raise ReferenceError('Thời lượng hoặc tín hiệu mẫu không hợp lệ. Hãy chọn lại tệp âm thanh.')
    frame = max(1, round(rate * .02))
    padded = np.pad(samples, (0, (-len(samples)) % frame))
    energies = np.sqrt(np.mean(padded.reshape(-1, frame).astype('float64') ** 2, axis=1))
    peak = float(energies.max())
    if peak <= 1e-5:
        raise ReferenceError('Mẫu không có tín hiệu đủ rõ để chọn tự động. Chọn một đoạn có tiếng nói rõ hơn.')
    active = energies >= max(1e-5, peak * .08)
    # Reserve room for short padding. Count active frames, avoiding a single
    # loud transient deciding the entire interval through raw peak amplitude.
    width = min(len(active), max(1, int(7.7 * rate / frame)))
    counts = np.convolve(active.astype('int32'), np.ones(width, dtype='int32'), mode='valid')
    first = int(np.argmax(counts))
    chosen = np.flatnonzero(active[first:first + width]) + first
    if not len(chosen):
        raise ReferenceError('Không chọn được đoạn mẫu có tín hiệu. Hãy chọn mốc đoạn nói rõ lời.')
    start = max(0, chosen[0] * frame / rate - .12)
    end = min(actual, (chosen[-1] + 1) * frame / rate + .12)
    if end - start < 3:
        # Prefer extra context before the utterance to avoid a long silent
        # tail dominating the reference encoder's final recurrent state.
        start = max(0, end - 3)
        end = min(actual, max(end, start + 3))
    if end - start > 8:
        end = start + 8
    # Return sample-aligned times so preview and stored crop select the same
    # samples and cannot fail the 3-second lower bound through float rounding.
    start_frame, end_frame = round(start * rate), round(end * rate)
    if end_frame - start_frame < 3 * rate:
        start_frame = max(0, end_frame - 3 * rate)
        end_frame = min(len(samples), start_frame + 3 * rate)
    return {'start': start_frame / rate, 'end': end_frame / rate, 'text': ''}


def describe_reference(content, duration, *, require_transcript=True, decoded=None):
    preset, item = known_source(content)
    if item is not None and require_transcript and not item['reference'].get('text', '').strip():
        # Audio-only native presets do not supply invented words to F5.
        preset, item = None, None
    selected = item['reference'] if item else {'start': 0, 'end': min(duration, 8), 'text': ''}
    suggested = not require_transcript and item is None and decoded is not None
    if suggested:
        selected = suggest_audio_reference(decoded, duration)
    return {
        'duration': duration,
        'known_preset': preset,
        'reference_start': selected['start'],
        'reference_end': selected['end'],
        'transcript': selected['text'],
        'transcript_verified': bool(item and item.get('reference_text_verified', False)),
        'transcript_source': item.get('reference_text_source', 'project_prefill') if item else 'manual',
        'automatic': item is not None,
        'requires_transcript': item is None and require_transcript,
        'requires_selection': item is None and duration > 8.001 and not suggested,
        'automatic_selection': suggested or item is not None,
        'selection_source': 'verified_project_interval' if item else 'signal_energy' if suggested else 'manual',
        'reference_conditioning': 'audio_and_transcript' if require_transcript else 'audio',
        'cross_language_reference': not require_transcript,
    }


def select_reference(content, duration, transcript, start=None, end=None, *, require_transcript=True, decoded=None):
    """Resolve a crop and editable project prefill without replacing user words."""
    try:
        info = describe_reference(content, duration, require_transcript=require_transcript, decoded=decoded)
    except ReferenceError:
        if start is None or end is None:
            raise
        # A weak automatic energy estimate must not block an explicitly chosen
        # interval. The normal crop checks still validate the actual samples.
        info = describe_reference(content, duration, require_transcript=require_transcript)
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
        if not require_transcript and info['automatic_selection']:
            start, end = info['reference_start'], info['reference_end']
        elif duration > 8.001:
            detail = ' và nhập đúng lời của đoạn đã chọn' if require_transcript else ''
            raise ReferenceError('Mẫu dài hơn 8 giây. Chọn đoạn 3–8 giây, nghe lại' + detail + '.')
        else:
            start, end = 0.0, duration
    if (isinstance(start, bool) or isinstance(end, bool)
            or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
            or not math.isfinite(start) or not math.isfinite(end)
            or start < 0 or end > duration + 0.001 or not 3 <= end - start <= 8.001):
        raise ReferenceError('Đoạn mẫu cần dài 3–8 giây và nằm trong âm thanh gốc.')
    if not isinstance(transcript, str) or len(transcript) > 2000:
        raise ReferenceError('Lời mẫu cần là văn bản, tối đa 2.000 ký tự.')
    if require_transcript and not transcript.strip():
        raise ReferenceError('Nhập đúng lời Hmong của đoạn mẫu đã chọn; tool không tự đoán lời mẫu.')
    return {
        'source_sha256': hashlib.sha256(content).hexdigest(),
        'source_duration': duration,
        'reference_start': float(start),
        'reference_end': float(end),
        'transcript': transcript.strip(),
        'automatic_reference': automatic,
        'automatic_selection': info['automatic_selection'] and (start, end) == (info['reference_start'], info['reference_end']),
        'reference_selection_source': info['selection_source'],
        'known_preset': info['known_preset'],
        'reference_conditioning': info['reference_conditioning'],
        'cross_language_reference': info['cross_language_reference'],
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
