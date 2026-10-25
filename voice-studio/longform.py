"""Sequential, restartable TXT chapters with a streaming ZIP64 deliverable.

The parent retains the exact source. Chapters carry the *already parsed* speech
plan; reparsing chapter text would lose persistent emotion and pause controls.
No combined WAV is produced, and a bounded worker result is never accepted if
it reports omitted speech or a duration limit.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import threading
import wave
import zipfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from narration import MAX_SECONDS, Segment, plan_segments
from state_io import read_progress, write_json_atomic, write_progress

MAX_CHARACTERS = 1_000_000
PART_CHARACTERS = 10_000
VERSION = 1
_ID = re.compile(r'[a-f0-9]{32}\Z')
# Persisted progress, export metadata and wall times must not invalidate a
# resume. Every synthesis/segmentation setting is explicitly bound instead.
_SETTINGS = (
    'engine', 'voice_id', 'speaker', 'language', 'quality', 'speed', 'format',
    'delivery', 'paragraph_pause', 'skip_timestamps', 'segment_plan',
    'hmong_steps', 'hmong_backend', 'hmong_reference_fingerprint',
    'hmong_voice_snapshot',
    'reference_text', 'emotion', 'emotion_strength', 'auto_rhythm',
    'hmong_phrase_context', 'nano_steps', 'nano_threads', 'nano_parallel',
)


@dataclass(frozen=True)
class Chapter:
    index: int
    start: int
    end: int
    segments: tuple[Segment, ...]
    characters: int

    @property
    def text(self):
        """Human-readable spoken transcript; the worker uses segments instead."""
        return '\n'.join(segment.text for segment in self.segments if segment.text)


def validate_job(job):
    if (job.get('engine') not in {'f5_hmong', 'hmong_native'}
            or job.get('language', 'mww') != 'mww'
            or job.get('input_format', 'txt') != 'txt' or job.get('video_id')
            or job.get('character_cast')):
        raise ValueError('Chia chương dài chỉ hỗ trợ kịch bản TXT Hmong, không ghép video hoặc phân vai SRT.')
    text = job.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHARACTERS:
        raise ValueError('Kịch bản TXT Hmong cần từ 1 đến 1.000.000 ký tự.')
    if job.get('format', 'wav') not in {'wav', 'mp3'}:
        raise ValueError('Chọn WAV hoặc MP3 cho âm thanh từng chương.')


def plan_chapters(job, segments=None, *, limit=PART_CHARACTERS):
    """Partition complete segments, preserving every speech/control field.

    Split only between planned segments. Bound known inserted silence as well
    as text where a new chapter can contain speech; pathological pause-only
    source is rejected by the worker's strict duration check, never clipped.
    """
    validate_job(job)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 240:
        raise ValueError('Chapter character limit must be at least 240.')
    source = plan_segments(job) if segments is None else segments
    source = tuple(replace(segment) for segment in source)
    if not any(segment.text for segment in source):
        raise ValueError('Nhập nội dung đọc, không chỉ ký hiệu nghỉ.')
    if any(len(segment.text) > limit for segment in source):
        raise ValueError('Một đoạn đọc vượt giới hạn chương; cần lập lại kế hoạch đoạn.')
    chapters, start, characters, known_silence = [], 0, 0, 0.0
    spoken_remaining = sum(bool(segment.text) for segment in source)
    has_speech = False
    for index, segment in enumerate(source):
        added = len(segment.text)
        silence = segment.pause + segment.rhythm_pause
        # A pause stays in the original order. Do not create chapters without
        # speech, since such chapters cannot be sent to a speech synthesizer.
        if has_speech and spoken_remaining and (
                characters + added > limit or known_silence + silence > 1800):
            chapters.append(Chapter(len(chapters) + 1, start, index,
                                    source[start:index], characters))
            start, characters, known_silence, has_speech = index, 0, 0.0, False
        characters += added
        known_silence += silence
        has_speech = has_speech or bool(segment.text)
        spoken_remaining -= bool(segment.text)
    chapters.append(Chapter(len(chapters) + 1, start, len(source), source[start:], characters))
    return chapters


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def plan_identity(job, chapters):
    settings = {key: job.get(key) for key in _SETTINGS}
    # Explicit speech-only subtitle work must not share a timed plan. Omitted
    # or True retains previous identities, including all legacy TXT chapters.
    if job.get('input_format') == 'srt' and job.get('subtitle_timing', True) is False:
        settings['subtitle_timing'] = False
    return _digest({'version': VERSION, 'text': job['text'],
                    'settings': settings,
                    'chapters': [[asdict(segment) for segment in chapter.segments]
                                 for chapter in chapters]})


def child_id(parent_id, index, identity):
    return hashlib.sha256(f'longform-v1:{parent_id}:{index:04d}:{identity}'.encode('utf-8')).hexdigest()[:32]


def _read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _file_digest(path, check_cancel=lambda: None):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            check_cancel()
            digest.update(block)
    return digest.hexdigest()


def _validate_result(result, chapter, audio, audio_format):
    if (result.get('duration_limited') is not False
            or result.get('completed') != len(chapter.segments)
            or result.get('total') != len(chapter.segments)):
        raise ValueError(f'Chương {chapter.index} chưa đọc hết hoặc vượt 3 giờ. '
                         'Các chương đã xong được giữ; không xuất bản thu bị cắt lời.')
    duration = result.get('audio_seconds')
    if (not isinstance(duration, (int, float)) or not math.isfinite(duration)
            or not 0 < duration <= MAX_SECONDS):
        raise ValueError(f'Chương {chapter.index} có thời lượng không hợp lệ.')
    if not audio.is_file() or audio.stat().st_size < 44:
        raise ValueError(f'Không tìm thấy âm thanh hoàn chỉnh của chương {chapter.index}.')
    if audio_format == 'wav':
        try:
            with wave.open(str(audio), 'rb') as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 24000):
                    raise ValueError('Sai định dạng PCM của chương.')
                remaining = source.getnframes()
                if remaining <= 0 or abs(remaining / 24000 - duration) > .01:
                    raise ValueError('Thời lượng WAV không khớp kết quả chương.')
                # Header-only/truncated WAV files must never become reusable
                # completion checkpoints. Read bounded blocks from disk.
                while remaining:
                    count = min(65536, remaining)
                    if len(source.readframes(count)) != count * 2:
                        raise ValueError('Tệp WAV của chương chưa ghi hoàn chỉnh.')
                    remaining -= count
        except (wave.Error, EOFError) as exc:
            raise ValueError('Tệp WAV của chương không hợp lệ.') from exc


def _completed_checkpoint(folder, identity, chapter, audio_format, check_cancel):
    checkpoint = _read_json(folder / 'complete.json')
    if checkpoint.get('identity') != identity:
        return None
    result = checkpoint.get('result', {})
    try:
        audio = folder / ('audio.' + audio_format)
        _validate_result(result, chapter, audio, audio_format)
        for name in ('audio.' + audio_format, 'transcript.txt', 'subtitles.srt'):
            if checkpoint.get('sha256', {}).get(name) != _file_digest(folder / name, check_cancel):
                return None
    except InterruptedError:
        raise
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return result


def _zip_file(archive, path, name, check_cancel):
    # force_zip64 handles chapters or an archive exceeding the RIFF/4GB limit.
    # Stored audio avoids spending hours recompressing already encoded data.
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_STORED
    with Path(path).open('rb') as source, archive.open(info, 'w', force_zip64=True) as target:
        while block := source.read(1024 * 1024):
            check_cancel()
            target.write(block)


def run_longform(job, data, execute_worker, env, *, cancelled=None):
    """Run in the existing single job queue; return the parent result.

    execute_worker(path, env, work) uses the existing resident worker process.
    Cancellation propagates while it blocks. Finished chapter checkpoints and
    an interrupted child's chunk cache survive retries. All child audio stays
    individually bounded; the only combined output is a streamed ZIP64 file.
    """
    data = Path(data)
    ident = job.get('id', '')
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        raise ValueError('Mã tác vụ dài không hợp lệ.')
    from character_cast import validate_job_references
    validate_job_references(job, data)
    chapters = plan_chapters(job)
    identity = plan_identity(job, chapters)
    parent = data / 'parts' / ident
    parent.mkdir(parents=True, exist_ok=True)
    plan_path = parent / 'plan.json'
    previous = _read_json(plan_path)
    if plan_path.exists() and previous.get('identity') != identity:
        raise ValueError('Nội dung hoặc thiết lập chương đã thay đổi. Tạo tác vụ mới; các chương cũ được giữ nguyên.')
    audio_format = job.get('format', 'wav')
    total = sum(len(chapter.segments) for chapter in chapters)
    plan = {'version': VERSION, 'identity': identity, 'source_characters': len(job['text']),
            'total': total, 'chapters': [
                {'index': chapter.index, 'id': child_id(ident, chapter.index, identity),
                 'start': chapter.start, 'end': chapter.end, 'characters': chapter.characters}
                for chapter in chapters]}
    write_json_atomic(plan_path, plan)
    original = parent / 'original.txt'
    if not original.exists():
        pending_source = parent / 'original.txt.tmp'
        pending_source.write_bytes(job['text'].encode('utf-8'))
        pending_source.replace(original)
    elif original.read_bytes().decode('utf-8') != job['text']:
        raise ValueError('Bản TXT gốc đã thay đổi; tạo tác vụ mới để giữ đúng nguồn.')

    def check_cancel():
        if (parent / 'cancel.flag').exists() or (cancelled is not None and cancelled()):
            raise InterruptedError('Đã dừng. Các chương và đoạn đã tạo được giữ để tiếp tục.')

    results, public_chapters = [], []
    completed = 0
    audio_seconds = 0.0
    reused = 0
    for chapter, entry in zip(chapters, plan['chapters']):
        check_cancel()
        folder = parent / 'chapters' / f'{chapter.index:04d}'
        folder.mkdir(parents=True, exist_ok=True)
        childwork = data / 'parts' / entry['id']
        audio = folder / ('audio.' + audio_format)
        result = _completed_checkpoint(folder, identity, chapter, audio_format, check_cancel)
        if result is not None:
            reused += 1
        else:
            childwork.mkdir(parents=True, exist_ok=True)
            (childwork / 'cancel.flag').unlink(missing_ok=True)
            child = {key: job.get(key) for key in _SETTINGS if key in job}
            child.update(id=entry['id'], text=chapter.text, input_format='txt', format=audio_format,
                         status='running', max_minutes=180, _longform_parent_id=ident,
                         _longform_identity=identity,
                         _PREPLANNED_SEGMENTS=[asdict(segment) for segment in chapter.segments])
            child_path = folder / 'job.json'
            write_json_atomic(child_path, child)
            monitor_done = threading.Event()
            monitor_errors = []

            def monitor():
                while not monitor_done.is_set():
                    try:
                        check_cancel()
                    except InterruptedError:
                        (childwork / 'cancel.flag').touch()
                    except Exception as exc:
                        monitor_errors.append(exc)
                        (childwork / 'cancel.flag').touch()
                        return
                    child_progress = read_progress(childwork / 'progress.json')
                    current = min(len(chapter.segments), max(0, child_progress.get('completed', 0)))
                    write_progress(parent / 'progress.json', {
                        'completed': completed + current, 'total': total,
                        'progress': min(95, round(95 * (completed + current) / total)),
                        'chapter': chapter.index, 'chapter_count': len(chapters),
                        'completed_chapters': len(results),
                        'audio_seconds': audio_seconds + child_progress.get('audio_seconds', 0),
                        'phase': f'Chương {chapter.index}/{len(chapters)}: ' + child_progress.get('phase', 'Đang chuẩn bị'),
                    })
                    monitor_done.wait(.1)

            monitor_thread = threading.Thread(target=monitor, name='longform-progress', daemon=True)
            monitor_thread.start()
            try:
                code = execute_worker(child_path, env, childwork)
            finally:
                monitor_done.set()
                monitor_thread.join()
            check_cancel()
            if monitor_errors:
                raise monitor_errors[0]
            if code == -2:
                raise InterruptedError('Đã dừng. Các chương đã tạo được giữ để tiếp tục.')
            if code:
                detail = _read_json(childwork / 'worker-done.json').get('user_error')
                raise RuntimeError(detail or f'Không tạo được chương {chapter.index}; có thể tiếp tục từ đoạn đã tạo.')
            result = _read_json(childwork / 'result.json')
            generated = data / 'audio' / (entry['id'] + '.' + audio_format)
            _validate_result(result, chapter, generated, audio_format)
            subtitles = data / 'audio' / (entry['id'] + '.srt')
            if not subtitles.is_file():
                raise ValueError(f'Chương {chapter.index} chưa có phụ đề hoàn chỉnh.')
            # Only promote output after the worker proves every planned segment
            # completed. No parent archive can contain a limited/partial part.
            generated.replace(audio)
            subtitles.replace(folder / 'subtitles.srt')
            # Keep the archive's UTF-8/LF transcript identical on Windows;
            # text-mode writes would expand LF to CRLF inside the ZIP.
            (folder / 'transcript.txt').write_bytes((chapter.text + '\n').encode('utf-8'))
            hashes = {name: _file_digest(folder / name, check_cancel)
                      for name in ('audio.' + audio_format, 'transcript.txt', 'subtitles.srt')}
            write_json_atomic(folder / 'complete.json', {'identity': identity,
                                                       'result': result, 'sha256': hashes})
            shutil.rmtree(childwork, ignore_errors=True)
        results.append(result)
        completed += len(chapter.segments)
        audio_seconds += result['audio_seconds']
        public_chapters.append({**entry, 'audio_seconds': result['audio_seconds'],
                                'format': audio_format, 'completed': len(chapter.segments),
                                'total': len(chapter.segments),
                                'files': {'audio': f'chapters/{chapter.index:04d}/audio.{audio_format}',
                                          'txt': f'chapters/{chapter.index:04d}/transcript.txt',
                                          'srt': f'chapters/{chapter.index:04d}/subtitles.srt'}})
        write_progress(parent / 'progress.json', {
            'completed': completed, 'total': total, 'progress': min(95, round(95 * completed / total)),
            'chapter': chapter.index, 'chapter_count': len(chapters),
            'completed_chapters': len(results), 'audio_seconds': audio_seconds,
            'phase': f'Đã hoàn tất {len(results)}/{len(chapters)} chương',
        })

    check_cancel()
    manifest = {'version': VERSION, 'identity': identity, 'source_file': 'original.txt',
                'source_characters': len(job['text']), 'audio_format': audio_format,
                'audio_seconds': audio_seconds, 'total': total, 'completed': completed,
                'duration_limited': False, 'chapter_count': len(chapters), 'chapters': public_chapters}
    write_json_atomic(parent / 'manifest.json', manifest)
    pending = parent / 'archive.zip.tmp'
    destination = data / 'audio' / (ident + '.zip')
    try:
        with zipfile.ZipFile(pending, 'w', allowZip64=True) as archive:
            _zip_file(archive, original, 'original.txt', check_cancel)
            _zip_file(archive, parent / 'manifest.json', 'manifest.json', check_cancel)
            for entry in public_chapters:
                for relative in entry['files'].values():
                    _zip_file(archive, parent / relative, relative, check_cancel)
        check_cancel()
        destination.parent.mkdir(parents=True, exist_ok=True)
        pending.replace(destination)
    finally:
        pending.unlink(missing_ok=True)
    result = {**manifest, 'longform': True, 'progress': 100, 'completed_chapters': len(chapters),
              'reused_chapters': reused,
              'spoken_audio_seconds': sum(part.get('spoken_audio_seconds', 0) for part in results),
              'inserted_silence_seconds': sum(part.get('inserted_silence_seconds', 0) for part in results)}
    write_json_atomic(parent / 'result.json', result)
    write_progress(parent / 'progress.json', {key: result[key] for key in (
        'completed', 'total', 'progress', 'chapter_count', 'completed_chapters', 'audio_seconds')})
    return result
