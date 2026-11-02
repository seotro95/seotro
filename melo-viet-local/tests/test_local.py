import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import wave

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app
import worker


@pytest.fixture(autouse=True)
def clean_model_cache():
    worker.models.clear();worker.model=None;worker.model_key=None
    yield
    worker.models.clear();worker.model=None;worker.model_key=None


def wait(studio):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        with studio.lock:job=dict(studio.job)
        if job['status'] not in {'queued','running'}:return job
        time.sleep(.01)
    raise AssertionError('Timed out')


class FakeReader:
    def __init__(self,*args):pass
    def request(self,body,cancel=None):
        if body['op']=='voices':return {'voices':[{'id':body['language'],'name':body['language']}],'model_load_seconds':0}
        with wave.open(body['output'],'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*2400)
        return {'voices':[], 'audio_seconds':.1,'model_load_seconds':0,'voice':body['voice'],'engine':'synthetic test only'}
    def close(self):pass


@pytest.fixture
def studio(tmp_path):
    s=app.Studio(tmp_path,reader_factory=FakeReader)
    yield s
    s.close()


@pytest.mark.parametrize('language',list(app.LABELS))
def test_each_supported_language_routes_to_the_correct_isolated_reader(studio,language):
    seen=[]
    class Reader(FakeReader):
        def __init__(self,root,name,offline):self.name=name
        def request(self,body,cancel=None):seen.append(self.name);return super().request(body,cancel)
    studio.reader_factory=Reader
    studio.start({'op':'voices','language':language,'threads':4})
    assert wait(studio)['status']=='done'
    assert seen==['viet' if language=='VI' else 'melo']


@pytest.mark.parametrize('language',['XX','TH','EN-US','vi','../x'])
def test_unsupported_languages_are_rejected_without_substitution(studio,language):
    with pytest.raises(ValueError):studio.start({'op':'voices','language':language})


def test_outputs_are_owned_and_speed_report_does_not_verify_30x(studio,tmp_path):
    studio.start({'op':'render','language':'VI','voice':'VI','text':'Xin chào.','output':'../outside.wav'})
    result=wait(studio)
    assert result['status']=='done' and result['target_30x_verified'] is False
    assert (tmp_path/'outputs'/result['id']/'part-0001.wav').is_file()
    assert not (tmp_path.parent/'outside.wav').exists()
    assert 'khoảng nghỉ' in result['measurement']


def test_cancelled_late_result_cannot_overwrite_next_job(studio):
    entered=threading.Event();release=threading.Event()
    class Slow(FakeReader):
        def request(self,body,cancel=None):entered.set();release.wait(5);return super().request(body,cancel)
    studio.reader_factory=lambda root,engine,offline:Slow() if engine=='viet' else FakeReader()
    first=studio.start({'op':'voices','language':'VI'})
    assert entered.wait(2)
    studio.cancel()
    second=studio.start({'op':'voices','language':'EN'})
    assert wait(studio)['id']==second['id']
    release.set();time.sleep(.05)
    assert studio.job['id']==second['id'] and studio.job['status']=='done'


@pytest.mark.parametrize('threads',[0,17,True,1.5,'4'])
def test_invalid_cpu_budgets_are_rejected(studio,threads):
    with pytest.raises(ValueError):studio.start({'op':'voices','language':'EN','threads':threads})


def test_http_origin_guard_and_generated_audio_route(studio):
    server=app.ThreadingHTTPServer(('127.0.0.1',0),app.handler(studio))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    try:
        with urllib.request.urlopen(base+'/api/config') as r:assert len(json.load(r)['languages'])==27
        req=urllib.request.Request(base+'/api/start',data=json.dumps({'op':'render','language':'EN','voice':'EN','text':'Hello.'}).encode(),headers={'Content-Type':'application/json','Origin':'https://attacker.example'})
        with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        assert e.value.code==403
        req=urllib.request.Request(base+'/api/start',data=json.dumps({'op':'render','language':'EN','voice':'EN','text':'Hello.'}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as r:assert r.status==202
        job=wait(studio)
        with urllib.request.urlopen(base+job['audio_url']) as r:assert r.read().startswith(b'RIFF')
        with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(base+'/audio/../../app.py')
    finally:server.shutdown();server.server_close();thread.join(2)


def test_worker_protocol_starts_before_sdk_import_and_rejects_unknown_language():
    result=subprocess.run([sys.executable,str(ROOT/'worker.py')],input=json.dumps({'op':'voices','language':'RU'})+'\n',capture_output=True,text=True,timeout=10)
    lines=result.stdout.splitlines();assert json.loads(lines[0])=={'ready':True}
    assert json.loads(lines[1])['ok'] is False


@pytest.mark.parametrize('language',['VI','EN'])
def test_pcm_headroom_preserves_waveform_duration_and_requested_text(tmp_path,language):
    rate=24000;source=(1.8*np.sin(2*np.pi*220*np.arange(2400)/rate)).astype(np.float32)
    class Model:
        sample_rate=rate
        hps=type('H',(),{'data':type('D',(),{'spk2id':{'speaker':0},'sampling_rate':rate})()})()
        def infer(self,text,voice):assert text=='Original text' and voice=='speaker';return source.copy()
        def tts_to_file(self,text,speaker,**kwargs):assert text=='Original text' and speaker==0 and kwargs['speed']==1;return source.copy()
    path=tmp_path/'out.wav'
    result=worker.synthesize(Model(),language,'speaker','Original text',path)
    import soundfile
    audio,sample_rate=soundfile.read(path)
    assert len(audio)==len(source) and sample_rate==rate
    assert np.max(np.abs(audio))<=.951
    assert np.max(np.abs(audio-source*(.95/np.max(np.abs(source)))))<.00004


def test_resident_model_is_reused_and_cpu_mode_is_explicit(monkeypatch):
    from types import SimpleNamespace
    seen=[]
    class TTS:
        hps=SimpleNamespace(data=SimpleNamespace(spk2id={'EN-US':0}))
        def __init__(self,**kwargs):seen.append(kwargs)
    monkeypatch.setitem(sys.modules,'melo.api',SimpleNamespace(TTS=TTS))
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(set_num_threads=lambda count:None))
    monkeypatch.setattr(worker,'model',None);monkeypatch.setattr(worker,'model_key',None)
    first,_,_=worker.read_model('EN',4);second,_,_=worker.read_model('EN',4)
    assert first is second and seen==[{'language':'EN','device':'cpu'}]


def test_empty_or_nonfinite_audio_never_replaces_existing_file(tmp_path):
    class Model:
        sample_rate=24000
        def infer(self,*args,**kwargs):return np.array([float('nan')],dtype=np.float32)
    path=tmp_path/'out.wav';path.write_bytes(b'previous')
    with pytest.raises(ValueError):worker.synthesize(Model(),'VI','voice','Hello',path)
    assert path.read_bytes()==b'previous'


@pytest.mark.parametrize('filename,action',[('CAI_DAT.bat','install'),('MO_TOOL.bat','run'),('MO_OFFLINE.bat','offline')])
def test_windows_entrypoints_set_the_expected_action_without_changing_execution_policy(filename,action):
    source=(ROOT/filename).read_text()
    assert 'set "MELO_VIET_ACTION='+action+'"' in source
    assert 'ExecutionPolicy' not in source


def test_failed_language_switch_cannot_reuse_a_released_model(monkeypatch):
    from types import SimpleNamespace
    class TTS:
        hps=SimpleNamespace(data=SimpleNamespace(spk2id={'EN-US':0}))
        def __init__(self,language,device):
            if language=='FR':raise RuntimeError('Synthetic missing model')
    monkeypatch.setitem(sys.modules,'melo.api',SimpleNamespace(TTS=TTS))
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(set_num_threads=lambda count:None))
    monkeypatch.setattr(worker,'model',None);monkeypatch.setattr(worker,'model_key',None)
    first,_,_=worker.read_model('EN',4)
    with pytest.raises(RuntimeError):worker.read_model('FR',4)
    again,_,_=worker.read_model('EN',4)
    assert again is first  # Failed construction keeps the valid cached model.


def test_melo_speaker_catalog_accepts_upstream_hparams_mapping(monkeypatch):
    from types import SimpleNamespace
    class HParams:
        def keys(self):return {'EN-US':0,'EN-BR':1}.keys()
        def __getitem__(self,key):
            if not isinstance(key,str):raise TypeError('getattr(): attribute name must be string')
            return {'EN-US':0,'EN-BR':1}[key]
    class TTS:
        hps=SimpleNamespace(data=SimpleNamespace(spk2id=HParams()))
        def __init__(self,**kwargs):pass
    monkeypatch.setitem(sys.modules,'melo.api',SimpleNamespace(TTS=TTS))
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(set_num_threads=lambda count:None))
    monkeypatch.setattr(worker,'model',None);monkeypatch.setattr(worker,'model_key',None)
    _,voices,_=worker.read_model('EN',4)
    assert [v['id'] for v in voices]==['EN-US','EN-BR']
