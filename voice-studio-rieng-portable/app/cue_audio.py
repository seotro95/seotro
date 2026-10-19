"""Sample-bounded, pitch-preserving subtitle fitting with streamed WAV I/O."""
import math
import subprocess
import time
import wave
from pathlib import Path


MAX_FAST_INPUT_FRAMES = 24000 * 60
MAX_FAST_OUTPUT_FRAMES = 24000 * 120


def _wsola_stage(samples, target_frames, cancel_path=None):
    """Overlap locally correlated waveform grains without changing pitch.

    First and last grains are anchored to the complete source. Intermediate
    grains follow its timeline with a short correlation search. This is the
    explicit fast rendering option; FFmpeg remains the quality default.
    """
    import numpy as np
    source_frames = len(samples)
    frame = min(960, source_frames//2, target_frames//2)
    frame -= frame % 2
    if frame < 128:
        raise ValueError('Câu quá ngắn cho bộ căn nhịp nhanh.')
    hop = frame//2
    search = min(240, frame//4)
    positions = np.rint(np.linspace(0, target_frames-frame,
                                   max(2, math.ceil((target_frames-frame)/hop)+1))).astype(int)
    output = np.empty(target_frames, dtype=np.float32)
    output[:frame] = samples[:frame]
    previous_end, previous_source = frame, 0
    for index, position in enumerate(positions[1:], 1):
        check_cancel(cancel_path)
        overlap = previous_end-position
        expected = round(position/(target_frames-frame)*(source_frames-frame))
        if index == len(positions)-1:
            source = source_frames-frame
        else:
            low = max(previous_source+1, expected-search, 0)
            high = min(source_frames-frame, expected+search)
            low = min(low, high)
            reference = output[position:previous_end]
            area = samples[low:high+overlap]
            correlation = np.correlate(area, reference, mode='valid')
            energies = np.cumsum(np.concatenate(([0.], area.astype(np.float64)**2)))
            energies = energies[overlap:]-energies[:-overlap]
            scores = correlation/np.sqrt(np.maximum(energies, 1e-15))
            source = low+int(np.argmax(scores))
        weight = np.arange(overlap, dtype=np.float32)/max(1, overlap-1)
        output[position:previous_end] *= 1-weight
        output[position:previous_end] += samples[source:source+overlap]*weight
        output[previous_end:position+frame] = samples[source+overlap:source+frame]
        previous_source, previous_end = source, position+frame
    return output


def wsola_samples(samples, tempo, cancel_path=None):
    """Bound short-cue memory and chain moderate waveform stretch ratios."""
    import numpy as np
    if not math.isfinite(tempo) or tempo <= 0:
        raise ValueError('Nhịp đọc phải là số dương hữu hạn.')
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim != 1:
        raise ValueError('Bộ căn nhịp nhanh cần âm thanh mono.')
    target = round(len(samples)/tempo)
    if len(samples) > MAX_FAST_INPUT_FRAMES or target > MAX_FAST_OUTPUT_FRAMES or min(len(samples), target) < 512:
        raise ValueError('Câu ngoài giới hạn bộ căn nhịp nhanh; cần FFmpeg.')
    check_cancel(cancel_path)
    if target == len(samples):
        return samples
    while len(samples)/target > 2:
        samples = _wsola_stage(samples, round(len(samples)/2), cancel_path)
    while len(samples)/target < .5:
        samples = _wsola_stage(samples, round(len(samples)*2), cancel_path)
    return _wsola_stage(samples, target, cancel_path)


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


def apply_tempo(source, destination, tempo, cancel_path=None, timeout=120, backend='ffmpeg'):
    """Run streaming FFmpeg and stop promptly when the recording is cancelled."""
    check_cancel(cancel_path)
    if backend == 'wsola':
        import soundfile as sf
        info = sf.info(str(source))
        target_frames = round(info.frames/tempo)
        if info.frames <= MAX_FAST_INPUT_FRAMES and target_frames <= MAX_FAST_OUTPUT_FRAMES and min(info.frames, target_frames) >= 512:
            samples, rate = sf.read(str(source), dtype='float32')
            if rate != 24000 or samples.ndim != 1:
                raise ValueError('PCM input format mismatch')
            samples = wsola_samples(samples, tempo, cancel_path)
            sf.write(str(destination), samples, 24000, subtype='PCM_16')
            return 'wsola'
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
    return 'ffmpeg'


def fit_cue_audio(path, target_frames, cancel_path=None, backend='ffmpeg'):
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
        tempo = source_frames/target_frames*(1 if backend == 'wsola' else 1.002)
        # Small FFT/overlap windows can make FFmpeg slightly longer than the
        # mathematical ratio. Compare integer samples and refit, never atrim.
        for attempt in range(12):
            check_cancel(cancel_path)
            used_backend=apply_tempo(source, fitted, tempo, cancel_path, timeout=max(120, source_frames/24000*2+30),backend=backend)
            try:
                _, _, fitted_frames = pcm_bounds(fitted, cancel_path)
            except ValueError as exc:
                raise ValueError('Ô SRT quá ngắn để căn giọng bằng nhịp đọc mà vẫn giữ lời; không xuất câu rỗng. Hãy nới mốc hoặc sửa lời câu này.') from exc
            if fitted_frames <= target_frames:
                fitted.replace(path)
                return {'tempo': tempo, 'frames': fitted_frames, 'trimmed_frames': trimmed_frames, 'fitted': True, 'backend':used_backend}
            tempo *= max(1.005, fitted_frames/target_frames*1.005)
        raise ValueError('Không căn được đầy đủ lời vào ô SRT sau khi điều chỉnh nhịp; hãy nới mốc hoặc sửa lời câu này.')
    finally:
        trimmed.unlink(missing_ok=True)
        fitted.unlink(missing_ok=True)
