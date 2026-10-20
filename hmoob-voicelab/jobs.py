"""One warm inference worker, bounded checkpoints and resumable long documents."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import queue
import shutil
import threading
import time
import uuid

from audio_io import PART_SECONDS, assemble, inspect_wav, write_samples
from longform import CHUNK_CHARACTERS, PLANNER_VERSION, plan, validate_text
from voices import atomic_json

ACTIVE = {'queued', 'running', 'cancelling'}


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_options(payload):
    if not isinstance(payload, dict):
        raise ValueError('Yêu cầu phải là đối tượng JSON.')
    text = validate_text(payload.get('text'))
    voice, quality, speed = payload.get('voice', 'female'), payload.get('quality', 'fast'), payload.get('speed', 1)
    if voice not in ('female', 'male') or quality not in ('fast', 'standard', 'draft'):
        raise ValueError('Giọng hoặc chế độ tạo không hợp lệ.')
    if (isinstance(speed, bool) or not isinstance(speed, (int, float))
            or not math.isfinite(speed) or not .5 <= speed <= 2):
        raise ValueError('Tốc độ đọc phải từ 0,5 đến 2 lần.')
    return text, voice, quality, float(speed)


class JobManager:
    def __init__(self, data, voices, engine, part_seconds=PART_SECONDS, minimum_free=128 * 1024**2):
        self.root = Path(data) / 'jobs'
        self.root.mkdir(parents=True, exist_ok=True)
        self.voices, self.engine = voices, engine
        self.part_seconds, self.minimum_free = part_seconds, minimum_free
        self.lock = threading.RLock()
        self.pending = queue.Queue()
        self.cancellations = {}
        self.closed = threading.Event()
        self.thread = None
        # Processes do not survive a published filesystem snapshot or restart.
        for folder in self.root.iterdir():
            if not folder.is_dir() or not (folder / 'job.json').is_file():
                continue
            job = self._read(folder.name)
            if job['status'] in ACTIVE:
                job.update(status='cancelled', error='Phiên trước đã dừng. Bấm Tiếp tục để dùng lại các đoạn đã lưu.')
                self._save(job)

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._loop, name='hmoob-speech', daemon=True)
            self.thread.start()

    def close(self):
        self.closed.set()
        with self.lock:
            for event in self.cancellations.values():
                event.set()
        self.pending.put(None)

    def folder(self, ident):
        if not isinstance(ident, str) or len(ident) != 32 or any(c not in '0123456789abcdef' for c in ident):
            raise KeyError('Không tìm thấy tác vụ.')
        path = self.root / ident
        if not (path / 'job.json').is_file():
            raise KeyError('Không tìm thấy tác vụ.')
        return path

    def _read(self, ident):
        return json.loads((self.folder(ident) / 'job.json').read_text(encoding='utf-8'))

    def _save(self, job):
        job['updated_at'] = now()
        atomic_json(self.root / job['id'] / 'job.json', job)

    def _summary(self, job):
        result = dict(job)
        for private in ('reference',):
            result.pop(private, None)
        generated = job.get('new_audio_seconds', 0)
        measured = job.get('synthesis_seconds', 0)
        result['speed_factor'] = round(generated / measured, 2) if measured > 0 and generated else None
        completed = job['completed_segments']
        # Estimate only after enough work; it is a measurement, never a guarantee.
        result['estimated_remaining_seconds'] = (round(measured / completed * (job['total_segments'] - completed))
                                                  if completed >= 3 and measured > 0 else None)
        return result

    def get(self, ident):
        with self.lock:
            return self._summary(self._read(ident))

    def list(self):
        with self.lock:
            records = [self._read(p.name) for p in self.root.iterdir()
                       if p.is_dir() and (p / 'job.json').is_file()]
            return [self._summary(j) for j in sorted(records, key=lambda j: j['created_at'], reverse=True)[:100]]

    def _ensure_capacity(self):
        if sum(item['status'] in ACTIVE for item in self.list()) >= 4:
            raise ValueError('Hàng đợi tối đa 4 tác vụ. Chờ hoặc dừng một tác vụ trước.')
        if shutil.disk_usage(self.root).free < self.minimum_free:
            raise ValueError('Thiếu dung lượng đĩa. Giải phóng chỗ trước khi tạo/tiếp tục giọng.')

    def create(self, payload):
        text, voice, quality, speed = validate_options(payload)
        with self.lock:
            self._ensure_capacity()
            ident = uuid.uuid4().hex
            folder = self.root / ident
            folder.mkdir()
            try:
                reference = self.voices.snapshot(voice, folder / 'reference.wav')
                (folder / 'text.txt').write_text(text, encoding='utf-8', newline='')
                spans = plan(text)
                atomic_json(folder / 'plan.json', {'version': PLANNER_VERSION, 'chunk_characters': CHUNK_CHARACTERS,
                                                  'spans': spans})
                (folder / 'chunks').mkdir()
                (folder / 'parts').mkdir()
                job = {'id': ident, 'status': 'queued', 'created_at': now(), 'voice': voice,
                       'quality': quality, 'speed': speed, 'characters': len(text),
                       'total_segments': len(spans), 'completed_segments': 0, 'completed_characters': 0,
                       'audio_seconds': 0, 'processing_seconds': 0, 'synthesis_seconds': 0,
                       'new_audio_seconds': 0, 'progress': 0, 'error': '', 'parts': [],
                       'reference': reference, 'planner_version': PLANNER_VERSION}
                self._save(job)
                self.cancellations[ident] = threading.Event()
                self.pending.put(ident)
            except Exception:
                shutil.rmtree(folder)
                raise
            return self._summary(job)

    def cancel(self, ident):
        with self.lock:
            job = self._read(ident)
            if job['status'] in ACTIVE:
                self.cancellations.setdefault(ident, threading.Event()).set()
                job['status'] = 'cancelled' if job['status'] == 'queued' else 'cancelling'
                self._save(job)
            return self._summary(job)

    def resume(self, ident):
        with self.lock:
            job = self._read(ident)
            if job['status'] not in ('cancelled', 'error'):
                raise ValueError('Chỉ tiếp tục tác vụ đã dừng hoặc có lỗi.')
            self._ensure_capacity()
            self.cancellations[ident] = threading.Event()
            job.update(status='queued', error='')
            self._save(job)
            self.pending.put(ident)
            return self._summary(job)

    def _loop(self):
        while not self.closed.is_set():
            ident = self.pending.get()
            if ident is None:
                return
            with self.lock:
                job = self._read(ident)
                if job['status'] != 'queued':
                    continue
                event = self.cancellations[ident]
                job.update(status='running', error='')
                self._save(job)
            self._run(job, event)

    def _run(self, job, event):
        folder = self.folder(job['id'])
        started = time.monotonic()
        old_processing = job.get('processing_seconds', 0)
        chapter, chapter_seconds, part_number = [], 0.0, 1
        parts = []
        audio_seconds = 0.0
        completed = 0

        def checkpoint(status=None, error=''):
            with self.lock:
                # Keep a concurrently requested cancellation visible to pollers.
                current = self._read(job['id'])
                job.update(status=status or ('cancelling' if current['status'] == 'cancelling' else 'running'),
                           completed_segments=completed, audio_seconds=round(audio_seconds, 3),
                           processing_seconds=round(old_processing + time.monotonic() - started, 3),
                           progress=100 if status == 'done' else min(99, int(100 * completed / job['total_segments'])),
                           parts=list(parts), error=error)
                self._save(job)

        def publish_chapter():
            nonlocal chapter, chapter_seconds, part_number
            if not chapter:
                return
            name = f'chapter-{part_number:04d}.wav'
            duration = assemble(chapter, folder / 'parts' / name)
            parts.append({'name': name, 'url': f'/api/jobs/{job["id"]}/parts/{name}',
                          'audio_seconds': round(duration, 3)})
            part_number += 1
            chapter, chapter_seconds = [], 0.0

        try:
            # Path.read_text normalizes CRLF. Use open(newline='') for saved offsets.
            with (folder / 'text.txt').open(encoding='utf-8', newline='') as source:
                text = source.read()
            saved_plan = json.loads((folder / 'plan.json').read_text(encoding='utf-8'))
            if saved_plan['version'] != PLANNER_VERSION:
                raise ValueError('Phiên bản chia đoạn khác. Giữ bản tool đã tạo tác vụ để tiếp tục.')
            spans = saved_plan['spans']
            for index, span in enumerate(spans):
                if self.closed.is_set() or event.is_set():
                    checkpoint('cancelled')
                    return
                segment = text[span['start']:span['end']].strip()
                if segment:
                    path = folder / 'chunks' / f'{index:07d}.wav'
                    if path.exists():
                        frames, rate = inspect_wav(path)
                    else:
                        if shutil.disk_usage(folder).free < self.minimum_free:
                            raise ValueError('Đĩa gần đầy. Các đoạn đã xong được giữ lại; giải phóng chỗ rồi Tiếp tục.')
                        tick = time.monotonic()
                        samples, rate = self.engine.synthesize(segment, folder / 'reference.wav',
                                                                job['reference']['text'], speed=job['speed'],
                                                                quality=job['quality'])
                        frames, rate = write_samples(path, samples, rate)
                        elapsed = time.monotonic() - tick
                        job['synthesis_seconds'] += elapsed
                        job['new_audio_seconds'] += frames / rate
                    duration = frames / rate
                    if chapter and chapter_seconds + duration > self.part_seconds:
                        publish_chapter()
                    chapter.append(path)
                    chapter_seconds += duration
                    audio_seconds += duration
                completed = index + 1
                job['completed_characters'] = span['end']
                checkpoint()
            publish_chapter()
            if not parts:
                raise ValueError('Chưa tạo được âm thanh. Kiểm tra nội dung và mô hình.')
            checkpoint('done')
            # Completed chapters are the durable output; avoid retaining a second
            # full document of PCM checkpoints after successful publication.
            try:
                shutil.rmtree(folder / 'chunks')
                (folder / 'chunks').mkdir()
            except OSError:
                # Completed chapter files already contain the full recording.
                # A leftover cache must not turn a successful read into an error.
                pass
        except Exception as exc:
            checkpoint('error', str(exc)[:1200] or 'Không tạo được giọng. Các đoạn đã xong vẫn được giữ lại.')
