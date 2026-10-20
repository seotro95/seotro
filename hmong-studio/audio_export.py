"""File-backed, cancellable MP3 downloads for completed voice jobs.

The PCM result remains the authoritative lossless download. MP3 is generated on
demand with FFmpeg, never by loading a long recording into Python or JavaScript.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import wave

MAX_SECONDS = 24 * 60 * 60
_ACTIVE_TASKS = set()
_PROCESSES = set()


def _wav_info(path):
    try:
        size = path.stat().st_size
        with path.open('rb') as stream, wave.open(stream, 'rb') as reader:
            frames, rate = reader.getnframes(), reader.getframerate()
            channels, width = reader.getnchannels(), reader.getsampwidth()
            if (reader.getcomptype() != 'NONE' or not 0 < frames
                    or not 1 <= channels <= 8 or not 1 <= width <= 4
                    or not 0 < rate <= 384000 or frames / rate > MAX_SECONDS
                    or stream.tell() + frames * channels * width > size):
                raise ValueError('Tệp WAV không hợp lệ hoặc vượt giới hạn 24 giờ.')
            reader.setpos(frames - 1)
            if len(reader.readframes(1)) != channels * width:
                raise ValueError('Tệp WAV bị thiếu dữ liệu; chưa xuất MP3.')
        stat = path.stat()
        return frames / rate, (stat.st_size, stat.st_mtime_ns, frames, rate, channels, width)
    except (OSError, EOFError, wave.Error) as exc:
        raise ValueError('Không đọc được WAV hoàn chỉnh để xuất MP3.') from exc


def _tail(path, limit=4096):
    try:
        with path.open('rb') as stream:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - limit))
            return stream.read(limit).decode('utf-8', errors='replace').strip()
    except OSError:
        return ''


async def _stop(process):
    if process.returncode is not None:
        return
    try:
        if os.name == 'nt':
            killer = await asyncio.create_subprocess_exec(
                'taskkill', '/PID', str(process.pid), '/T', '/F',
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            try:
                await asyncio.wait_for(killer.wait(), timeout=10)
            except asyncio.TimeoutError:
                killer.kill()
                await killer.wait()
            if process.returncode is None:
                process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
    await process.wait()


async def _run_command(command, log_path, *, output_path=None, timeout=60):
    """Drain stderr to a bounded tail and retain ownership across cancellation."""
    options = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == 'nt' else {'start_new_session': True})
    process = None
    spawning = None
    draining = None
    output = None

    async def drain_stderr(stream):
        tail = bytearray()
        try:
            while chunk := await stream.read(65536):
                tail.extend(chunk)
                if len(tail) > 4096:
                    del tail[:-4096]
        finally:
            log_path.write_bytes(tail)

    try:
        if output_path is not None:
            output = output_path.open('wb')
        spawning = asyncio.create_task(asyncio.create_subprocess_exec(
            *map(str, command), stdin=asyncio.subprocess.DEVNULL,
            stdout=output if output is not None else asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE, **options))
        process = await asyncio.shield(spawning)
        _PROCESSES.add(process)
        draining = asyncio.create_task(drain_stderr(process.stderr))
        await asyncio.wait_for(process.wait(), timeout=timeout)
        await draining
        if process.returncode != 0:
            detail = _tail(log_path)
            raise RuntimeError('Không xuất/kiểm tra được MP3.' + (' ' + detail if detail else ''))
    except BaseException:
        if process is None and spawning is not None:
            try:
                process = await spawning
            except (Exception, asyncio.CancelledError):
                pass
        if process is not None:
            if draining is None:
                draining = asyncio.create_task(drain_stderr(process.stderr))
            await _stop(process)
        raise
    finally:
        if draining is not None:
            # The owned encoder has exited or has just been killed. Continue
            # draining its finite pipe even when the request was cancelled.
            try:
                await asyncio.wait_for(asyncio.shield(draining), timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                draining.cancel()
                await asyncio.gather(draining, return_exceptions=True)
        if output is not None:
            output.close()
        if process is not None:
            _PROCESSES.discard(process)


async def _probe_mp3(path, directory, ffprobe, expected_seconds=None):
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
        raise RuntimeError('Không nhận được MP3 hợp lệ.')
    report = directory / 'probe.json'
    await _run_command([
        ffprobe, '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-select_streams', 'a:0', '-show_entries',
        'stream=codec_name,duration:format=duration', '-of', 'json', path,
    ], directory / 'probe.log', output_path=report, timeout=30)
    try:
        if report.stat().st_size > 64 * 1024:
            raise ValueError('oversized probe')
        info = json.loads(report.read_text(encoding='utf-8'))
        streams = info['streams']
        duration = float(info['format']['duration'])
        if (not isinstance(streams, list) or len(streams) != 1
                or streams[0]['codec_name'] != 'mp3'
                or not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS + .12
                or (expected_seconds is not None and abs(duration - expected_seconds) > .12)):
            raise ValueError('codec/duration mismatch')
        return duration
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RuntimeError('MP3 chưa có đúng codec hoặc thời lượng WAV; chưa lưu bản xuất.') from exc


async def ensure_mp3(job):
    """Return a completed job's validated MP3, sharing one conversion per job.

    Invalid input raises ValueError. Missing tools or failed conversion raises
    RuntimeError/OSError. Cancellation kills only this export's process group,
    discards its intermediates, and preserves the WAV and any previous MP3.
    """
    task = asyncio.current_task()
    _ACTIVE_TASKS.add(task)
    owns_export = False
    try:
        lock = job.setdefault('_mp3_lock', asyncio.Lock())
        async with lock:
            if job.get('status') != 'completed':
                raise ValueError('Chỉ xuất MP3 sau khi tạo voice hoàn tất.')
            try:
                folder = Path(job['temp'].name)
            except (KeyError, TypeError, AttributeError) as exc:
                raise ValueError('Không tìm thấy thư mục kết quả voice.') from exc
            source = folder / 'audio.bin'
            if not source.is_file() or source.is_symlink() or source.stat().st_size <= 0:
                raise ValueError('Không tìm thấy bản thu hoàn chỉnh để xuất MP3.')
            media_type = job.get('media_type')
            if media_type not in {'audio/wav', 'audio/x-wav', 'audio/mpeg'}:
                raise ValueError('Bản thu này chưa hỗ trợ xuất MP3; hãy tải bản gốc.')
            ffprobe = shutil.which('ffprobe')
            ffmpeg = shutil.which('ffmpeg')
            if not ffprobe or (media_type != 'audio/mpeg' and not ffmpeg):
                raise RuntimeError('Cần FFmpeg và ffprobe để xuất MP3. Chạy lại bộ cài Studio.')
            job['_mp3_export_active'] = True
            owns_export = True
            with tempfile.TemporaryDirectory(prefix='.mp3-export-', dir=folder) as scratch:
                directory = Path(scratch)
                if media_type == 'audio/mpeg':
                    await _probe_mp3(source, directory, ffprobe)
                    return source
                duration, signature = _wav_info(source)
                destination = folder / 'audio.mp3'
                if job.get('_mp3_source_signature') == signature and destination.is_file():
                    try:
                        await _probe_mp3(destination, directory, ffprobe, duration)
                        return destination
                    except RuntimeError:
                        # Rebuild an incomplete/corrupt cached export atomically.
                        pass
                partial = directory / 'audio.mp3.part'
                await _run_command([
                    ffmpeg, '-nostdin', '-v', 'error', '-y', '-protocol_whitelist',
                    'file,pipe', '-i', source, '-map', '0:a:0', '-vn',
                    '-map_metadata', '-1', '-c:a', 'libmp3lame', '-q:a', '2',
                    '-f', 'mp3', partial,
                ], directory / 'encode.log', timeout=max(60, min(12 * 3600, duration * 2 + 30)))
                await _probe_mp3(partial, directory, ffprobe, duration)
                if _wav_info(source)[1] != signature:
                    raise RuntimeError('WAV đã thay đổi khi xuất MP3; chưa ghi đè bản xuất.')
                os.replace(partial, destination)
                job['_mp3_source_signature'] = signature
                return destination
    except asyncio.TimeoutError as exc:
        raise RuntimeError('Hết thời gian xuất/kiểm tra MP3; bản WAV được giữ nguyên.') from exc
    finally:
        if owns_export:
            job['_mp3_export_active'] = False
        _ACTIVE_TASKS.discard(task)


async def shutdown():
    """Cancel outstanding exports before the owner removes job directories."""
    current = asyncio.current_task()
    tasks = [task for task in _ACTIVE_TASKS if task is not current and not task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    for process in tuple(_PROCESSES):
        await _stop(process)
