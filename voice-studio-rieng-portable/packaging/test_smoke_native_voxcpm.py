"""The real ASGI smoke starts current UI/API without synthesizing or deleting data."""
from pathlib import Path
import sys

import pytest

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))
import app
from smoke_native_voxcpm import app_http_smoke


@pytest.fixture
def current_app_data(tmp_path, monkeypatch):
    for name in ('voices', 'audio', 'jobs', 'models', 'parts'):
        (tmp_path / name).mkdir()
    preserved = {
        'voices/private.keep': b'existing personal voice',
        'jobs/history.keep': b'existing history',
        'models/model.keep': b'existing model',
    }
    for name, value in preserved.items():
        (tmp_path / name).write_bytes(value)
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    yield tmp_path, preserved
    for name, value in preserved.items():
        assert (tmp_path / name).read_bytes() == value


def test_http_smoke_exercises_actual_lifespan_ui_catalog_and_text_conversion(current_app_data):
    data, preserved = current_app_data
    result = app_http_smoke(APP, app.app.version)
    assert result['lifespan_started_and_stopped']
    assert result['ui_html'] and result['current_ui_script'] and result['voice_catalog']
    assert result['voice_catalog_count'] > 0 and result['txt_conversion']
    assert result['config_version'] == app.app.version
    assert result['private_voice_unlock_attempted'] is False
    assert result['additional_model_inference_attempted'] is False
    assert not list((data / 'jobs').glob('*.json'))
    assert not list((data / 'audio').iterdir())
    assert not list((data / 'parts').iterdir())


def test_http_smoke_rejects_a_different_application_version(current_app_data):
    with pytest.raises(ValueError, match='application/version'):
        app_http_smoke(APP, 'different-version')
