import hashlib
import io
import json
from pathlib import Path
import time
import wave

import pytest
from fastapi.testclient import TestClient

import app
import voice_jobs
from test_subtitle_voice_api import upload

WORKER = r'''
import json,sys,wave
from pathlib import Path
for line in sys.stdin:
    folder=Path(json.loads(line)['folder']); payload=json.loads((folder/'input.json').read_text(encoding='utf-8'))
    if payload['timing']=='fit':
        print(json.dumps({'ok':False,'error':'Phụ đề quá ngắn; có thể tạo lại đọc liền.'}),flush=True)
        continue
    parts=folder/'parts';parts.mkdir(exist_ok=True)
    with wave.open(str(parts/'part-0001.wav'),'wb') as audio:
        audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(bytes([1,1])*2400)
    (folder/'result.json').write_text(json.dumps({'completed':1,'total':1,'audio_seconds':.1,'parts':[{'number':1,'filename':'part-0001.wav','seconds':.1}]}))
    print(json.dumps({'ok':True}),flush=True)
'''


def wait_job(client, ident):
    deadline=time.monotonic()+5
    while True:
        result=client.get('/api/speech/jobs/'+ident).json()
        if result['status']!='running':return result
        assert time.monotonic()<deadline
        time.sleep(.01)


def test_history_survives_restart_downloads_and_retry_keeps_original_voice(tmp_path,monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR',str(tmp_path/'data'))
    monkeypatch.setattr(app.cloning_engine,'availability',lambda:{'ready':True,'reason':''})
    monkeypatch.setattr(app,'hardware_info',lambda:{'device':'cpu'})
    worker=tmp_path/'fake_worker.py';worker.write_text(WORKER);monkeypatch.setattr(voice_jobs,'WORKER',worker)
    text='196\n00:05:33,366 --> 00:05:34,533\nnws tsis txhawj txog nws tus kheej ntau'
    with TestClient(app.app) as client:
        voice=upload(client)
        result=client.post('/api/speech/jobs',json={'voice':voice['id'],'text':text})
        assert result.status_code==202
        failed=result.json()['id'];assert wait_job(client,failed)['status']=='failed'
        old_folder=voice_jobs.get(failed)['folder']; original=(old_folder/'reference.wav').read_bytes()
        client.put('/api/voices/'+voice['id']+'/reference',json={'start':0,'end':4,'text':'New text for future recordings.'})
        result=client.post('/api/speech/jobs/'+failed+'/retry-natural')
        assert result.status_code==202,result.text
        new=result.json()['id'];assert new!=failed
        final=wait_job(client,new);assert final['status']=='completed',final
        snapshot=json.loads((voice_jobs.get(new)['folder']/'input.json').read_text())
        assert snapshot['timing']=='natural' and snapshot['_reference']['text']=='This is the exact English reference.'
        assert Path(snapshot['_reference']['path']).read_bytes()==original
        assert snapshot['target_seconds'] is None
        assert client.get('/api/speech/jobs/'+failed).json()['status']=='failed'
    with TestClient(app.app) as client:
        history=client.get('/api/speech/jobs').json()['jobs']
        assert len(history)==2
        assert next(item for item in history if item['id']==failed)['first_speech_seconds']==333.366
        assert next(item for item in history if item['id']==new)['first_speech_seconds']==0
        final=next(item for item in history if item['id']==new)
        assert final['status']=='completed' and 'nws tsis txhawj' in final['title']
        assert '196' not in final['title'] and '00:05' not in final['title']
        response=client.get(final['parts'][0]['url']+'?download=true')
        assert 'attachment' in response.headers['content-disposition']
        with wave.open(io.BytesIO(response.content)) as sound:assert sound.getnframes()==2400
        ranged=client.get(final['parts'][0]['url'],headers={'Range':'bytes=0-43'})
        assert ranged.status_code==206 and len(ranged.content)==44
        assert client.post('/api/speech/jobs/'+new+'/retry-natural').status_code==409


def test_quoted_user_srt_preserves_hmong_tone_letters_and_warns_dense_slot():
    data=app.preview_document(app.DocumentInput(text='"196\n00:05:33,366 --> 00:05:34,533\nnws tsis txhawj txog nws tus kheej ntau"'))
    assert data['text']=='nws tsis txhawj txog nws tus kheej ntau'
    assert data['timed'] and data['duration']==334.533 and data['cue_count']==1
    assert data['warnings'] and '1.167' in data['warnings'][0]


def test_first_spoken_position_points_to_correct_chapter():
    result=app.public_job({'id':'abc','first_speech_seconds':2000.125,'parts':[
        {'number':1,'seconds':1800},{'number':2,'seconds':600}]})
    assert 'speech_offset_seconds' not in result['parts'][0]
    assert result['parts'][1]['speech_offset_seconds']==200.125
