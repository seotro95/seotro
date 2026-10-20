"""Bounded mono PCM files; never assemble a whole document in memory."""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import sys
import wave

MAX_CHUNK_SECONDS = 180
PART_SECONDS = 30 * 60


def inspect_wav(path):
    with wave.open(str(path), 'rb') as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise ValueError('Đoạn âm thanh phải là WAV mono PCM 16-bit.')
        rate, frames = source.getframerate(), source.getnframes()
        if not 8000 <= rate <= 96000 or not frames:
            raise ValueError('Đoạn âm thanh rỗng hoặc sai tần số.')
        if Path(path).stat().st_size < 44 + frames * 2:
            raise ValueError('Đoạn âm thanh lưu chưa đầy đủ.')
        return frames, rate


def write_samples(path, samples, rate):
    if isinstance(rate, bool) or not isinstance(rate, int) or not 8000 <= rate <= 96000:
        raise ValueError('Mô hình trả tần số lấy mẫu không hợp lệ.')
    if not 0 < len(samples) <= MAX_CHUNK_SECONDS * rate:
        raise ValueError('Đoạn âm thanh rỗng hoặc dài bất thường; chưa có bản đọc hoàn tất.')
    # Only one short model result is materialized at a time.
    pcm, peak = array('h'), 0.0
    for value in samples:
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('Mô hình trả mẫu âm thanh không hợp lệ.')
        peak = max(peak, abs(value))
        pcm.append(round(max(-1, min(1, value)) * 32767))
    if peak < 1e-6:
        raise ValueError('Mô hình chỉ tạo im lặng. Kiểm tra lời và mẫu giọng.')
    if sys.byteorder != 'little':
        pcm.byteswap()
    path = Path(path)
    temporary = path.with_suffix('.pending')
    try:
        with wave.open(str(temporary), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(pcm.tobytes())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return len(pcm), rate


def assemble(paths, destination):
    """Stream a chapter from short checkpoints, checking every frame."""
    destination = Path(destination)
    temporary = destination.with_suffix('.pending')
    frames, rate = 0, None
    try:
        with wave.open(str(temporary), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            for path in paths:
                count, current_rate = inspect_wav(path)
                if rate is None:
                    rate = current_rate
                    output.setframerate(rate)
                elif rate != current_rate:
                    raise ValueError('Mô hình đổi tần số lấy mẫu giữa các đoạn.')
                with wave.open(str(path), 'rb') as source:
                    remaining = count
                    while remaining:
                        block = source.readframes(min(32768, remaining))
                        if not block:
                            raise ValueError('Đoạn âm thanh bị thiếu dữ liệu.')
                        output.writeframesraw(block)
                        remaining -= len(block) // 2
                frames += count
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return frames / rate
