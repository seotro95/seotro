"""Bounded generation jobs. Each worker can be terminated independently."""
import asyncio
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import uuid
from fastapi import HTTPException

WORKER = Path(__file__).with_name('voice_worker.py')
JOBS = {}


def view(job):
    return {k: job[k] for k in ('id', 'status', 'message')}


def stop_process(process):
    if process.returncode is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, subprocess.SubprocessError):
        pass


async def run(job, payload):
    process = None
    spawning = None
    try:
        folder = Path(job['temp'].name)
        options = {'start_new_session': True} if os.name != 'nt' else {}
        with (folder / 'worker.log').open('wb') as log:
            spawning = asyncio.create_task(asyncio.create_subprocess_exec(sys.executable, str(WORKER), str(folder),
                stdin=asyncio.subprocess.PIPE, stdout=log, stderr=log, **options))
            process = await asyncio.shield(spawning)
            job['process'] = process
            if job['status'] == 'cancelled':
                stop_process(process)
            await process.communicate(json.dumps(payload).encode())
        if job['status'] == 'cancelled':
            return
        result_file = folder / 'result.json'
        result = json.loads(result_file.read_text()) if result_file.exists() else {'error': 'Bộ máy tạo giọng đã dừng bất thường. Kiểm tra cấu hình và thư viện AI.'}
        if process.returncode != 0 or result.get('error'):
            job.update(status='failed', message=result.get('error', 'Không tạo được giọng.'))
        else:
            audio = folder / 'audio.bin'
            if not audio.exists() or not 0 < audio.stat().st_size <= 50*1024*1024:
                job.update(status='failed', message='Không nhận được âm thanh hợp lệ.')
            else:
                job.update(status='completed', message='Đã tạo voice. Bạn có thể nghe và tải WAV.', media_type=result['media_type'])
    except asyncio.CancelledError:
        job.update(status='cancelled', message='Đã dừng tạo voice.')
        if process is None and spawning is not None:
            process = await spawning
        if process:
            stop_process(process)
            await process.wait()
        raise
    except Exception:
        job.update(status='failed', message='Không khởi động được bộ máy tạo voice.')
    finally:
        if process is not None and process.returncode is None:
            stop_process(process)
            await process.wait()
        job.pop('process', None)


def get(job_id):
    if job_id not in JOBS:
        raise HTTPException(404, 'Không tìm thấy tác vụ. Máy chủ có thể đã khởi động lại.')
    return JOBS[job_id]


def create(payload):
    if any(j['status'] == 'running' for j in JOBS.values()):
        raise HTTPException(409, 'Đang có tác vụ tạo voice. Dừng hoặc chờ hoàn tất trước.')
    while len(JOBS) >= 10:
        key = next(k for k,v in JOBS.items() if v['status'] != 'running')
        JOBS.pop(key)['temp'].cleanup()
    job = {'id': uuid.uuid4().hex, 'status': 'running', 'message': 'Đang tạo voice…', 'temp': tempfile.TemporaryDirectory(prefix='hmong-voice-')}
    JOBS[job['id']] = job
    job['task'] = asyncio.create_task(run(job, payload))
    return view(job)


async def cancel(job_id):
    job = get(job_id)
    if job['status'] == 'running':
        job.update(status='cancelled', message='Đã dừng tạo voice.')
        job['task'].cancel()
        try:
            await job['task']
        except asyncio.CancelledError:
            pass
    return view(job)


async def shutdown():
    for key in list(JOBS):
        await cancel(key)
        JOBS[key]['temp'].cleanup()
    JOBS.clear()
