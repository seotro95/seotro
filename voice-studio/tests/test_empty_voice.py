import importlib,wave
from unittest.mock import Mock
import pytest
from test_app import studio
from narration import Segment,validate_voice_text


def pcm(path,frames=24000,silent=False):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes((b'\x00\x00' if silent else b'\x00\x20')*frames)


def test_empty_audio_retry_keeps_exact_text_and_does_not_cache_empty(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path));worker=importlib.import_module('worker');calls=[]
    def synth(text,path):calls.append(text);pcm(path,0 if len(calls)==1 else 24000)
    worker.prepare_chunk({'engine':'vieneu','speed':1},Segment(text='Xin chào.'),0,tmp_path,synth)
    assert calls==['Xin chào.']*2
    with wave.open(str(tmp_path/'000000.wav')) as f:assert f.getnframes()==24000
    assert not (tmp_path/'raw-000000.wav').exists()


def test_all_silence_is_retried_and_reported_with_cue(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path));worker=importlib.import_module('worker');calls=[]
    def synth(text,path):calls.append(text);pcm(path,silent=True)
    with pytest.raises(ValueError,match='Câu SRT 3.*sau 3 lần'):
        worker.prepare_chunk({'engine':'vieneu','speed':1,'input_format':'srt','speaker':'Mai Anh'},Segment(text='Xin chào.',cue=2),0,tmp_path,synth)
    assert len(calls)==3 and not (tmp_path/'000000.wav').exists()


def test_invalid_empty_checkpoint_is_regenerated_and_stop_prevents_retry(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path));worker=importlib.import_module('worker');pcm(tmp_path/'000000.wav',0)
    synth=Mock(side_effect=lambda text,path:pcm(path));worker.prepare_chunk({'engine':'vieneu','speed':1},Segment(text='Xin chào.'),0,tmp_path,synth);assert synth.call_count==1
    def stop(text,path):pcm(path,0);(tmp_path/'cancel.flag').touch()
    with pytest.raises(InterruptedError):worker.prepare_chunk({'engine':'vieneu','speed':1},Segment(text='Xin chào.'),1,tmp_path,stop)
    assert not (tmp_path/'000001.wav').exists()


@pytest.mark.parametrize('text',['你好，欢迎来到餐馆。','こんにちは。','안녕하세요.'])
def test_vieneu_rejects_unsupported_text_before_synthesis(text):
    with pytest.raises(ValueError,match='Dịch lời'):validate_voice_text(text,'vieneu_nano','Câu SRT 1')
    validate_voice_text(text,'qwen','Câu SRT 1')


def test_wrong_script_api_fails_before_queue(studio):
    client,root=studio;(root/'models/vieneu_nano.ready').touch()
    response=client.post('/api/speech',json={'text':'1\n00:00:00,000 --> 00:00:03,000\n你好\n','input_format':'srt','language':'vi','voice_id':'nano-minhquan','format':'wav'})
    assert response.status_code==422 and 'Câu SRT 1' in response.json()['detail'] and 'Dịch lời' in response.json()['detail']
    assert not list((root/'jobs').glob('*.json'))


def test_nano_render_recovers_with_same_voice_at_sixteen_steps(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path));worker=importlib.import_module('worker');monkeypatch.setattr(worker,'DATA',tmp_path);(tmp_path/'audio').mkdir();steps=[]
    def factory(job):
        steps.append((job['nano_steps'],job['speaker']))
        return lambda text,path:pcm(path,24000 if job['nano_steps']>=16 else 0)
    monkeypatch.setattr(worker,'get_synthesizer',factory)
    worker.render({'id':'retry','engine':'vieneu_nano','text':'Xin chào.','nano_steps':4,'speaker':'Minh Quân','language':'vi','speed':1,'format':'wav'})
    assert steps==[(4,'Minh Quân'),(4,'Minh Quân'),(16,'Minh Quân')]
    with wave.open(str(tmp_path/'audio/retry.wav')) as f:assert f.getnframes()>0


def test_sentence_punctuation_and_emoji_do_not_become_empty_speech_chunks():
    from narration import plan_segments
    segments=plan_segments({'text':'Xin chào!!!😊','engine':'vieneu_nano','input_format':'txt'})
    assert ''.join(s.text for s in segments)=='Xin chào!!!😊'
    for s in segments:
        if s.text:validate_voice_text(s.text,'vieneu_nano')


def test_fresh_versioned_assets_are_used_when_opening_updated_studio(studio):
    client,_=studio
    import re,app
    response=client.get('/')
    assert response.headers['cache-control']=='no-store'
    assets=re.findall(r'(?:src|href)="(/static/[^" ]+)"',response.text)
    assert len(assets)>=6
    for asset in assets:
        assert '?v='+app.app.version in asset
        assert client.get(asset).status_code==200
