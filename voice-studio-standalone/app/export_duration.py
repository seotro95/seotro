"""Verify real decoded exports before marking a timed voice job complete."""
from pathlib import Path
import subprocess
import uuid
import wave

from timeline_audio import RATE, pcm_frames


def _wav_frames(path):
    expected = pcm_frames(path)
    actual = 0
    with wave.open(str(path), 'rb') as audio:
        while block := audio.readframes(65536):
            actual += len(block) // 2
    if actual != expected or actual <= 0:
        raise ValueError('Tệp voice rỗng hoặc thiếu mẫu âm thanh; hãy tạo lại bản thu.')
    return actual


def verify_audio_export(path, work, expected_frames=None):
    path, work = Path(path), Path(work)
    decoded = None
    try:
        if path.suffix.lower() == '.wav':
            frames = _wav_frames(path)
        else:
            decoded = work / ('verify-' + uuid.uuid4().hex + '.wav')
            subprocess.run([
                'ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
                '-vn', '-ac', '1', '-ar', str(RATE), '-codec:a', 'pcm_s16le',
                '-y', str(decoded),
            ], capture_output=True, check=True, timeout=600)
            frames = _wav_frames(decoded)
        error = frames - expected_frames if expected_frames is not None else None
        if error not in (None, 0):
            raise ValueError(
                f'File voice thực tế dài {frames/RATE:.6f}s, khác thời lượng đích '
                f'{expected_frames/RATE:.6f}s. Tool chưa công bố file; hãy tạo lại.'
            )
        return {'verified': True, 'measurement': 'decoded_pcm',
                'sample_rate': RATE, 'sample_frames': frames,
                'audio_seconds': frames/RATE,
                'target_seconds': expected_frames/RATE if expected_frames is not None else None,
                'error_frames': error}
    finally:
        if decoded is not None:
            decoded.unlink(missing_ok=True)
