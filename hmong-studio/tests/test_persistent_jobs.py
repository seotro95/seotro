"""Exercise warm reuse and cancellation with the production worker and a tiny engine."""
import asyncio
import json
from pathlib import Path
import textwrap
import wave

import voice_jobs


FAKE_APP = '''
import asyncio, json, struct, sys, types, wave
from pathlib import Path
from fastapi.responses import FileResponse
app = types.ModuleType('app')
class Speech:
    @staticmethod
    def model_validate(value):
        return value
app.Speech = Speech
cache_uses = 0
def availability():
    if cache_uses == 3:
        return {'loaded': True, 'device': ['bad'], 'precision': 'float32',
                'reference_cache_entries': True}
    return {'loaded': True, 'device': 'cpu', 'precision': 'float32',
            'reference_cache_entries': cache_uses, 'secret_not_exported': 'private'}
app.cosy_engine = types.SimpleNamespace(availability=availability)
async def generate_speech(payload, progress=None, output_path=None):
    global cache_uses
    cache_uses += 1
    progress({'progress': 35, 'phase': 'generating', 'completed_units': 1,
              'total_units': 2, 'generated_seconds': 1.25, 'message': 'Đang tạo từng câu.'})
    if payload['text'] == 'wait':
        (output_path.parent / '.hmong-voice-test.part').write_bytes(b'partial audio')
        scratch = output_path.parent / 'timeline-scratch'
        scratch.mkdir()
        (scratch / 'chunk.wav').write_bytes(b'partial segment')
        await asyncio.sleep(60)
    elif payload['text'] == 'invalid-progress':
        await asyncio.sleep(.12)
        progress({'progress': float('nan'), 'phase': 'completed',
                  'completed_units': 2, 'total_units': 1, 'generated_seconds': -1})
        await asyncio.sleep(.25)
    progress({'progress': 100, 'phase': 'assembling', 'completed_units': 2,
              'total_units': 2, 'generated_seconds': 2.5, 'message': 'Đang ghép âm thanh.'})
    await asyncio.sleep(.2)
    if payload['text'] == 'bad-audio':
        output_path.write_bytes(b'RIFF-not-a-wave')
        scratch = output_path.parent / 'hmong-timeline-failed'
        scratch.mkdir()
        (scratch / 'timeline.part').write_bytes(b'failed partial timeline')
        cleanup = output_path.parent / '.audio-clean-failed'
        cleanup.mkdir()
        (cleanup / 'finished.wav').write_bytes(b'failed cleanup output')
    elif payload['text'] == 'one-hour':
        size = 24000 * 2 * 3600
        header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + size, b'WAVE',
                             b'fmt ', 16, 1, 1, 24000, 48000, 2, 16, b'data', size)
        with output_path.open('wb') as audio:
            audio.write(header)
            audio.truncate(44 + size)
    else:
        with wave.open(str(output_path), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(struct.pack('<h', cache_uses) * 100)
    return FileResponse(output_path, media_type='audio/wav')
app.generate_speech = generate_speech
sys.modules['app'] = app
'''


def worker_script(tmp_path):
    script = tmp_path / 'tiny-engine-worker.py'
    script.write_text(textwrap.dedent(FAKE_APP) + '\n' +
                      'sys.path.insert(0, ' + repr(str(Path(voice_jobs.__file__).parent)) + ')\n' +
                      'import voice_worker\nasyncio.run(voice_worker.main())\n', encoding='utf-8')
    return script


async def until(job_id, condition, timeout=8):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        job = voice_jobs.get(job_id)
        status = voice_jobs.view(job)
        if condition(status):
            return status
        assert asyncio.get_running_loop().time() < deadline, status
        await asyncio.sleep(.01)


def test_model_stays_warm_and_progress_waits_for_verified_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        try:
            first = voice_jobs.create({'text': 'first'})['id']
            working = await until(first, lambda state: state['progress'] == 99)
            process = voice_jobs.get(first)['process']
            assert working['status'] == 'running'
            assert working['audio_bytes'] == 0
            assert working['message'] == 'Đang ghép âm thanh.'
            assert working['completed_units'] == working['total_units'] == 2
            assert working['generated_seconds'] == 2.5
            assert working['elapsed_seconds'] > 0
            assert not (Path(voice_jobs.get(first)['temp'].name) / 'result.json').exists()
            finished = await until(first, lambda state: state['status'] != 'running')
            assert finished['status'] == 'completed'
            assert finished['progress'] == 100
            assert finished['runtime'] == {'loaded': True, 'device': 'cpu',
                                           'precision': 'float32', 'reference_cache_entries': 1}
            assert voice_jobs.worker_runtime() == finished['runtime']

            second = voice_jobs.create({'text': 'á' * 1_000_000})['id']
            await until(second, lambda state: state['progress'] > 0)
            assert voice_jobs.get(second)['process'].pid == process.pid
            await until(second, lambda state: state['status'] != 'running')
            with wave.open(str(Path(voice_jobs.get(second)['temp'].name) / 'audio.bin')) as audio:
                # The fake model's in-memory state persists, beyond PID reuse.
                assert int.from_bytes(audio.readframes(1), 'little') == 2
            assert process.returncode is None
            assert voice_jobs.worker_runtime()['reference_cache_entries'] == 2
            third = voice_jobs.create({'text': 'invalid-runtime'})['id']
            invalid = await until(third, lambda state: state['status'] != 'running')
            assert invalid['status'] == 'completed'
            assert invalid['runtime'] == voice_jobs.worker_runtime() == {}
        finally:
            await voice_jobs.shutdown()
        assert process.returncode is not None
        assert voice_jobs.worker_runtime() == {}

    asyncio.run(scenario())


def test_stop_discards_only_owned_worker_and_restart_loads_fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        unrelated = await asyncio.create_subprocess_exec(
            __import__('sys').executable, '-c', 'import time; time.sleep(60)')
        try:
            first = voice_jobs.create({'text': 'wait'})['id']
            await until(first, lambda state: state['progress'] == 35)
            old = voice_jobs.get(first)['process']
            cancelled = await voice_jobs.cancel(first)
            assert cancelled['status'] == 'cancelled'
            assert cancelled['progress'] == 35
            assert cancelled['runtime'] == voice_jobs.worker_runtime() == {}
            assert old.returncode is not None
            assert not Path(voice_jobs.get(first)['temp'].name).exists()
            assert unrelated.returncode is None
            second = voice_jobs.create({'text': 'second'})['id']
            await until(second, lambda state: state['progress'] > 0)
            new = voice_jobs.get(second)['process']
            assert new.pid != old.pid
            await until(second, lambda state: state['status'] != 'running')
            with wave.open(str(Path(voice_jobs.get(second)['temp'].name) / 'audio.bin')) as audio:
                assert int.from_bytes(audio.readframes(1), 'little') == 1
        finally:
            await voice_jobs.shutdown()
            unrelated.kill()
            await unrelated.wait()

    asyncio.run(scenario())


def test_invalid_progress_or_audio_never_reports_false_completion(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        try:
            job = voice_jobs.create({'text': 'invalid-progress'})['id']
            progress = await until(job, lambda state: state['progress'] > 0)
            assert progress['progress'] == 35
            assert progress['phase'] == 'generating'
            assert progress['completed_units'] == 1
            assert progress['generated_seconds'] == 1.25
            await until(job, lambda state: state['status'] != 'running')
            bad = voice_jobs.create({'text': 'bad-audio'})['id']
            failed = await until(bad, lambda state: state['status'] != 'running')
            assert failed['status'] == 'failed'
            assert failed['progress'] < 100
            await voice_jobs.get(bad)['task']
            folder = Path(voice_jobs.get(bad)['temp'].name)
            assert not (folder / 'audio.bin').exists()
            assert not (folder / 'hmong-timeline-failed').exists()
            assert not (folder / '.audio-clean-failed').exists()
        finally:
            await voice_jobs.shutdown()

    asyncio.run(scenario())


def test_one_hour_wav_is_file_backed_and_not_limited_to_50mb(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        try:
            job = voice_jobs.create({'text': 'one-hour'})['id']
            done = await until(job, lambda state: state['status'] != 'running')
            assert done['status'] == 'completed', done
            assert done['progress'] == 100
            audio = Path(voice_jobs.get(job)['temp'].name) / 'audio.bin'
            assert audio.stat().st_size == done['audio_bytes'] == 172800044
            assert voice_jobs._valid_audio(audio, 'audio/wav')
            # Truncating a claimed long WAV must not produce a completed result.
            with audio.open('r+b') as stream:
                stream.truncate(100)
            assert not voice_jobs._valid_audio(audio, 'audio/wav')
        finally:
            await voice_jobs.shutdown()

    asyncio.run(scenario())


def test_cancel_during_child_creation_never_orphans_worker(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        original_spawn = asyncio.create_subprocess_exec
        created = asyncio.Event()
        release = asyncio.Event()
        children = []

        async def delayed_spawn(*args, **kwargs):
            child = await original_spawn(*args, **kwargs)
            children.append(child)
            created.set()
            await release.wait()
            return child

        monkeypatch.setattr(asyncio, 'create_subprocess_exec', delayed_spawn)
        try:
            job = voice_jobs.create({'text': 'wait'})['id']
            await asyncio.wait_for(created.wait(), 5)
            stopping = asyncio.create_task(voice_jobs.cancel(job))
            await asyncio.sleep(.01)
            assert not stopping.done()
            release.set()
            result = await asyncio.wait_for(stopping, 5)
            assert result['status'] == 'cancelled'
            assert result['progress'] == 0
            assert len(children) == 1
            assert children[0].returncode is not None
        finally:
            release.set()
            await voice_jobs.shutdown()

    asyncio.run(scenario())
