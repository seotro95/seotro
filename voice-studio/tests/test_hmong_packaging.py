"""Check privacy boundaries and launcher configuration without downloading models."""
from __future__ import annotations

import hashlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

import pytest

PACKAGING = Path(__file__).resolve().parents[1] / 'packaging'
sys.path.insert(0, str(PACKAGING))
spec = importlib.util.spec_from_file_location('build_hmong_windows', PACKAGING / 'build_hmong_windows.py')
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


def source_fixture(root):
    root.mkdir()
    for name in ('app.py', 'worker.py', 'bundle_check.py', 'runtime_instance.py', 'hmong_acceleration.py',
                 'hmong_engine.py', 'hmong_expression.py', 'hmong_f5.py',
                 'hmong_native.py', 'hmong_native_models.py', 'prepare_hmong_native.py',
                 'hmong_reference.py', 'hmong_text.py', 'hmong_assets.py', 'prepare_hmong.py',
                 'hmong_launcher.py', 'studio_variant.py'):
        (root / name).write_text('# app\n', encoding='utf-8')
    for name in ('HMONG-README.md', 'requirements-hmong.txt'):
        (root / name).write_text('Hmong-only instructions\n', encoding='utf-8')
    for name in ('README.md', 'requirements.txt', 'requirements-qwen.txt', 'requirements-tested.txt',
                 'install.bat', 'start.bat', 'download_models.bat', 'VALIDATION.md'):
        (root / name).write_text('unrelated Vietnamese environment\n', encoding='utf-8')
    for name in ('docs/HMONG-NATIVE.md', 'static/app.js', 'assets/hmong/female.wav', 'assets/hmong/male.wav',
                 'assets/hmong/source-female.mp3', 'assets/hmong/source-male.mp3',
                 'assets/hmong/voices.json', '.data/voices/personal.wav',
                 '.data/models/private.bin', '.venv/Lib/private.py', 'assets/private.wav', '.env'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
    from bundle_check import NATIVE_VENDOR_REQUIRED
    manifest = {}
    for name in NATIVE_VENDOR_REQUIRED:
        path = root / 'hmong_native_vendor' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'# reviewed code or license\n')
        manifest[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / 'hmong_native_vendor/manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    # These files must not be copied, even when left beside vendored code.
    (root / 'hmong_native_vendor/model.pth').write_bytes(b'weights')
    (root / 'hmong_native_vendor/private.json').write_bytes(b'private data')
    (root / 'hmong_native_vendor/__pycache__').mkdir()
    (root / 'hmong_native_vendor/__pycache__/models.pyc').write_bytes(b'cached bytecode')


def test_source_copy_includes_only_approved_assets(tmp_path):
    source = tmp_path / 'source'
    source_fixture(source)
    output = tmp_path / 'output'
    packaging.copy_source(output, source)
    assert (output / 'static/app.js').read_bytes() == b'fixture'
    assert (output / 'assets/hmong/female.wav').is_file()
    assert (output / 'assets/hmong/male.wav').is_file()
    assert (output / 'assets/hmong/source-female.mp3').is_file()
    assert (output / 'assets/hmong/source-male.mp3').is_file()
    assert not (output / '.data').exists()
    assert not (output / '.venv').exists()
    assert not (output / '.env').exists()
    assert not (output / 'assets/private.wav').exists()
    assert (output / 'bundle_check.py').is_file() and (output / 'hmong_text.py').is_file()
    assert (output / 'runtime_instance.py').is_file()
    assert (output / 'hmong_expression.py').is_file()
    assert (output / 'hmong_acceleration.py').is_file()
    assert (output / 'hmong_native.py').is_file()
    assert (output / 'docs/HMONG-NATIVE.md').is_file()
    assert (output / 'hmong_native_models.py').is_file()
    assert (output / 'hmong_native_vendor/openvoice/LICENSE').is_file()
    assert (output / 'hmong_native_vendor/watermark/LICENSE').is_file()
    assert not (output / 'hmong_native_vendor/model.pth').exists()
    assert not (output / 'hmong_native_vendor/private.json').exists()
    assert not (output / 'hmong_native_vendor/__pycache__').exists()
    assert (output / 'README.md').read_text() == 'Hmong-only instructions\n'
    assert (output / 'requirements.txt').read_text() == 'Hmong-only instructions\n'
    for name in ('requirements-qwen.txt', 'requirements-tested.txt', 'download_models.bat', 'VALIDATION.md'):
        assert not (output / name).exists()


def test_archive_has_valid_crc_and_matching_sha256(tmp_path):
    root = tmp_path / 'Voice-Studio-Hmong-1.5.3'
    root.mkdir()
    (root / 'hello.txt').write_bytes(b'relocatable')
    archive = tmp_path / 'bundle.zip'
    digest = packaging.archive_package(root, archive)
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert Path(str(archive) + '.sha256').read_text().strip() == digest + '  bundle.zip'
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert bundle.read(root.name + '/hello.txt') == b'relocatable'


def test_environment_and_batch_keep_data_in_hmong_package(tmp_path, monkeypatch):
    monkeypatch.setenv('PYTHONHOME', 'unrelated-python')
    monkeypatch.setenv('PYTHONPATH', 'unrelated-packages')
    monkeypatch.setenv('HF_HUB_OFFLINE', '1')
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    environment = packaging.build_environment(tmp_path, offline=False)
    assert 'PYTHONHOME' not in environment and 'PYTHONPATH' not in environment
    assert 'HF_HUB_OFFLINE' not in environment
    assert environment['VOICE_STUDIO_VARIANT'] == 'hmong'
    assert environment['VOICE_STUDIO_DATA_DIR'] == str(tmp_path / 'voice-studio-hmong/.data')
    assert environment['HMOOB_MODEL_DIR'] == str(tmp_path / 'voice-studio-hmong/.data/models')
    assert environment['HMOOB_BACKEND'] == 'f5', 'Normal build paths must not inherit native selection'
    assert packaging.build_environment(tmp_path, offline=True, backend='native')['HMOOB_BACKEND'] == 'native'
    assert packaging.build_environment(tmp_path, offline=True)['HF_HUB_OFFLINE'] == '1'
    packaging.write_launcher(tmp_path)
    batch = (tmp_path / 'MO_VOICE_STUDIO_HMONG.bat').read_bytes()
    assert b'\r\n' in batch
    assert b'set "HMOOB_BACKEND=native"' in batch
    assert b'call "%~dp0tools\\launch_hmong.bat" %*' in batch
    assert [path.name for path in tmp_path.glob('*.bat')] == ['MO_VOICE_STUDIO_HMONG.bat']
    helper = (tmp_path / 'tools/launch_hmong.bat').read_bytes()
    assert b'VOICE_STUDIO_VARIANT=hmong' in helper
    assert b'VOICE_STUDIO_DATA_DIR=%CD%\\voice-studio-hmong\\.data' in helper
    assert b'hmong_launcher.py" %*' in helper
    assert b'cd /d "%~dp0.."' in helper
    fallback = (tmp_path / 'tools/MO_F5_HMONG.bat').read_bytes()
    assert b'set "HMOOB_BACKEND=f5"' in fallback
    assert b'call "%~dp0launch_hmong.bat" %*' in fallback
    assert len(list(tmp_path.rglob('*.bat'))) == 5
    install = (tmp_path / 'tools/install_hmong_cuda.bat').read_bytes()
    assert b'if "%~1"=="" goto setup' in install and b'--install-cuda' in install
    for path in tmp_path.rglob('*.bat'):
        alias = path.read_bytes()
        assert b'\r\n' in alias and b'.venv' not in alias and b'pip install' not in alias


def test_single_download_bundles_only_approved_reports_and_generated_auditions(tmp_path):
    source = tmp_path / 'qa-reports'
    source.mkdir()
    names = ('native-smoke.json', 'f5-smoke.json', 'browser-smoke.json', 'model-sources.json',
             'Hmong-female-2-preview.mp3', 'Hmong-male-2-preview.mp3')
    for name in (*names, 'private.wav', 'model.pth', 'credentials.json'):
        (source / name).write_bytes(b'fixture: ' + name.encode())
    root = tmp_path / 'portable'
    packaging.bundle_reports(root, source)
    assert {path.name for path in (root / 'reports').iterdir()} == set(names)
    for name in names:
        assert (root / 'reports' / name).read_bytes() == (source / name).read_bytes()


def test_single_download_rejects_a_missing_generated_audition(tmp_path):
    source = tmp_path / 'qa-reports'
    source.mkdir()
    with pytest.raises(ValueError, match='Required release report/audition'):
        packaging.bundle_reports(tmp_path / 'portable', source)


def browser_report_fixture():
    expected = packaging.expected_reference_fingerprints()
    cases = []
    for index, (name, ident) in enumerate([
            ('main_male_button', 'hmong-male'), ('main_female_button', 'hmong-female'),
            ('library_preset_after_cloned_filter', 'hmong-male'),
            ('main_female_to_workspace_speech', 'hmong-female')]):
        cases.append({'case': name, 'voice_id': ident, 'post_voice_id': ident, 'speaker': ident,
                      'hmong_reference_fingerprint': expected[ident], 'engine': 'hmong_native',
                      'job_id': 'job-' + str(index), 'status': 'done', 'real_ui_post': True,
                      'audio_bytes': 48044, 'audio_seconds': 1, 'sha256': 'a' * 64,
                      'peak_amplitude': .2, 'sample_rate': 24000, 'sample_width': 2,
                      'playback': {'ready_state': 4, 'media_error': None, 'current_time': .1, 'duration': 1},
                      'audio_playback_checked': True, 'download_verified': True,
                      'original_text_preserved': True, 'text': 'Nyob-zoo, kuv yog ib tug Hmoob.'})
    return {'success': True, 'platform': 'win32', 'native_windows_validation': True,
            'real_ui_synthesis': True, 'engine': 'hmong_native',
            'cloned_filter_library_selection': True, 'cross_panel_selection': True,
            'hyphenated_text_preserved': True,
            'runtime': {'version': packaging.VERSION + '-hmong', 'backend': 'hmong_native'},
            'browser': {'channel': 'msedge', 'version': '142.0', 'responses_mocked': False},
            'script_sha256': hashlib.sha256((PACKAGING / 'browser_hmong_portable.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            'expected_reference_fingerprints': expected,
            'voices': {'hmong-male': cases[0], 'hmong-female': cases[1]}, 'cases': cases}


def test_windows_browser_gate_accepts_all_actual_ui_synthesis_cases():
    report = browser_report_fixture()
    assert packaging.validate_browser_report(report) is report


@pytest.mark.parametrize('failure', ['linux', 'skipped', 'library', 'workspace', 'speaker',
                                    'reference', 'missing_case', 'wrong_case', 'silent_audio',
                                    'no_playback', 'stale_script', 'hyphen_text'])
def test_windows_browser_gate_rejects_incomplete_or_wrong_voice_evidence(failure):
    report = copy.deepcopy(browser_report_fixture())
    if failure == 'linux':
        report['platform'] = 'linux'
    elif failure == 'skipped':
        report['real_ui_synthesis'] = False
    elif failure == 'library':
        report['cloned_filter_library_selection'] = False
    elif failure == 'workspace':
        report['cross_panel_selection'] = False
    elif failure == 'speaker':
        report['cases'][0]['speaker'] = 'hmong-female'
    elif failure == 'reference':
        report['cases'][1]['hmong_reference_fingerprint'] = 'b' * 64
    elif failure == 'missing_case':
        report['cases'].pop()
    elif failure == 'wrong_case':
        report['cases'][3]['case'] = 'another_main_case'
    elif failure == 'silent_audio':
        report['cases'][2]['audio_bytes'] = 0
    elif failure == 'no_playback':
        report['cases'][0]['audio_playback_checked'] = False
    elif failure == 'stale_script':
        report['script_sha256'] = 'b' * 64
    else:
        for case in report['cases']:
            case['text'] = 'Nyob zoo.'
    with pytest.raises(ValueError):
        packaging.validate_browser_report(report)


def test_publication_gate_reads_mandatory_browser_evidence_from_the_zip(tmp_path):
    root = tmp_path / ('Voice-Studio-Hmong-' + packaging.VERSION)
    packaging.write_launcher(root)
    report = browser_report_fixture()
    reports = root / 'reports'
    reports.mkdir()
    files = {'BUILD.json': {'version': packaging.VERSION, 'windows_browser_validation': True},
             'reports/browser-smoke.json': report,
             'reports/native-smoke.json': {'success': True, 'main_launcher': {
                 'browser_ui': report, 'second_launch_reused': True, 'active_job_preserved': True}},
             'reports/f5-smoke.json': {'success': True, 'advanced_f5_launcher': {'second_launch_reused': True}}}
    for name, value in files.items():
        (root / name).write_text(json.dumps(value), encoding='utf-8')
    for name in ('Hmong-female-2-preview.mp3', 'Hmong-male-2-preview.mp3'):
        (reports / name).write_bytes(b'ID3' + b'x' * 1200)
    # The pinned Python runtime contains standard BAT files of its own.
    activation = root / 'runtime/Scripts/activate.bat'
    activation.parent.mkdir(parents=True)
    activation.write_bytes(b'@echo off\r\n')
    archive = tmp_path / 'release.zip'
    packaging.archive_package(root, archive)
    assert packaging.validate_release_archive(archive) == report
    extra = root / 'UNEXPECTED.BAT'
    extra.write_bytes(b'@echo off\r\n')
    packaging.archive_package(root, archive)
    with pytest.raises(ValueError, match='one root BAT'):
        packaging.validate_release_archive(archive)
    extra.unlink()
    (reports / 'browser-smoke.json').unlink()
    packaging.archive_package(root, archive)
    with pytest.raises(KeyError, match='browser-smoke'):
        packaging.validate_release_archive(archive)


def test_browser_smoke_requires_a_separate_qa_interpreter(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('smoke_hmong_browser', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    monkeypatch.delenv('HMOOB_BROWSER_PYTHON', raising=False)
    with pytest.raises(RuntimeError, match='separate HMOOB_BROWSER_PYTHON'):
        smoke.check_browser_selection(tmp_path, 'http://127.0.0.1:8770', tmp_path / 'reports')
    interpreter = tmp_path / 'runtime/python.exe'
    interpreter.parent.mkdir()
    interpreter.touch()
    monkeypatch.setenv('HMOOB_BROWSER_PYTHON', str(interpreter))
    with pytest.raises(RuntimeError, match='outside the portable package'):
        smoke.check_browser_selection(tmp_path, 'http://127.0.0.1:8770', tmp_path / 'reports')


def test_browser_smoke_passes_verified_references_to_external_browser_without_development_bypass(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('smoke_hmong_browser_run', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    interpreter = tmp_path / 'qa/python.exe'
    interpreter.parent.mkdir()
    interpreter.touch()
    monkeypatch.setenv('HMOOB_BROWSER_PYTHON', str(interpreter))
    expected = packaging.expected_reference_fingerprints()
    monkeypatch.setitem(sys.modules, 'hmong_assets', SimpleNamespace(reference_fingerprint=expected.__getitem__))
    report = browser_report_fixture()
    report['runtime']['url'] = 'http://127.0.0.1:8770'
    reports = tmp_path / 'reports'
    reports.mkdir()
    def run(command, **kwargs):
        assert Path(command[0]) == interpreter
        assert Path(command[1]).name == 'browser_hmong_portable.py'
        assert command[2:4] == ['--url', report['runtime']['url']]
        assert command[4:6] == ['--reports', str(reports)]
        assert command[6] == '--expected-references'
        assert json.loads(command[7]) == expected
        assert len(command) == 8, 'Production QA must never pass --allow-non-windows'
        assert kwargs == {'check': True, 'timeout': 1800}
        (reports / 'browser-smoke.json').write_text(json.dumps(report), encoding='utf-8')
    monkeypatch.setattr(smoke.subprocess, 'run', run)
    assert smoke.check_browser_selection(tmp_path / 'portable', report['runtime']['url'], reports) == report


def test_source_copy_refuses_linked_assets(tmp_path):
    source = tmp_path / 'source'
    source_fixture(source)
    try:
        (source / 'assets/hmong/external').symlink_to(source / '.env')
    except OSError:
        pytest.skip('Symlink permission unavailable on this host')
    with pytest.raises(ValueError, match='Linked application assets'):
        packaging.copy_source(tmp_path / 'output', source)


@pytest.mark.parametrize('failure', ['modified_code', 'missing_license', 'path_escape', 'model_weight'])
def test_native_vendor_requires_pinned_code_and_licenses_and_rejects_unapproved_paths(tmp_path, failure):
    from bundle_check import BundleError, validate_native_vendor
    source = tmp_path / 'source'
    source_fixture(source)
    vendor = source / 'hmong_native_vendor'
    assert validate_native_vendor(source) == 27
    manifest_path = vendor / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if failure == 'modified_code':
        (vendor / 'vits/models.py').write_bytes(b'changed code')
    elif failure == 'missing_license':
        del manifest['openvoice/LICENSE']
    elif failure == 'path_escape':
        manifest['../app.py'] = hashlib.sha256((source / 'app.py').read_bytes()).hexdigest()
    else:
        manifest['model.pth'] = hashlib.sha256((vendor / 'model.pth').read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(BundleError):
        validate_native_vendor(source)
    with pytest.raises(ValueError, match='Mã hoặc giấy phép'):
        packaging.copy_source(tmp_path / 'output', source)


@pytest.mark.parametrize('name', ['bundle_check.py', 'hmong_text.py', 'hmong_expression.py',
                                 'hmong_acceleration.py', 'hmong_native.py', 'hmong_native_models.py',
                                 'prepare_hmong_native.py', 'runtime_instance.py'])
def test_source_copy_rejects_missing_new_runtime_modules(tmp_path, name):
    source = tmp_path / 'source'
    source_fixture(source)
    (source / name).unlink()
    with pytest.raises(ValueError, match=name):
        packaging.copy_source(tmp_path / 'output', source)


def test_native_smoke_probes_primary_and_every_advanced_batch(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('smoke_hmong', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    root = tmp_path / 'Relocated Hmong test with spaces' / 'Voice-Studio-Hmong-1.5.3'
    root.mkdir(parents=True)
    packaging.write_launcher(root)
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        assert command[1:3] == ['/d', '/c']
        assert (kwargs['cwd'] / command[3]).is_file()
        assert kwargs['stdin'] == smoke.subprocess.DEVNULL
        expected = 'f5' if command[3] == 'MO_F5_HMONG.bat' else 'native'
        if command[3] in {'MO_VOICE_STUDIO_HMONG.bat', 'MO_F5_HMONG.bat'}:
            assert kwargs['env']['HMOOB_BACKEND'] != expected, 'Probe must test inherited backend override'
        label = 'F5-Hmong' if expected == 'f5' else 'Hmong nhanh thử nghiệm'
        return SimpleNamespace(returncode=0, stdout=label + '\nPASS: verified models\n')
    monkeypatch.setattr(smoke.subprocess, 'run', run)
    result = smoke.check_batch_entrypoints(root)
    assert len(calls) == len(result) == 5
    assert result['MO_VOICE_STUDIO_HMONG.bat']['engine'] == 'hmong_native'
    assert result['tools/MO_F5_HMONG.bat']['engine'] == 'f5_hmong'
    assert {args[0][-1] for args in calls} == {'--check', '--setup-only'}
    assert result['tools/launch_hmong.bat']['argument'] == '--setup-only'
    assert result['tools/install_hmong_cuda.bat']['argument'] == '--check'
    assert all('--install-cuda' not in args[0] for args in calls), 'Native CPU QA must never download CUDA'


def test_native_smoke_rejects_false_success_without_pass(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('smoke_hmong_failed', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    monkeypatch.setattr(smoke.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout='tool incomplete\n'))
    with pytest.raises(RuntimeError, match='MO_VOICE_STUDIO_HMONG.bat'):
        smoke.check_batch_entrypoints(tmp_path)


@pytest.mark.parametrize('backend,second_ok', [('native', True), ('f5', True), ('native', False)])
def test_windows_launcher_smoke_checks_reuse_and_only_cleans_up_its_first_process(tmp_path, monkeypatch,
                                                                               backend, second_ok):
    spec = importlib.util.spec_from_file_location('smoke_hmong_reuse', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    data = tmp_path / 'voice-studio-hmong/.data'
    monkeypatch.setattr(smoke, 'os', SimpleNamespace(name='nt', environ={'VOICE_STUDIO_DATA_DIR': str(data)}))
    url = 'http://127.0.0.1:8770'
    engine = 'hmong_native' if backend == 'native' else 'f5_hmong'
    instance = {'instance_id': 'qa-server', 'pid': 102, 'url': url, 'data_id': 'qa-data',
                'root_id': 'qa-root', 'backend': engine, 'version': '1.5.3-hmong'}
    process = SimpleNamespace(pid=101, stdout=io.StringIO('Studio: ' + url + '\n'),
                              poll=lambda: None, wait=lambda **kwargs: 0)
    server = SimpleNamespace(is_running=lambda: True, parents=lambda: [SimpleNamespace(pid=101)])
    monkeypatch.setitem(sys.modules, 'psutil', SimpleNamespace(Process=lambda pid: server if pid == 102 else None))
    calls = []
    def popen(command, **kwargs):
        assert command[1:3] == ['/d', '/c']
        assert command[3] == ('MO_VOICE_STUDIO_HMONG.bat' if backend == 'native' else 'MO_F5_HMONG.bat')
        assert kwargs['cwd'] == (tmp_path if backend == 'native' else tmp_path / 'tools')
        assert (data / 'server.lock').read_bytes() == b''
        assert json.loads((data / 'server-instance.json').read_text())['instance_id'] == 'stale-build-qa-instance'
        calls.append(('first', command))
        return process
    def run(command, **kwargs):
        calls.append(('run', command))
        if command[0] == 'taskkill':
            assert command == ['taskkill', '/PID', '101', '/T', '/F']
        if command[-1] == '--no-browser':
            assert kwargs['timeout'] == 15
            kwargs['stdout'].write('REUSED: existing Voice Studio\nStudio: ' + url + '\n')
            return SimpleNamespace(returncode=0 if second_ok else 1)
        return SimpleNamespace(returncode=0)
    requested = []
    class Opener:
        def open(self, request, timeout):
            address = request if isinstance(request, str) else request.full_url
            path = address.removeprefix(url)
            requested.append(path)
            value = {'/api/config': {'variant': 'hmong', 'models': {engine: True},
                                     'hmong_engine': engine, 'hmong_steps': None if backend == 'native' else 16,
                                     'version': instance['version']},
                     '/api/runtime': instance,
                     '/api/history': {'items': [{'id': 'previous', 'status': 'done'}]},
                     '/api/speech': {'id': 'active-qa', 'status': 'queued'},
                     '/api/jobs/active-qa': {'id': 'active-qa', 'status': 'done',
                                             'engine': engine, 'audio_seconds': 1.5}}[path]
            if path == '/api/jobs/active-qa' and requested.count(path) == 1:
                value = {**value, 'status': 'running'}
            response = io.BytesIO(json.dumps(value).encode())
            response.status = 202 if path == '/api/speech' else 200
            return response
    monkeypatch.setattr(smoke.subprocess, 'Popen', popen)
    monkeypatch.setattr(smoke.subprocess, 'run', run)
    monkeypatch.setattr(smoke.urllib.request, 'build_opener', lambda *_args: Opener())
    if second_ok:
        result = smoke.check_web_launcher(tmp_path, backend)
        assert result['second_launch_reused'] and result['same_url_and_pid']
        assert result['actual_cmd_batch'] is True
        assert result['batch_entrypoint'] == ('MO_VOICE_STUDIO_HMONG.bat' if backend == 'native'
                                               else 'tools/MO_F5_HMONG.bat')
        assert result['active_job_preserved'] is (backend == 'native')
        assert ('/api/speech' in requested) is (backend == 'native')
    else:
        with pytest.raises(AssertionError, match='second launcher'):
            smoke.check_web_launcher(tmp_path, backend)
    assert [command for kind, command in calls if command[0] == 'taskkill'] == [
        ['taskkill', '/PID', '101', '/T', '/F']]


def test_native_expression_sample_exercises_two_local_emotions_in_two_synthesis_chunks():
    from narration import plan_segments
    spec = importlib.util.spec_from_file_location('smoke_hmong_expression', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    segments = plan_segments({'text': smoke.EXPRESSIVE_SAMPLE, 'engine': 'f5_hmong',
        'segment_plan': 'hmong-expression-v1', 'emotion': 'warm', 'emotion_strength': .65,
        'auto_rhythm': False, 'hmong_phrase_context': True, 'paragraph_pause': 0})
    speech = [segment for segment in segments if segment.text]
    assert [(segment.emotion, segment.emphasis) for segment in speech] == [('warm', True), ('serious', False)]
    assert [segment.pause for segment in segments if not segment.text] == [.25]
    assert all('[emotion=' not in segment.text and '**' not in segment.text for segment in speech)
    plain = ' '.join(segment.text for segment in speech)
    assert plain == smoke.PLAIN_SAMPLE
    for word in smoke.PRONUNCIATION_TEST_WORDS:
        assert word in plain.split() or word + '.' in plain.split()
    female = plan_segments({'text': smoke.PLAIN_SAMPLE, 'engine': 'f5_hmong',
        'segment_plan': 'hmong-expression-v1', 'emotion': 'warm', 'emotion_strength': .65,
        'auto_rhythm': False, 'hmong_phrase_context': True, 'paragraph_pause': 0})
    assert len(female) == 1 and female[0].text == smoke.PLAIN_SAMPLE


def test_native_speed_gate_rejects_a_measurement_inflated_by_inserted_silence():
    from performance import speed_report
    spec = importlib.util.spec_from_file_location('smoke_hmong_speed', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    job = {'audio_seconds': 120, 'spoken_audio_seconds': 2, 'inserted_silence_seconds': 118,
           'wall_processing_seconds': 1, 'speed_report': speed_report(120, 1, spoken_audio_seconds=2)}
    report = smoke.check_spoken_speed(job)
    assert report['realtime_multiplier'] == 2 and report['target_30x_verified_one_hour'] is False
    job['speed_report'] = speed_report(120, 1)
    with pytest.raises(AssertionError):
        smoke.check_spoken_speed(job)


def test_generated_audition_exports_existing_job_without_another_synthesis(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('smoke_hmong_preview', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    audio = b'ID3' + b'x' * 1200
    requests = []
    def get(url):
        requests.append(url)
        return SimpleNamespace(status_code=200, content=audio, headers={'content-type': 'audio/mpeg'})
    def probe(command, **kwargs):
        assert command[0] == 'ffprobe' and Path(command[-1]).read_bytes() == audio
        return b'{"streams":[{"codec_name":"mp3"}],"format":{"duration":"1.5"}}'
    monkeypatch.setattr(smoke.subprocess, 'check_output', probe)
    job = {'id': 'already-completed-job', 'voice_id': 'hmong-female', 'text': 'Nyob zoo.',
           'audio_seconds': 1.5, 'engine': 'hmong_native', 'hmong_backend': 'vits_openvoice_v2',
           'hmong_steps': None, 'hmong_precision': 'fp32', 'hmong_device': 'cpu', 'delivery': 'review',
           'emotion': 'warm', 'emotion_strength': .65, 'auto_rhythm': False, 'hmong_phrase_context': True,
           'spoken_audio_seconds': 1.5, 'inserted_silence_seconds': 0, 'speed_report': {}}
    # A get-only client makes any accidental new POST /api/speech fail.
    result = smoke.export_generated_preview(SimpleNamespace(get=get), job, tmp_path)
    assert requests == ['/api/jobs/already-completed-job/export.mp3']
    assert (tmp_path / 'Hmong-female-2-preview.mp3').read_bytes() == audio
    assert result['sha256'] == hashlib.sha256(audio).hexdigest()
    assert result['generated'] is True and result['original_source_recording'] is False
    assert result['settings']['hmong_steps'] is None and result['settings']['hmong_precision'] == 'fp32'
    assert result['settings']['engine'] == 'hmong_native'
    assert result['settings']['hmong_backend'] == 'vits_openvoice_v2'
    assert result['settings']['hmong_device'] == 'cpu'
    assert result['settings']['hmong_phrase_context'] is True and result['settings']['auto_rhythm'] is False
    assert result['pronunciation_evaluated'] is False and result['target_30x_verified'] is False


@pytest.mark.parametrize('gender,source_seconds,reference_end', [
    ('male', 4.702, 4.65), ('female', 23.745, 4.9),
])
def test_native_clone_validation_uses_current_manifest_for_short_and_long_sources(
        gender, source_seconds, reference_end):
    spec = importlib.util.spec_from_file_location('smoke_hmong_refs', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    metadata = {'sha256': 'a' * 64, 'duration': source_seconds,
                'reference': {'start': .05, 'end': reference_end, 'text': 'Nyob zoo.'}}
    personal = {'engine': 'f5_hmong', 'automatic_reference': True, 'known_preset': 'hmong-' + gender,
                'source_sha256': metadata['sha256'], 'source_duration': source_seconds - .01,
                'transcript': 'Nyob zoo.', 'reference_start': .05, 'reference_end': reference_end,
                'duration': reference_end - .05}
    smoke.check_source_reference(personal, metadata, gender)
    personal['source_duration'] += 1
    with pytest.raises(AssertionError, match='Wrong source duration'):
        smoke.check_source_reference(personal, metadata, gender)


def test_optional_benchmark_keeps_settings_equal_even_when_joining_is_slower(tmp_path, monkeypatch):
    np = pytest.importorskip('numpy')
    spec = importlib.util.spec_from_file_location('benchmark_hmong', PACKAGING / 'benchmark_hmong.py')
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    hooks = []
    removed = []
    def register(hook):
        hooks.append(hook)
        return SimpleNamespace(remove=lambda: removed.append(True))
    model = SimpleNamespace(precision='fp32', ema_model=SimpleNamespace(
        transformer=SimpleNamespace(register_forward_pre_hook=register)))
    calls = []
    def infer(_ref, _words, text, _model, **kwargs):
        calls.append((text, kwargs))
        for _ in range(16):
            hooks[0](None, ())
        return np.full(24000, .2), 24000
    def load(_root, _device, *, precision):
        assert precision == 'fp32'
        return model
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(set_num_threads=lambda _: None,
        get_num_threads=lambda: 4, manual_seed=lambda _: None, from_numpy=lambda x: x))
    monkeypatch.setitem(sys.modules, 'soundfile', SimpleNamespace(
        read=lambda *args, **kwargs: (np.zeros((24000, 1)), 24000)))
    monkeypatch.setitem(sys.modules, 'hmong_assets', SimpleNamespace(
        reference=lambda _: (tmp_path / 'female.wav', 'Nyob zoo.')))
    monkeypatch.setitem(sys.modules, 'hmong_f5', SimpleNamespace(load_local_model=load, infer_batch=infer))
    clock = iter((0, 1, 10, 12))
    monkeypatch.setattr(benchmark.time, 'monotonic', lambda: next(clock))
    result = benchmark.compare(tmp_path)
    assert all(call[1] == {'steps': 16, 'speed': 1, 'device': 'cpu'} for call in calls)
    assert result['sequential_sentences']['nfe'] == 32
    assert result['joined_paragraph']['nfe'] == 16
    assert result['sequential_over_joined_wall_ratio'] == .5
    assert result['speedup_required'] is False and removed == [True]
