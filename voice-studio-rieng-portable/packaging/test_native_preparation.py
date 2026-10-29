"""Native preparation refuses corrupt weights without damaging an old install."""
import importlib.util
import json
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / 'app'
spec = importlib.util.spec_from_file_location('prepare_native_for_test', APP / 'prepare_native.py')
prepare_native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_native)


def test_invalid_source_preserves_previous_install_and_marker(tmp_path):
    target = tmp_path / 'data/models/omnivoice'
    target.mkdir(parents=True)
    old = target / prepare_native.MODEL_FILENAME
    old.write_bytes(b'previous model')
    marker = target.parent / 'omnivoice.ready'
    marker.write_text('{"previous": true}')
    bad = tmp_path / 'corrupt.gguf'
    bad.write_bytes(b'GGUFcorrupt')
    with pytest.raises(ValueError, match='SHA256'):
        prepare_native.prepare(tmp_path / 'data', bad)
    assert old.read_bytes() == b'previous model'
    assert json.loads(marker.read_text()) == {'previous': True}
    assert not list(target.glob('*.tmp'))


def test_valid_model_installs_marker_and_does_not_download_twice(tmp_path, monkeypatch):
    import hashlib
    payload = b'GGUFsynthetic-verified-test-model'
    monkeypatch.setattr(prepare_native, 'MODEL_SIZE', len(payload))
    monkeypatch.setattr(prepare_native, 'MODEL_SHA256', hashlib.sha256(payload).hexdigest())
    original_verify = prepare_native.verify_model
    monkeypatch.setattr(prepare_native, 'verify_model', lambda path: original_verify(path, len(payload), hashlib.sha256(payload).hexdigest()))
    source = tmp_path / 'test.gguf'
    source.write_bytes(payload)
    marker = prepare_native.prepare(tmp_path / 'data', source)
    assert marker['sha256'] == hashlib.sha256(payload).hexdigest()
    assert marker['model_dir'] == 'omnivoice'
    assert marker['private_reference_audio_included'] is False
    assert marker['speech_speed_claimed'] is False
    assert (tmp_path / 'data/models/omnivoice/omnivoice-q8_0.gguf').read_bytes() == payload
    def reject_network(*args, **kwargs):
        pytest.fail('An already verified model must not be downloaded again')
    assert prepare_native.prepare(tmp_path / 'data', opener=reject_network)['sha256'] == marker['sha256']


def test_update_archive_excludes_all_installation_data(tmp_path, monkeypatch):
    import sys
    import zipfile
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent))
    import build_native_bundle
    root = tmp_path / 'portable'
    for name, content in {
        'app/app.py': 'current app',
        'app/fast_multilingual.py': 'new backend',
        'app/.data/voices/private.json': 'private voice',
        'app/.data/jobs/private.json': 'private history',
        'app/.data/models/model.gguf': 'model',
        'app/voice-library/manifest.json': 'private default reference metadata',
        'app/voice-library/voices/default.wav': 'private default reference',
        'app/__pycache__/app.pyc': 'compiled code',
        'runtime-native/cpu/audiocpp.dll': 'native',
        'runtime/python.exe': 'python',
        'TAI_GIONG_DA_NGON_NGU_NHANH.bat': 'install',
        'DOC_TRUOC_NATIVE.txt': 'guide',
    }.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    full, update = build_native_bundle.package(root, tmp_path / 'downloads')
    with zipfile.ZipFile(update) as archive:
        names = archive.namelist()
        assert not any('/.data/' in name or '/__pycache__/' in name or '/voice-library/' in name for name in names)
        assert any(name.endswith('/app/fast_multilingual.py') for name in names)
        assert any(name.endswith('/runtime-native/cpu/audiocpp.dll') for name in names)
        assert not any(name.endswith('/runtime/python.exe') for name in names)


def test_asr_install_checks_every_file_before_atomic_swap(tmp_path, monkeypatch):
    import hashlib
    records = []
    source = tmp_path / 'asr-source'
    source.mkdir()
    for name in ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt'):
        payload = ('test-' + name).encode()
        (source / name).write_bytes(payload)
        records.append({'name': name, 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    monkeypatch.setattr(prepare_native, 'ASR_FILES', records)
    result = prepare_native.prepare_asr(tmp_path / 'data', source)
    destination = tmp_path / 'data/models/native-asr'
    assert result['reference_audio_uploaded'] is False
    old_manifest = (destination / 'VOICE-STUDIO-ASR.json').read_bytes()
    # Force a repair, then provide corrupt replacement data. Failed validation
    # must preserve the previous directory and its provenance marker.
    (destination / 'model.bin').write_bytes(b'broken previous model')
    (source / 'config.json').write_bytes(b'corrupt replacement')
    with pytest.raises(ValueError, match='SHA256'):
        prepare_native.prepare_asr(tmp_path / 'data', source)
    assert (destination / 'model.bin').read_bytes() == b'broken previous model'
    assert (destination / 'VOICE-STUDIO-ASR.json').read_bytes() == old_manifest
    assert not list(destination.parent.glob('native-asr.*.tmp'))


@pytest.mark.parametrize('with_asr', [False, True])
def test_windows_speech_check_keeps_native_audio_inside_data_directory(tmp_path, monkeypatch, with_asr):
    """The report may be external; the native child restricts every WAV to DATA."""
    import sys
    from types import SimpleNamespace
    import numpy as np
    import soundfile as sf
    from unittest.mock import Mock
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent))
    import smoke_native
    data = tmp_path / 'private-data'
    output = tmp_path / 'external-public-report/qa.json'
    transcript = tmp_path / 'public-reference.txt'
    transcript.write_text('This is the public reference recording.')
    paths = []
    def create(*args, **kwargs):
        def synthesize(text, path):
            assert path.resolve().is_relative_to(data.resolve())
            paths.append(path)
            sf.write(path, .1 * np.sin(np.arange(12000) / 20), 24000, subtype='PCM_16')
        return synthesize
    backend = SimpleNamespace(create_synthesizer=create, execution_info=lambda: {'backend': 'omnivoice', 'device': 'cpu'},
                              close_backends=Mock())
    monkeypatch.setitem(sys.modules, 'fast_multilingual', backend)
    def reference_transcript(*args):
        cache = data / 'cache/native-transcripts'
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / 'public.json'
        if not path.exists():
            path.write_text('{"text":"This is the public reference recording."}')
        return 'This is the public reference recording.'
    monkeypatch.setitem(sys.modules, 'native_transcript', SimpleNamespace(reference_transcript=reference_transcript))
    arguments = ['smoke_native.py', '--app-dir', str(tmp_path / 'app'), '--data-dir', str(data),
                 '--reference', str(tmp_path / 'public.wav'), '--reference-text', str(transcript), '--output', str(output)]
    if with_asr:
        arguments += ['--asr-reference', str(tmp_path / 'public-english.wav')]
    monkeypatch.setattr(sys, 'argv', arguments)
    smoke_native.main()
    assert output.is_file() and len(paths) == (4 if with_asr else 3)
    assert all(path.parent == data / 'qa-audio' for path in paths)
    backend.close_backends.assert_called_once()
