"""Language-independent duration fitting and verification of decoded audio."""
import math
import subprocess
import uuid
import wave
from pathlib import Path

from narration import MAX_SECONDS, PCMWriter

RATE = 24000


def target_frames(seconds):
    if not math.isfinite(seconds) or not 0 < seconds <= MAX_SECONDS:
        raise ValueError('Thời lượng đích phải lớn hơn 0 và không quá 180 phút.')
    frames = round(seconds * RATE)
    if frames < 1:
        raise ValueError('Thời lượng đích quá ngắn để tạo âm thanh.')
    return frames


def pcm_frames(path):
    with wave.open(str(path), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, RATE):
            raise ValueError('Âm thanh cần là PCM mono 24 kHz, 16 bit.')
        return audio.getnframes()


def expected_duration(job, cues=None):
    if cues and job.get('cue_fit', 'strict') == 'strict':
        return cues[-1]['end']
    return job.get('target_seconds') if not cues else None


def fit_target(source, destination, seconds, maximum_tempo, normalize, work):
    """Refit the original PCM; pad silence, and never trim speech to fit."""
    frames = target_frames(seconds)
    original = pcm_frames(source)
    if not original:
        raise ValueError('Chưa có âm thanh để căn thời lượng.')
    ratio = original / frames
    if ratio > maximum_tempo + 1e-9:
        raise ValueError(
            f'TXT đọc dài {original/RATE:.2f}s cho thời lượng đích {seconds:.2f}s; '
            f'cần tăng tốc {ratio:.2f}×, vượt mức {maximum_tempo:.2f}×. '
            'Tăng thời lượng đích hoặc sửa lời; tool không cắt mất nội dung.'
        )
    # Avoid unnaturally stretching a short script across a long target.
    # Remaining time is silence. Explicit controls and all text stay in order.
    tempo = max(0.7, ratio)
    fitted = Path(work) / 'target-fit.wav'
    speech = source
    speech_frames = original
    if abs(tempo - 1) > 1e-9:
        for attempt in range(6):
            if (Path(work) / 'cancel.flag').exists():
                raise InterruptedError('Tác vụ đã dừng.')
            normalize(source, fitted, tempo, 1)
            speech_frames = pcm_frames(fitted)
            if 0 < speech_frames <= frames:
                speech = fitted
                break
            if not speech_frames or tempo >= maximum_tempo or attempt == 5:
                raise ValueError(
                    'Không căn được TXT vào thời lượng đích ở tốc độ cho phép. '
                    'Tăng thời lượng hoặc sửa lời; tool không cắt âm thanh.'
                )
            # Always transform the original; do not compound pitch/time changes.
            tempo = min(maximum_tempo, tempo * (speech_frames + 48) / frames)
        else:
            raise ValueError('Không căn được thời lượng TXT.')
    if speech_frames > frames:
        raise ValueError('Voice vượt thời lượng đích; không cắt mất lời.')
    writer = PCMWriter(destination, max_seconds=frames/RATE, strict=True)
    try:
        writer.append(speech)
        writer.silence((frames-writer.frames)/RATE)
    finally:
        writer.close()
    if pcm_frames(destination) != frames:
        raise ValueError('Âm thanh chưa khớp thời lượng đích.')
    return {
        'raw_seconds': original/RATE,
        'tempo': tempo,
        'timing_scale': speech_frames/original,
        'padding_seconds': (frames-speech_frames)/RATE,
    }


def verify_export(path, work, expected_seconds=None):
    """Measure the actual file, honoring MP3 gapless delay/padding when decoding."""
    path = Path(path)
    decoded = None
    try:
        if path.suffix.lower() == '.wav':
            frames = pcm_frames(path)
        else:
            decoded = Path(work) / f'verify-{uuid.uuid4().hex}.wav'
            subprocess.run([
                'ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
                '-vn', '-ac', '1', '-ar', str(RATE), '-codec:a', 'pcm_s16le',
                '-y', str(decoded),
            ], check=True, timeout=600, capture_output=True)
            frames = pcm_frames(decoded)
        if frames <= 0:
            raise ValueError('Tệp voice xuất ra không có âm thanh.')
        expected = target_frames(expected_seconds) if expected_seconds is not None else None
        error = frames-expected if expected is not None else None
        if error not in (None, 0):
            raise ValueError(
                f'Tệp voice thực tế dài {frames/RATE:.6f}s, '
                f'chưa khớp thời lượng đích {expected/RATE:.6f}s. '
                'Tệp chưa được công bố; hãy tạo lại voice.'
            )
        return {
            'audio_seconds': frames/RATE,
            'sample_frames': frames,
            'sample_rate': RATE,
            'expected_seconds': expected/RATE if expected is not None else None,
            'error_frames': error,
            'verified': True,
            'measurement': 'decoded_pcm',
        }
    finally:
        if decoded is not None:
            decoded.unlink(missing_ok=True)
