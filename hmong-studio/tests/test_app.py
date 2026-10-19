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
    for payload in ({'text':'hello','dialect':'unknown'}, {'text':'x','dialect':'hnj','speed':4}, {'text':' ','dialect':'mww'}):
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
    with patch.dict(os.environ, {'HMONG_TTS_URL':'https://tts.example/speech','HMONG_TTS_TOKEN':'test-token','HMONG_TTS_CLONING':'1'}), patch.object(module.httpx, 'AsyncClient', client):
        response = asyncio.run(module.speech(module.Speech(text='Nyob zoo',dialect='mww',voice='hmong-white-male')))
        assert response.body == b'RIFFtest'
        assert response.media_type == 'audio/wav'


def test_only_white_hmong_and_known_reference_voices():
    for payload in ({'text':'Nyob zoo','dialect':'hnj'}, {'text':'Nyob zoo','dialect':'mww','voice':'unknown'}):
        assert request('POST','/api/speech',json=payload).status_code == 422
    assert request('GET','/api/status').json()['dialects'] == ['mww', 'vi', 'en']


def test_reference_audio_served_unchanged():
    from pathlib import Path
    for voice in ('female','male'):
        name = f'hmong-white-{voice}.mp3'
        response = request('GET', '/static/voices/' + name)
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('audio/mpeg')
        assert response.content == (Path(__file__).resolve().parents[1]/'static/voices'/name).read_bytes()


def test_local_tts_route_uses_selected_language_and_returns_wav():
    with patch.dict(os.environ, {}, clear=True), patch('app.local_engine.synthesize', return_value=b'RIFFtest') as synth:
        r = request('POST', '/api/speech', json={'text':'Hello', 'dialect':'en','speed':1.2})
        assert r.status_code == 200
        assert r.content == b'RIFFtest'
        synth.assert_called_once_with('Hello', 'en', 1.2, 'model-default', 'neutral')


def test_transcription_route_forwards_audio_and_language():
    with patch.dict(os.environ, {}, clear=True), patch('app.local_engine.transcribe', return_value='Nyob zoo') as transcribe:
        r=request('POST','/api/transcribe?language=mww',content=b'audio-test')
        assert r.status_code == 200
        assert r.json()['text'] == 'Nyob zoo'
        transcribe.assert_called_once_with(b'audio-test','mww')


def test_asr_empty_audio_and_invalid_language_rejected():
    assert request('POST','/api/transcribe',content=b'').status_code == 422
    assert request('POST','/api/transcribe?language=hnj',content=b'x').status_code == 422


def test_no_silent_gender_or_emotion_emulation():
    import local_engine
    for voice,emotion in [('hmong-white-female','neutral'),('model-default','warm')]:
        try:
            local_engine.synthesize('Nyob zoo','mww',1,voice,emotion)
        except local_engine.EngineError as e:
            assert 'không hỗ trợ' in str(e)
        else:
            raise AssertionError('Unsupported features must not silently succeed')


def test_missing_verified_hmong_tts_model_explained():
    import local_engine
    with patch.dict(os.environ, {}, clear=True):
        try:
            local_engine.synthesize('Nyob zoo','mww',1,'model-default','neutral')
        except local_engine.EngineError as e:
            assert 'HMONG_LOCAL_TTS_MODEL' in str(e)
        else:
            raise AssertionError('Hmong must not silently fall back to another language')


def test_remote_asr_sends_audio_and_receives_text():
    import app as module
    from starlette.requests import Request
    original_client = httpx.AsyncClient
    def handler(req):
        assert req.content == b'audio-test'
        assert req.url.params['language'] == 'mww'
        assert req.headers['Authorization'] == 'Bearer test-token'
        return httpx.Response(200, json={'text':'Nyob zoo'})
    def client(**kwargs):
        return original_client(transport=httpx.MockTransport(handler), **kwargs)
    async def receive():
        return {'type':'http.request', 'body':b'audio-test', 'more_body':False}
    req = Request({'type':'http', 'method':'POST', 'path':'/api/transcribe', 'headers':[]}, receive)
    with patch.dict(os.environ, {'HMONG_ASR_URL':'https://asr.example/transcribe', 'HMONG_ASR_TOKEN':'test-token'}), patch.object(module.httpx,'AsyncClient',client):
        result = asyncio.run(module.transcribe(req,'mww'))
        assert result['text'] == 'Nyob zoo'


def test_reference_voice_catalog_does_not_claim_cloning_ready():
    with patch.dict(os.environ, {}, clear=True):
        catalog = request('GET','/api/voices').json()['voices']
        assert [v['id'] for v in catalog] == ['model-default','hmong-white-female','hmong-white-male']
        assert not catalog[1]['generation_configured']
