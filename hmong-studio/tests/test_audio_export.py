"""Export correctness/process ownership tests, not a TTS performance benchmark."""
import array
import asyncio
import hashlib
import math
from pathlib import Path
import shutil
import sys
import tempfile
import wave

import pytest

import audio_export


pytestmark = pytest.mark.skipif(
    not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg/ffprobe required')


@pytest.fixture
def job():
    with tempfile.TemporaryDirectory(prefix='mp3-export-test-') as folder:
        source = Path(folder) / 'audio.bin'
        samples = array.array('h', (round(8000 * math.sin(index * 2 * math.pi * 440 / 24000))
                                   for index in range(29628)))
        if sys.byteorder != 'little':
            samples.byteswap()
        with wave.open(str(source), 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(24000)
            writer.writeframes(samples.tobytes())
        holder = type('Folder', (), {'name': folder})()
        yield {'temp': holder, 'media_type': 'audio/wav', 'status': 'completed'}


def source(job):
    return Path(job['temp'].name) / 'audio.bin'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_mp3_export_keeps_wav_duration_and_shares_concurrent_conversion(job, monkeypatch):
    original = digest(source(job))
    encoding = []
    run = audio_export._run_command

    async def counted(command, *args, **options):
        if '-c:a' in command:
            encoding.append(list(command))
        return await run(command, *args, **options)

    monkeypatch.setattr(audio_export, '_run_command', counted)

    async def scenario():
        first, second = await asyncio.gather(audio_export.ensure_mp3(job), audio_export.ensure_mp3(job))
        assert first == second == source(job).with_name('audio.mp3')
        assert len(encoding) == 1
        assert first.stat().st_size > 1000
        assert not list(first.parent.glob('.mp3-export-*'))
        assert not audio_export._PROCESSES and not audio_export._ACTIVE_TASKS
        assert job['_mp3_export_active'] is False
        return first

    output = asyncio.run(scenario())
    assert output.is_file() and digest(source(job)) == original
    assert job['_mp3_source_signature'] == audio_export._wav_info(source(job))[1]


def test_corrupt_cached_mp3_is_rebuilt_and_original_wav_stays_intact(job):
    original = digest(source(job))

    async def scenario():
        output = await audio_export.ensure_mp3(job)
        output.write_bytes(b'broken cache')
        again = await audio_export.ensure_mp3(job)
        assert again == output and again.stat().st_size > 1000

    asyncio.run(scenario())
    assert digest(source(job)) == original


def test_file_based_conversion_does_not_read_whole_audio_into_python(job, monkeypatch):
    before = digest(source(job))
    with monkeypatch.context() as patched:
        patched.setattr(Path, 'read_bytes', lambda *args: pytest.fail('Whole audio read is forbidden'))
        assert asyncio.run(audio_export.ensure_mp3(job)).is_file()
    assert digest(source(job)) == before


def test_already_mp3_is_verified_and_returned_without_reencoding(job, monkeypatch):
    mp3 = asyncio.run(audio_export.ensure_mp3(job))
    source(job).write_bytes(mp3.read_bytes())
    before = digest(source(job))
    job['media_type'] = 'audio/mpeg'
    run = audio_export._run_command

    async def no_encoding(command, *args, **options):
        assert '-c:a' not in command
        return await run(command, *args, **options)

    monkeypatch.setattr(audio_export, '_run_command', no_encoding)
    assert asyncio.run(audio_export.ensure_mp3(job)) == source(job)
    assert digest(source(job)) == before


@pytest.mark.parametrize('status', ['running', 'paused', 'failed', 'cancelled'])
def test_incomplete_job_is_rejected_without_starting_export(job, status):
    job['status'] = status
    before = digest(source(job))
    with pytest.raises(ValueError, match='hoàn tất'):
        asyncio.run(audio_export.ensure_mp3(job))
    assert digest(source(job)) == before
    assert not audio_export._PROCESSES


@pytest.mark.parametrize('invalid', ['missing', 'empty', 'truncated', 'wrong_type'])
def test_invalid_source_never_publishes_mp3(job, invalid):
    if invalid == 'missing':
        source(job).unlink()
    elif invalid == 'empty':
        source(job).write_bytes(b'')
    elif invalid == 'truncated':
        with source(job).open('r+b') as stream:
            stream.truncate(60)
    else:
        job['media_type'] = 'audio/ogg'
    with pytest.raises(ValueError):
        asyncio.run(audio_export.ensure_mp3(job))
    assert not source(job).with_name('audio.mp3').exists()
    assert not list(source(job).parent.glob('.mp3-export-*'))


def test_missing_tools_preserve_source_and_previous_export(job, monkeypatch):
    previous = source(job).with_name('audio.mp3')
    previous.write_bytes(b'previous export')
    before = digest(source(job))
    monkeypatch.setattr(audio_export.shutil, 'which', lambda command: None)
    with pytest.raises(RuntimeError, match='FFmpeg'):
        asyncio.run(audio_export.ensure_mp3(job))
    assert digest(source(job)) == before and previous.read_bytes() == b'previous export'


def test_failed_conversion_preserves_existing_mp3_and_bounds_error_log(job, monkeypatch):
    original = digest(source(job))
    previous = source(job).with_name('audio.mp3')
    previous.write_bytes(b'previous export')
    run = audio_export._run_command

    async def failing(command, *args, **options):
        if '-c:a' in command:
            command = [sys.executable, '-c', 'import sys;sys.stderr.write("x"*20000);sys.exit(3)']
        return await run(command, *args, **options)

    monkeypatch.setattr(audio_export, '_run_command', failing)
    with pytest.raises(RuntimeError) as error:
        asyncio.run(audio_export.ensure_mp3(job))
    assert len(str(error.value)) < 4300
    assert digest(source(job)) == original and previous.read_bytes() == b'previous export'
    assert not list(previous.parent.glob('.mp3-export-*'))


def test_probe_rejects_invalid_encoded_output_before_atomic_publish(job, monkeypatch):
    previous = source(job).with_name('audio.mp3')
    previous.write_bytes(b'previous export')
    original = digest(source(job))
    run = audio_export._run_command

    async def corrupt_output(command, *args, **options):
        if '-c:a' in command:
            Path(command[-1]).write_bytes(b'not mp3')
            return
        return await run(command, *args, **options)

    monkeypatch.setattr(audio_export, '_run_command', corrupt_output)
    with pytest.raises(RuntimeError):
        asyncio.run(audio_export.ensure_mp3(job))
    assert previous.read_bytes() == b'previous export'
    assert digest(source(job)) == original


@pytest.mark.parametrize('shutdown', [False, True], ids=['request-cancel', 'app-shutdown'])
def test_cancellation_stops_only_owned_encoder_and_preserves_audio(job, monkeypatch, shutdown):
    previous = source(job).with_name('audio.mp3')
    previous.write_bytes(b'previous export')
    original = digest(source(job))
    run = audio_export._run_command

    async def slow(command, *args, **options):
        if '-c:a' in command:
            command = [sys.executable, '-c', 'import time;time.sleep(60)']
        return await run(command, *args, **options)

    monkeypatch.setattr(audio_export, '_run_command', slow)

    async def scenario():
        tasks = [asyncio.create_task(audio_export.ensure_mp3(job))]
        if shutdown:
            # The second request waits on the same job lock, not another encoder.
            tasks.append(asyncio.create_task(audio_export.ensure_mp3(job)))
        deadline = asyncio.get_running_loop().time() + 5
        while not audio_export._PROCESSES:
            assert asyncio.get_running_loop().time() < deadline
            await asyncio.sleep(.01)
        processes = tuple(audio_export._PROCESSES)
        assert len(processes) == 1
        assert job['_mp3_export_active'] is True
        if shutdown:
            await audio_export.shutdown()
        else:
            queued = asyncio.create_task(audio_export.ensure_mp3(job))
            await asyncio.sleep(.01)
            queued.cancel()
            await asyncio.gather(queued, return_exceptions=True)
            assert job['_mp3_export_active'] is True
            assert processes[0].returncode is None
            tasks[0].cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert all(isinstance(result, asyncio.CancelledError) for result in results)
        assert all(process.returncode is not None for process in processes)
        assert not audio_export._PROCESSES and not audio_export._ACTIVE_TASKS
        assert job['_mp3_export_active'] is False

    asyncio.run(scenario())
    assert previous.read_bytes() == b'previous export'
    assert digest(source(job)) == original
    assert not list(previous.parent.glob('.mp3-export-*'))
