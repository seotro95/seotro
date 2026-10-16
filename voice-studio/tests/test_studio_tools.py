import asyncio
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import writing
from translation import translate_cues
from video_tasks import logo_filters,run
from dubbing import inspect_video
from test_app import studio


@pytest.mark.parametrize('provider',['openai','gemini'])
def test_cloud_translation_preserves_cues_without_ollama(monkeypatch,provider):
    seen=[]
    async def api(method,url,**kwargs):
        seen.append((url,kwargs))
        if provider=='openai':
            return {'status':'completed','output':[{'content':[{'type':'output_text','text':'{"texts":["Xin chào","Số 123"]}'}]}]}
        return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"texts":["Xin chào","Số 123"]}'}]}}]}
    async def no_ollama(*args):raise AssertionError('Cloud translation must not require Ollama')
    monkeypatch.setattr(writing,'request_api',api);monkeypatch.setattr(writing,'request_local',no_ollama)
    monkeypatch.setattr(writing,'get_key',lambda p:'private-test-key')
    cues=[{'start':0,'end':1,'text':'Hello'},{'start':2,'end':3,'text':'Number 123'}]
    assert translate_cues(cues,'vi','',lambda *a:None,provider,'en-US')==[{'start':0,'end':1,'text':'Xin chào'},{'start':2,'end':3,'text':'Số 123'}]
    assert seen and seen[0][1]['headers']


def test_key_only_in_child_environment_not_job_files(studio,monkeypatch):
    import app
    client,data=studio
    key='never-write-this-test-key'
    monkeypatch.setattr(writing,'get_key',lambda p:key)
    monkeypatch.setattr(app.executor,'submit',lambda *args:None)
    r=client.post('/api/video-tasks',json={'action':'translate_text','text':'Hello','target_language':'vi','provider':'openai'})
    assert r.status_code==202,r.text
    ident=r.json()['id'];work=app.video_task_work(ident)
    seen={}
    class FakeProcess:
        returncode=0
        def poll(self):return 0
    def spawn(*args,**kwargs):seen.update(kwargs);return FakeProcess()
    monkeypatch.setattr(app.subprocess,'Popen',spawn)
    app.run_video_task(ident)
    assert seen['env']['OPENAI_API_KEY']==key
    assert key not in (work/'job.json').read_text()
    assert all(key not in path.read_text(errors='ignore') for path in data.rglob('*.json'))


def test_catalog_never_hides_unloaded_international_voices(studio,monkeypatch):
    client,data=studio
    monkeypatch.setenv('VOICE_STUDIO_PORTABLE','1')
    voices=client.get('/api/voices').json()['voices']
    korean=[v for v in voices if 'ko' in v['languages'] and v['engine']=='qwen']
    assert korean and all(v['ready'] is False for v in korean)
    assert client.post('/api/video-tasks',json={'action':'prepare_voice','engine':'shell'}).status_code==422


def test_missing_asr_model_is_actionable_before_enqueue(studio):
    client,data=studio
    (data/'videos').mkdir();ident='a'*32
    (data/'videos'/f'{ident}.json').write_text(json.dumps({'duration':3}))
    r=client.post('/api/video-tasks',json={'video_id':ident,'action':'subtitles'})
    assert r.status_code==503 and 'Whisper' in r.json()['detail']
    assert not list((data/'jobs').glob('*.json'))


def test_multi_region_colors_are_validated_and_encoded(tmp_path):
    videos=tmp_path/'videos';videos.mkdir();work=tmp_path/'video_tasks'/'b';work.mkdir(parents=True)
    source=videos/'a.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x240:r=5:d=0.4','-c:v','libx264','-f','mp4',str(source)],check=True)
    meta=inspect_video(source);(videos/'a.json').write_text(json.dumps(meta))
    regions=[{'x':10,'y':10,'w':40,'h':30,'mode':'color','color':'#ff0000'},{'x':100,'y':100,'w':40,'h':30,'mode':'color','color':'#00ff00'}]
    job={'video_id':'a','action':'logo','logos':regions,'export_quality':'fast'}
    path=work/'job.json';path.write_text(json.dumps(job));run(path)
    import numpy as np
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(work/'output.mp4'),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
    image=np.frombuffer(raw,dtype=np.uint8).reshape(240,320,3)
    assert image[25,25,0]>200 and image[25,25,1]<40
    assert image[115,115,1]>200 and image[115,115,0]<40
    with pytest.raises(ValueError):logo_filters({'logos':[dict(regions[0],color='red;movie=bad')]},meta)
    with pytest.raises(ValueError):logo_filters({'logos':[regions[0]]*21},meta)


def test_recognition_cache_skips_second_decode(tmp_path,monkeypatch):
    import faster_whisper,dubbing
    from recognition import recognize
    source=tmp_path/'videos'/'a.source';source.parent.mkdir();source.write_bytes(b'input')
    model=tmp_path/'models'/'whisper-base';model.mkdir(parents=True);(model/'model.bin').write_bytes(b'model')
    work=tmp_path/'work';work.mkdir();calls=[]
    class FakeWhisper:
        def __init__(self,*a,**kw):calls.append(1)
        def transcribe(self,*a,**kw):return iter([SimpleNamespace(start=0,end=1,text='Xin chào')]),None
    monkeypatch.setattr(faster_whisper,'WhisperModel',FakeWhisper)
    monkeypatch.setattr(dubbing,'run_ffmpeg',lambda *a,**kw:None)
    job={'source_language':'vi','accurate':False}
    first=recognize(source,model,job,work,{'duration':2},lambda *a:None)
    second=recognize(source,model,job,work,{'duration':2},lambda *a:None)
    assert first==second and len(calls)==1
    source.write_bytes(b'changed-input')
    recognize(source,model,job,work,{'duration':2},lambda *a:None)
    assert len(calls)==2


def test_refresh_explicitly_invalidates_sapi_cache(studio,monkeypatch):
    import app
    client,_=studio;calls=[]
    class VoiceScan:
        def __call__(self):return []
        def cache_clear(self):calls.append('clear')
    monkeypatch.setattr(app,'installed_voices',VoiceScan())
    assert client.post('/api/voices/refresh').status_code==200
    assert calls==['clear']


def test_text_translation_chunking_keeps_words_and_pause_markup(tmp_path,monkeypatch):
    import video_tasks
    work=tmp_path/'video_tasks'/'a';work.mkdir(parents=True)
    text=('Xin **chào** [pause=0.7] thế giới số 123.\n'*90).strip()
    def identity(cues,language,model,update,provider,source):
        assert provider=='openai' and source=='en-US'
        assert all(isinstance(c['text'],str) for c in cues)
        update(98,'Test transport')
        return cues
    monkeypatch.setattr(video_tasks,'translate_cues',identity)
    path=work/'job.json';path.write_text(json.dumps({'action':'translate_text','text':text,'input_format':'txt','target_language':'vi','source_language':'en-US','provider':'openai'}))
    video_tasks.run(path)
    assert (work/'translated.txt').read_text().split()==text.split()


def test_incomplete_cloud_translation_never_returns_partial_cues(monkeypatch):
    async def incomplete(*a,**kw):return {'status':'incomplete','output':[]}
    monkeypatch.setattr(writing,'request_api',incomplete);monkeypatch.setattr(writing,'get_key',lambda p:'test-key')
    cues=[{'start':0,'end':2,'text':'Original text'}]
    with pytest.raises(ValueError,match='chưa đầy đủ'):translate_cues(cues,'vi','',lambda *a:None,'openai','en')
    assert cues[0]['text']=='Original text'


def test_delete_video_removes_recognition_cache(studio):
    client,data=studio;ident='b'*32
    (data/'videos').mkdir();(data/'videos'/f'{ident}.json').write_text(json.dumps({'id':ident,'duration':2}))
    cache=data/'asr_cache'/ident;cache.mkdir(parents=True);(cache/'cached.srt').write_text('private test transcript')
    assert client.delete('/api/videos/'+ident).status_code==204
    assert not cache.exists()
