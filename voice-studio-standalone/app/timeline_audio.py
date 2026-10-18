"""Sample-accurate cue assembly without discarding spoken audio.

Timestamped scripts define a video timeline.  Speech may be time-stretched
within a bounded, pitch-preserving range; any remaining cue space is silence.
The original generated PCM is always retained for resume and refitting.
"""
import math
from pathlib import Path
import shutil
import subprocess
import wave

RATE = 24000


def pcm_frames(path):
    with wave.open(str(path), 'rb') as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, RATE):
            raise ValueError('Căn thời gian cần âm thanh PCM mono 24 kHz.')
        return source.getnframes()


def timeline_frames(cues, seconds=None, maximum=10800):
    """Resolve an explicit video length or the last cue, never silently clip it."""
    end = cues[-1]['end']
    target = end if seconds is None else seconds
    if not math.isfinite(target) or target <= 0 or target > 10800:
        raise ValueError('Độ dài video phải lớn hơn 0 và không quá 3 giờ.')
    if round(target * RATE) < round(end * RATE):
        raise ValueError(f'Độ dài video {target:.3f}s ngắn hơn mốc cuối {end:.3f}s trong lời thoại.')
    if round(target * RATE) > round(maximum * RATE):
        raise ValueError(f'Lời thoại cần {target:.3f}s nhưng giới hạn xuất chỉ {maximum:.3f}s. Tăng giới hạn độ dài; tool không cắt lời để ép khớp.')
    return round(target * RATE)


def _atempo_filters(tempo):
    # FFmpeg's atempo is most stable in [0.5, 2]. Chaining also keeps this
    # helper correct if a future explicitly-selected policy uses a wider range.
    filters = []
    while tempo > 2:
        filters.append('atempo=2')
        tempo /= 2
    while tempo < .5:
        filters.append('atempo=0.5')
        tempo /= .5
    filters.append(f'atempo={tempo:.12g}')
    return ','.join(filters)


def fit_cue(source, output, frames, *, min_tempo=.65, max_tempo=2.0,
            cancel_flag=None, cue_number=1):
    """Fit speech at or below its cue window; leave exact padding to assembly.

    atempo uses analysis windows, so its output length is not exactly the
    input length divided by the requested ratio. Refit from the original if
    necessary. Never trim a tail to conceal a duration mismatch.
    """
    if frames <= 0:
        raise ValueError(f'Câu {cue_number}: ô lời thoại phải có độ dài lớn hơn 0.')
    if not 0 < min_tempo <= 1 <= max_tempo or not all(map(math.isfinite, (min_tempo, max_tempo))):
        raise ValueError('Giới hạn căn nhịp không hợp lệ.')
    source, output = Path(source), Path(output)
    original_frames = pcm_frames(source)
    ratio = original_frames / frames
    if ratio > max_tempo + 1e-9:
        raise ValueError(f'Câu {cue_number}: lời dài {original_frames / RATE:.3f}s nhưng ô chỉ {frames / RATE:.3f}s, cần đọc nhanh {ratio:.2f}× (giới hạn {max_tempo:g}×). Rút ngắn lời hoặc nới mốc; tool giữ đủ lời và không cắt âm thanh.')
    tempo = max(min_tempo, ratio)
    # Exact-length source PCM needs no transform, particularly for tiny cues.
    if original_frames == frames:
        shutil.copyfile(source, output)
        return {'tempo': 1.0, 'raw_frames': original_frames, 'speech_frames': original_frames, 'padding_frames': 0}
    for attempt in range(7):
        if cancel_flag is not None and Path(cancel_flag).exists():
            raise InterruptedError('Tác vụ đã dừng.')
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source),
                        '-vn', '-ac', '1', '-ar', str(RATE), '-af', _atempo_filters(tempo),
                        '-codec:a', 'pcm_s16le', '-y', str(output)], check=True, timeout=120)
        fitted_frames = pcm_frames(output)
        if fitted_frames <= 0:
            raise ValueError(f'Câu {cue_number}: căn nhịp không tạo được lời đọc; hãy nới mốc thời gian.')
        if fitted_frames <= frames:
            return {'tempo': tempo, 'raw_frames': original_frames, 'speech_frames': fitted_frames,
                    'padding_frames': frames - fitted_frames}
        if tempo >= max_tempo or attempt == 6:
            raise ValueError(f'Câu {cue_number}: lời vẫn vượt ô ở mức đọc nhanh {max_tempo:g}×. Rút ngắn lời hoặc nới mốc; tool không cắt mất từ.')
        # Small safety margin avoids another overshoot due to atempo windows;
        # the subsequent silence fill makes the cue boundary sample-exact.
        tempo = min(max_tempo, tempo * fitted_frames / frames * 1.002)
    raise AssertionError('unreachable')


def fill_to_frame(writer, target):
    """Place the next sample exactly at a timeline boundary."""
    if writer.frames > target:
        raise ValueError('Lời đọc vượt mốc thời gian; tool không cắt âm thanh để che lỗi.')
    if target > writer.limit:
        raise ValueError('Mốc thời gian vượt giới hạn xuất âm thanh.')
    writer.silence_frames(target - writer.frames)

