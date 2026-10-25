"""Bounded speech chunks, resumable disk checkpoints, and playable WAV chapters."""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import wave

import cloning_engine

MAX_CHARACTERS = 1_000_000
CHAPTER_SECONDS = 1800
PLAN_VERSION = 1
STYLES = {
    'natural': {'label': 'Tự nhiên', 'speed': 1.0, 'sentence_pause': .12, 'paragraph_pause': .3},
    'storytelling': {'label': 'Kể chuyện', 'speed': .94, 'sentence_pause': .25, 'paragraph_pause': .6},
    'film_review': {'label': 'Review phim', 'speed': 1.08, 'sentence_pause': .1, 'paragraph_pause': .3},
    'news': {'label': 'Tin tức', 'speed': 1.02, 'sentence_pause': .15, 'paragraph_pause': .35},
    'advertising': {'label': 'Quảng cáo', 'speed': 1.1, 'sentence_pause': .08, 'paragraph_pause': .25},
    'relaxing': {'label': 'Thư giãn', 'speed': .85, 'sentence_pause': .4, 'paragraph_pause': .8},
}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name, suffix='.pending', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(value, output, ensure_ascii=False)
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def plan_text(text, style='natural', limit=350):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHARACTERS:
        raise ValueError('Nhập từ 1 đến 1.000.000 ký tự có nội dung.')
    if style not in STYLES:
        raise ValueError('Kiểu đọc không hợp lệ.')
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError('Độ dài mỗi đoạn phải là số nguyên dương.')
    profile = STYLES[style]
    result, pending = [], ''
    def flush(paragraph=False):
        nonlocal pending
        if pending.strip():
            result.append({'text': pending.strip(), 'pause': profile['paragraph_pause' if paragraph else 'sentence_pause']})
        pending = ''
    for match in re.finditer(r'\S+\s*', text):
        token = match.group()
        word = token.rstrip()
        if pending and len(pending) + 1 + len(word) > limit:
            flush()
        # Even an unbroken million-character token stays bounded.
        offset = 0
        while len(word) - offset > limit:
            if pending:
                flush()
            pending = word[offset:offset + limit]
            offset += limit
            flush()
        word = word[offset:]
        if word:
            pending = (pending + ' ' + word).strip()
        paragraph = '\n' in token or '\r' in token
        sentence = word.endswith(('.', '!', '?', ';', '…'))
        if len(pending) >= 160 and (paragraph or sentence):
            flush(paragraph)
    flush(True)
    if result:
        result[-1]['pause'] = 0
    return result


def wav_info(path):
    with wave.open(str(path), 'rb') as source:
        rate, frames = source.getframerate(), source.getnframes()
        if source.getnchannels() != 1 or source.getsampwidth() != 2 or rate != 24000 or frames <= 0:
            raise ValueError('Đoạn WAV không đúng định dạng 24 kHz mono.')
        # Files written by this module have the canonical PCM header.
        if Path(path).stat().st_size != 44 + frames * 2:
            raise ValueError('Đoạn WAV chưa được ghi đầy đủ.')
        return frames / rate


def write_chunk(path, audio, pause):
    with wave.open(io.BytesIO(audio), 'rb') as source:
        rate, frames = source.getframerate(), source.getnframes()
        if source.getnchannels() != 1 or source.getsampwidth() != 2 or rate != 24000 or frames <= 0:
            raise ValueError('Bộ tạo giọng trả WAV không hợp lệ.')
        raw = source.readframes(frames)
        if len(raw) != frames * 2:
            raise ValueError('Bộ tạo giọng trả WAV chưa đầy đủ.')
    temporary = path.with_suffix('.pending')
    try:
        with wave.open(str(temporary), 'wb') as output:
            output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            output.writeframesraw(raw)
            output.writeframesraw(b'\0\0' * round(pause * rate))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return frames / rate


def make_chapter(folder, number, chunks):
    destination = folder / 'parts' / f'part-{number:04d}.wav'
    seconds = sum(wav_info(path) for path in chunks)
    # A completed, matching chapter can be reused after resume.
    if destination.is_file():
        try:
            if abs(wav_info(destination) - seconds) < .001:
                return {'number': number, 'filename': destination.name, 'seconds': seconds}
        except (OSError, ValueError, wave.Error, EOFError):
            pass
    temporary = destination.with_suffix('.pending')
    try:
        with wave.open(str(temporary), 'wb') as output:
            output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            for path in chunks:
                with wave.open(str(path), 'rb') as source:
                    while block := source.readframes(65536):
                        output.writeframesraw(block)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {'number': number, 'filename': destination.name, 'seconds': seconds}


def process_job(folder):
    folder = Path(folder)
    payload = json.loads((folder / 'input.json').read_text(encoding='utf-8'))
    style = payload.get('style', 'natural')
    quality = payload.get('quality', 'fast')
    speed = payload.get('speed', 1)
    if quality not in cloning_engine.QUALITY_STEPS:
        raise ValueError('Chế độ chất lượng không hợp lệ.')
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not math.isfinite(speed) or not .5 <= speed <= 2:
        raise ValueError('Tốc độ đọc phải từ 0,5 đến 2 lần.')
    plan = plan_text(payload['text'], style)
    reference = payload['_reference']
    sample = Path(reference['path'])
    # A checkpoint must belong to exactly the same text, style, voice and sample.
    fingerprint = hashlib.sha256(json.dumps({
        'version': PLAN_VERSION, 'text': payload['text'], 'style': style, 'quality': quality,
        'speed': speed, 'voice': payload['voice'], 'reference_text': reference['text'],
        'reference_sha256': hashlib.sha256(sample.read_bytes()).hexdigest(),
    }, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    checkpoint = folder / 'checkpoint.json'
    saved = json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.is_file() else {}
    if saved and saved.get('fingerprint') != fingerprint:
        raise ValueError('Thiết lập khác bản đang dừng. Tạo tác vụ mới để giữ nguyên bản thu cũ.')
    for name in ('chunks', 'parts'):
        (folder / name).mkdir(parents=True, exist_ok=True)
    effective_speed = max(.5, min(2, speed * STYLES[style]['speed']))
    started = time.perf_counter()
    previous_elapsed = saved.get('elapsed_seconds', 0)
    spoken_seconds = saved.get('spoken_seconds', 0)
    completed = saved.get('completed', 0)
    if (isinstance(completed, bool) or not isinstance(completed, int)
            or not 0 <= completed <= len(plan)
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) or value < 0
                   for value in (previous_elapsed, spoken_seconds))):
        raise ValueError('Checkpoint không hợp lệ. Giữ lại tác vụ và tạo tác vụ mới.')
    completed_before = completed
    audio_seconds = 0.0
    chapters, pending = [], []
    pending_seconds = 0.0

    def report(message, done=False):
        elapsed = previous_elapsed + time.perf_counter() - started
        throughput = spoken_seconds / elapsed if spoken_seconds > 0 and elapsed > 0 else None
        runtime_device = getattr(cloning_engine, 'runtime_device', lambda: None)()
        data = {'completed': completed, 'total': len(plan), 'progress': 100 if done else min(99, int(completed * 100 / len(plan))),
                'message': message, 'audio_seconds': audio_seconds, 'elapsed_seconds': round(elapsed, 3),
                'throughput': throughput, 'estimated_seconds_for_hour': 3600 / throughput if throughput else None,
                'device': runtime_device, 'parts': chapters, 'style': style, 'quality': quality,
                'effective_speed': effective_speed, 'resumed': completed_before > 0}
        atomic_json(folder / 'progress.json', data)
        return data

    def add_chunk(path):
        nonlocal pending, pending_seconds, audio_seconds
        seconds = wav_info(path)
        if pending and pending_seconds + seconds > CHAPTER_SECONDS:
            chapters.append(make_chapter(folder, len(chapters) + 1, pending))
            pending, pending_seconds = [], 0.0
        pending.append(path)
        pending_seconds += seconds
        audio_seconds += seconds

    # Rebuild the chapter layout using disk headers only, never a whole-book waveform.
    for index in range(completed):
        path = folder / 'chunks' / f'chunk-{index:06d}.wav'
        try:
            add_chunk(path)
        except (OSError, ValueError, wave.Error, EOFError):
            raise ValueError('Một đoạn đã lưu bị thiếu/hỏng. Tạo tác vụ mới; không ghi đè các phần còn tốt.') from None
    report('Đang nạp mô hình…' if not completed else 'Đang tiếp tục từ đoạn đã lưu…')
    for index in range(completed, len(plan)):
        if shutil.disk_usage(folder).free < 100 * 1024 * 1024:
            raise ValueError('Ổ đĩa còn dưới 100 MB. Giải phóng dung lượng rồi bấm Tiếp tục.')
        segment = plan[index]
        report(f'Đang tạo đoạn {index + 1}/{len(plan)}…')
        audio = cloning_engine.synthesize(segment['text'], effective_speed, sample, reference['text'], quality=quality)
        path = folder / 'chunks' / f'chunk-{index:06d}.wav'
        spoken_seconds += write_chunk(path, audio, segment['pause'])
        del audio
        add_chunk(path)
        completed = index + 1
        elapsed = previous_elapsed + time.perf_counter() - started
        atomic_json(checkpoint, {'fingerprint': fingerprint, 'completed': completed,
                                'spoken_seconds': spoken_seconds, 'elapsed_seconds': elapsed})
        report(f'Đã tạo {completed}/{len(plan)} đoạn.')
    if pending:
        chapters.append(make_chapter(folder, len(chapters) + 1, pending))
    result = report('Đã tạo xong tất cả các phần.', done=True)
    atomic_json(folder / 'result.json', result)
    return result
