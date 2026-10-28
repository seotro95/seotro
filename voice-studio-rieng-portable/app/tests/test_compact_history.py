"""Polling large scripts must not transfer or parse them on every update."""
import json
from unittest.mock import Mock

import app
from test_standalone_api import studio  # noqa: F401


def record(data,ident,text,status='done'):
    value={'id':ident,'text':text,'status':status,'created_at':'2026-01-01T00:00:00Z',
           'voice_id':'nano-minhquan','voice_name':'Public test','engine':'vieneu_nano',
           'format':'wav','language':'vi','input_format':'txt'}
    app.write_json(data/'jobs'/f'{ident}.json',value)
    return value


def test_million_character_history_compacts_without_changing_original(studio):
    client,data=studio
    text=('Xin chào. '*111112)[:1000000]
    value=record(data,'a'*32,text)
    compact=client.get('/api/history?compact=true')
    assert compact.status_code==200 and len(compact.content)<2000
    item=compact.json()['items'][0]
    assert 'text' not in item and item['text_excerpt']==text[:220] and item['text_length']==1000000
    assert client.get('/api/history').json()['items'][0]['text']==text
    assert client.get('/api/jobs/'+'a'*32).json()==value
    assert json.loads((data/'jobs'/('a'*32+'.json')).read_text())==value


def test_compact_poll_reuses_script_metadata_but_reads_live_progress(studio,monkeypatch):
    client,data=studio
    ident='b'*32
    record(data,ident,'Lời đọc đầy đủ. '*10000,'running')
    work=data/'parts'/ident;work.mkdir()
    read=Mock(wraps=app.read_json)
    monkeypatch.setattr(app,'read_json',read)
    first=client.get('/api/jobs/'+ident+'?compact=true').json()
    assert 'text' not in first
    app.write_json(work/'progress.json',{'completed':12,'progress':36,'phase':'Đang đọc'})
    second=client.get('/api/jobs/'+ident+'?compact=true').json()
    assert second['completed']==12 and second['progress']==36
    assert read.call_count==1


def test_job_file_replacement_invalidates_compact_cache(studio):
    client,data=studio
    ident='c'*32
    record(data,ident,'Lời đầu.','queued')
    assert client.get('/api/jobs/'+ident+'?compact=true').json()['text_excerpt']=='Lời đầu.'
    record(data,ident,'Lời sau.','done')
    updated=client.get('/api/jobs/'+ident+'?compact=true').json()
    assert updated['text_excerpt']=='Lời sau.' and updated['status']=='done'
    (data/'jobs'/f'{ident}.json').unlink()
    assert client.get('/api/jobs/'+ident+'?compact=true').status_code==404
    assert client.get('/api/history?compact=true').json()['items']==[]
