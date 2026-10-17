import hashlib
import io
import json

import pytest

import piper_voice
from piper_catalog import DEMO_TEXTS, presets


def test_country_selection_uses_exact_native_model():
    voices = presets()
    assert len({voice['id'] for voice in voices}) == 16
    assert {voice['languages'][0] for voice in voices} == set(DEMO_TEXTS)
    belgium = next(voice for voice in voices if voice['languages'] == ['nl-BE'])
    brazil = next(voice for voice in voices if voice['languages'] == ['pt-BR'])
    assert belgium['culture'] == 'nl-BE'
    assert brazil['culture'] == 'pt-BR'
    assert all(voice['commercial'] and voice['engine'] == 'piper' for voice in voices)


def test_failed_download_never_replaces_file_or_leaves_partial(tmp_path, monkeypatch):
    destination = tmp_path / 'voice.onnx'
    destination.write_bytes(b'old')
    expected = b'good'
    item = {'name': destination.name, 'path': 'voice.onnx', 'size': len(expected),
            'sha256': hashlib.sha256(expected).hexdigest()}
    monkeypatch.setattr(piper_voice.urllib.request, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'evil'))
    monkeypatch.setattr(piper_voice.time, 'sleep', lambda seconds: None)
    with pytest.raises(RuntimeError, match='Không tải được'):
        piper_voice._download_file(destination, item)
    assert destination.read_bytes() == b'old'
    assert list(tmp_path.iterdir()) == [destination]


def test_ready_marker_requires_successful_audio_and_matching_manifest(tmp_path, monkeypatch):
    payload = b'model'
    item = {'name': 'test.onnx', 'path': 'test.onnx', 'size': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}
    monkeypatch.setattr(piper_voice, 'PIPER_MODELS', {'test': {'files': [item]}})
    paths = piper_voice.model_paths(tmp_path, 'test')
    paths['directory'].mkdir(parents=True)
    (paths['directory'] / item['name']).write_bytes(payload)
    marker = {'model': 'test', 'revision': piper_voice.PIPER_REVISION,
              'sample_seconds': 1.0, 'nonzero': True,
              'sha256': {item['name']: item['sha256']}}
    paths['marker'].write_text('[]')
    assert not piper_voice.model_ready(tmp_path, 'test')
    paths['marker'].write_text(json.dumps({**marker, 'sha256': []}))
    assert not piper_voice.model_ready(tmp_path, 'test')
    paths['marker'].write_text(json.dumps(marker))
    assert piper_voice.model_ready(tmp_path, 'test')
    marker['nonzero'] = False
    paths['marker'].write_text(json.dumps(marker))
    assert not piper_voice.model_ready(tmp_path, 'test')
    marker['nonzero'] = True
    paths['marker'].write_text(json.dumps(marker))
    (paths['directory'] / item['name']).write_bytes(b'truncated')
    assert not piper_voice.model_ready(tmp_path, 'test')


def test_unknown_model_cannot_select_arbitrary_path(tmp_path):
    with pytest.raises(ValueError, match='Không tìm thấy'):
        piper_voice.model_paths(tmp_path, '../../outside')
