"""Advisory signal measurements for an unchanged, normalized voice reference.

Energy does not distinguish speech from music, noise, or another speaker. These
measurements cannot verify a transcript, pronunciation, or a cloned identity.
"""
from __future__ import annotations

import array
import math
import sys
import wave


GUIDANCE = (
    'Chọn đoạn 3–8 giây có một người nói rõ, tự nhiên; tránh nhạc nền và tiếng vọng.',
    'Nghe lại đoạn đã chọn và nhập đúng toàn bộ lời Hmong của đoạn đó.',
    'Dùng bản thu không méo tiếng; không cần tự tăng âm lượng hoặc khử nhiễu.',
)
ANALYSIS_NOTE = ('Các số đo chỉ mô tả tín hiệu âm thanh, không xác nhận có tiếng nói, '
                 'đúng lời hay mức độ giống giọng.')


def _dbfs(amplitude):
    return round(20 * math.log10(amplitude), 2) if amplitude > 0 else None


def analyze_reference(path):
    """Measure mono PCM16/24k WAV without editing it or rejecting weak audio.

    Quiet/active audio uses 20 ms RMS windows and a fixed -45 dBFS threshold.
    Full-scale samples can indicate clipping; they do not prove distortion.
    Invalid or truncated normalized WAV data raises ValueError.
    """
    try:
        with wave.open(str(path), 'rb') as audio:
            rate, count = audio.getframerate(), audio.getnframes()
            if (audio.getnchannels() != 1 or audio.getsampwidth() != 2
                    or rate != 24000 or not 0 < count <= 30.001 * rate):
                raise ValueError('Đo chất lượng cần WAV mono PCM 16-bit, 24.000 Hz, tối đa 30 giây.')
            content = audio.readframes(count)
            if len(content) != count * 2:
                raise ValueError('Không đủ dữ liệu âm thanh của đoạn giọng mẫu.')
    except (OSError, wave.Error, EOFError) as exc:
        raise ValueError('Không đọc được WAV để kiểm tra đoạn giọng mẫu.') from exc

    samples = array.array('h')
    samples.frombytes(content)
    if sys.byteorder != 'little':
        samples.byteswap()
    energy = sum(float(sample) ** 2 for sample in samples)
    rms = math.sqrt(energy / count) / 32768
    peak = max(abs(sample) for sample in samples) / 32768
    clipped = sum(sample >= 32767 or sample <= -32768 for sample in samples)
    quiet_count = 0
    frame_size = rate // 50
    quiet_energy = (32768 * 10 ** (-45 / 20)) ** 2
    for start in range(0, count, frame_size):
        frame = samples[start:start + frame_size]
        if sum(float(sample) ** 2 for sample in frame) / len(frame) < quiet_energy:
            quiet_count += len(frame)

    quiet_fraction = quiet_count / count
    clipped_ratio = clipped / count
    advisories = []
    if clipped_ratio >= .001:
        advisories.append('Nhiều mẫu chạm mức âm lượng tối đa; nếu nghe rè hoặc vỡ tiếng, hãy thu lại nhỏ tiếng hơn.')
    if rms < 10 ** (-35 / 20):
        advisories.append('Âm lượng bản thu thấp; nên thu lại gần micro hơn ở nơi yên tĩnh.')
    if quiet_fraction > .4:
        advisories.append('Đoạn mẫu có nhiều khoảng âm lượng thấp; chọn đoạn nói liền mạch hơn để giữ rõ đặc trưng giọng.')
    return {
        'duration_seconds': round(count / rate, 3),
        'active_audio_seconds': round((count - quiet_count) / rate, 3),
        'quiet_fraction': round(quiet_fraction, 6),
        'peak_dbfs': _dbfs(peak),
        'rms_dbfs': _dbfs(rms),
        'clipped_sample_ratio': round(clipped_ratio, 6),
        'attention_recommended': bool(advisories),
        'advisories': advisories,
        'guidance': list(GUIDANCE),
        'analysis_note': ANALYSIS_NOTE,
    }
