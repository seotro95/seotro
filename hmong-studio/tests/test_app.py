import asyncio
import os
from unittest.mock import patch

import httpx
from app import app


def request(method, path, **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(run())


def test_workspace_and_assets():
    assert 'Hmong Trắng' in request('GET', '/').text
    assert 'Hmong Hoa' not in request('GET', '/').text
    assert 'hmong-white-male' in request('GET', '/').text
    assert 'hmong-white-female' in request('GET', '/').text
    for name in ('app.js', 'style.css'):
        assert request('GET', '/static/' + name).status_code == 200


def test_missing_engine_is_explicit():
    with patch.dict(os.environ, {}, clear=True):
        assert request('GET', '/api/status').json()['tts_configured'] is False
        assert request('POST', '/api/speech', json={'text':'Nyob zoo', 'dialect':'mww'}).status_code == 503


def test_reject_invalid_dialect_speed_and_empty_script():
    for payload in ({'text':'hello','dialect':'vi'}, {'text':'x','dialect':'hnj','speed':4}, {'text':' ','dialect':'mww'}, {'text':'x'*10001,'dialect':'mww'}):
        assert request('POST', '/api/speech', json=payload).status_code == 422


def test_no_insecure_tts_destination():
    with patch.dict(os.environ, {'HMONG_TTS_URL':'http://example.com'}):
        assert request('POST','/api/speech',json={'text':'Nyob zoo','dialect':'mww'}).status_code == 503


def test_adapter_forwards_dialect_and_returns_audio():
    import json
    import app as module
    original_client = httpx.AsyncClient
    def handler(req):
        assert json.loads(req.content)['dialect'] == 'mww'
        assert json.loads(req.content)['voice'] == 'hmong-white-male'
        assert req.headers['Authorization'] == 'Bearer test-token'
        return httpx.Response(200, content=b'RIFFtest', headers={'content-type':'audio/wav'})
    def client(**kwargs):
        return original_client(transport=httpx.MockTransport(handler), **kwargs)
    with patch.dict(os.environ, {'HMONG_TTS_URL':'https://tts.example/speech','HMONG_TTS_TOKEN':'test-token'}), patch.object(module.httpx, 'AsyncClient', client):
        response = asyncio.run(module.speech(module.Speech(text='Nyob zoo',dialect='mww',voice='hmong-white-male')))
        assert response.body == b'RIFFtest'
        assert response.media_type == 'audio/wav'


def test_only_white_hmong_and_known_reference_voices():
    for payload in ({'text':'Nyob zoo','dialect':'hnj'}, {'text':'Nyob zoo','dialect':'mww','voice':'unknown'}):
        assert request('POST','/api/speech',json=payload).status_code == 422
    assert request('GET','/api/status').json()['dialects'] == ['mww']


def test_reference_audio_served_unchanged():
    from pathlib import Path
    for voice in ('female','male'):
        name = f'hmong-white-{voice}.mp3'
        response = request('GET', '/static/voices/' + name)
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('audio/mpeg')
        assert response.content == (Path(__file__).resolve().parents[1]/'static/voices'/name).read_bytes()
