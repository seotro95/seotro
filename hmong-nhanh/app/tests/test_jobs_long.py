import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
import wave

import pytest
from fastapi import HTTPException

import voice_jobs as jobs


WORKER_SOURCE = r'''
import json,os,struct,sys,time,wave
from pathlib import Path
for line in sys.stdin:
    folder=Path(json.loads(line)['folder'])
    data=json.loads((folder/'input.json').read_text())
    (folder/'worker-pid.txt').write_text(str(os.getpid()))
    parts=folder/'parts';parts.mkdir(exist_ok=True)
    path=parts/'part-0001.wav'
    mode=data.get('_test_mode','done')
    frames=27*1024*1024 if mode=='large' else 2400
    if not path.exists():
        with path.open('wb') as out:
            out.write(struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',36+frames*2,b'WAVE',b'fmt ',16,1,1,24000,48000,2,16,b'data',frames*2))
            out.write(b'\x01\x01')
            out.seek(44+frames*2-2);out.write(b'\x01\x01')
    record={'number':1,'filename':path.name,'seconds':frames/24000}
    progress={'completed':1,'total':2 if mode=='block' else 1,'progress':50 if mode=='block' else 100,
              'audio_seconds':frames/24000,'elapsed_seconds':.2,'parts':[record], 'device':'test-worker-'+str(os.getpid())}
    (folder/'progress.json').write_text(json.dumps(progress))
    attempted=folder/'attempted'
    if mode=='block' and not attempted.exists():
        attempted.touch();time.sleep(60)
    progress.update(completed=progress['total'],progress=100)
    if mode=='bad-result':
        progress['parts'][0]['filename']='../outside.wav'
    (folder/'result.json').write_text(json.dumps(progress))
    print(json.dumps({'ok':True}),flush=True)
'''


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path / 'data'))
    worker = tmp_path / 'fake_worker.py'
    worker.write_text(WORKER_SOURCE, encoding='utf-8')
    monkeypatch.setattr(jobs, 'WORKER', worker)
    reference = tmp_path / 'source.wav'
    with wave.open(str(reference), 'wb') as sound:
        sound.setnchannels(1); sound.setsampwidth(2); sound.setframerate(24000)
        sound.writeframes(b'\x01\x01' * 24000 * 4)
    return tmp_path, reference


def payload(reference, **extra):
    return {'text':'Nyob zoo.', 'voice':'hmong-white-female', 'quality':'fast', 'style':'natural',
            'speed':1.0, '_reference': {'path':str(reference), 'text':'Exact reference words.'}, **extra}


async def finished(ident, timeout=8):
    deadline = asyncio.get_running_loop().time()+timeout
    while jobs.get(ident)['status']=='running':
        assert asyncio.get_running_loop().time()<deadline
        await asyncio.sleep(.01)
    # create/resume only becomes available after the lifecycle task also ends.
    task = jobs.get(ident).get('task')
    if task is not None:
        await task
    return jobs.view(jobs.get(ident))


def test_keeps_worker_warm_and_public_progress_omits_script_and_reference(local):
    _, reference = local
    async def scenario():
        try:
            first = jobs.create(payload(reference))
            one = await finished(first['id'])
            assert one['status']=='completed',one
            pid = jobs.get(first['id'])['folder'].joinpath('worker-pid.txt').read_text()
            second=jobs.create(payload(reference,voice='hmong-white-male'))
            two=await finished(second['id'])
            assert two['status']=='completed',two
            assert jobs.get(second['id'])['folder'].joinpath('worker-pid.txt').read_text()==pid
            assert one['progress']==100 and one['parts'][0]['number']==1
            assert two['voice']=='hmong-white-male' and two['characters']==9
            encoded=json.dumps(two)
            assert 'Nyob zoo.' not in encoded and 'Exact reference words' not in encoded
            assert str(reference) not in encoded and '_reference' not in encoded
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_reference_snapshot_and_one_million_chars_are_persisted(local):
    _, reference = local
    original=reference.read_bytes()
    async def scenario():
        try:
            first=jobs.create(payload(reference,text='x'*1_000_000))
            folder=jobs.get(first['id'])['folder']
            data=json.loads((folder/'input.json').read_text())
            assert len(data['text'])==1_000_000
            assert data['_reference']['path']==str(folder/'reference.wav')
            reference.write_bytes(b'replaced library sample')
            assert (folder/'reference.wav').read_bytes()==original
            assert (await finished(first['id']))['status']=='completed'
            with pytest.raises(HTTPException) as error:
                jobs.create(payload(folder/'reference.wav',text='x'*1_000_001))
            assert error.value.status_code==422
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_cancel_preserves_parts_resume_reuses_checkpoints_and_new_worker(local):
    _, reference = local
    async def scenario():
        try:
            started=jobs.create(payload(reference,_test_mode='block'))
            ident=started['id'];folder=jobs.get(ident)['folder']
            deadline=asyncio.get_running_loop().time()+8
            while not (folder/'attempted').exists():
                assert asyncio.get_running_loop().time()<deadline
                await asyncio.sleep(.01)
            old_pid=(folder/'worker-pid.txt').read_text()
            part=folder/'parts/part-0001.wav'
            before=(part.stat().st_mtime_ns,hashlib.sha256(part.read_bytes()).hexdigest())
            with pytest.raises(HTTPException) as busy:
                jobs.create(payload(reference))
            assert busy.value.status_code==409
            start=time.monotonic()
            stopped=await jobs.cancel(ident)
            assert time.monotonic()-start<5
            assert stopped['status']=='cancelled' and stopped['resumable']
            assert stopped['completed']==1 and stopped['parts']
            resumed=jobs.resume(ident)
            assert resumed['status']=='running'
            result=await finished(ident)
            assert result['status']=='completed',result
            assert (folder/'worker-pid.txt').read_text()!=old_pid
            assert (part.stat().st_mtime_ns,hashlib.sha256(part.read_bytes()).hexdigest())==before
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_reloads_completed_jobs_and_marks_interrupted_ones_resumable(local):
    _, reference=local
    async def scenario():
        first=jobs.create(payload(reference))
        assert (await finished(first['id']))['status']=='completed'
        folder=jobs.get(first['id'])['folder']
        await jobs.shutdown()
        assert jobs.get(first['id'])['status']=='completed'
        assert len(jobs.list_jobs())==1
        await jobs.shutdown()
        metadata=json.loads((folder/'metadata.json').read_text())
        metadata['status']='running'
        (folder/'metadata.json').write_text(json.dumps(metadata))
        restored=jobs.view(jobs.get(first['id']))
        assert restored['status']=='cancelled' and restored['resumable']
        assert 'Phiên trước' in restored['message']
        await jobs.shutdown()
    asyncio.run(scenario())


def test_wav_parts_above_fifty_megabytes_are_valid(local):
    _,reference=local
    async def scenario():
        try:
            first=jobs.create(payload(reference,_test_mode='large'))
            result=await finished(first['id'])
            assert result['status']=='completed',result
            file=jobs.get(first['id'])['folder']/'parts'/result['parts'][0]['filename']
            assert file.stat().st_size>50*1024*1024
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_invalid_part_paths_fail_and_invalid_ids_never_escape_data_root(local):
    _,reference=local
    async def scenario():
        try:
            first=jobs.create(payload(reference,_test_mode='bad-result'))
            result=await finished(first['id'])
            assert result['status']=='failed'
            assert result['parts'][0]['filename']=='part-0001.wav'
            for ident in ('../x','bad','/'+'a'*32):
                with pytest.raises(HTTPException) as error:
                    jobs.get(ident)
                assert error.value.status_code==404
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_cancel_before_worker_starts_and_resume(local):
    _,reference=local
    async def scenario():
        try:
            first=jobs.create(payload(reference))
            assert (await jobs.cancel(first['id']))['status']=='cancelled'
            assert (jobs.get(first['id'])['folder']/'input.json').exists()
            jobs.resume(first['id'])
            assert (await finished(first['id']))['status']=='completed'
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())


def test_real_serve_worker_reuses_processor_and_keeps_protocol_clean(local, monkeypatch):
    tmp_path,reference=local
    worker=tmp_path/'real_voice_worker.py'
    worker.write_text(Path(jobs.__file__).with_name('voice_worker.py').read_text(),encoding='utf-8')
    (tmp_path/'longform.py').write_text('''import json,wave
calls=0
print('processor imported; this must stay off stdout protocol')
def process_job(folder):
    global calls
    calls+=1
    print('model diagnostic text; this must also stay off stdout')
    parts=folder/'parts';parts.mkdir(exist_ok=True)
    with wave.open(str(parts/'part-0001.wav'),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(24000)
        out.writeframes(bytes([1,1])*2400)
    result={'completed':1,'total':1,'progress':100,'device':'calls-'+str(calls),
            'parts':[{'number':1,'filename':'part-0001.wav','seconds':.1}]}
    (folder/'result.json').write_text(json.dumps(result))
''',encoding='utf-8')
    monkeypatch.setattr(jobs,'WORKER',worker)
    async def scenario():
        try:
            one=jobs.create(payload(reference))
            assert (await finished(one['id']))['device']=='calls-1'
            two=jobs.create(payload(reference))
            assert (await finished(two['id']))['device']=='calls-2'
            log=(jobs.data_root()/'worker.log').read_text()
            assert 'processor imported' in log and 'model diagnostic' in log
        finally:
            await jobs.shutdown()
    asyncio.run(scenario())
