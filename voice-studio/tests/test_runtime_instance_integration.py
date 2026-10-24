"""A rejected second lifecycle cannot interrupt the incumbent's work."""
import json
import os

from fastapi.testclient import TestClient
import pytest

import app
from runtime_instance import RECORD_NAME, StudioBusy, make_data_id, make_root_id


@pytest.fixture
def studio_data(tmp_path, monkeypatch):
    for folder in ('voices', 'audio', 'jobs', 'models', 'parts', 'videos'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setenv('VOICE_STUDIO_URL', 'http://127.0.0.1:8789')
    return tmp_path


def test_identity_is_bound_to_the_locked_data_and_not_cached(studio_data):
    (studio_data / 'server.lock').write_bytes(b'')
    (studio_data / RECORD_NAME).write_text('{"instance_id":"obsolete","pid":99999999}')
    with TestClient(app.app) as client:
        response = client.get('/api/runtime')
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        identity = response.json()
        assert identity['data_id'] == make_data_id(studio_data)
        assert identity['root_id'] == make_root_id(app.BASE)
        assert identity['pid'] == os.getpid()
        assert identity['url'] == 'http://127.0.0.1:8789'
        assert identity['version'] == app.APP_VERSION
        assert identity['instance_id'] != 'obsolete'
        assert 'data_dir' not in identity and 'root_dir' not in identity
        assert json.loads((studio_data / RECORD_NAME).read_text()) == identity
    assert not (studio_data / RECORD_NAME).exists()
    assert (studio_data / 'server.lock').read_bytes() == b'0'


def test_second_lifecycle_leaves_running_job_and_live_identity_untouched(studio_data):
    with TestClient(app.app) as client:
        identity = client.get('/api/runtime').json()
        job_path = studio_data / 'jobs' / ('a' * 32 + '.json')
        job = {'id': 'a' * 32, 'status': 'running', 'created_at': app.now(), 'completed': 1}
        job_path.write_text(json.dumps(job))
        original = job_path.read_bytes()
        with pytest.raises(StudioBusy):
            with TestClient(app.app):
                pytest.fail('A duplicate must fail before lifespan changes jobs or executor')
        assert job_path.read_bytes() == original
        assert client.get('/api/runtime').json() == identity
        assert json.loads((studio_data / RECORD_NAME).read_text()) == identity


def test_stopped_server_restarts_without_deleting_lock_or_history(studio_data):
    history = studio_data / 'jobs' / ('b' * 32 + '.json')
    history.write_text(json.dumps({'id': 'b' * 32, 'status': 'done', 'created_at': app.now()}))
    before = history.read_bytes()
    with TestClient(app.app) as client:
        first = client.get('/api/runtime').json()['instance_id']
    with TestClient(app.app) as client:
        second = client.get('/api/runtime').json()['instance_id']
    assert first != second
    assert history.read_bytes() == before
    assert (studio_data / 'server.lock').read_bytes() == b'0'
