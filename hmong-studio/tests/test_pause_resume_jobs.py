"""Control the production worker with a synthetic tiny engine, never a speed claim."""
import asyncio
import json
from pathlib import Path
import tempfile
import textwrap
import time
import wave

from fastapi import HTTPException
import pytest

import voice_jobs as jobs
import voice_worker


TINY_APP = '''
import asyncio, struct, sys, types, wave
from pathlib import Path
from fastapi.responses import FileResponse
app = types.ModuleType('app')
loads = 0
class Speech:
    @staticmethod
    def model_validate(value):
        return value
app.Speech = Speech
def load(root):
    global loads
    loads += 1
def availability():
    return {'ready': True, 'loaded': loads > 0, 'device': 'cpu', 'precision': 'float32',
            'reference_cache_entries': 1, 'compute_mode': 'ultra'}
app.cosy_engine = types.SimpleNamespace(availability=availability,
                                      _load_engine=load, model_dir=lambda: 'local')
async def generate_speech(payload, progress=None, output_path=None):
    if loads == 0:
        load('local')
    if payload['text'] == 'slow-before-checkpoint':
        await asyncio.sleep(.3)
    with wave.open(str(output_path), 'wb') as writer:
        writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(24000)
        for number in range(1, 5):
            await asyncio.sleep(.08)
            writer.writeframesraw(struct.pack('<h', number) * 240)
            progress({'progress': number * 20, 'phase': 'synthesis',
                      'message': 'Synthetic control fixture', 'completed_units': number,
                      'total_units': 4, 'generated_seconds': number * .5,
                      'synthesized_seconds': number * .3, 'reused_seconds': number * .2,
                      'cache_hits': number, 'active_workers': 0, 'batch_size': 1})
    return FileResponse(output_path, media_type='audio/wav')
app.generate_speech = generate_speech
sys.modules['app'] = app
'''


def worker_script(tmp_path):
    path = tmp_path / 'control-worker.py'
    path.write_text(textwrap.dedent(TINY_APP) + '\n' +
                    'sys.path.insert(0, ' + repr(str(Path(jobs.__file__).parent)) + ')\n' +
                    'import voice_worker\nasyncio.run(voice_worker.main())\n', encoding='utf-8')
    return path


async def until(job_id, condition, timeout=8):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        state = jobs.view(jobs.get(job_id))
        if condition(state):
            return state
        assert asyncio.get_running_loop().time() < deadline, state
        await asyncio.sleep(.01)


def test_pause_ack_freezes_work_and_resume_keeps_process_audio_order_and_timing(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        try:
            job_id = jobs.create({'text': 'four chunks'})['id']
            await until(job_id, lambda state: state['completed_units'] >= 1)
            process = jobs.get(job_id)['process']
            requested = await jobs.pause(job_id)
            assert requested['pause_requested'] is True
            paused = await until(job_id, lambda state: state['status'] == 'paused')
            assert paused['progress'] < 100 and paused['active_workers'] == 0
            assert paused['runtime']['compute_mode'] == 'ultra'
            with pytest.raises(HTTPException) as conflict:
                jobs.create({'text': 'another'})
            assert conflict.value.status_code == 409
            await asyncio.sleep(.25)
            still_paused = jobs.view(jobs.get(job_id))
            assert still_paused['completed_units'] == paused['completed_units']
            assert still_paused['progress'] == paused['progress']
            assert still_paused['paused_seconds'] >= .24
            assert abs(still_paused['active_elapsed_seconds'] - paused['active_elapsed_seconds']) < .03
            assert still_paused['speed_multiplier'] == pytest.approx(paused['speed_multiplier'], abs=.01)
            continued = await jobs.resume(job_id)
            assert continued['status'] == 'running' and not continued['pause_requested']
            finished = await until(job_id, lambda state: state['status'] == 'completed')
            assert process is jobs._WORKER_STATE['process'] and process.returncode is None
            assert finished['progress'] == 100 and finished['active_workers'] == 0
            assert finished['eta_seconds'] == 0
            assert finished['cache_hits'] == 4
            assert finished['synthesized_seconds'] == pytest.approx(1.2)
            assert finished['reused_seconds'] == pytest.approx(.8)
            assert finished['speed_multiplier'] == pytest.approx(
                finished['synthesized_seconds'] / finished['active_elapsed_seconds'], rel=.02)
            assert finished['paused_seconds'] >= .24
            assert finished['estimated_total_seconds'] == pytest.approx(.04)
            with wave.open(str(Path(jobs.get(job_id)['temp'].name) / 'audio.bin')) as reader:
                import array
                samples = array.array('h', reader.readframes(reader.getnframes()))
                assert list(samples) == [number for number in range(1, 5) for _ in range(240)]
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_pause_pending_is_not_reported_as_paused_and_can_be_withdrawn(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        try:
            job_id = jobs.create({'text': 'slow-before-checkpoint'})['id']
            await until(job_id, lambda state: state['phase'] == 'starting')
            pending = await jobs.pause(job_id)
            assert pending['status'] == 'running' and pending['pause_requested']
            await asyncio.sleep(.05)
            assert jobs.view(jobs.get(job_id))['status'] == 'running'
            resumed = await jobs.resume(job_id)
            assert resumed['status'] == 'running' and not resumed['pause_requested']
            done = await until(job_id, lambda state: state['status'] == 'completed')
            assert done['paused_seconds'] == 0
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_stop_while_paused_terminates_owned_process_and_removes_partial(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        try:
            job_id = jobs.create({'text': 'four chunks'})['id']
            await until(job_id, lambda state: state['completed_units'] >= 1)
            await jobs.pause(job_id)
            await until(job_id, lambda state: state['status'] == 'paused')
            process = jobs.get(job_id)['process']
            folder = Path(jobs.get(job_id)['temp'].name)
            stopped = await jobs.cancel(job_id)
            assert stopped['status'] == 'cancelled' and stopped['progress'] < 100
            assert not stopped['pause_requested'] and stopped['active_workers'] == 0
            assert process.returncode is not None and not folder.exists()
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_preload_reuses_one_worker_without_creating_audio_job(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, 'WORKER', worker_script(tmp_path))

    async def scenario():
        try:
            runtime = await jobs.preload()
            assert runtime['loaded'] is True and runtime['device'] == 'cpu'
            assert jobs.JOBS == {}
            process = jobs._WORKER_STATE['process']
            job_id = jobs.create({'text': 'four chunks'})['id']
            await until(job_id, lambda state: state['status'] == 'completed')
            assert jobs._WORKER_STATE['process'] is process
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_shutdown_cancels_a_preload_it_owns(monkeypatch, tmp_path):
    path = tmp_path / 'slow-preload.py'
    path.write_text('import sys,time\nfor line in sys.stdin:\n time.sleep(60)\n')
    monkeypatch.setattr(jobs, 'WORKER', path)

    async def scenario():
        loading = asyncio.create_task(jobs.preload())
        while jobs._WORKER_STATE is None:
            await asyncio.sleep(.01)
        process = jobs._WORKER_STATE['process']
        await jobs.shutdown()
        assert loading.cancelled() and process.returncode is not None
        assert not jobs._PRELOAD_TASKS and jobs.worker_runtime() == {}
    asyncio.run(scenario())


def test_invalid_progress_or_unacknowledged_pause_cannot_publish_metrics(tmp_path):
    now = time.monotonic()
    with tempfile.TemporaryDirectory(dir=tmp_path) as folder:
        job = {'id': 'unit', 'status': 'running', 'message': 'previous', 'progress': 10,
               'phase': 'synthesis', 'temp': type('Folder', (), {'name': folder})(),
               'started_at': now, 'completed_units': 1, 'total_units': 4,
               'generated_seconds': 2, 'audio_bytes': 0, 'runtime': {},
               'synthesized_seconds': 1, '_control_revision': 1, 'pause_requested': True}
        update = {'progress': 90, 'phase': 'paused', 'completed_units': 3,
                  'total_units': 4, 'generated_seconds': 6, 'cache_hits': True}
        progress = Path(folder) / 'progress.json'
        progress.write_text(json.dumps(update))
        state = jobs.view(job)
        assert state['status'] == 'running' and state['progress'] == 10
        assert state['synthesized_seconds'] == 1
        del update['cache_hits']
        progress.write_text(json.dumps(update))
        assert jobs.view(job)['status'] == 'running'
        ack = Path(folder) / 'control-ack.json'
        ack.write_text(json.dumps({'revision': 0, 'paused': True, 'at_monotonic': now}))
        assert jobs.view(job)['status'] == 'running'
        ack.write_text(json.dumps({'revision': 1, 'paused': True, 'at_monotonic': now + 99}))
        assert jobs.view(job)['status'] == 'running'


def test_paused_time_starts_at_ack_and_only_new_synthesis_counts_toward_speed(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs.time, 'monotonic', lambda: 25.0)
    with tempfile.TemporaryDirectory(dir=tmp_path) as folder:
        job = {'id': 'unit', 'status': 'running', 'message': 'previous', 'progress': 50,
               'phase': 'synthesis', 'temp': type('Folder', (), {'name': folder})(),
               'started_at': 10.0, 'completed_units': 1, 'total_units': 2,
               'generated_seconds': 1000, 'audio_bytes': 0, 'runtime': {},
               'synthesized_seconds': 5, 'reused_seconds': 995,
               '_control_revision': 1, 'pause_requested': True}
        (Path(folder) / 'control-ack.json').write_text(json.dumps({
            'revision': 1, 'paused': True, 'at_monotonic': 15.0}))
        state = jobs.view(job)
        assert state['paused_seconds'] == 10 and state['active_elapsed_seconds'] == 5
        assert state['speed_multiplier'] == 1 and state['eta_seconds'] == 5
        assert state['estimated_total_seconds'] == 2000


def test_ack_timestamp_is_stable_across_progress_updates_for_the_same_control(tmp_path, monkeypatch):
    control = {'revision': 2, 'paused': False}
    (tmp_path / 'control.json').write_text(json.dumps(control))
    state = {}
    monkeypatch.setattr(voice_worker.time, 'monotonic', lambda: 30.0)
    voice_worker.cooperative_checkpoint(tmp_path, {'progress': 10}, state)
    assert json.loads((tmp_path / 'control-ack.json').read_text())['at_monotonic'] == 30
    monkeypatch.setattr(voice_worker.time, 'monotonic', lambda: 50.0)
    voice_worker.cooperative_checkpoint(tmp_path, {'progress': 20}, state)
    assert json.loads((tmp_path / 'control-ack.json').read_text())['at_monotonic'] == 30


def test_create_does_not_evict_an_active_mp3_export(monkeypatch):
    async def never_run(job, payload):
        pass
    monkeypatch.setattr(jobs, 'run', never_run)

    async def scenario():
        try:
            for number in range(10):
                jobs.JOBS[str(number)] = {'id': str(number), 'status': 'completed',
                    '_mp3_export_active': True,
                    'temp': tempfile.TemporaryDirectory(prefix='hmong-export-fixture-')}
            with pytest.raises(HTTPException) as busy:
                jobs.create({'text': 'new'})
            assert busy.value.status_code == 409 and len(jobs.JOBS) == 10
            removable = jobs.JOBS['5']
            removable['_mp3_export_active'] = False
            folder = Path(removable['temp'].name)
            new = jobs.create({'text': 'new'}, estimated_total_seconds=60)
            assert new['estimated_total_seconds'] == 60 and not folder.exists()
            assert '0' in jobs.JOBS and '5' not in jobs.JOBS
            await jobs.get(new['id'])['task']
        finally:
            # Minimal completed fixture records have no tasks to await.
            for key, job in list(jobs.JOBS.items()):
                if 'task' not in job:
                    job['temp'].cleanup()
                    del jobs.JOBS[key]
            await jobs.shutdown()
    asyncio.run(scenario())
