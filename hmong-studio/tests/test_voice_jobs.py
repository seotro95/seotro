import asyncio
import os
from pathlib import Path
import time
from fastapi.testclient import TestClient
import app
import voice_jobs


def test_worker_success_download_and_server_rejects_empty(monkeypatch,tmp_path):
    worker=tmp_path/'worker.py'
    worker.write_text("import sys,json,wave\nfrom pathlib import Path\nfor line in sys.stdin:\n r=json.loads(line);p=Path(r['folder']);d=r['payload']\n assert d['emotion']=='review'\n assert d['voice']=='hmong-white-female'\n with wave.open(str(p/'audio.bin'),'wb') as w:\n  w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\\0\\0'*10)\n (p/'result.json').write_text(json.dumps({'media_type':'audio/wav'}))\n")
    monkeypatch.setattr(voice_jobs,'WORKER',worker)
    with TestClient(app.app) as client:
        assert client.post('/api/speech/jobs',json={'text':'  ','dialect':'mww'}).status_code==422
        response=client.post('/api/speech/jobs',json={'text':'Nyob zoo','dialect':'mww','voice':'hmong-white-female','emotion':'review'})
        assert response.status_code==202
        job=response.json()['id']
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            state=client.get('/api/speech/jobs/'+job).json()
            if state['status']!='running':break
            time.sleep(.02)
        assert state['status']=='completed',state
        assert client.get('/api/speech/jobs/'+job+'/audio').content.startswith(b'RIFF')
        assert client.post('/api/speech/jobs/'+job+'/stop').json()['status']=='completed'


def test_stop_terminates_real_worker_and_can_restart(monkeypatch,tmp_path):
    worker=tmp_path/'worker.py'
    worker.write_text('import sys,time\nfor line in sys.stdin:\n time.sleep(60)\n')
    monkeypatch.setattr(voice_jobs,'WORKER',worker)
    async def scenario():
        job=voice_jobs.create({'text':'test'})
        deadline=asyncio.get_running_loop().time()+5
        while 'process' not in voice_jobs.get(job['id']):
            assert asyncio.get_running_loop().time()<deadline
            await asyncio.sleep(.01)
        process=voice_jobs.get(job['id'])['process']
        cancelled=await voice_jobs.cancel(job['id'])
        assert cancelled['status']=='cancelled'
        assert process.returncode is not None
        assert not (Path(voice_jobs.get(job['id'])['temp'].name)/'audio.bin').exists()
        again=voice_jobs.create({'text':'restart'})
        assert again['status']=='running'
        await voice_jobs.cancel(again['id'])
        await voice_jobs.shutdown()
    asyncio.run(scenario())


def test_real_worker_reports_missing_model(monkeypatch):
    monkeypatch.delenv('HMONG_TTS_URL',raising=False)
    monkeypatch.delenv('HMONG_LOCAL_TTS_MODEL',raising=False)
    with TestClient(app.app) as client:
        job=client.post('/api/speech/jobs',json={'text':'Nyob zoo','dialect':'mww'}).json()['id']
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            state=client.get('/api/speech/jobs/'+job).json()
            if state['status']!='running':break
            time.sleep(.03)
        assert state['status']=='failed',state
        assert 'Hmong' in state['message']
        assert client.get('/api/speech/jobs/'+job+'/audio').status_code==409
