import importlib
import json
import wave
import pytest
from fastapi.testclient import TestClient
import app
from subtitles import normalize_script, parse_srt

@pytest.mark.parametrize('encoding', ['utf-8-sig', 'utf-16', 'utf-16-be', 'utf-16-le'])
def test_windows_text_import(encoding):
    with TestClient(app.app) as client:
        response=client.post('/api/scripts/import',files={'file':('lời.TXT','[00:01] Xin chào\n[00:03] Cảm ơn\n[00:05]'.encode(encoding),'text/plain')})
    assert response.status_code==200,response.text
    body=response.json()
    assert body['input_format']=='srt' and body['duration']==5
    assert [c['text'] for c in parse_srt(body['text'])]==['Xin chào','Cảm ơn']

def test_ambiguous_final_time_and_overlap_are_rejected():
    with pytest.raises(ValueError,match='kết thúc'):
        normalize_script('[00:01] Xin chào','txt')
    with pytest.raises(ValueError):
        normalize_script('00:02 --> 00:04 Xin chào\n00:03 --> 00:05 Cảm ơn','txt')
    assert normalize_script('Tôi có 20 phút và 100 nghìn đồng.','txt')[1]=='txt'

@pytest.mark.parametrize('seconds,limit,success',[(.7,1.5,True),(1.75,2,True),(2.5,1.5,False)])
def test_render_exact_timeline(tmp_path,monkeypatch,seconds,limit,success):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path))
    worker=importlib.import_module('worker');monkeypatch.setattr(worker,'DATA',tmp_path)
    (tmp_path/'audio').mkdir()
    text,kind=normalize_script('[00:00.500] Xin chào\n[00:01.500]','txt')
    def synth(text,path):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
            import math,struct
            f.writeframes(b''.join(struct.pack('<h',round(6000*math.sin(n*.07))) for n in range(round(seconds*24000))))
    job={'id':'timed','text':text,'input_format':kind,'engine':'system','format':'wav','speed':1,'max_cue_tempo':limit,'cue_fit':'strict'}
    if not success:
        with pytest.raises(ValueError,match='Câu SRT 1'):worker.render(job,synth)
        assert not (tmp_path/'audio/timed.wav').exists()
        return
    worker.render(job,synth)
    with wave.open(str(tmp_path/'audio/timed.wav')) as f:
        assert f.getnframes()==36000
        assert f.readframes(12000)==b'\0\0'*12000
        assert any(f.readframes(12000))
    assert parse_srt((tmp_path/'audio/timed.srt').read_text())==parse_srt(text)
    assert json.loads((tmp_path/'parts/timed/alignment.json').read_text())['sync_ok']


def test_explicit_txt_ranges():
    text,kind=normalize_script('00:00 --> 00:05 Xin chào\n00:06 --> 00:10 Cảm ơn','txt')
    assert kind=='srt'
    assert parse_srt(text)[-1]['end']==10

@pytest.mark.parametrize('encoding',['utf-8','utf-16'])
def test_million_character_file_and_segment_coverage(encoding):
    from narration import plan_segments
    source=('Xin chào các bạn. '*62500)[:1_000_000]
    assert len(source)==1_000_000
    with TestClient(app.app) as client:
        response=client.post('/api/scripts/import', files={'file':('dai.txt',source.encode(encoding),'text/plain')})
        assert response.status_code==200,response.text
        assert response.json()['text']==source
        too_long=client.post('/api/scripts/import',files={'file':('dai.txt',(source+'a').encode(encoding),'text/plain')})
        assert too_long.status_code==422
    segments=plan_segments({'text':source,'engine':'vieneu_nano','segment_plan':'nano-packed-v1'})
    assert ''.join(s.text for s in segments).replace(' ','')==source.replace(' ','')
    assert all(len(s.text)<=130 for s in segments)


def test_long_srt_and_original_example_exact_samples(tmp_path,monkeypatch):
    from subtitles import export_srt
    assert parse_srt(export_srt([{'start':72000,'end':72005,'text':'Xin chào'}]))[-1]['end']==72005
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path))
    worker=importlib.import_module('worker');monkeypatch.setattr(worker,'DATA',tmp_path)
    (tmp_path/'audio').mkdir()
    text='1\n00:27:20,519 --> 00:27:23,671\nXin chào.'
    def synth(text,path):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
            f.writeframes(b'\x00\x20'*24000)
    worker.render({'id':'example','text':text,'input_format':'srt','engine':'system','format':'wav','speed':1},synth)
    with wave.open(str(tmp_path/'audio/example.wav')) as f:
        assert f.getnframes()==round(1643.671*24000)
        f.setpos(round(1640.519*24000)-1)
        assert f.readframes(1)==b'\0\0'
        assert f.readframes(1)!=b'\0\0'
    assert parse_srt((tmp_path/'audio/example.srt').read_text())==parse_srt(text)


def test_duration_overflow_never_publishes_incomplete_audio(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path))
    worker=importlib.import_module('worker');monkeypatch.setattr(worker,'DATA',tmp_path)
    (tmp_path/'audio').mkdir()
    def synth(text,path):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
            f.writeframes(b'\x00\x20'*48000)
    with pytest.raises(ValueError,match='vượt giới hạn'):
        worker.render({'id':'limit','text':'Xin chào.','engine':'system','format':'wav','speed':1,'max_minutes':.01},synth)
    assert not (tmp_path/'audio/limit.wav').exists()
