"""Pitch-preserving fitting and bounded WAV timeline output for subtitle cues."""
from __future__ import annotations

import io
from pathlib import Path
import shutil
import wave

RATE = 24000
BLOCK_FRAMES = 65536
RESERVE_BYTES = 100 * 1024 * 1024


def fit_wav(audio, target_frames, cue_number, max_speed=2):
    """Fit every generated sample to a cue, never truncate spoken content."""
    with wave.open(io.BytesIO(audio), 'rb') as source:
        frames = source.getnframes()
        if (source.getnchannels() != 1 or source.getsampwidth() != 2
                or source.getframerate() != RATE or frames <= 0):
            raise ValueError('Bộ tạo giọng trả WAV không hợp lệ.')
        raw = source.readframes(frames)
        if len(raw) != frames * 2:
            raise ValueError('Bộ tạo giọng trả WAV chưa đầy đủ.')
    if type(target_frames) is not int or target_frames <= 0:
        raise ValueError(f'Phụ đề {cue_number} có khoảng thời gian quá ngắn.')
    if max_speed not in (2, 4):
        raise ValueError('Giới hạn căn nhịp phải là 2 hoặc 4 lần.')
    ratio = frames / target_frames
    if not .5 <= ratio <= max_speed:
        seconds, target = frames / RATE, target_frames / RATE
        raise ValueError(
            f'Phụ đề {cue_number}: lời đọc tự nhiên dài {seconds:.2f} giây nhưng khoảng phụ đề là '
            f'{target:.2f} giây. Chỉ căn nhịp từ 0,5 đến {max_speed} lần; '
            'sửa mốc thời gian hoặc bấm Tạo lại đọc liền. Không cắt bỏ lời đọc.')
    if frames != target_frames:
        import numpy as np
        import librosa
        samples = np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768
        # A phase vocoder changes duration without changing the sample rate/pitch.
        # librosa determines the exact output length from round(n / rate).
        fft_size = max(32, min(1024, 2 ** (frames.bit_length() - 1)))
        fitted = librosa.effects.time_stretch(samples, rate=ratio,
                                             n_fft=fft_size, hop_length=fft_size // 4)
        if len(fitted) != target_frames or not np.isfinite(fitted).all():
            raise ValueError('Không căn được đúng thời lượng phụ đề; chưa có bản đọc hoàn tất.')
        raw = np.clip(np.rint(fitted * 32768), -32768, 32767).astype('<i2').tobytes()
    result = io.BytesIO()
    with wave.open(result, 'wb') as output:
        output.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        output.writeframes(raw)
    return result.getvalue(), frames / RATE, ratio


def frame_count(path):
    with wave.open(str(path), 'rb') as source:
        count = source.getnframes()
        if (source.getnchannels() != 1 or source.getsampwidth() != 2
                or source.getframerate() != RATE or count <= 0
                or Path(path).stat().st_size != 44 + count * 2):
            raise ValueError('Phần WAV đã lưu bị thiếu hoặc hỏng.')
        return count


class TimelineWriter:
    """Write silence and speech sequentially, splitting even gaps at chapter bounds."""
    def __init__(self, folder, total_frames, chapter_frames):
        if total_frames <= 0 or chapter_frames <= 0:
            raise ValueError('Thời lượng bản đọc không hợp lệ.')
        self.folder = Path(folder)
        self.total = total_frames
        self.chapter_frames = chapter_frames
        self.cursor = 0
        self.parts = []
        self.output = None
        self.expected = 0
        self.written = 0
        self.destination = None
        self.temporary = None
        self.reused = False

    def _open(self):
        number = self.cursor // self.chapter_frames + 1
        self.expected = min(self.chapter_frames, self.total - self.cursor)
        self.written = 0
        self.destination = self.folder / 'parts' / f'part-{number:04d}.wav'
        self.temporary = self.destination.with_suffix('.pending')
        self.reused = False
        if self.destination.is_file() and not self.destination.is_symlink():
            try:
                self.reused = frame_count(self.destination) == self.expected
            except (OSError, ValueError, wave.Error, EOFError):
                pass
        if not self.reused:
            if shutil.disk_usage(self.folder).free < self.expected * 2 + 44 + RESERVE_BYTES:
                raise ValueError('Không đủ đĩa để ghi phần âm thanh và giữ 100 MB trống. Giải phóng dung lượng rồi bấm Tiếp tục.')
            self.output = wave.open(str(self.temporary), 'wb')
            self.output.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))

    def _finish_part(self):
        if self.output is not None:
            self.output.close()
            self.output = None
            self.temporary.replace(self.destination)
        number = len(self.parts) + 1
        self.parts.append({'number': number, 'filename': self.destination.name,
                           'seconds': self.expected / RATE})
        self.expected = 0

    def _write(self, raw):
        offset = 0
        frames = len(raw) // 2
        if self.cursor + frames > self.total:
            raise ValueError('Âm thanh vượt thời gian cuối của phụ đề.')
        while offset < frames:
            if not self.expected:
                self._open()
            count = min(frames - offset, self.expected - self.written)
            if not self.reused:
                self.output.writeframesraw(raw[offset * 2:(offset + count) * 2])
            self.cursor += count
            self.written += count
            offset += count
            if self.written == self.expected:
                self._finish_part()

    def silence_until(self, end_frame):
        if end_frame < self.cursor or end_frame > self.total:
            raise ValueError('Mốc thời gian phụ đề bị chồng lên nhau hoặc ngoài phạm vi.')
        blank = b'\0\0' * BLOCK_FRAMES
        while self.cursor < end_frame:
            count = min(BLOCK_FRAMES, end_frame - self.cursor)
            self._write(blank[:count * 2])

    def append(self, path, start_frame, end_frame, padding_frames=0):
        self.silence_until(start_frame)
        if (type(padding_frames) is not int or padding_frames < 0
                or frame_count(path) + padding_frames != end_frame - start_frame):
            raise ValueError('Đoạn đã lưu không khớp mốc phụ đề; giữ lại dữ liệu và tạo tác vụ mới.')
        with wave.open(str(path), 'rb') as source:
            while raw := source.readframes(BLOCK_FRAMES):
                self._write(raw)
        # Long subtitle slots do not require stretching speech beyond 2x or
        # allocating one enormous waveform. Silence is streamed across parts.
        self.silence_until(end_frame)
        if self.cursor != end_frame:
            raise ValueError('Đoạn âm thanh chưa được ghi đầy đủ.')

    def finish(self):
        self.silence_until(self.total)
        if self.output is not None or self.expected:
            raise ValueError('Chưa ghi đủ các phần âm thanh.')

    def abort(self):
        if self.output is not None:
            self.output.close()
            self.output = None
        if self.temporary is not None:
            self.temporary.unlink(missing_ok=True)
