import json,uuid,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_app import studio
from subtitles import minute_timestamp


def test_timed_text_export_and_caption_language(studio):
    client,root=studio
    ident=uuid.uuid4().hex;(root/'videos').mkdir();(root/'videos'/f'{ident}.json').write_text(json.dumps({'duration':200}))
    project={'language':'ja','cues':[{'start':90.5,'end':94.25,'text':'こんにちは。'}]}
    saved=client.put(f'/api/videos/{ident}/editor',json=project);assert saved.status_code==200 and saved.json()['language']=='ja'
    assert client.get(f'/api/videos/{ident}/editor').json()['language']=='ja'
    response=client.get(f'/api/videos/{ident}/editor/export.timed-txt')
    assert response.status_code==200 and response.text=='01:30.500 --> 01:34.250\nこんにちは。'
    assert 'こんにちは。' in client.get(f'/api/videos/{ident}/editor/export.srt').text
    assert minute_timestamp(10800)=='180:00.000'


def test_detected_caption_language_survives_recognition_cache(tmp_path,monkeypatch):
    import faster_whisper,dubbing
    from recognition import recognize
    source=tmp_path/'videos/a.source';source.parent.mkdir();source.write_bytes(b'video')
    model=tmp_path/'models/whisper-base';model.mkdir(parents=True);(model/'model.bin').write_bytes(b'model')
    work=tmp_path/'work';work.mkdir();calls=[]
    class Whisper:
        def __init__(self,*a,**kw):calls.append(1)
        def transcribe(self,*a,**kw):return iter([SimpleNamespace(start=0,end=1,text='你好')]),SimpleNamespace(language='zh')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Whisper);monkeypatch.setattr(dubbing,'run_ffmpeg',lambda *a,**kw:None)
    for _ in range(2):
        recognize(source,model,{'source_language':'auto'},work,{'duration':2},lambda *a:None)
        assert json.loads((work/'recognition.json').read_text())['language']=='zh'
        (work/'recognition.json').unlink()
    assert len(calls)==1


@pytest.mark.parametrize('language,translated',[('vi','Xin chào'),('en-US','Hello'),('ja','こんにちは'),('ko','안녕하세요')])
def test_subtitle_translation_result_keeps_actual_language_and_timing(tmp_path,monkeypatch,language,translated):
    import video_tasks
    from dubbing import inspect_video
    video=tmp_path/'videos';video.mkdir();source=video/'a.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x90:d=2','-c:v','libx264','-f','mp4',str(source)],check=True)
    (video/'a.json').write_text(json.dumps(inspect_video(source)))
    work=tmp_path/'video_tasks/b';work.mkdir(parents=True)
    path=work/'job.json';path.write_text(json.dumps({'video_id':'a','action':'subtitles','source_language':'zh','target_language':language,'srt':'1\n00:00:00,200 --> 00:00:01,500\n你好\n'}))
    def translate(cues,*args):return [dict(c,text=translated) for c in cues]
    monkeypatch.setattr(video_tasks,'translate_cues',translate);video_tasks.run(path)
    from subtitles import parse_srt
    assert parse_srt((work/'output.srt').read_text())==[{'start':.2,'end':1.5,'text':translated}]
    assert json.loads((work/'result.json').read_text())['caption_language']==language
