import json
import subprocess
from pathlib import Path
import pytest
from video_tasks import validate_logo, translate_cues
from dubbing import inspect_video


def test_logo_bounds():
    meta={'width':320,'height':240}
    assert validate_logo({'x':10,'y':20,'w':40,'h':30},meta)=='delogo=x=10:y=20:w=40:h=30'
    for rect in ({'x':0,'y':1,'w':20,'h':20},{'x':310,'y':1,'w':20,'h':20}):
        with pytest.raises(ValueError):
            validate_logo(rect,meta)


def test_translation_preserves_times_and_rejects_missing(monkeypatch):
    import writing
    async def status(): return {'models':['local:latest']}
    async def good(*args): return {'message':{'content':'{"texts":["Xin chào"]}'}}
    monkeypatch.setattr(writing,'local_status',status)
    monkeypatch.setattr(writing,'request_local',good)
    cues=[{'start':1.2,'end':3.4,'text':'Hello'}]
    assert translate_cues(cues,'vi','local',lambda *a:None)==[{'start':1.2,'end':3.4,'text':'Xin chào'}]
    async def bad(*args): return {'message':{'content':'{"texts":[]}'}}
    monkeypatch.setattr(writing,'request_local',bad)
    with pytest.raises(ValueError): translate_cues(cues,'vi','local',lambda *a:None)


def test_real_logo_export(tmp_path):
    from video_tasks import run
    video=tmp_path/'videos';video.mkdir()
    work=tmp_path/'video_tasks'/'b';work.mkdir(parents=True)
    source=video/'a.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=10:duration=1','-c:v','libx264','-f','mp4',str(source)],check=True)
    meta=inspect_video(source)
    (video/'a.json').write_text(json.dumps(meta))
    job={'video_id':'a','action':'logo','logo':{'x':10,'y':10,'w':50,'h':30}}
    path=work/'job.json';path.write_text(json.dumps(job))
    run(path)
    out=inspect_video(work/'output.mp4')
    assert out['width']==320 and out['height']==240 and abs(out['duration']-1)<.1
    assert json.loads((work/'progress.json').read_text())['progress']==100


def test_video_task_api_export_and_cancel(tmp_path,monkeypatch):
    import app
    import time
    from fastapi.testclient import TestClient
    monkeypatch.setattr(app,'DATA',tmp_path)
    for folder in ('voices','audio','jobs','models','parts','videos'):
        (tmp_path/folder).mkdir()
    source=tmp_path/'input.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=10:duration=1','-c:v','libx264',str(source)],check=True)
    with TestClient(app.app) as client:
        with source.open('rb') as file:
            response=client.post('/api/videos',files={'file':('test.mp4',file,'video/mp4')})
        assert response.status_code==201,response.text
        video_id=response.json()['id']
        assert client.get(f'/api/videos/{video_id}/frame').content[:2]==b'\xff\xd8'
        response=client.post('/api/video-tasks',json={'video_id':video_id,'action':'logo','logo':{'x':10,'y':10,'w':40,'h':30}})
        assert response.status_code==202,response.text
        ident=response.json()['id']
        for _ in range(100):
            task=client.get('/api/video-tasks/'+ident).json()
            if task['status'] not in ('queued','running'):break
            time.sleep(.1)
        assert task['status']=='done',task
        assert task['progress']==100
        assert client.get(task['video_url']).status_code==200
        assert client.get(f'/api/video-tasks/{ident}/job.json').status_code==404
        # Queued tasks must honor Stop before launching a worker.
        work=app.video_task_work('c'*32);work.mkdir()
        app.write_json(work/'job.json',{'id':'c'*32,'status':'queued'})
        assert client.post('/api/video-tasks/'+'c'*32+'/cancel').status_code==200
        app.run_video_task('c'*32)
        assert app.read_json(work/'job.json')['status']=='cancelled'
