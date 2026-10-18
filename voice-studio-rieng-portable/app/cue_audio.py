"""Sample-bounded, pitch-preserving subtitle fitting with streamed WAV I/O."""
import math
import subprocess
import time
import wave
from pathlib import Path


def atempo_filter(tempo):
    """Keep every atempo stage in its overlap-add range, including large fits."""
    if not math.isfinite(tempo) or tempo <= 0:
        raise ValueError('Nhịp đọc phải là số dương hữu hạn.')
    stages = []
    while tempo > 2:
        stages.append('atempo=2')
        tempo /= 2
    while tempo < .5:
        stages.append('atempo=0.5')
        tempo *= 2
    stages.append(f'atempo={tempo:.12g}')
    return ','.join(stages)


def check_cancel(cancel_path):
    if cancel_path is not None and Path(cancel_path).exists():
        raise InterruptedError('Tác vụ đã dừng; các đoạn đã tạo được giữ để tiếp tục.')


def pcm_bounds(path, cancel_path=None):
    """Find only exact digital silence at the boundaries, in bounded blocks."""
    with wave.open(str(path), 'rb') as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 24000):
            raise ValueError('PCM input format mismatch')
        frames = source.getnframes()
        first = None
        position = 0
        while position < frames:
            check_cancel(cancel_path)
            block = source.readframes(min(65536, frames-position))
            if not block:
                raise ValueError('Tệp âm thanh bị thiếu dữ liệu.')
            leading = len(block)-len(block.lstrip(b'\0'))
            if leading < len(block):
                first = position+leading//2
                break
            position += len(block)//2
        if first is None:
            raise ValueError('Âm thanh câu SRT rỗng hoặc chỉ có im lặng; không bỏ qua lời.')
        position = frames
        while position > first:
            check_cancel(cancel_path)
            begin = max(first, position-65536)
            source.setpos(begin)
            block = source.readframes(position-begin)
            nonzero_bytes = len(block.rstrip(b'\0'))
            if nonzero_bytes:
                return first, begin+(nonzero_bytes+1)//2, frames
            position = begin
    raise ValueError('Không tìm được lời đọc trong câu SRT.')


def copy_pcm_window(source_path, destination, begin, end, cancel_path=None):
    """Remove zero samples only; never trim a voiced sample to meet a clock."""
    with wave.open(str(source_path), 'rb') as source, wave.open(str(destination), 'wb') as target:
        target.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        source.setpos(begin)
        remaining = end-begin
        while remaining:
            check_cancel(cancel_path)
            block = source.readframes(min(65536, remaining))
            if not block:
                raise ValueError('Tệp âm thanh bị thiếu dữ liệu.')
            target.writeframesraw(block)
            remaining -= len(block)//2


def apply_tempo(source, destination, tempo, cancel_path=None, timeout=120):
    """Run streaming FFmpeg and stop promptly when the recording is cancelled."""
    check_cancel(cancel_path)
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source), '-vn', '-ac', '1', '-ar', '24000',
               '-af', atempo_filter(tempo), '-codec:a', 'pcm_s16le', '-y', str(destination)]
    errors_path = Path(destination).with_suffix('.ffmpeg.log')
    with errors_path.open('wb') as errors, subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=errors) as process:
        started = time.monotonic()
        try:
            while process.poll() is None:
                check_cancel(cancel_path)
                if time.monotonic()-started > timeout:
                    raise subprocess.TimeoutExpired(command, timeout)
                time.sleep(.05)
            check_cancel(cancel_path)
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, command)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    errors_path.unlink(missing_ok=True)


def fit_cue_audio(path, target_frames, cancel_path=None):
    """Refit the complete original cue until it fits; the writer adds the gap.

    No speech is cut and no resampling is used to raise pitch. Only digital
    silence at the original cue's boundaries may be removed. Each retry reads
    that same source, rather than repeatedly degrading an already fitted voice.
    """
    path = Path(path)
    if target_frames < 1:
        raise ValueError('Khoảng thời gian câu SRT phải chứa ít nhất một mẫu âm thanh.')
    first, end, raw_frames = pcm_bounds(path, cancel_path)
    if raw_frames <= target_frames:
        return {'tempo': 1.0, 'frames': raw_frames, 'trimmed_frames': 0, 'fitted': False}
    trimmed = path.with_name(path.stem+'-trimmed.wav')
    fitted = path.with_name(path.stem+'-fitted.wav')
    source = path
    trimmed_frames = first+raw_frames-end
    try:
        if trimmed_frames:
            copy_pcm_window(path, trimmed, first, end, cancel_path)
            source = trimmed
        source_frames = end-first
        if source_frames <= target_frames:
            if source != path:
                source.replace(path)
            return {'tempo': 1.0, 'frames': source_frames, 'trimmed_frames': trimmed_frames, 'fitted': True}
        tempo = source_frames/target_frames*1.002
        # Small FFT/overlap windows can make FFmpeg slightly longer than the
        # mathematical ratio. Compare integer samples and refit, never atrim.
        for attempt in range(12):
            check_cancel(cancel_path)
            apply_tempo(source, fitted, tempo, cancel_path, timeout=max(120, source_frames/24000*2+30))
            try:
                _, _, fitted_frames = pcm_bounds(fitted, cancel_path)
            except ValueError as exc:
                raise ValueError('Ô SRT quá ngắn để căn giọng bằng nhịp đọc mà vẫn giữ lời; không xuất câu rỗng. Hãy nới mốc hoặc sửa lời câu này.') from exc
            if fitted_frames <= target_frames:
                fitted.replace(path)
                return {'tempo': tempo, 'frames': fitted_frames, 'trimmed_frames': trimmed_frames, 'fitted': True}
            tempo *= max(1.005, fitted_frames/target_frames*1.005)
        raise ValueError('Không căn được đầy đủ lời vào ô SRT sau khi điều chỉnh nhịp; hãy nới mốc hoặc sửa lời câu này.')
    finally:
        trimmed.unlink(missing_ok=True)
        fitted.unlink(missing_ok=True)
