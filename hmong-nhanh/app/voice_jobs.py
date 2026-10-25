"""Durable recording jobs with one reusable, cancellable inference worker."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import uuid
import wave

from fastapi import HTTPException

BASE = Path(__file__).resolve().parent
WORKER = BASE / 'voice_worker.py'
JOBS = {}
_loaded_root = None
_warm_worker = None
_worker_log = None
ID_PATTERN = re.compile(r'[0-9a-f]{32}')
PART_PATTERN = re.compile(r'part-([0-9]{4,8})\.wav')
STATES = {'running', 'completed', 'failed', 'cancelled'}
DETAILS = ('title', 'voice', 'voice_name', 'quality', 'style', 'speed', 'characters', 'benchmark',
           'timing', 'source_format', 'spoken_characters', 'target_seconds', 'first_speech_seconds')
METRICS = ('completed', 'total', 'progress', 'elapsed_seconds', 'audio_seconds',
           'throughput', 'estimated_seconds_for_hour', 'device')


def now():
    return datetime.now(timezone.utc).isoformat()


def data_root():
    return (Path(os.getenv('HMONG_STUDIO_DATA_DIR', str(BASE / '.data'))) / 'jobs').resolve()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.pending')
    try:
        with temporary.open('w', encoding='utf-8') as output:
            json.dump(value, output, ensure_ascii=False, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path, limit=16 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Invalid state file')
    with path.open(encoding='utf-8') as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError('Invalid state data')
    return value


def persist(job):
    job['updated_at'] = now()
    metadata = {key: job[key] for key in ('id', 'status', 'message', 'created_at', 'updated_at')}
    metadata.update({key: job[key] for key in DETAILS if key in job})
    atomic_json(job['folder'] / 'metadata.json', metadata)


def _restore(folder):
    if folder.is_symlink() or not folder.is_dir() or not ID_PATTERN.fullmatch(folder.name):
        return None
    try:
        metadata = read_json(folder / 'metadata.json', 65536)
        if metadata.get('id') != folder.name or metadata.get('status') not in STATES:
            return None
        job = {key: metadata.get(key, '') for key in ('id', 'status', 'message', 'created_at', 'updated_at')}
        job['folder'] = folder
        job.update({key: metadata[key] for key in DETAILS if key in metadata})
        if not job.get('title') or 'first_speech_seconds' not in job:
            try:
                from documents import parse_document
                source = read_json(folder / 'input.json')
                document = parse_document(source['text'], timing='natural')
                job['title'] = job.get('title') or ' '.join(document['text'].split())[:120]
                job['first_speech_seconds'] = (document['cues'][0]['start']
                    if source.get('timing', 'auto') != 'natural' and document['cues'] else 0)
            except (OSError, ValueError, KeyError, TypeError):
                job['title'] = 'Bản đọc đã lưu'
        if job['status'] == 'running':
            job.update(status='cancelled', message='Phiên trước đã dừng. Bấm Tiếp tục để đọc tiếp từ đoạn đã lưu.')
            persist(job)
        return job
    except (OSError, ValueError, TypeError):
        return None


def _active():
    return any(job['status'] == 'running' or (job.get('task') is not None and not job['task'].done())
               for job in JOBS.values())


def _load():
    global _loaded_root
    root = data_root()
    if _loaded_root == root:
        return
    if _active():
        raise HTTPException(409, 'Đang có tác vụ đọc. Dừng trước khi đổi thư mục dữ liệu.')
    root.mkdir(parents=True, exist_ok=True)
    JOBS.clear()
    for folder in root.iterdir():
        job = _restore(folder)
        if job is not None:
            JOBS[job['id']] = job
    _loaded_root = root


def get(ident):
    _load()
    if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident):
        raise HTTPException(404, 'Không tìm thấy bản đọc.')
    if ident not in JOBS:
        job = _restore(data_root() / ident)
        if job is not None:
            JOBS[ident] = job
    if ident not in JOBS:
        raise HTTPException(404, 'Không tìm thấy bản đọc.')
    return JOBS[ident]


def _parts(folder, values, verify=False):
    if not isinstance(values, list):
        return []
    result = []
    seen = set()
    for item in values:
        if not isinstance(item, dict):
            if verify:
                raise ValueError('Invalid audio part')
            continue
        number, filename, seconds = item.get('number'), item.get('filename'), item.get('seconds')
        match = PART_PATTERN.fullmatch(filename) if isinstance(filename, str) else None
        valid = (type(number) is int and number > 0 and match is not None and int(match.group(1)) == number
                 and number not in seen and isinstance(seconds, (int, float)) and not isinstance(seconds, bool)
                 and math.isfinite(seconds) and seconds > 0)
        path = folder / 'parts' / filename if match else None
        valid = valid and not (folder / 'parts').is_symlink() and path.is_file() and not path.is_symlink()
        if not valid:
            if verify:
                raise ValueError('Missing or invalid audio part')
            continue
        if verify:
            try:
                with wave.open(str(path), 'rb') as audio:
                    rate = audio.getframerate()
                    frames = audio.getnframes()
                    if (audio.getnchannels() != 1 or audio.getsampwidth() != 2 or not 8000 <= rate <= 96000
                            or frames <= 0 or path.stat().st_size < frames * 2 + 44
                            or abs(frames / rate - seconds) > max(.05, 1 / rate)
                            or len(audio.readframes(min(frames, 32))) != min(frames, 32) * 2):
                        raise ValueError('Invalid WAV')
            except (OSError, wave.Error, EOFError) as exc:
                raise ValueError('Invalid WAV') from exc
        seen.add(number)
        result.append({'number': number, 'filename': filename, 'seconds': seconds})
    return result


def view(job):
    public = {key: job.get(key, '') for key in ('id', 'status', 'message', 'created_at', 'updated_at')}
    public.update({key: job[key] for key in DETAILS if key in job})
    public.update(completed=0, total=0, progress=0, elapsed_seconds=0, audio_seconds=0,
                  throughput=None, estimated_seconds_for_hour=None, parts=[])
    filename = 'result.json' if job['status'] == 'completed' else 'progress.json'
    try:
        data = read_json(job['folder'] / filename)
    except (OSError, ValueError, TypeError):
        data = {}
    if job['status'] == 'running' and isinstance(data.get('message'), str):
        public['message'] = data['message'][:1000]
    for key in ('alignment', 'source_format'):
        if isinstance(data.get(key), str):
            public[key] = data[key][:80]
    if isinstance(data.get('warnings'), list):
        public['warnings'] = [value[:500] for value in data['warnings'][:20] if isinstance(value, str)]
    for key in METRICS:
        value = data.get(key)
        if key == 'device':
            if isinstance(value, str):
                public[key] = value[:80]
        elif value is None and key in ('throughput', 'estimated_seconds_for_hour'):
            public[key] = None
        elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            public[key] = value
    public['progress'] = min(100 if job['status'] == 'completed' else 99, public['progress'])
    if job['status'] == 'completed':
        public['progress'] = 100
    public['parts'] = _parts(job['folder'], data.get('parts', []))
    public['resumable'] = job['status'] in {'cancelled', 'failed'} and (job['folder'] / 'input.json').is_file()
    return public


def list_jobs():
    _load()
    return [view(job) for job in sorted(JOBS.values(), key=lambda item: item['created_at'], reverse=True)]


def stop_process(process):
    if process.returncode is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill()
        except ProcessLookupError:
            pass


async def _stop_worker():
    global _warm_worker, _worker_log
    process, log = _warm_worker, _worker_log
    _warm_worker = None
    _worker_log = None
    if process is not None:
        await asyncio.to_thread(stop_process, process)
        await process.wait()
    if log is not None:
        log.close()


async def _ensure_worker():
    global _warm_worker, _worker_log
    if _warm_worker is not None and _warm_worker.returncode is None:
        return _warm_worker
    await _stop_worker()
    log = (data_root() / 'worker.log').open('ab', buffering=0)
    options = {'start_new_session': True} if os.name != 'nt' else {}
    spawning = asyncio.create_task(asyncio.create_subprocess_exec(
        sys.executable, str(WORKER), '--serve', stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=log, limit=65536, **options))
    try:
        process = await asyncio.shield(spawning)
    except asyncio.CancelledError:
        try:
            process = await spawning
            await asyncio.to_thread(stop_process, process)
            await process.wait()
        finally:
            log.close()
        raise
    except Exception:
        log.close()
        raise
    _warm_worker, _worker_log = process, log
    return process


def _validate_result(job):
    result = read_json(job['folder'] / 'result.json')
    if result.get('error'):
        raise ValueError(str(result['error'])[:1000])
    parts = _parts(job['folder'], result.get('parts'), verify=True)
    if not parts or len(parts) != len(result.get('parts', [])):
        raise ValueError('Không có các phần âm thanh hoàn tất để tải.')
    if type(result.get('completed')) is not int or result['completed'] != result.get('total') or result['completed'] <= 0:
        raise ValueError('Bản đọc chưa xử lý hết văn bản.')
    return result


async def run(job):
    try:
        process = await _ensure_worker()
        job['process'] = process
        process.stdin.write((json.dumps({'folder': str(job['folder'])}) + '\n').encode('utf-8'))
        await process.stdin.drain()
        line = await process.stdout.readline()
        if not line:
            raise RuntimeError('Bộ máy tạo giọng đã dừng. Bấm Tiếp tục để dùng lại các đoạn đã lưu.')
        reply = json.loads(line)
        if not isinstance(reply, dict) or reply.get('ok') is not True:
            raise RuntimeError(str(reply.get('error', 'Không tạo được bản đọc. Bấm Tiếp tục để thử lại.'))[:1000])
        _validate_result(job)
        job.update(status='completed', message='Đã đọc xong toàn bộ văn bản. Nghe hoặc tải từng phần WAV.')
        persist(job)
    except asyncio.CancelledError:
        await _stop_worker()
        job.update(status='cancelled', message='Đã dừng. Các đoạn hoàn tất được giữ lại; bấm Tiếp tục để đọc tiếp.')
        persist(job)
        raise
    except Exception as exc:
        await _stop_worker()
        if job['status'] != 'cancelled':
            message = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else 'Không khởi động được bộ máy tạo giọng. Kiểm tra thư viện và dung lượng RAM.'
            job.update(status='failed', message=message[:1000])
            persist(job)
    finally:
        job.pop('process', None)


def _start(job):
    job.update(status='running', message='Đang tạo giọng; các đoạn hoàn tất được lưu để tiếp tục.')
    persist(job)
    job['task'] = asyncio.create_task(run(job))
    return view(job)


def create(payload):
    _load()
    if _active():
        raise HTTPException(409, 'Đang có bản đọc được xử lý. Dừng hoặc chờ hoàn tất trước.')
    if not isinstance(payload, dict) or not isinstance(payload.get('text'), str) or not payload['text'].strip() or len(payload['text']) > 1_000_000:
        raise HTTPException(422, 'Nhập từ 1 đến 1.000.000 ký tự để tạo giọng.')
    reference = payload.get('_reference')
    if not isinstance(reference, dict) or not isinstance(reference.get('text'), str) or not reference['text'].strip():
        raise HTTPException(422, 'Thiếu lời khớp mẫu giọng đã chọn.')
    source = Path(reference.get('path', ''))
    if not source.is_file():
        raise HTTPException(422, 'Không tìm thấy mẫu giọng đã chọn.')
    ident = uuid.uuid4().hex
    folder = data_root() / ident
    folder.mkdir()
    try:
        # Every job owns its reference. Editing or removing the library copy
        # cannot change a recording or prevent it from resuming later.
        shutil.copyfile(source, folder / 'reference.wav')
        snapshot = {**payload, '_reference': {'path': str(folder / 'reference.wav'), 'text': reference['text']}}
        atomic_json(folder / 'input.json', snapshot)
        job = {'id': ident, 'folder': folder, 'status': 'running', 'message': '',
               'created_at': now(), 'updated_at': now()}
        job.update({key: payload[key] for key in DETAILS if key in payload})
        job['characters'] = len(payload['text'])
        JOBS[ident] = job
        return _start(job)
    except Exception:
        JOBS.pop(ident, None)
        shutil.rmtree(folder, ignore_errors=True)
        raise


def resume(ident):
    job = get(ident)
    if job['status'] not in {'failed', 'cancelled'}:
        raise HTTPException(409, 'Chỉ tiếp tục bản đọc bị dừng hoặc gặp lỗi.')
    if _active():
        raise HTTPException(409, 'Đang có bản đọc được xử lý. Dừng hoặc chờ hoàn tất trước.')
    try:
        payload = read_json(job['folder'] / 'input.json')
        sample = job['folder'] / 'reference.wav'
        if sample.is_symlink() or not sample.is_file() or not payload.get('_reference', {}).get('text'):
            raise ValueError('missing reference')
        # Resolve the saved reference to this job even if the data folder moved.
        payload['_reference']['path'] = str(sample)
        atomic_json(job['folder'] / 'input.json', payload)
    except (OSError, ValueError, TypeError):
        raise HTTPException(409, 'Thiếu dữ liệu bản đọc đã lưu; không thể tiếp tục.') from None
    (job['folder'] / 'result.json').unlink(missing_ok=True)
    return _start(job)


def retry_natural(ident):
    """Make a separate recording using the failed job's frozen voice pair."""
    job = get(ident)
    if job['status'] != 'failed' or job.get('timing') not in {'auto', 'fit'}:
        raise HTTPException(409, 'Chỉ tạo lại đọc liền cho bản phụ đề đã gặp lỗi.')
    try:
        payload = read_json(job['folder'] / 'input.json')
        sample = job['folder'] / 'reference.wav'
        if sample.is_symlink() or not sample.is_file() or not payload.get('_reference', {}).get('text'):
            raise ValueError('Missing reference')
        payload['_reference']['path'] = str(sample)
        payload['timing'] = 'natural'
        payload['target_seconds'] = None
        payload['first_speech_seconds'] = 0
        payload['title'] = ('Đọc liền · ' + str(job.get('title') or 'Bản đọc đã lưu'))[:120]
    except (OSError, ValueError, TypeError):
        raise HTTPException(409, 'Thiếu dữ liệu bản đọc hoặc mẫu giọng đã lưu; không tự chuyển sang giọng khác.') from None
    return create(payload)


async def cancel(ident):
    job = get(ident)
    if job['status'] == 'running':
        job.update(status='cancelled', message='Đang dừng và giữ các đoạn đã hoàn tất…')
        persist(job)
        task = job.get('task')
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        # Handles a task cancelled before its coroutine ever started.
        await _stop_worker()
        job.update(status='cancelled', message='Đã dừng. Các đoạn hoàn tất được giữ lại; bấm Tiếp tục để đọc tiếp.')
        persist(job)
    return view(job)


async def shutdown():
    global _loaded_root
    for ident in list(JOBS):
        if JOBS[ident]['status'] == 'running':
            await cancel(ident)
    await _stop_worker()
    JOBS.clear()
    _loaded_root = None
