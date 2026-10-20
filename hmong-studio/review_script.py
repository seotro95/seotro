"""Parse long review scripts and place locally generated speech on an SRT timeline.

Timestamps are instructions for placement, never text for the speech model. WAV
assembly copies bounded PCM blocks so a long review need not fit in memory.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import wave

import cosy_engine


MAX_SCRIPT_CHARACTERS = 1_000_000
MAX_CUES = 20_000
MAX_OUTPUT_SECONDS = 24 * 60 * 60
SAMPLE_RATE = 24_000
_COPY_FRAMES = 32_768
_TIMING = re.compile(
    r'^\s*(\d{2}):([0-5]\d):([0-5]\d)[,.](\d{3})\s*-->\s*'
    r'(\d{2}):([0-5]\d):([0-5]\d)[,.](\d{3})\s*$')


class ScriptError(ValueError):
    pass


@dataclass(frozen=True)
class Cue:
    text: str
    start: float | None = None
    end: float | None = None


@dataclass(frozen=True)
class Script:
    cues: tuple[Cue, ...]
    timed: bool
    duration: float


def parse_script(text, input_format='auto'):
    """Accept plain text or SRT with optional indexes and multiline cue text."""
    if input_format not in {'auto', 'text', 'srt'}:
        raise ScriptError('Định dạng kịch bản phải là auto, text hoặc srt.')
    if not isinstance(text, str) or not text.strip():
        raise ScriptError('Hãy nhập nội dung cần đọc.')
    if len(text) > MAX_SCRIPT_CHARACTERS:
        raise ScriptError('Mỗi lượt hỗ trợ tối đa 1.000.000 ký tự, gồm cả mốc thời gian.')
    text = text.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip()
    if not text:
        raise ScriptError('Hãy nhập nội dung cần đọc.')
    timed = input_format == 'srt' or (input_format == 'auto' and '-->' in text)
    if not timed:
        return Script((Cue(text),), False, 0.0)
    cues = []
    previous_end = 0.0
    for number, block in enumerate(re.split(r'\n(?:[ \t]*\n)+', text), 1):
        if number > MAX_CUES:
            raise ScriptError('Kịch bản SRT vượt giới hạn 20.000 đoạn; hãy chia thành nhiều lượt.')
        lines = [line.strip() for line in block.split('\n')]
        if lines and lines[0].isdigit():
            lines = lines[1:]
        match = _TIMING.fullmatch(lines[0]) if lines else None
        if match is None:
            raise ScriptError(f'Mốc thời gian đoạn {number} không hợp lệ. Dùng 00:00:00,200 --> 00:00:02,700.')
        values = [int(item) for item in match.groups()]
        start = ((values[0] * 60 + values[1]) * 60 + values[2]) + values[3] / 1000
        end = ((values[4] * 60 + values[5]) * 60 + values[6]) + values[7] / 1000
        if end <= start:
            raise ScriptError(f'Đoạn {number}: thời gian kết thúc phải lớn hơn thời gian bắt đầu.')
        if start < previous_end:
            raise ScriptError(f'Đoạn {number}: các mốc thời gian bị chồng lấn hoặc sai thứ tự.')
        if end > MAX_OUTPUT_SECONDS:
            raise ScriptError('Kịch bản vượt giới hạn 24 giờ mỗi lượt; hãy chia nhỏ hơn.')
        content = '\n'.join(lines[1:]).strip()
        content = re.sub(r'</?(?:b|i|u|font)(?:\s+[^>]*)?>', '', content,
                         flags=re.IGNORECASE).strip()
        if not content or '-->' in content:
            raise ScriptError(f'Đoạn {number} thiếu lời đọc hoặc thiếu dòng trống giữa các mốc thời gian.')
        cues.append(Cue(content, start, end))
        previous_end = end
    return Script(tuple(cues), True, previous_end)


def _validate_timeline(script):
    if not isinstance(script, Script) or not script.timed or not script.cues or len(script.cues) > MAX_CUES:
        raise ScriptError('Cần kịch bản SRT hợp lệ để tạo âm thanh theo mốc thời gian.')
    previous_end = 0.0
    text_length = 0
    for number, cue in enumerate(script.cues, 1):
        if (not isinstance(cue, Cue) or not isinstance(cue.text, str) or not cue.text.strip()
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) for value in (cue.start, cue.end))
                or cue.start < previous_end or cue.end <= cue.start or cue.end > MAX_OUTPUT_SECONDS):
            raise ScriptError(f'Đoạn {number} có nội dung hoặc mốc thời gian không hợp lệ.')
        text_length += len(cue.text)
        previous_end = cue.end
    if (text_length > MAX_SCRIPT_CHARACTERS or not isinstance(script.duration, (int, float))
            or not math.isfinite(script.duration)
            or not math.isclose(script.duration, previous_end, abs_tol=1e-6)):
        raise ScriptError('Độ dài kịch bản SRT không hợp lệ.')
    return text_length


def _audio_frames(path):
    try:
        with wave.open(str(path), 'rb') as reader:
            if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate(), reader.getcomptype()) != (1, 2, SAMPLE_RATE, 'NONE'):
                raise ScriptError('Đoạn voice phải là WAV PCM16, mono, 24 kHz.')
            frames = reader.getnframes()
            if not 0 < frames <= SAMPLE_RATE * MAX_OUTPUT_SECONDS:
                raise ScriptError('Đoạn voice rỗng hoặc vượt giới hạn 24 giờ.')
            # A header alone is insufficient: reject a truncated source before
            # promoting the assembled result, without reading all audio at once.
            reader.setpos(frames - 1)
            if len(reader.readframes(1)) != 2:
                raise ScriptError('Tệp WAV của đoạn voice bị thiếu dữ liệu.')
            return frames
    except (OSError, EOFError, wave.Error) as exc:
        raise ScriptError('Không đọc được tệp WAV của đoạn voice.') from exc


def _fit_cue(source, destination, frames, slot_frames, number):
    ratio = frames / slot_frames
    if ratio > 2.0:
        raise ScriptError(f'Đoạn {number} đọc dài {frames / SAMPLE_RATE:.2f} giây nhưng chỉ có '
                          f'{slot_frames / SAMPLE_RATE:.2f} giây. Hãy tăng thời gian hoặc rút ngắn lời đọc; '
                          'tool không cắt mất lời hoặc tăng tốc quá 2 lần.')
    if not shutil.which('ffmpeg'):
        raise ScriptError('Cần FFmpeg để khớp lời đọc với mốc thời gian. Chạy lại bộ cài AI.')
    # atempo may round its final analysis window. Leave a small margin, then
    # check the actual output rather than trimming speech to a timestamp.
    factor = min(2.0, ratio * 1.02)
    for attempt in range(3):
        try:
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-protocol_whitelist',
                            'file,pipe', '-i', str(source), '-af', f'atempo={factor:.10f}',
                            '-ac', '1', '-ar', str(SAMPLE_RATE), '-c:a', 'pcm_s16le',
                            '-f', 'wav', str(destination)], capture_output=True, check=True,
                           timeout=max(30, min(600, math.ceil(frames / SAMPLE_RATE * 2))))
        except (OSError, subprocess.SubprocessError) as exc:
            raise ScriptError(f'Không điều chỉnh được tốc độ đoạn {number} theo mốc thời gian.') from exc
        fitted = _audio_frames(destination)
        if fitted <= slot_frames:
            return destination, fitted
        if factor >= 2.0:
            break
        factor = min(2.0, factor * fitted / slot_frames * 1.01)
    raise ScriptError(f'Đoạn {number} chưa khớp khoảng thời gian ở tốc độ tối đa 2 lần. '
                      'Hãy tăng thời gian kết thúc hoặc rút ngắn lời đọc.')


def _silence(writer, frames):
    buffer = b'\0\0' * _COPY_FRAMES
    while frames:
        count = min(frames, _COPY_FRAMES)
        writer.writeframesraw(buffer[:count * 2])
        frames -= count


def _copy_audio(source, writer, frames):
    with wave.open(str(source), 'rb') as reader:
        while frames:
            count = min(frames, _COPY_FRAMES)
            block = reader.readframes(count)
            if len(block) != count * 2:
                raise ScriptError('Tệp WAV của đoạn voice bị thiếu dữ liệu; chưa lưu bản đọc.')
            writer.writeframesraw(block)
            frames -= count


def render_timeline(script, reference_path, emotion='review', speed=1.0, *, progress=None, output_path=None,
                    compute_mode='standard', cleanup='off'):
    """Generate each cue and stream a pitch-preserving, exactly placed WAV.

    Short speech is followed by silence. Speech longer than its slot is sped up
    by at most 2x; a cue that still cannot fit raises instead of losing words.
    Only a completely validated result replaces a caller's existing output.
    """
    total_text = _validate_timeline(script)
    if compute_mode not in {'standard', 'fast', 'ultra'} or cleanup not in {'off', 'light', 'strong'}:
        raise ScriptError('Chế độ tạo hoặc mức lọc ồn không hợp lệ.')
    if emotion not in cosy_engine.STYLES:
        raise ScriptError('Cách đọc đã chọn chưa được bộ máy Hmong hỗ trợ.')
    if (isinstance(speed, bool) or not isinstance(speed, (int, float))
            or not math.isfinite(speed) or not .5 <= speed <= 2):
        raise ScriptError('Tốc độ đọc phải nằm trong khoảng 0,5 đến 2,0.')
    target = Path(output_path).expanduser().resolve() if output_path is not None else None
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
    total_units = len(script.cues)
    completed_units = 0
    completed_text = 0
    generated_seconds = 0.0
    last_progress = 0.0
    synthesized = reused = 0.0
    cache_hits = 0
    current = {'synthesized_seconds': 0.0, 'reused_seconds': 0.0, 'cache_hits': 0, 'active_workers': 0}

    def report(percent, phase, message, seconds=None):
        nonlocal last_progress, generated_seconds
        last_progress = max(last_progress, min(99.0, float(percent)))
        if seconds is not None:
            generated_seconds = max(generated_seconds, min(script.duration, float(seconds)))
        if progress is not None:
            progress({'progress': round(last_progress, 2), 'phase': phase, 'message': message,
                      'completed_units': completed_units, 'total_units': total_units,
                      'generated_seconds': round(generated_seconds, 3),
                      'synthesized_seconds': round(synthesized + current['synthesized_seconds'], 3),
                      'reused_seconds': round(reused + current['reused_seconds'], 3),
                      'cache_hits': cache_hits + current['cache_hits'],
                      'active_workers': current['active_workers'], 'batch_size': 1})

    report(1, 'loading', f'Đang chuẩn bị kịch bản review gồm {total_units} đoạn theo mốc thời gian.')
    with tempfile.TemporaryDirectory(prefix='hmong-timeline-', dir=target.parent if target else None) as folder:
        folder = Path(folder)
        assembled = folder / 'timeline.part'
        total_frames = round(script.duration * SAMPLE_RATE)
        cursor = 0
        with wave.open(str(assembled), 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(SAMPLE_RATE)
            writer.setnframes(total_frames)
            for index, cue in enumerate(script.cues, 1):
                current.update(synthesized_seconds=0.0, reused_seconds=0.0, cache_hits=0, active_workers=0)
                source = folder / 'cue.wav'
                fitted = folder / 'fitted.wav'
                start = round(cue.start * SAMPLE_RATE)
                end = round(cue.end * SAMPLE_RATE)
                slot = end - start
                if slot <= 0:
                    raise ScriptError(f'Đoạn {index} ngắn hơn độ phân giải âm thanh 24 kHz.')

                def cue_progress(update):
                    for name in ('synthesized_seconds', 'reused_seconds'):
                        value = update.get(name, 0)
                        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                            current[name] = max(current[name], float(value))
                    hits = update.get('cache_hits', 0)
                    if isinstance(hits, int) and not isinstance(hits, bool) and hits >= 0:
                        current['cache_hits'] = max(current['cache_hits'], hits)
                    current['active_workers'] = 1 if update.get('active_workers') == 1 else 0
                    fraction = max(0.0, min(1.0, float(update.get('progress', 0)) / 100))
                    report(1 + 94 * (completed_text + len(cue.text) * fraction) / total_text,
                           update.get('phase', 'synthesis'),
                           f'Đoạn {index}/{total_units}: {update.get("message", "Đang tạo voice.")}',
                           cue.start + min(cue.end - cue.start, max(0, float(update.get('generated_seconds', 0)))))

                options = {'progress': cue_progress, 'output_path': source}
                if compute_mode != 'standard':
                    options['compute_mode'] = compute_mode
                if cleanup != 'off':
                    options['cleanup'] = cleanup
                cosy_engine.synthesize(cue.text, reference_path, emotion, speed, **options)
                synthesized += current['synthesized_seconds']
                reused += current['reused_seconds']
                cache_hits += current['cache_hits']
                current.update(synthesized_seconds=0.0, reused_seconds=0.0, cache_hits=0, active_workers=0)
                frames = _audio_frames(source)
                if frames > slot:
                    report(1 + 94 * (completed_text + len(cue.text) * .99) / total_text,
                           'alignment', f'Đang khớp lời đọc đoạn {index}/{total_units} với mốc thời gian.')
                    source, frames = _fit_cue(source, fitted, frames, slot, index)
                _silence(writer, start - cursor)
                _copy_audio(source, writer, frames)
                _silence(writer, slot - frames)
                cursor = end
                completed_units += 1
                completed_text += len(cue.text)
                report(1 + 94 * completed_text / total_text, 'synthesis',
                       f'Đã tạo và khớp {completed_units}/{total_units} đoạn.', cue.end)
                source.unlink(missing_ok=True)
                fitted.unlink(missing_ok=True)
        report(98, 'finalizing', 'Đang kiểm tra tệp review và các mốc thời gian.')
        if _audio_frames(assembled) != total_frames:
            raise ScriptError('Độ dài bản đọc chưa khớp mốc thời gian cuối; chưa lưu tệp.')
        report(99, 'complete', 'Đã tạo xong âm thanh theo mốc thời gian.', script.duration)
        if target is None:
            return assembled.read_bytes()
        os.replace(assembled, target)
        return target
