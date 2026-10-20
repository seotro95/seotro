"""Bounded jobs with one reusable, isolated and independently cancellable worker."""
import asyncio
import json
import math
import os
import re
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import wave
from fastapi import HTTPException

WORKER = Path(__file__).with_name('voice_worker.py')
JOBS = {}
_WORKER_STATE = None
_WORKER_LOCK = None
_PRELOAD_TASKS = set()
_AUDIO_TYPES = {'audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/ogg'}
# 24 hours of 24 kHz mono PCM16, allowing FFmpeg's small WAV metadata chunks.
MAX_WAV_BYTES = 24 * 60 * 60 * 24000 * 2 + 64 * 1024
_ACTIVE_STATUSES = {'running', 'paused'}


def _write_control(job, paused):
    """Publish a new request; only a matching worker acknowledgement pauses time."""
    revision = job.get('_control_revision', 0) + 1
    path = Path(job['temp'].name) / 'control.json'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.control-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump({'revision': revision, 'paused': paused}, stream)
    try:
        for attempt in range(4):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(.01)
    finally:
        temporary.unlink(missing_ok=True)
    job['_control_revision'] = revision
    job['pause_requested'] = paused


def _end_pause(job, at=None):
    started = job.pop('_pause_started_at', None)
    if started is not None:
        at = time.monotonic() if at is None else at
        job['_paused_seconds'] = job.get('_paused_seconds', 0.0) + max(0, at - started)


def _refresh_control(job):
    if job['status'] not in _ACTIVE_STATUSES:
        return
    try:
        ack = _read_json(Path(job['temp'].name) / 'control-ack.json')
        revision, paused = ack.get('revision'), ack.get('paused')
        if (isinstance(revision, bool) or not isinstance(revision, int)
                or revision != job.get('_control_revision', 0) or not isinstance(paused, bool)
                or paused != job.get('pause_requested', False)):
            return
        acknowledged_at = _number(ack.get('at_monotonic'))
        now = time.monotonic()
        if not job['started_at'] <= acknowledged_at <= now + .1:
            return
        acknowledged_at = min(now, acknowledged_at)
        if paused:
            job.setdefault('_pause_started_at', acknowledged_at)
            job.update(status='paused', phase='paused', active_workers=0,
                       message='Đã tạm dừng ở ranh giới đoạn. Bấm Tiếp tục để tạo tiếp.')
        else:
            _end_pause(job, acknowledged_at)
            job['status'] = 'running'
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        pass


def _lock():
    global _WORKER_LOCK
    if _WORKER_LOCK is None:
        _WORKER_LOCK = asyncio.Lock()
    return _WORKER_LOCK


def _read_json(path):
    if path.stat().st_size > 16 * 1024:
        raise ValueError('oversized worker metadata')
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('invalid worker metadata')
    return data


def _number(value, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0
            or (maximum is not None and value > maximum)):
        raise ValueError('invalid progress value')
    return value


def _refresh_progress(job):
    if job['status'] not in _ACTIVE_STATUSES:
        return
    _refresh_control(job)
    try:
        info = _read_json(Path(job['temp'].name) / 'progress.json')
        progress = _number(info['progress'], 100)
        completed = info.get('completed_units', 0)
        total = info.get('total_units', 0)
        if (isinstance(completed, bool) or not isinstance(completed, int)
                or isinstance(total, bool) or not isinstance(total, int)
                or not 0 <= completed <= total <= 1000000):
            raise ValueError('invalid progress units')
        generated = _number(info.get('generated_seconds', 0), 24 * 60 * 60)
        phase = info.get('phase', 'generating')
        if not isinstance(phase, str) or not phase or len(phase) > 80 or any(ord(c) < 32 for c in phase):
            raise ValueError('invalid progress phase')
        metrics = {}
        for key in ('synthesized_seconds', 'reused_seconds'):
            if key in info:
                metrics[key] = _number(info[key], 24 * 60 * 60)
        for key, maximum in (('cache_hits', 1000000), ('active_workers', 1), ('batch_size', 1)):
            if key in info:
                value = info[key]
                if (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum
                        or (key == 'batch_size' and value != 1)):
                    raise ValueError('invalid worker metric')
                metrics[key] = value
        if job['status'] == 'paused':
            phase = 'paused'
            metrics['active_workers'] = 0
        elif phase == 'paused':
            # A progress file cannot acknowledge suspension or a stale pause.
            phase = 'resuming' if not job.get('pause_requested') else 'pausing'
        job.update(progress=max(job['progress'], min(99, progress)), phase=phase,
                   completed_units=completed, total_units=total,
                   generated_seconds=generated, **metrics)
        runtime = _validated_runtime(info.get('runtime'))
        if runtime:
            job['runtime'] = runtime
            if _WORKER_STATE is not None and job.get('process') is _WORKER_STATE['process']:
                _WORKER_STATE['runtime'] = runtime
        message = info.get('message')
        if job['status'] != 'paused' and isinstance(message, str) and 0 < len(message) <= 1000:
            job['message'] = message
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        # A missing or malformed progress update must never complete a job.
        pass


def view(job):
    _refresh_progress(job)
    end = job.get('finished_at', time.monotonic())
    elapsed = max(0.0, end - job['started_at'])
    paused = job.get('_paused_seconds', 0.0)
    if '_pause_started_at' in job:
        paused += max(0.0, end - job['_pause_started_at'])
    active = max(0.0, elapsed - paused)
    completed, total = job['completed_units'], job['total_units']
    estimate = job.get('_estimated_total_seconds')
    if estimate is None and completed > 0 and total >= completed and job['generated_seconds'] > 0:
        estimate = job['generated_seconds'] * total / completed
    if job['status'] == 'completed':
        estimate = job.get('audio_duration_seconds') or job['generated_seconds'] or estimate
    eta = (active * (total - completed) / completed
           if completed > 0 and total > completed and job['status'] in _ACTIVE_STATUSES else None)
    if job['status'] == 'completed':
        eta = 0.0
    new_seconds = job.get('synthesized_seconds', 0.0)
    speed = new_seconds / active if active > 0 and new_seconds > 0 else None
    return {**{k: job[k] for k in ('id', 'status', 'message', 'progress', 'phase',
                'completed_units', 'total_units', 'generated_seconds', 'audio_bytes', 'runtime')},
            'elapsed_seconds': round(elapsed, 2), 'active_elapsed_seconds': round(active, 3),
            'paused_seconds': round(paused, 3), 'pause_requested': job.get('pause_requested', False),
            'synthesized_seconds': new_seconds, 'reused_seconds': job.get('reused_seconds', 0.0),
            'cache_hits': job.get('cache_hits', 0), 'batch_size': job.get('batch_size', 1),
            'active_workers': (0 if job['status'] not in _ACTIVE_STATUSES or '_pause_started_at' in job
                               else job.get('active_workers', 0)),
            'speed_multiplier': round(speed, 4) if speed is not None else None,
            'estimated_total_seconds': round(estimate, 3) if estimate is not None else None,
            'eta_seconds': round(eta, 3) if eta is not None else None}


def _validated_runtime(info):
    if not isinstance(info, dict) or not isinstance(info.get('loaded'), bool):
        return {}
    device, precision, references = (info.get(key) for key in
                                    ('device', 'precision', 'reference_cache_entries'))
    if (not isinstance(device, str) or not re.fullmatch(r'(?:auto|cpu|mps|cuda(?::[0-9]{1,3})?)', device)
            or not isinstance(precision, str)
            or precision not in {'auto', 'float32', 'float32_int8_flow', 'float16', 'float16_autocast',
                                 'bfloat16', 'bfloat16_autocast'}
            or isinstance(references, bool) or not isinstance(references, int)
            or not 0 <= references <= 1000000):
        return {}
    runtime = {'loaded': info['loaded'], 'device': device, 'precision': precision,
               'reference_cache_entries': references}
    mode = info.get('compute_mode')
    if isinstance(mode, str) and mode in {'standard', 'fast', 'ultra'}:
        runtime['compute_mode'] = mode
    offloaded = info.get('text_embedding_offloaded')
    if isinstance(offloaded, bool):
        runtime['text_embedding_offloaded'] = offloaded
    return runtime


def worker_runtime():
    """Return the last measured child state without querying/importing its model."""
    if _WORKER_STATE is None or _WORKER_STATE['process'].returncode is not None:
        return {}
    return dict(_WORKER_STATE.get('runtime', {}))


def stop_process(process):
    if process.returncode is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, timeout=10)
            if process.returncode is None:
                process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, OSError, subprocess.SubprocessError):
        pass


async def _dispose_worker(state):
    global _WORKER_STATE
    if state is None:
        return
    if _WORKER_STATE is state:
        _WORKER_STATE = None
    stop_process(state['process'])
    await state['process'].wait()
    state['temp'].cleanup()


async def _worker():
    global _WORKER_STATE
    source = str(Path(WORKER).resolve())
    if _WORKER_STATE is not None:
        if (_WORKER_STATE['process'].returncode is None
                and _WORKER_STATE['source'] == source):
            return _WORKER_STATE
        await _dispose_worker(_WORKER_STATE)
    folder = tempfile.TemporaryDirectory(prefix='hmong-engine-')
    options = {'start_new_session': True} if os.name != 'nt' else {}
    spawning = None
    process = None
    try:
        with (Path(folder.name) / 'worker.log').open('wb') as log:
            spawning = asyncio.create_task(asyncio.create_subprocess_exec(
                sys.executable, source, stdin=asyncio.subprocess.PIPE,
                stdout=log, stderr=log, **options))
            process = await asyncio.shield(spawning)
        _WORKER_STATE = {'process': process, 'temp': folder, 'source': source, 'runtime': {}}
        return _WORKER_STATE
    except BaseException:
        # Cancellation can arrive between child creation and the awaited return.
        # Always recover ownership of that child before propagating cancellation.
        if process is None and spawning is not None:
            try:
                process = await spawning
            except Exception:
                pass
        if process is not None:
            stop_process(process)
            await process.wait()
        folder.cleanup()
        raise


async def preload():
    """Warm the same bounded worker, without creating a synthetic audio job."""
    task = asyncio.current_task()
    _PRELOAD_TASKS.add(task)
    state = None
    try:
        async with _lock():
            state = await _worker()
            with tempfile.TemporaryDirectory(prefix='hmong-preload-') as folder:
                folder = Path(folder)
                process = state['process']
                process.stdin.write((json.dumps({'action': 'preload', 'folder': str(folder)}) + '\n').encode())
                await process.stdin.drain()
                result_file = folder / 'result.json'
                while not result_file.exists():
                    if process.returncode is not None:
                        raise RuntimeError('preload worker exited without result')
                    await asyncio.sleep(.1)
                result = _read_json(result_file)
                state['runtime'] = _validated_runtime(result.get('runtime'))
                reason = result.get('error')
                if isinstance(reason, str) and reason:
                    print('Chưa nạp sẵn mô hình: ' + reason[:1000], file=sys.stderr, flush=True)
                return dict(state['runtime'])
    except asyncio.CancelledError:
        if state is not None:
            await _dispose_worker(state)
        raise
    except Exception:
        if state is not None:
            await _dispose_worker(state)
        return {}
    finally:
        _PRELOAD_TASKS.discard(task)


def _valid_audio(path, media_type):
    if media_type not in _AUDIO_TYPES or not path.is_file():
        return False
    size = path.stat().st_size
    if not 0 < size <= (MAX_WAV_BYTES if media_type in {'audio/wav', 'audio/x-wav'} else 50 * 1024 * 1024):
        return False
    if media_type not in {'audio/wav', 'audio/x-wav'}:
        return True
    try:
        with path.open('rb') as stream, wave.open(stream, 'rb') as audio:
            frames = audio.getnframes()
            frame_bytes = audio.getnchannels() * audio.getsampwidth()
            return (frames > 0 and audio.getframerate() > 0
                    and frames / audio.getframerate() <= 24 * 60 * 60
                    and stream.tell() + frames * frame_bytes <= size
                    and len(audio.readframes(1)) == frame_bytes)
    except (OSError, EOFError, wave.Error):
        return False


def _discard_partial_audio(job):
    # All paths are inside this job's private directory. Call only after the
    # owned process has exited so Windows has released its native file handles.
    folder = Path(job['temp'].name)
    for path in [folder / 'audio.bin', *folder.glob('.hmong-voice-*.part')]:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    scratch = [*folder.glob('hmong-timeline-*'), *folder.glob('.audio-clean-*')]
    for path in scratch:
        try:
            if path.is_symlink():
                path.unlink()
            else:
                shutil.rmtree(path)
        except OSError:
            pass


def _finish(job, status, message):
    _end_pause(job)
    job.update(status=status, message=message, phase=status,
               finished_at=time.monotonic(), pause_requested=False, active_workers=0)
    if status in {'cancelled', 'failed'}:
        job['runtime'] = {}


async def run(job, payload):
    state = None
    try:
        # The lock also prevents a replacement job racing a cancellation that is
        # still terminating the old process tree.
        async with _lock():
            if job['status'] == 'cancelled':
                return
            state = await _worker()
            process = state['process']
            job['process'] = process
            job['runtime'] = worker_runtime()
            job['phase'] = 'loading'
            folder = Path(job['temp'].name)
            request = {'folder': str(folder), 'payload': payload}
            process.stdin.write((json.dumps(request, ensure_ascii=True) + '\n').encode('utf-8'))
            await process.stdin.drain()
            result_file = folder / 'result.json'
            while not result_file.exists():
                _refresh_progress(job)
                if process.returncode is not None:
                    raise RuntimeError('worker exited without a result')
                await asyncio.sleep(0.1)
            _refresh_progress(job)
            result = _read_json(result_file)
            if result.get('error'):
                message = result['error']
                if not isinstance(message, str) or not message or len(message) > 4000:
                    raise ValueError('invalid worker error')
                _finish(job, 'failed', message)
                await _dispose_worker(state)
                _discard_partial_audio(job)
                return
            media_type = result.get('media_type')
            audio = folder / 'audio.bin'
            if not _valid_audio(audio, media_type):
                _finish(job, 'failed', 'Không nhận được âm thanh hợp lệ.')
                await _dispose_worker(state)
                _discard_partial_audio(job)
                return
            state['runtime'] = _validated_runtime(result.get('runtime'))
            job.update(media_type=media_type, progress=100, audio_bytes=audio.stat().st_size,
                       runtime=worker_runtime())
            if media_type in {'audio/wav', 'audio/x-wav'}:
                with wave.open(str(audio), 'rb') as reader:
                    job['audio_duration_seconds'] = reader.getnframes() / reader.getframerate()
            _finish(job, 'completed', 'Đã tạo voice. Bạn có thể nghe và tải WAV.')
    except asyncio.CancelledError:
        _finish(job, 'cancelled', 'Đã dừng tạo voice.')
        if state is not None:
            await _dispose_worker(state)
        job['temp'].cleanup()
        raise
    except Exception:
        _finish(job, 'failed', 'Bộ máy tạo giọng đã dừng bất thường. Kiểm tra cấu hình và thư viện AI.')
        if state is not None:
            await _dispose_worker(state)
        _discard_partial_audio(job)
    finally:
        job.pop('process', None)


def get(job_id):
    if job_id not in JOBS:
        raise HTTPException(404, 'Không tìm thấy tác vụ. Máy chủ có thể đã khởi động lại.')
    return JOBS[job_id]


def create(payload, *, estimated_total_seconds=None):
    if any(j['status'] in _ACTIVE_STATUSES for j in JOBS.values()):
        raise HTTPException(409, 'Đang có tác vụ tạo voice. Dừng hoặc chờ hoàn tất trước.')
    while len(JOBS) >= 10:
        key = next((k for k, value in JOBS.items()
                    if value['status'] not in _ACTIVE_STATUSES and not value.get('_mp3_export_active')
                    and not value.get('_downloads_active')), None)
        if key is None:
            raise HTTPException(409, 'Các kết quả đang xuất hoặc tải. Chờ tải xong trước khi tạo lượt mới.')
        JOBS.pop(key)['temp'].cleanup()
    job = {'id': uuid.uuid4().hex, 'status': 'running', 'message': 'Đang tạo voice…',
           'temp': tempfile.TemporaryDirectory(prefix='hmong-voice-'),
           'started_at': time.monotonic(), 'progress': 0, 'phase': 'queued',
           'completed_units': 0, 'total_units': 0, 'generated_seconds': 0, 'audio_bytes': 0, 'runtime': {},
           'synthesized_seconds': 0.0, 'reused_seconds': 0.0, 'cache_hits': 0,
           'active_workers': 0, 'batch_size': 1, 'pause_requested': False,
           '_paused_seconds': 0.0, '_control_revision': 0}
    if estimated_total_seconds is not None:
        try:
            estimate = _number(estimated_total_seconds, 24 * 60 * 60)
            if estimate > 0:
                job['_estimated_total_seconds'] = estimate
        except ValueError:
            job['temp'].cleanup()
            raise HTTPException(422, 'Thời lượng dự kiến không hợp lệ.') from None
    JOBS[job['id']] = job
    job['task'] = asyncio.create_task(run(job, payload))
    return view(job)


async def cancel(job_id):
    job = get(job_id)
    if job['status'] in _ACTIVE_STATUSES:
        _finish(job, 'cancelled', 'Đã dừng tạo voice.')
        job['task'].cancel()
        try:
            await job['task']
        except asyncio.CancelledError:
            pass
        job['temp'].cleanup()
    return view(job)


async def pause(job_id):
    job = get(job_id)
    _refresh_progress(job)
    if job['status'] == 'running' and not job.get('pause_requested'):
        _write_control(job, True)
        job.update(phase='pausing', message='Đang chờ hết phần đang xử lý để tạm dừng an toàn…')
    return view(job)


async def resume(job_id):
    job = get(job_id)
    _refresh_progress(job)
    if job['status'] in _ACTIVE_STATUSES and (job.get('pause_requested') or '_pause_started_at' in job):
        _write_control(job, False)
        job.update(status='running', phase='resuming', message='Đang tiếp tục tạo voice…')
    return view(job)


async def shutdown():
    global _WORKER_LOCK
    tasks = []
    for task in tuple(_PRELOAD_TASKS):
        if task is not asyncio.current_task() and not task.done():
            task.cancel()
            tasks.append(task)
    for job in list(JOBS.values()):
        task = job['task']
        if not task.done():
            if job['status'] in _ACTIVE_STATUSES:
                _finish(job, 'cancelled', 'Đã dừng tạo voice.')
            task.cancel()
        tasks.append(task)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    async with _lock():
        await _dispose_worker(_WORKER_STATE)
    for job in JOBS.values():
        job['temp'].cleanup()
    JOBS.clear()
    _WORKER_LOCK = None
