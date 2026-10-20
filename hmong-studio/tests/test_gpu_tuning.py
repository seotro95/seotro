import json
from types import SimpleNamespace

import pytest

import cosy_engine as engine
import gpu_tuning as tuning


def fake_torch(name='NVIDIA GeForce GTX 1060 6GB', cuda=True):
    properties = SimpleNamespace(name=name, total_memory=6 * 1024**3, major=6, minor=1)
    return SimpleNamespace(
        __version__='2.6.0+cu124', version=SimpleNamespace(cuda='12.4'),
        cuda=SimpleNamespace(is_available=lambda: cuda, current_device=lambda: 0,
                             get_device_properties=lambda device: properties),
        backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=False)),
                                 cudnn=SimpleNamespace(allow_tf32=False)))


def results():
    # The lowest wall time alone is misleading when a mode produces less speech.
    return [{'precision': 'float32', 'elapsed_seconds': 3, 'speech_seconds': 2},
            {'precision': 'float16', 'elapsed_seconds': 2, 'speech_seconds': 1}]


def test_choice_uses_measured_speech_throughput_and_is_bound_to_gpu_and_model(tmp_path):
    path = tmp_path / 'gpu.json'
    torch = fake_torch()
    tuning.save_choice(path, torch, 'float32', results())
    assert tuning.load_choice(path, torch) == 'float32'
    assert tuning.load_choice(path, fake_torch('another GPU')) is None
    assert tuning.load_choice(path, fake_torch(cuda=False)) is None
    assert json.loads(path.read_text())['one_hour_verified'] is False
    record = json.loads(path.read_text())
    record['revision'] = 'a different model'
    path.write_text(json.dumps(record))
    assert tuning.load_choice(path, torch) is None


def test_cannot_save_unmeasured_or_slower_precision_and_existing_record_is_preserved(tmp_path):
    path = tmp_path / 'gpu.json'
    torch = fake_torch()
    tuning.save_choice(path, torch, 'float32', results())
    previous = path.read_bytes()
    for precision, measured in [('float16', results()), ('float32', []),
                                ('float32', [results()[1]]), ('unknown', results())]:
        with pytest.raises(ValueError):
            tuning.save_choice(path, torch, precision, measured)
        assert path.read_bytes() == previous


@pytest.mark.parametrize('value', [0, -1, True, float('nan'), float('inf'), '3'])
def test_invalid_measurement_does_not_replace_existing_settings(tmp_path, value):
    path = tmp_path / 'gpu.json'
    path.write_bytes(b'previous settings')
    measured = results()
    measured[0]['elapsed_seconds'] = value
    with pytest.raises(ValueError):
        tuning.save_choice(path, fake_torch(), 'float32', measured)
    assert path.read_bytes() == b'previous settings'


def test_failed_atomic_replace_preserves_settings_and_removes_owned_temp(tmp_path, monkeypatch):
    path = tmp_path / 'gpu.json'
    path.write_bytes(b'previous settings')
    def locked(source, target):
        raise PermissionError('Windows holds the settings file')
    monkeypatch.setattr(tuning.os, 'replace', locked)
    with pytest.raises(PermissionError):
        tuning.save_choice(path, fake_torch(), 'float32', results())
    assert path.read_bytes() == b'previous settings'
    assert not list(tmp_path.glob('.gpu-tuning-*'))


def test_malformed_stale_and_oversized_settings_fall_back_without_changing_file(tmp_path):
    path = tmp_path / 'gpu.json'
    for content in ('not json', '[]', '{"schema": 1}', 'x' * (64 * 1024 + 1)):
        path.write_text(content)
        assert tuning.load_choice(path, fake_torch()) is None
        assert path.read_text() == content


def test_library_and_gpu_memory_changes_invalidate_choice(tmp_path):
    path = tmp_path / 'gpu.json'
    torch = fake_torch()
    tuning.save_choice(path, torch, 'float32', results())
    torch.__version__ = '2.7.0+cu124'
    assert tuning.load_choice(path, torch) is None
    torch = fake_torch()
    torch.cuda.get_device_properties(0).total_memory = 8 * 1024**3
    assert tuning.load_choice(path, torch) is None


def test_saved_gpu_precision_is_used_only_in_auto_mode(tmp_path, monkeypatch):
    path = tmp_path / 'gpu.json'
    torch = fake_torch()
    tuning.save_choice(path, torch, 'float32', results())
    monkeypatch.setattr(tuning, 'settings_path', lambda: path)
    monkeypatch.setenv('HMONG_COSY_PRECISION', 'auto')
    assert engine._device_options(torch) == {'device': 'cuda', 'fp16': False}
    monkeypatch.setenv('HMONG_COSY_PRECISION', 'float16')
    assert engine._device_options(torch) == {'device': 'cuda', 'fp16': True}
    monkeypatch.setenv('HMONG_COSY_PRECISION', 'float32')
    assert engine._device_options(torch) == {'device': 'cuda', 'fp16': False}


def test_cpu_defaults_stay_float32_and_explicit_fp16_needs_cuda(monkeypatch):
    torch = fake_torch(cuda=False)
    monkeypatch.setenv('HMONG_COSY_PRECISION', 'auto')
    assert engine._device_options(torch) == {'device': 'cpu', 'fp16': False}
    monkeypatch.setenv('HMONG_COSY_PRECISION', 'float16')
    with pytest.raises(engine.EngineError, match='FP16'):
        engine._device_options(torch)
    monkeypatch.setenv('HMONG_COSY_PRECISION', 'wrong')
    with pytest.raises(engine.EngineError, match='HMONG_COSY_PRECISION'):
        engine._device_options(torch)
