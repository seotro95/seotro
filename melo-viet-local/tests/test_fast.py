import asyncio
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time
from types import SimpleNamespace
import wave

import numpy as np
import pytest

import app
import fast_backend
import online_backend
from test_studio import body,await_job


def test_real_catalog_adds_twenty_languages_and_only_uses_fp32_models():
    models=fast_backend.catalog()
    assert len(models)==49 and sum(m.get('bundled',True) for m in models)==27 and len(fast_backend.labels())==24
    assert set(app.LOCAL_LABELS)==set(app.LABELS)|set(fast_backend.labels())|set(app.MULTI_LANGUAGES)|{'HMN'}
    assert len(set(app.FAST_LABELS)-set(app.LABELS))==20
    for model in models:
        assert 'int8' not in model['id'] and 'fp16' not in model['id']
        assert model['quality']=='medium' if model.get('bundled',True) else model['quality'] in {'x_low','low','medium','high'}
        assert len(model['archive_sha256'])==64 and model['archive_bytes']>0
        assert model['archive_url'].startswith('https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/')


@pytest.mark.parametrize('language',list(app.FAST_LABELS))
def test_fast_voice_discovery_is_real_and_requires_no_model_download(language,monkeypatch):
    monkeypatch.setattr(fast_backend,'ensure_model',lambda *a,**k:pytest.fail('Listing voices must not download a model'))
    result=fast_backend.handle({'op':'voices','language':language})
    assert result['voices'] and all(v['id'].startswith('piper:') for v in result['voices'])
    assert app.backend_for({'op':'voices','engine':'local','language':language,'local_provider':'fast'})=='piper'


def test_offline_missing_model_never_attempts_network(tmp_path,monkeypatch):
    monkeypatch.setattr(fast_backend,'model_root',lambda:tmp_path)
    monkeypatch.setattr(fast_backend.urllib.request,'urlopen',lambda *a,**k:pytest.fail('Offline must not connect'))
    with pytest.raises(ValueError,match='ngoại tuyến'):fast_backend.ensure_model(fast_backend.catalog()[0],True)


def test_download_checks_sha_and_ignores_traversal_and_links(tmp_path,monkeypatch):
    ident='en_US-test-medium';files={'model.onnx':b'fake model bytes','config.json':b'{}','MODEL_CARD':b'public test'}
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:bz2') as t:
        mapping={'model.onnx':ident+'.onnx','config.json':ident+'.onnx.json','MODEL_CARD':'MODEL_CARD'}
        for name,raw in files.items():
            entry=tarfile.TarInfo('vits-piper-'+ident+'/'+mapping[name]);entry.size=len(raw);t.addfile(entry,io.BytesIO(raw))
        entry=tarfile.TarInfo('../outside.txt');entry.size=6;t.addfile(entry,io.BytesIO(b'unsafe'))
        link=tarfile.TarInfo('vits-piper-'+ident+'/escape');link.type=tarfile.SYMTYPE;link.linkname='/etc/passwd';t.addfile(link)
    raw=stream.getvalue();record={'id':ident,'files':{n:hashlib.sha256(v).hexdigest() for n,v in files.items()},'archive_bytes':len(raw),'archive_sha256':hashlib.sha256(raw).hexdigest(),'archive_url':'https://github.com/public/test'}
    monkeypatch.setattr(fast_backend,'model_root',lambda:tmp_path/'models')
    monkeypatch.setattr(fast_backend.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(raw))
    folder=fast_backend.ensure_model(record)
    assert set(p.name for p in folder.iterdir())==set(files)
    assert not (tmp_path/'outside.txt').exists()
    for name,content in files.items():assert (folder/name).read_bytes()==content


def test_batch_output_order_is_preserved_when_workers_finish_out_of_order(tmp_path,monkeypatch):
    model=fast_backend.catalog()[0];voice=fast_backend.voices_for(model['language'])[0]['id']
    monkeypatch.setattr(fast_backend,'load_voice',lambda record,threads,offline,lane,keep:(lane,0))
    def generate(reader,text,path,selected):
        time.sleep((3-reader)*.005);Path(path).write_text(text);return {'text':text}
    monkeypatch.setattr(fast_backend,'generate',generate)
    entries=[{'text':str(i),'output':str(tmp_path/(str(i)+'.wav'))} for i in range(4)]
    result=fast_backend.handle({'op':'render_many','language':model['language'],'voice':voice,'threads':2,'entries':entries})
    assert [r['text'] for r in result['results']]==['0','1','2','3']


class PiperFake:
    next=0
    def __init__(self,*args):pass
    def close(self):pass
    def request(self,payload,cancel=None):
        assert payload['op']=='render_many'
        results=[]
        for entry in payload['entries']:
            PiperFake.next+=1
            with wave.open(entry['output'],'wb') as f:
                f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(PiperFake.next.to_bytes(2,'little')*2400)
            results.append({'audio_seconds':.1,'model_load_seconds':0})
        return {'results':results,'model_load_seconds':0}


def test_parallel_chunk_assembly_preserves_order_and_each_fresh_duplicate(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'available_cpus',lambda:64);PiperFake.next=0
    s=app.Studio(tmp_path,reader_factory=PiperFake)
    try:
        voice=fast_backend.voices_for('ES')[0]['id']
        j=await_job(s,s.start(body(language='ES',voice=voice,text=('X'*79+' ')*5,chunk_size=80,chunk_workers=4,use_cache=False))['id'])
        assert j['status']=='done' and j['parallel_chunks']==4 and j['completed_chunks']==5
        with wave.open(str(tmp_path/'outputs'/j['id']/'part-0001.wav'),'rb') as f:audio=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
        nonzero=audio[audio!=0]
        assert np.array_equal(nonzero,np.repeat(np.arange(1,6,dtype='<i2'),2400))
    finally:s.close()


def test_cpu_quota_limits_parallel_chunks(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'available_cpus',lambda:4);PiperFake.next=0
    s=app.Studio(tmp_path,reader_factory=PiperFake)
    try:
        j=await_job(s,s.start(body(language='ES',voice=fast_backend.voices_for('ES')[0]['id'],text='Hola.',threads=4,chunk_workers=4))['id'])
        assert j['status']=='done' and j['parallel_chunks']==1
    finally:s.close()


def test_online_refresh_replaces_stale_memory_and_disk_catalog(tmp_path,monkeypatch):
    monkeypatch.setattr(online_backend,'catalog_file',lambda:tmp_path/'catalog.json')
    monkeypatch.setattr(online_backend,'CATALOG',[{'ShortName':'stale'}])
    async def fetch():return [{'ShortName':'fresh','Locale':'en-US','Gender':'Female','FriendlyName':'fresh'}]
    monkeypatch.setattr(online_backend,'fetch_catalog',fetch)
    assert online_backend.get_catalog()[0]['ShortName']=='stale'
    assert online_backend.get_catalog(True)[0]['ShortName']=='fresh'
    assert json.loads((tmp_path/'catalog.json').read_text())[0]['ShortName']=='fresh'


def test_online_no_audio_error_is_visible_and_never_changes_selected_voice(monkeypatch,tmp_path):
    selected=[]
    class NoAudioReceived(Exception):pass
    class Communicate:
        def __init__(self,text,voice,**kwargs):selected.append(voice)
        async def save(self,output):raise NoAudioReceived('No audio')
    async def no_sleep(*args):pass
    monkeypatch.setitem(sys.modules,'edge_tts',SimpleNamespace(Communicate=Communicate))
    monkeypatch.setattr(online_backend.asyncio,'sleep',no_sleep)
    with pytest.raises(RuntimeError,match='không trả về âm thanh'):
        asyncio.run(online_backend.download_audio('Hello','en-US-Test',tmp_path/'a.mp3'))
    assert selected==['en-US-Test']*3
