"""Native VoxCPM must retain the selected sample, settings and original timeline."""
import json
import sys
from types import SimpleNamespace

import pytest

from test_native_worker import native_worker  # noqa: F401
from test_worker_optimization import worker, tones, write_pcm  # noqa: F401


def test_voxcpm_native_constructor_uses_reference_without_asr(native_worker, tmp_path, monkeypatch):
    calls = []
    reference = tmp_path / 'selected-voice.wav'
    monkeypatch.setitem(sys.modules, 'voice_library', SimpleNamespace(
        resolve_reference=lambda ident, data: (reference, {'transcript': '', 'native_language': 'ko'})))
    monkeypatch.setitem(sys.modules, 'voxcpm_backend', SimpleNamespace(close_backends=lambda: calls.append('close-cpu-torch')))
    def create(path, data, **options):
        calls.append((path, data, options))
        return object()
    monkeypatch.setitem(sys.modules, 'fast_multilingual', SimpleNamespace(create_synthesizer=create))
    native_worker.load_synthesizer({'engine': 'voxcpm', 'voice_id': 'selected', 'language': 'ko',
        'international_backend': 'voxcpm_native', 'international_device': 'cuda', 'voxcpm_steps': 8, 'nano_threads': 3})
    assert calls == ['close-cpu-torch', (reference, tmp_path, {
        'threads': 3, 'steps': 8, 'device': 'cuda', 'language': 'ko', 'family': 'voxcpm2', 'native_performance': 'off'})]


def test_voxcpm_native_render_retains_srt_gaps_without_counting_them_as_speech(native_worker, tmp_path, monkeypatch):
    calls = []
    def create(text, path):
        calls.append(text)
        write_pcm(path, tones([220], .1))
    monkeypatch.setattr(native_worker, 'get_synthesizer', lambda job: create)
    monkeypatch.setattr(native_worker, 'create_render_pool', lambda *a: pytest.fail('Q8 GPU model replicated'))
    monkeypatch.setitem(sys.modules, 'fast_multilingual', SimpleNamespace(execution_info=lambda: {
        'backend': 'voxcpm_native', 'device': 'cuda', 'precision': 'q8_0', 'voxcpm_steps': 8}))
    text = '1\n00:00:00,000 --> 00:00:00,500\n안녕하세요.\n\n2\n00:00:01,000 --> 00:00:01,500\n다음 문장입니다.'
    native_worker.render({'id': 'native-voxcpm', 'text': text, 'input_format': 'srt',
        'engine': 'voxcpm', 'language': 'ko', 'international_backend': 'voxcpm_native',
        'international_device': 'cuda', 'voxcpm_steps': 8, 'nano_threads': 3, 'nano_parallel': 8,
        'format': 'wav', 'speed': 1, 'cue_fit': 'strict'})
    result = json.loads((tmp_path / 'parts/native-voxcpm/result.json').read_text())
    assert calls == ['안녕하세요.', '다음 문장입니다.']
    actual = result['execution_settings']
    assert actual['backend'] == 'voxcpm_native' and actual['model_memory'] == 'native'
    assert actual['workers'] == 1 and actual['voxcpm_steps'] == 8 and actual['device'] == 'cuda'
    assert 'omnivoice_steps' not in actual
    assert result['audio_seconds'] == 1.5 and result['spoken_audio_seconds'] == pytest.approx(.2)


@pytest.mark.parametrize('change', [{'international_backend': 'omnivoice'}, {'international_device': 'cpu'}, {'voxcpm_steps': 10}, {'render_mode': 'fast'}])
def test_voxcpm_native_settings_invalidate_synthesizer(native_worker, monkeypatch, change):
    monkeypatch.setattr(native_worker, 'load_synthesizer', lambda job: object())
    job = {'engine': 'voxcpm', 'voice_id': 'selected', 'language': 'ja',
           'international_backend': 'voxcpm_native', 'international_device': 'cuda', 'voxcpm_steps': 8}
    original = native_worker.get_synthesizer(job)
    assert native_worker.get_synthesizer(job) is original
    assert native_worker.get_synthesizer({**job, **change}) is not original
