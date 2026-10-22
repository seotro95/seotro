"""Check privacy boundaries and launcher configuration without downloading models."""
from __future__ import annotations

import hashlib
import importlib.util
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
    for name in ('app.py', 'worker.py', 'bundle_check.py', 'hmong_engine.py', 'hmong_f5.py',
                 'hmong_reference.py', 'hmong_text.py', 'hmong_assets.py', 'prepare_hmong.py',
                 'hmong_launcher.py', 'studio_variant.py'):
        (root / name).write_text('# app\n', encoding='utf-8')
    for name in ('HMONG-README.md', 'requirements-hmong.txt'):
        (root / name).write_text('Hmong-only instructions\n', encoding='utf-8')
    for name in ('README.md', 'requirements.txt', 'requirements-qwen.txt', 'requirements-tested.txt',
                 'install.bat', 'start.bat', 'download_models.bat', 'VALIDATION.md'):
        (root / name).write_text('unrelated Vietnamese environment\n', encoding='utf-8')
    for name in ('static/app.js', 'assets/hmong/female.wav', 'assets/hmong/male.wav',
                 'assets/hmong/source-female.mp3', 'assets/hmong/source-male.mp3',
                 'assets/hmong/voices.json', '.data/voices/personal.wav',
                 '.data/models/private.bin', '.venv/Lib/private.py', 'assets/private.wav', '.env'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')


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
    assert (output / 'README.md').read_text() == 'Hmong-only instructions\n'
    assert (output / 'requirements.txt').read_text() == 'Hmong-only instructions\n'
    for name in ('requirements-qwen.txt', 'requirements-tested.txt', 'download_models.bat', 'VALIDATION.md'):
        assert not (output / name).exists()


def test_archive_has_valid_crc_and_matching_sha256(tmp_path):
    root = tmp_path / 'Voice-Studio-Hmong-1.2.0'
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
    environment = packaging.build_environment(tmp_path, offline=False)
    assert 'PYTHONHOME' not in environment and 'PYTHONPATH' not in environment
    assert 'HF_HUB_OFFLINE' not in environment
    assert environment['VOICE_STUDIO_VARIANT'] == 'hmong'
    assert environment['VOICE_STUDIO_DATA_DIR'] == str(tmp_path / 'voice-studio-hmong/.data')
    assert environment['HMOOB_MODEL_DIR'] == str(tmp_path / 'voice-studio-hmong/.data/models')
    assert packaging.build_environment(tmp_path, offline=True)['HF_HUB_OFFLINE'] == '1'
    packaging.write_launcher(tmp_path)
    batch = (tmp_path / 'MO_VOICE_STUDIO_HMONG.bat').read_bytes()
    assert b'\r\n' in batch
    assert b'VOICE_STUDIO_VARIANT=hmong' in batch
    assert b'VOICE_STUDIO_DATA_DIR=%~dp0voice-studio-hmong\\.data' in batch
    assert b'hmong_launcher.py" %*' in batch
    for folder, target in ((tmp_path, b'%~dp0MO_VOICE_STUDIO_HMONG.bat'),
                           (tmp_path / 'voice-studio-hmong', b'%~dp0..\\MO_VOICE_STUDIO_HMONG.bat')):
        for name in ('start.bat', 'start_hmong.bat', 'install.bat', 'install_hmong.bat'):
            alias = (folder / name).read_bytes()
            assert b'\r\n' in alias and target in alias
            assert b'%*' in alias and b'exit /b %ERRORLEVEL%' in alias
            assert b'.venv' not in alias and b'pip install' not in alias
            if name.startswith('install'):
                assert b'if "%~1"=="" goto setup' in alias and b'--setup-only' in alias


def test_source_copy_refuses_linked_assets(tmp_path):
    source = tmp_path / 'source'
    source_fixture(source)
    try:
        (source / 'assets/hmong/external').symlink_to(source / '.env')
    except OSError:
        pytest.skip('Symlink permission unavailable on this host')
    with pytest.raises(ValueError, match='Linked application assets'):
        packaging.copy_source(tmp_path / 'output', source)


@pytest.mark.parametrize('name', ['bundle_check.py', 'hmong_text.py'])
def test_source_copy_rejects_missing_new_runtime_modules(tmp_path, name):
    source = tmp_path / 'source'
    source_fixture(source)
    (source / name).unlink()
    with pytest.raises(ValueError, match=name):
        packaging.copy_source(tmp_path / 'output', source)


def test_native_smoke_probes_every_root_and_inner_batch_alias(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('smoke_hmong', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    root = tmp_path / 'Relocated Hmong test with spaces' / 'Voice-Studio-Hmong-1.2.0'
    root.mkdir(parents=True)
    packaging.write_launcher(root)
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        assert command[1:3] == ['/d', '/c']
        assert (kwargs['cwd'] / command[3]).is_file()
        assert kwargs['stdin'] == smoke.subprocess.DEVNULL
        return SimpleNamespace(returncode=0, stdout='PASS: verified models\n')
    monkeypatch.setattr(smoke.subprocess, 'run', run)
    result = smoke.check_batch_entrypoints(root)
    assert len(calls) == len(result) == 9
    assert {args[0][-1] for args in calls} == {'--check', '--setup-only'}
    assert result['voice-studio-hmong/install.bat']['argument'] == '--setup-only'
    assert result['voice-studio-hmong/start.bat']['argument'] == '--check'


def test_native_smoke_rejects_false_success_without_pass(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('smoke_hmong_failed', PACKAGING / 'smoke_hmong_portable.py')
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    monkeypatch.setattr(smoke.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout='tool incomplete\n'))
    with pytest.raises(RuntimeError, match='MO_VOICE_STUDIO_HMONG.bat'):
        smoke.check_batch_entrypoints(tmp_path)


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
