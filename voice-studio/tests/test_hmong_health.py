"""Runtime failures and diagnostic PCM plumbing; synthesis doubles are not QA proof."""
import hashlib
import json
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor
import threading
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

import hmong_assets
import hmong_health as health
import hmong_native
from hmong_engine import EngineError


@pytest.fixture
def diagnostic_data(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    monkeypatch.setenv('HMOOB_DEVICE', 'cpu')
    monkeypatch.setenv('HMOOB_PRECISION', 'auto')
    monkeypatch.delenv('HMOOB_HEALTH_RUN_ID', raising=False)
    monkeypatch.delenv('HMOOB_HEALTH_PRIVATE_RUNTIME_ID', raising=False)
    return tmp_path


def read_report(root, name='runtime-check.json'):
    return json.loads((root / 'diagnostics' / name).read_text(encoding='utf-8'))


def read_child_report(root, environment):
    return read_report(root, '.runtime-' + environment['HMOOB_HEALTH_PRIVATE_RUNTIME_ID'] + '.json')


def test_runtime_probe_loads_native_audio_code_without_models_or_network(diagnostic_data, monkeypatch):
    for name in ('torch', 'soxr', 'scipy', 'librosa'):
        pytest.importorskip(name)
    import urllib.request
    import socket
    monkeypatch.setattr(hmong_native, 'verify_models', lambda *args:
                        pytest.fail('The runtime probe must not inspect or load checkpoints'))
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *args, **kwargs:
                        pytest.fail('The runtime probe must not download anything'))
    monkeypatch.setattr(socket, 'create_connection', lambda *args, **kwargs:
                        pytest.fail('The runtime probe must not use a network connection'))
    report = health.probe_runtime()
    assert report['ok'] is True and report['inference_tested'] is False
    names = {item['name'] for item in report['checks']}
    assert {'cpu-conv1d-numpy', 'wav-soxr-scipy-librosa',
            'import:hmong_native_vendor.vits.models',
            'import:hmong_native_vendor.openvoice.models',
            'import:hmong_native_vendor.watermark.models.my_model'} <= names
    assert read_report(diagnostic_data) == report
    assert not list(diagnostic_data.rglob('*.wav'))


def test_runtime_import_error_saves_actionable_report_without_raw_path(diagnostic_data, monkeypatch):
    def broken_import(name):
        raise OSError('DLL load failed: C:/private-person/secret-token/torch.dll')
    monkeypatch.setattr(health.importlib, 'import_module', broken_import)
    report = health.probe_runtime()
    assert report['ok'] is False and report['phase'] == 'imports'
    assert 'DLL' in report['message'] and 'Visual C++' in report['message']
    assert 'private-person' not in json.dumps(report)
    assert read_report(diagnostic_data) == report


@pytest.mark.parametrize('backend,device,precision', [
    ('bad', 'cpu', 'auto'), ('native', 'bad', 'auto'), ('native', 'cpu', 'fp16'),
    ('f5', 'cpu', 'bad'), ('f5', ' CPU ', 'auto'), ('f5', 'cpu', ' FP32 ')])
def test_invalid_runtime_settings_fail_before_heavy_imports(diagnostic_data, monkeypatch, backend, device, precision):
    monkeypatch.setenv('HMOOB_BACKEND', backend)
    monkeypatch.setenv('HMOOB_DEVICE', device)
    monkeypatch.setenv('HMOOB_PRECISION', precision)
    monkeypatch.setattr(health.importlib, 'import_module', lambda name:
                        pytest.fail('Reject invalid configuration before importing native libraries'))
    report = health.probe_runtime()
    assert report['ok'] is False and report['phase'] == 'configuration'
    assert 'HMOOB_' in report['message']


def test_native_probe_uses_legacy_precision_compatibility(diagnostic_data, monkeypatch):
    monkeypatch.setenv('HMOOB_DEVICE', ' CPU ')
    monkeypatch.setenv('HMOOB_PRECISION', ' INT8 ')
    settings = health._configuration('native')
    assert settings['device'] == 'cpu' and settings['precision'] == 'fp32'
    assert settings['compatibility_note']


def test_parent_uses_selected_interpreter_clean_environment_and_child_report(diagnostic_data, monkeypatch):
    monkeypatch.setenv('PYTHONHOME', 'wrong-runtime')
    monkeypatch.setenv('PYTHONPATH', 'wrong-libraries')
    captured = []
    def run(command, **kwargs):
        captured.append((command, kwargs))
        report = read_child_report(diagnostic_data, kwargs['env'])
        report.update(ok=True, success=True, phase='complete', message='PASS: checked child')
        health._save(report)
        return SimpleNamespace(returncode=0, stdout='unneeded output')
    monkeypatch.setattr(health.subprocess, 'run', run)
    report = health.run_runtime_probe(health.BASE, timeout=13)
    assert report['ok'] is True and report['phase'] == 'complete'
    command, kwargs = captured[0]
    assert command == [health.sys.executable, str(health.BASE / 'hmong_health.py'), '--probe-runtime']
    assert kwargs['timeout'] == 13 and kwargs['cwd'] == health.BASE
    assert 'PYTHONHOME' not in kwargs['env'] and 'PYTHONPATH' not in kwargs['env']
    assert kwargs['env']['HF_HUB_OFFLINE'] == '1'
    assert kwargs['env']['HMOOB_HEALTH_RUN_ID'] == report['run_id']
    assert kwargs['env']['HMOOB_HEALTH_PRIVATE_RUNTIME_ID'] == report['run_id']
    assert kwargs['env']['VOICE_STUDIO_DATA_DIR'] == str(diagnostic_data)
    assert not list((diagnostic_data / 'diagnostics').glob('.runtime-*.json'))


@pytest.mark.parametrize('returncode,expected', [(3221225781, 'DLL'), (-9, 'RAM'), (3221225495, 'RAM')])
def test_parent_reports_native_crashes_and_rejects_stale_success(diagnostic_data, monkeypatch, returncode, expected):
    folder = diagnostic_data / 'diagnostics'
    folder.mkdir()
    (folder / 'runtime-check.json').write_text(json.dumps({
        'ok': True, 'success': True, 'schema_version': 1, 'kind': 'runtime', 'run_id': 'stale'}))
    monkeypatch.setattr(health.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(returncode=returncode, stdout='private-path secret=never-publish'))
    report = health.run_runtime_probe()
    assert report['ok'] is False and expected in report['message']
    assert report['returncode'] == returncode
    assert 'secret=' not in json.dumps(report)
    assert read_report(diagnostic_data) == report


def test_parent_preserves_graceful_child_failure(diagnostic_data, monkeypatch):
    def run(*args, **kwargs):
        report = read_child_report(diagnostic_data, kwargs['env'])
        report.update(phase='imports', message='Thiếu thư viện tạo giọng (soxr).')
        health._save(report)
        return SimpleNamespace(returncode=1, stdout='raw sensitive exception')
    monkeypatch.setattr(health.subprocess, 'run', run)
    report = health.run_runtime_probe()
    assert report['ok'] is False and report['phase'] == 'imports' and '(soxr)' in report['message']
    assert 'sensitive' not in json.dumps(report)


def test_parent_probe_timeout_saves_failure(diagnostic_data, monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 90, output='private traceback')
    monkeypatch.setattr(health.subprocess, 'run', run)
    report = health.run_runtime_probe()
    assert report['ok'] is False and 'quá thời gian' in report['message']
    assert 'private' not in json.dumps(report)
    assert not list((diagnostic_data / 'diagnostics').glob('.runtime-*.json'))


def test_parent_retains_last_completed_child_phase_after_crash(diagnostic_data, monkeypatch):
    def run(*args, **kwargs):
        report = read_child_report(diagnostic_data, kwargs['env'])
        report.update(phase='backend-imports', checks=[{'name': 'cpu-conv1d-numpy', 'ok': True}])
        health._save(report)
        return SimpleNamespace(returncode=3221225781, stdout='DLL load failed private-path')
    monkeypatch.setattr(health.subprocess, 'run', run)
    report = health.run_runtime_probe()
    assert report['ok'] is False and report['phase'] == 'backend-imports'
    assert report['checks'] == [{'name': 'cpu-conv1d-numpy', 'ok': True}]
    assert 'DLL' in report['message'] and 'private-path' not in json.dumps(report)
    assert not list((diagnostic_data / 'diagnostics').glob('.runtime-*.json'))


def test_concurrent_launcher_probes_read_their_own_reports(diagnostic_data, monkeypatch):
    children_complete = threading.Barrier(2)
    child_ids = []
    def run(*args, **kwargs):
        report = read_child_report(diagnostic_data, kwargs['env'])
        child_ids.append(report['run_id'])
        report.update(ok=True, success=True, phase='complete', message='PASS: own child ' + report['run_id'])
        health._save(report)
        # Both private children finish before either parent reads or publishes.
        children_complete.wait(timeout=5)
        return SimpleNamespace(returncode=0, stdout='')
    monkeypatch.setattr(health.subprocess, 'run', run)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: health.run_runtime_probe(), range(2)))
    assert all(report['ok'] for report in results)
    assert len(set(child_ids)) == 2
    for report in results:
        assert report['run_id'] in child_ids and report['message'].endswith(report['run_id'])
        assert report['report_path'] == str(diagnostic_data / 'diagnostics' / 'runtime-check.json')
    assert read_report(diagnostic_data)['run_id'] in child_ids
    assert not list((diagnostic_data / 'diagnostics').glob('.runtime-*.json'))


@pytest.mark.parametrize('private_id', ['../../outside', 'C:\\outside.json', 'a' * 32])
def test_private_child_report_rejects_paths_and_mismatched_ids(diagnostic_data, monkeypatch, private_id):
    monkeypatch.setenv('HMOOB_HEALTH_PRIVATE_RUNTIME_ID', private_id)
    monkeypatch.setenv('HMOOB_HEALTH_RUN_ID', 'b' * 32)
    monkeypatch.setattr(health.importlib, 'import_module', lambda name:
                        pytest.fail('Reject invalid private identity before native imports'))
    report = health.probe_runtime()
    assert report['ok'] is False and 'Mã kiểm tra' in report['message']
    assert report['report_path'] == str(diagnostic_data / 'diagnostics' / 'runtime-check.json')
    assert not list((diagnostic_data / 'diagnostics').glob('.runtime-*.json'))


def test_parent_does_not_promote_or_delete_an_untrusted_report_path(diagnostic_data, monkeypatch):
    outside = diagnostic_data / 'unrelated.json'
    outside.write_text('keep me')
    def run(*args, **kwargs):
        report = read_child_report(diagnostic_data, kwargs['env'])
        private_path = Path(report['report_path'])
        report.update(ok=True, success=True, phase='complete', message='PASS', report_path=str(outside))
        private_path.write_text(json.dumps(report))
        return SimpleNamespace(returncode=0, stdout='')
    monkeypatch.setattr(health.subprocess, 'run', run)
    report = health.run_runtime_probe()
    assert report['ok'] is True and report['report_path'] == str(diagnostic_data / 'diagnostics' / 'runtime-check.json')
    assert outside.read_text() == 'keep me'
    assert not list((diagnostic_data / 'diagnostics').glob('.runtime-*.json'))


def test_zero_exit_without_a_completed_child_report_cannot_pass(diagnostic_data, monkeypatch):
    monkeypatch.setattr(health.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout=''))
    report = health.run_runtime_probe()
    assert report['ok'] is False and report['phase'] == 'subprocess'


@pytest.mark.parametrize('action', [health.probe_runtime, health.test_voices, health.run_runtime_probe])
def test_unwritable_diagnostics_produce_actionable_console_failure(diagnostic_data, monkeypatch, capsys, action):
    def denied(*args, **kwargs):
        raise PermissionError('private-path secret')
    monkeypatch.setattr(health, 'write_json_atomic', denied)
    report = action()
    assert report['ok'] is False and report['report_saved'] is False
    assert 'quyền' in report['diagnostic_error']
    console = capsys.readouterr().out
    assert 'Không lưu được báo cáo' in console and 'private-path' not in console


@pytest.fixture
def synthetic_engine(diagnostic_data, monkeypatch):
    state = SimpleNamespace(instances=0, calls=[], samples=(np.sin(np.arange(4410) * .08) * .2).astype(np.float32),
                            rate=22050, failure=None)
    class Engine:
        device = 'cpu'
        def __init__(self):
            state.instances += 1
        def set_progress_callback(self, callback):
            self.progress = callback
        def synthesize(self, text, reference_path, reference_text, **kwargs):
            content = reference_path.read_bytes()
            state.calls.append({'text': text, 'path': reference_path, 'bytes': content,
                                'reference_text': reference_text, **kwargs})
            self.progress('Đang tạo âm thanh kiểm tra…')
            if state.failure is not None:
                raise state.failure
            return state.samples.copy(), state.rate
    monkeypatch.setattr(hmong_native, 'verify_models', lambda: ('verified',))
    monkeypatch.setattr(hmong_native, 'SpeechEngine', Engine)
    return state, Engine


@pytest.mark.parametrize('backend', ['native', 'f5'])
def test_both_voices_use_one_engine_exact_reference_snapshots_and_pcm24k(diagnostic_data, monkeypatch, synthetic_engine, backend):
    state, engine = synthetic_engine
    monkeypatch.setenv('HMOOB_BACKEND', backend)
    if backend == 'f5':
        import hmong_engine
        monkeypatch.setattr(hmong_engine, 'verify_models', lambda: ('verified',))
        monkeypatch.setattr(hmong_engine, 'SpeechEngine', engine)
        state.rate = 24000
    jobs = diagnostic_data / 'jobs'
    jobs.mkdir()
    (jobs / 'existing.json').write_text('{"status":"running"}')
    report = health.test_voices()
    assert report['ok'] is True and report['inference_tested'] is True
    assert report['pronunciation_evaluated'] is False and report['reference_similarity_evaluated'] is False
    assert state.instances == 1 and len(state.calls) == 2
    assert read_report(diagnostic_data, 'speech-check.json') == report
    assert (jobs / 'existing.json').read_text() == '{"status":"running"}'
    assert sorted(path.name for path in jobs.iterdir()) == ['existing.json']
    for gender, voice, call in zip(('male', 'female'), report['voices'], state.calls):
        original, words = hmong_assets.reference('hmong-' + gender)
        assert call['path'] != original and call['bytes'] == original.read_bytes()
        assert not call['path'].exists()  # Temporary exact-byte references are cleaned up.
        assert call['reference_text'] == voice['reference_text'] == words
        assert voice['reference_fingerprint'] == hmong_assets.reference_fingerprint('hmong-' + gender)
        assert voice['reference_sha256'] == hashlib.sha256(call['bytes']).hexdigest()
        assert call['quality'] == ('standard' if backend == 'native' else 'fast')
        path = diagnostic_data / 'diagnostics' / voice['output']
        info = sf.info(path)
        audio, rate = sf.read(path, dtype='int16')
        assert info.channels == 1 and info.subtype == 'PCM_16' and rate == 24000
        assert np.any(audio) and info.frames == voice['frames'] and voice['rms'] > 0
        assert voice['output_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('failure', ['silent', 'nan', 'stereo', 'empty', 'bad-rate', 'rounds-to-silence'])
def test_invalid_inference_is_never_reported_as_two_voice_success(diagnostic_data, synthetic_engine, failure):
    state, _ = synthetic_engine
    if failure == 'silent':
        state.samples[:] = 0
    elif failure == 'nan':
        state.samples[0] = np.nan
    elif failure == 'stereo':
        state.samples = state.samples[:, None]
    elif failure == 'empty':
        state.samples = state.samples[:0]
    elif failure == 'bad-rate':
        state.rate = True
    else:
        state.rate = 24000
        state.samples = np.ones(2400, dtype=np.float32) * 2e-6
    folder = diagnostic_data / 'diagnostics'
    folder.mkdir()
    (folder / 'test-male.wav').write_bytes(b'stale-success')
    (folder / 'test-female.wav').write_bytes(b'stale-success')
    report = health.test_voices()
    assert report['ok'] is False and report['voices'] == []
    assert not (folder / 'test-male.wav').exists() and not (folder / 'test-female.wav').exists()
    assert read_report(diagnostic_data, 'speech-check.json') == report


def test_missing_models_fail_offline_before_inference(diagnostic_data, synthetic_engine, monkeypatch):
    state, _ = synthetic_engine
    def missing():
        raise EngineError('missing model private-path')
    monkeypatch.setattr(hmong_native, 'verify_models', missing)
    report = health.test_voices()
    assert report['ok'] is False and report['phase'] == 'models'
    assert '--setup-only' in report['message'] and 'private-path' not in report['message']
    assert report['inference_tested'] is False and not state.calls


def test_inference_oom_produces_actionable_report(diagnostic_data, synthetic_engine):
    state, _ = synthetic_engine
    state.failure = RuntimeError('out of memory at C:/private-user/secret')
    report = health.test_voices()
    assert report['ok'] is False and 'RAM' in report['message'] and 'private-user' not in json.dumps(report)


def test_invalid_reference_is_actionable_before_either_voice_runs(diagnostic_data, synthetic_engine, monkeypatch):
    state, _ = synthetic_engine
    def invalid(ident):
        raise ValueError('bad SHA256 C:/private-path')
    monkeypatch.setattr(hmong_assets, 'reference', invalid)
    report = health.test_voices()
    assert report['ok'] is False and not state.calls
    assert 'SHA-256' in report['message'] and 'assets/hmong' in report['message']
    assert 'private-path' not in json.dumps(report)


def test_one_successful_voice_is_insufficient_for_a_successful_check(diagnostic_data, synthetic_engine, monkeypatch):
    state, engine = synthetic_engine
    synthesize = engine.synthesize
    def second_fails(self, *args, **kwargs):
        if state.calls:
            raise RuntimeError('out of memory')
        return synthesize(self, *args, **kwargs)
    monkeypatch.setattr(engine, 'synthesize', second_fails)
    report = health.test_voices()
    assert report['ok'] is False and len(report['voices']) == 1
    assert report['voices'][0]['id'] == 'hmong-male'
    assert (diagnostic_data / 'diagnostics' / 'test-male.wav').is_file()
    assert not (diagnostic_data / 'diagnostics' / 'test-female.wav').exists()


def test_health_cli_returns_failure_for_failed_real_check(monkeypatch):
    monkeypatch.setattr(health, 'test_voices', lambda: {'ok': False})
    monkeypatch.setattr(health, 'probe_runtime', lambda: {'ok': True})
    assert health.main(['--test-voice']) == 1
    assert health.main(['--probe-runtime']) == 0
