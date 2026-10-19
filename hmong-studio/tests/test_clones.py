import asyncio
import io
import json
import math
import struct
import wave

import httpx
import pytest
from fastapi.testclient import TestClient
import app
import clone_store


def sample(seconds=4, silent=False):
    output=io.BytesIO()
    with wave.open(output,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
        wav.writeframes(b''.join(struct.pack('<h',0 if silent else int(4000*math.sin(i*.1))) for i in range(seconds*24000)))
    return output.getvalue()


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(clone_store,'DATA',tmp_path/'clones')
    return TestClient(app.app)


def enroll(client, **options):
    return client.post('/api/clones',data={'name':'Giọng của tôi','transcript':'Kuv hais lus Hmoob.','consent':'true',**options},files={'file':('sample.wav',sample(),'audio/wav')})


def test_reference_lifecycle_and_no_engine(client,monkeypatch):
    monkeypatch.delenv('HMONG_CLONE_URL',raising=False)
    response=enroll(client)
    assert response.status_code==201,response.text
    voice=response.json()
    assert voice['duration']==4
    assert voice['consent_at']
    assert client.get(voice['reference']).content[:4]==b'RIFF'
    assert client.get('/api/clones').json()['voices'][0]['id']==voice['id']
    response=client.post('/api/speech',json={'text':'Nyob zoo','dialect':'mww','voice':voice['id'],'emotion':'review'})
    assert response.status_code==503
    assert client.delete('/api/clones/'+voice['id']).status_code==204
    assert client.get(voice['reference']).status_code==404
    assert client.get('/api/clones').json()=={'voices':[]}


def test_consent_and_invalid_audio(client):
    assert enroll(client,consent='false').status_code==422
    assert enroll(client,name='  ').status_code==422
    for data in (b'not audio',sample(1),sample(4,True),sample(61)):
        assert client.post('/api/clones',data={'name':'Test','transcript':'Test','consent':'true'},files={'file':('sample.wav',data,'audio/wav')}).status_code==422
    assert client.get('/api/clones').json()['voices']==[]
    assert client.get('/api/clones/custom-invalid/sample').status_code==404


def test_remote_receives_reference_text_and_review(client,monkeypatch):
    voice=enroll(client).json()
    monkeypatch.setenv('HMONG_CLONE_URL','https://clone.example/speech')
    monkeypatch.setenv('HMONG_CLONE_LANGUAGES','mww')
    monkeypatch.setenv('HMONG_CLONE_STYLES','neutral,review,storytelling')
    real_client=httpx.AsyncClient
    def handler(request):
        body=request.read()
        assert request.url==httpx.URL('https://clone.example/speech')
        assert b'reference_audio' in body and b'RIFF' in body
        assert b'Kuv hais lus Hmoob.' in body
        assert b'"emotion": "review"' in body
        return httpx.Response(200,content=sample(),headers={'Content-Type':'audio/wav'})
    monkeypatch.setattr(app.httpx,'AsyncClient',lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw))
    response=client.post('/api/speech',json={'text':'Nyob zoo','dialect':'mww','voice':voice['id'],'emotion':'review'})
    assert response.status_code==200,response.text
    assert response.content[:4]==b'RIFF'
    assert client.post('/api/speech',json={'text':'Nyob zoo','dialect':'mww','voice':voice['id'],'emotion':'news'}).status_code==422
    monkeypatch.delenv('HMONG_CLONE_LANGUAGES')
    assert client.post('/api/speech',json={'text':'Nyob zoo','dialect':'mww','voice':voice['id']}).status_code==503


def test_remote_failure_is_not_success(client,monkeypatch):
    voice=enroll(client).json()
    monkeypatch.setenv('HMONG_CLONE_URL','https://clone.example/speech')
    monkeypatch.setenv('HMONG_CLONE_LANGUAGES','mww')
    real_client=httpx.AsyncClient
    monkeypatch.setattr(app.httpx,'AsyncClient',lambda **kw:real_client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'error':'not audio'})),**kw))
    assert client.post('/api/speech',json={'text':'Nyob zoo','dialect':'mww','voice':voice['id']}).status_code==502
