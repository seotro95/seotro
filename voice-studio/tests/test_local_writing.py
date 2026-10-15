import json

import httpx

import writing
from test_app import studio  # noqa: F401


def mock_ollama(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(writing.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    for key in ('OPENAI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    writing.KEYS.clear()


def test_local_generate_without_any_key_or_external_request(studio, monkeypatch):
    client, _ = studio
    seen = []
    def handle(request):
        assert request.url.host == '127.0.0.1' and request.url.port == 11434
        assert 'authorization' not in request.headers and 'x-goog-api-key' not in request.headers
        seen.append(request)
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'qwen3:4b'}, {'name': 'bad:cloud'}, {'name': 'remote', 'remote_host': 'https://example.com'}]})
        assert request.url.path == '/api/chat'
        body = json.loads(request.content)
        assert body['model'] == 'qwen3:4b' and body['think'] is False and not body['stream']
        assert body['keep_alive'] == '0s'
        return httpx.Response(200, json={'message': {'content': 'Xin **chào** **[pause=0.8]**'}, 'done_reason': 'stop'})
    mock_ollama(monkeypatch, handle)
    config = client.get('/api/writing/connections').json()
    assert config['providers']['ollama']
    assert config['local']['models'] == ['qwen3:4b']
    assert not config['local']['requires_key']
    assert client.post('/api/writing/connect', json={'provider': 'ollama'}).status_code == 200
    response = client.post('/api/writing/generate', json={'prompt': 'Viết câu chào'})
    assert response.status_code == 200
    assert response.json()['provider'] == 'ollama' and '**chào**' in response.json()['text']
    assert '**[pause' not in response.json()['text']
    assert not writing.KEYS and seen


def test_missing_local_runtime_keeps_studio_usable(studio, monkeypatch):
    client, _ = studio
    def handle(request):
        raise httpx.ConnectError('not running', request=request)
    mock_ollama(monkeypatch, handle)
    response = client.get('/api/writing/connections')
    assert response.status_code == 200
    assert not response.json()['providers']['ollama']
    response = client.post('/api/writing/generate', json={'prompt': 'Test'})
    assert response.status_code == 503 and 'Ollama' in response.json()['detail']
    assert client.get('/api/voices').status_code == 200


def test_missing_model_and_cloud_models_are_not_generated(studio, monkeypatch):
    client, _ = studio
    def handle(request):
        assert request.url.path == '/api/tags'
        return httpx.Response(200, json={'models': []})
    mock_ollama(monkeypatch, handle)
    assert client.post('/api/writing/generate', json={'prompt': 'Test'}).status_code == 503
    assert client.post('/api/writing/generate', json={'prompt': 'Test', 'model': 'qwen3:cloud'}).status_code == 422
    assert client.post('/api/writing/generate', json={'prompt': 'Test', 'model': 'http://external'}).status_code == 422


def test_local_truncation_and_empty_response(studio, monkeypatch):
    client, _ = studio
    output = {'text': 'Một phần kịch bản'}
    def handle(request):
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'qwen3:4b'}]})
        return httpx.Response(200, json={'message': {'content': output['text']}, 'done_reason': 'length'})
    mock_ollama(monkeypatch, handle)
    response = client.post('/api/writing/generate', json={'prompt': 'Test'})
    assert response.status_code == 200 and response.json()['incomplete']
    output['text'] = ''
    assert client.post('/api/writing/generate', json={'prompt': 'Test'}).status_code == 502
