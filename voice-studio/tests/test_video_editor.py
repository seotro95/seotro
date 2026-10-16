import json
import subprocess
import pytest
from video_editor import validate_cues,write_ass
from video_tasks import run
from dubbing import inspect_video


def test_edit_validation():
    cues=[{'start':0,'end':1,'text':'Xin chào'}]
    assert validate_cues(cues,2)==cues
    for invalid in ([{'start':0,'end':3,'text':'a'}],[{'start':1,'end':1,'text':'a'}],cues+[{'start':.5,'end':2,'text':'b'}]):
        with pytest.raises(ValueError):validate_cues(invalid,2)


def test_real_burned_subtitles_and_logo(tmp_path):
    video=tmp_path/'videos';video.mkdir()
    work=tmp_path/'video_tasks'/'b';work.mkdir(parents=True)
    source=video/'a.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:size=320x240:rate=10:duration=2','-c:v','libx264','-f','mp4',str(source)],check=True)
    (video/'a.json').write_text(json.dumps(inspect_video(source)))
    path=work/'job.json';path.write_text(json.dumps({'video_id':'a','action':'render','logo':{'x':10,'y':10,'w':40,'h':30},'cues':[{'start':0,'end':1.5,'text':'Xin chào Việt Nam'}]}))
    run(path)
    out=work/'output.mp4'
    assert inspect_video(out)['duration']==2
    # Decoded pixels must contain the actual burned text, not a subtitle sidecar.
    def frame(file,at):
        return subprocess.check_output(['ffmpeg','-v','error','-ss',str(at),'-i',str(file),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
    import numpy as np
    pixels=np.frombuffer(frame(out,.5),dtype=np.uint8).reshape(240,320,3)
    assert ((pixels[120:]>180).all(axis=2)).sum()>20
    late=np.frombuffer(frame(out,1.8),dtype=np.uint8).reshape(240,320,3)
    assert ((late[120:]>180).all(axis=2)).sum()==0
    assert len(frame(out,1.8))==320*240*3


def test_project_api_and_timed_frame(tmp_path,monkeypatch):
    import app
    from fastapi.testclient import TestClient
    monkeypatch.setattr(app,'DATA',tmp_path)
    for folder in ('videos','parts','jobs','models','voices','audio'):(tmp_path/folder).mkdir()
    ident='a'*32
    source=tmp_path/'videos'/f'{ident}.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:size=320x240:rate=10:duration=2','-c:v','libx264','-f','mp4',str(source)],check=True)
    app.write_json(tmp_path/'videos'/f'{ident}.json',{'id':ident,**inspect_video(source)})
    with TestClient(app.app) as client:
        project={'cues':[{'start':0,'end':1,'text':'Đã sửa trực tiếp'}]}
        assert client.put(f'/api/videos/{ident}/editor',json=project).status_code==200
        assert client.get(f'/api/videos/{ident}/editor').json()==project
        assert client.get(f'/api/videos/{ident}/editor/export.txt').text=='Đã sửa trực tiếp'
        exported=client.get(f'/api/videos/{ident}/editor/export.srt').text
        assert '00:00:00,000 --> 00:00:01,000' in exported and 'Đã sửa trực tiếp' in exported
        assert client.get(f'/api/videos/{ident}/editor/export.exe').status_code==404
        assert client.post('/api/video-tasks',json={'video_id':ident,'action':'export','export_resolution':'8k'}).status_code==422
        assert client.get(f'/api/videos/{ident}/source',headers={'Range':'bytes=0-9'}).status_code==206
        assert client.get(f'/api/videos/{ident}/frame?at=1').content[:2]==b'\xff\xd8'
        assert client.get(f'/api/videos/{ident}/frame?at=-1').status_code==422
        assert client.post('/api/video-tasks',json={'video_id':ident,'action':'render','cues':[{'start':1,'end':3,'text':'a'}]}).status_code==422
