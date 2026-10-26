"""HTTP contracts for books and immutable character voice assignments."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app
import hmong_assets


@pytest.fixture
def studio(tmp_path, monkeypatch):
    for name in ('jobs','parts','audio','voices','models','videos'):
        (tmp_path/name).mkdir()
    monkeypatch.setattr(app,'DATA',tmp_path)
    monkeypatch.setattr(app,'IS_HMONG',True)
    monkeypatch.setattr(app,'PRESETS',hmong_assets.presets())
    monkeypatch.setattr(app,'LANGUAGES',{**app.LANGUAGES,'mww':'Hmong Trắng'})
    monkeypatch.setattr(app,'installed_voices',lambda:[])
    monkeypatch.setattr(app,'model_ready',lambda engine:True)
    with TestClient(app.app) as client:
        submit=Mock()
        monkeypatch.setattr(app.executor,'submit',submit)
        yield client,tmp_path,submit


def base(**changes):
    return {'text':'Nyob zoo.','voice_id':'hmong-male','language':'mww',**changes}


def test_million_character_book_queued_intact_and_limit(studio):
    client,data,submit=studio
    text=('Nyob zoo. '*100000)
    assert len(text)==1_000_000
    response=client.post('/api/speech',json=base(text=text))
    assert response.status_code==202,response.text
    job=response.json()
    assert job['longform'] is True and job['text']==text
    assert app.read_json(data/'jobs'/f"{job['id']}.json")['text']==text
    assert job['hmong_voice_snapshot']['voice_id']=='hmong-male'
    assert client.get('/api/config').json()['max_characters']==1_000_000
    assert client.post('/api/speech',json=base(text=text+'a')).status_code==422
    submit.assert_called_once()


def test_standard_retains_limit(studio,monkeypatch):
    client,_,submit=studio
    monkeypatch.setattr(app,'IS_HMONG',False)
    assert client.post('/api/speech',json=base(text='a '*100001)).status_code==422
    submit.assert_not_called()


SRT='1\n00:00:00,000 --> 00:00:04,000\nNyob zoo.\n\n2\n00:00:04,000 --> 00:00:08,000\nUa tsaug.\n'


def test_per_character_snapshots_and_null_fallback(studio):
    client,_,_=studio
    response=client.post('/api/speech',json=base(text=SRT,input_format='srt',
        character_voices={'girl':'hmong-female'},cue_characters=['girl',None]))
    assert response.status_code==202,response.text
    cast=response.json()['character_cast']
    assert cast['voices']['girl']['voice_id']=='hmong-female'
    assert cast['default_voice']['voice_id']=='hmong-male'
    assert cast['cues']==['girl',None]
    assert cast['voices']['girl']['hmong_reference_fingerprint']==hmong_assets.reference_fingerprint('hmong-female')


@pytest.mark.parametrize('changes',[
    {'cue_characters':['missing',None]},
    {'cue_characters':['girl']},
    {'character_voices':{'girl':'missing'}},
    {'character_voices':{'../x':'hmong-female'},'cue_characters':['../x',None]},
    {'input_format':'txt','text':'Nyob zoo. Ua tsaug.'},
])
def test_invalid_cast_rejected_before_queue(studio,changes):
    client,_,submit=studio
    payload=base(text=SRT,input_format='srt',character_voices={'girl':'hmong-female'},cue_characters=['girl',None])
    payload.update(changes)
    assert client.post('/api/speech',json=payload).status_code==422
    submit.assert_not_called()


def test_txt_caption_cast_keeps_source_and_frozen_per_cue_voices(studio):
    client,data,submit=studio
    response=client.post('/api/speech',json=base(text=SRT,input_format='txt',
        character_voices={'girl':'hmong-female'},cue_characters=['girl',None]))
    assert response.status_code==202,response.text
    job=response.json()
    assert job['input_format']=='srt' and job['source_input_format']=='txt'
    assert job['subtitle_timing'] is True and job['text']==SRT
    cast=job['character_cast']
    assert cast['cues']==['girl',None]
    assert cast['voices']['girl']['voice_id']=='hmong-female'
    assert cast['default_voice']['voice_id']=='hmong-male'
    assert cast['voices']['girl']['hmong_reference_fingerprint']==hmong_assets.reference_fingerprint('hmong-female')
    assert cast['default_voice']['hmong_reference_fingerprint']==hmong_assets.reference_fingerprint('hmong-male')
    assert app.read_json(data/'jobs'/f"{job['id']}.json")==job
    submit.assert_called_once_with(app.run_job,job['id'])


def test_txt_caption_cast_still_rejects_wrong_cue_count_before_queue(studio):
    client,_,submit=studio
    response=client.post('/api/speech',json=base(text=SRT,input_format='txt',
        character_voices={'girl':'hmong-female'},cue_characters=['girl']))
    assert response.status_code==422,response.text
    submit.assert_not_called()


def test_editor_preserves_character_and_source_cue_identity(studio):
    client,data,_=studio
    ident='f'*32
    app.write_json(data/'videos'/f'{ident}.json',{'id':ident,'duration':8})
    project={'project_version':2,'language':'mww','source_language':'mww',
        'characters':[{'id':'girl','name':'Poj niam','voice_id':'hmong-female'}],
        'cues':[{'id':'cue-1','character_id':'girl','start':0,'end':4,'text':'Nyob zoo.'}],
        'source_cues':[{'id':'cue-1','character_id':'girl','start':0,'end':4,'text':'Nyob zoo.'}]}
    response=client.put(f'/api/videos/{ident}/editor',json=project)
    assert response.status_code==200,response.text
    saved=client.get(f'/api/videos/{ident}/editor').json()
    for key in project:assert saved[key]==project[key]
    srt=client.get(f'/api/videos/{ident}/editor/export.srt').text
    assert 'Nyob zoo.' in srt and 'girl' not in srt and 'cue-1' not in srt
    project['cues'][0]['character_id']='unknown'
    assert client.put(f'/api/videos/{ident}/editor',json=project).status_code==422


def test_longform_download_routes_and_cleanup(studio):
    client,data,_=studio
    ident='e'*32
    child='a'*32
    app.write_json(data/'jobs'/f'{ident}.json',base(id=ident,status='done',longform=True,format='wav',created_at=app.now(),chapters=[{'index':1}],url=f'/api/jobs/{ident}/archive'))
    parent=data/'parts'/ident
    folder=parent/'chapters'/'0001'
    folder.mkdir(parents=True)
    (folder/'audio.wav').write_bytes(b'RIFF'+b'\0'*100)
    (data/'audio'/f'{ident}.zip').write_bytes(b'PKarchive')
    app.write_json(parent/'plan.json',{'chapters':[{'id':child}]})
    (data/'parts'/child).mkdir()
    assert client.get(f'/api/jobs/{ident}/archive').headers['content-type']=='application/zip'
    assert client.get(f'/api/jobs/{ident}/chapters/1').content[:4]==b'RIFF'
    assert client.get(f'/api/jobs/{ident}/chapters/0').status_code==404
    assert client.get(f'/api/jobs/{ident}/chapters/2').status_code==404
    assert client.get(f'/api/audio/{ident}').status_code==422
    assert client.delete(f'/api/history/{ident}').status_code==204
    assert not parent.exists() and not (data/'parts'/child).exists()
    assert not (data/'audio'/f'{ident}.zip').exists()
