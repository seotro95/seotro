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
_AUDIO_TYPES = {'audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/ogg'}
# 24 hours of 24 kHz mono PCM16, allowing FFmpeg's small WAV metadata chunks.
MAX_WAV_BYTES = 24 * 60 * 60 * 24000 * 2 + 64 * 1024


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
    if job['status'] != 'running':
        return
    try:
        info = _read_json(Path(job['temp'].name) / 'progress.json')
        progress = _number(info['progress'], 100)
        completed = info.get('completed_units', 0)
        total = info.get('total_units', 0)
        if (isinstance(completed, bool) or not isinstance(completed, int)
                or isinstance(total, bool) or not isinstance(total, int)
                or not 0 <= completed <= total <= 1000000):
            raise ValueError('invalid progress units')
        generated = _number(info.get('generated_seconds', 0))
        phase = info.get('phase', 'generating')
        if not isinstance(phase, str) or not phase or len(phase) > 80 or any(ord(c) < 32 for c in phase):
            raise ValueError('invalid progress phase')
        job.update(progress=max(job['progress'], min(99, progress)), phase=phase,
                   completed_units=completed, total_units=total,
                   generated_seconds=generated)
        message = info.get('message')
        if isinstance(message, str) and 0 < len(message) <= 1000:
            job['message'] = message
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        # A missing or malformed progress update must never complete a job.
        pass


def view(job):
    _refresh_progress(job)
    elapsed = job.get('finished_at', time.monotonic()) - job['started_at']
    return {**{k: job[k] for k in ('id', 'status', 'message', 'progress', 'phase',
                'completed_units', 'total_units', 'generated_seconds', 'audio_bytes', 'runtime')},
            'elapsed_seconds': round(max(0, elapsed), 2)}


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
    if isinstance(mode, str) and mode in {'standard', 'fast'}:
        runtime['compute_mode'] = mode
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
    job.update(status=status, message=message, phase=status,
               finished_at=time.monotonic())
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


def create(payload):
    if any(j['status'] == 'running' for j in JOBS.values()):
        raise HTTPException(409, 'Đang có tác vụ tạo voice. Dừng hoặc chờ hoàn tất trước.')
    while len(JOBS) >= 10:
        key = next(k for k, value in JOBS.items() if value['status'] != 'running')
        JOBS.pop(key)['temp'].cleanup()
    job = {'id': uuid.uuid4().hex, 'status': 'running', 'message': 'Đang tạo voice…',
           'temp': tempfile.TemporaryDirectory(prefix='hmong-voice-'),
           'started_at': time.monotonic(), 'progress': 0, 'phase': 'queued',
           'completed_units': 0, 'total_units': 0, 'generated_seconds': 0, 'audio_bytes': 0, 'runtime': {}}
    JOBS[job['id']] = job
    job['task'] = asyncio.create_task(run(job, payload))
    return view(job)


async def cancel(job_id):
    job = get(job_id)
    if job['status'] == 'running':
        _finish(job, 'cancelled', 'Đã dừng tạo voice.')
        job['task'].cancel()
        try:
            await job['task']
        except asyncio.CancelledError:
            pass
        job['temp'].cleanup()
    return view(job)


async def shutdown():
    global _WORKER_LOCK
    tasks = []
    for job in list(JOBS.values()):
        task = job['task']
        if not task.done():
            if job['status'] == 'running':
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
