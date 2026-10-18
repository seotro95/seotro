"""New submissions and old failed jobs must both enable automatic fitting."""
from unittest.mock import Mock
from test_standalone_api import studio  # noqa: F401
import app


def test_new_timed_submission_defaults_to_auto(studio,monkeypatch):
    client,data=studio
    monkeypatch.setattr(app.executor,'submit',Mock())
    monkeypatch.setattr(app,'installed_voices',lambda:[{'id':'test-system','name':'Test','engine':'system','speaker':'Test','languages':['vi']}])
    response=client.post('/api/speech',json={'text':'1\n00:00:00,000 --> 00:00:00,900\nXin chào bạn.','input_format':'srt','voice_id':'test-system'})
    assert response.status_code==202,response.text
    body=response.json()
    assert body['cue_fit']=='auto'
    assert app.read_json(data/'jobs'/f"{body['id']}.json")['cue_fit']=='auto'


def test_resume_upgrades_old_srt_and_keeps_checkpoints(studio,monkeypatch):
    client,data=studio
    monkeypatch.setattr(app.executor,'submit',Mock())
    ident='e'*32
    work=data/'parts'/ident;work.mkdir()
    (work/'000000.wav').write_bytes(b'existing checkpoint')
    (work/'cancel.flag').touch()
    app.write_json(data/'jobs'/f'{ident}.json',{'id':ident,'status':'error','error':'Câu SRT 9 đọc quá dài','input_format':'srt','cue_fit':'strict','speaker':'Test','voice_id':'test-system'})
    response=client.post(f'/api/jobs/{ident}/resume')
    assert response.status_code==202,response.text
    assert response.json()['cue_fit']=='auto'
    assert response.json()['status']=='queued'
    assert 'error' not in response.json()
    assert (work/'000000.wav').read_bytes()==b'existing checkpoint'
    assert not (work/'cancel.flag').exists()


def test_resume_strict_override_is_available(studio,monkeypatch):
    client,data=studio
    monkeypatch.setattr(app.executor,'submit',Mock())
    ident='d'*32
    app.write_json(data/'jobs'/f'{ident}.json',{'id':ident,'status':'error','input_format':'srt','cue_fit':'strict','speaker':'Test','voice_id':'test-system'})
    response=client.post(f'/api/jobs/{ident}/resume?auto_fit=false')
    assert response.status_code==202,response.text
    assert response.json()['cue_fit']=='strict'
