"""Incomplete bundles and wrong environments must fail before model setup."""
from importlib import metadata
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from bundle_check import BundleError, REQUIRED_FILES, validate_bundle
import hmong_launcher


ROOT = Path(__file__).resolve().parents[1]


def bundle_fixture(destination):
    for relative in REQUIRED_FILES:
        source, target = ROOT / relative, destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copytree(ROOT / 'hmong_native_vendor', destination / 'hmong_native_vendor',
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def isolate_launcher(monkeypatch, root):
    import hmong_health
    # These tests isolate bundle/dependency/model setup, while runtime probe
    # execution and its failure ordering have dedicated repair/health tests.
    monkeypatch.setattr(hmong_health, 'run_runtime_probe', lambda base: {'ok': True})
    monkeypatch.setattr(hmong_launcher, 'BASE', root)
    monkeypatch.setenv('VOICE_STUDIO_VARIANT', 'hmong')
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(root / '.test-data'))
    monkeypatch.setenv('HMOOB_BACKEND', 'f5')


def test_loose_source_files_fail_clearly_before_dependencies_or_model_download(tmp_path):
    bundle_fixture(tmp_path)
    shutil.rmtree(tmp_path / 'static')
    shutil.rmtree(tmp_path / 'assets')
    result = subprocess.run([sys.executable, str(tmp_path / 'hmong_launcher.py'), '--check'],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert 'TOÀN BỘ ZIP' in result.stdout
    assert 'static/index.html' in result.stdout
    assert 'assets/hmong/' in result.stdout
    assert 'PASS:' not in result.stdout
    assert 'PackageNotFoundError' not in result.stdout


def test_missing_static_cannot_pass_even_when_all_voice_assets_exist(tmp_path, monkeypatch):
    bundle_fixture(tmp_path)
    (tmp_path / 'static' / 'app.js').unlink()
    isolate_launcher(monkeypatch, tmp_path)
    monkeypatch.setattr(hmong_launcher, 'check_dependencies',
                        lambda: pytest.fail('Incomplete bundle must fail before checking dependencies'))
    with pytest.raises(BundleError, match='static/app.js'):
        hmong_launcher.main(['--check'])


def test_corrupted_default_mp3_fails_its_actual_checksum(tmp_path):
    bundle_fixture(tmp_path)
    (tmp_path / 'assets/hmong/source-male.mp3').write_bytes(b'corrupted MP3')
    with pytest.raises(BundleError, match='SHA256'):
        validate_bundle(tmp_path)


def test_empty_ui_asset_is_not_a_complete_application(tmp_path):
    bundle_fixture(tmp_path)
    (tmp_path / 'static/style.css').write_bytes(b'')
    with pytest.raises(BundleError, match='static/style.css'):
        validate_bundle(tmp_path)


def test_missing_package_names_the_hmong_installer(tmp_path, monkeypatch):
    bundle_fixture(tmp_path)
    isolate_launcher(monkeypatch, tmp_path)
    def version(name):
        if name == 'f5-tts':
            raise metadata.PackageNotFoundError(name)
        return '2.8.0' if name in {'torch', 'torchaudio'} else '1.0'
    monkeypatch.setattr(hmong_launcher.metadata, 'version', version)
    with pytest.raises(RuntimeError, match=r'f5-tts.*install_hmong\.bat'):
        hmong_launcher.main(['--check'])


def test_missing_audio_tools_is_actionable_and_does_not_download_models(tmp_path, monkeypatch):
    bundle_fixture(tmp_path)
    isolate_launcher(monkeypatch, tmp_path)
    monkeypatch.setattr(hmong_launcher, 'check_dependencies', lambda: None)
    monkeypatch.setattr(hmong_launcher.shutil, 'which', lambda _: None)
    monkeypatch.setattr(hmong_launcher.subprocess, 'run',
                        lambda *args, **kwargs: pytest.fail('Missing FFmpeg must fail before model setup'))
    with pytest.raises(RuntimeError, match=r'FFmpeg.*install_hmong\.bat'):
        hmong_launcher.main(['--check'])


def test_check_missing_models_stays_offline_and_never_reports_pass(tmp_path, monkeypatch, capsys):
    bundle_fixture(tmp_path)
    isolate_launcher(monkeypatch, tmp_path)
    monkeypatch.setattr(hmong_launcher, 'check_dependencies', lambda: None)
    monkeypatch.setattr(hmong_launcher.shutil, 'which', lambda name: '/tools/' + name)
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        if command[-1] == '-version':
            return SimpleNamespace(returncode=0)
        assert command[-1] == '--verify-only', 'Offline --check must never initiate downloads'
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(hmong_launcher.subprocess, 'run', run)
    assert hmong_launcher.main(['--check']) == 1
    output = capsys.readouterr().out
    assert 'Thiếu mô hình' in output and 'PASS:' not in output
    assert len(calls) == 3


def test_native_check_uses_native_manifest_and_never_downloads_or_falls_back_to_f5(tmp_path, monkeypatch, capsys):
    bundle_fixture(tmp_path)
    isolate_launcher(monkeypatch, tmp_path)
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    monkeypatch.setattr(hmong_launcher, 'check_dependencies', lambda: None)
    monkeypatch.setattr(hmong_launcher, 'check_audio_tools', lambda: None)
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        assert command == [sys.executable, str(tmp_path / 'prepare_hmong_native.py'), '--verify-only']
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(hmong_launcher.subprocess, 'run', run)
    assert hmong_launcher.main(['--check']) == 1
    output = capsys.readouterr().out
    assert 'Hmong nhanh thử nghiệm' in output and 'PASS:' not in output
    assert len(calls) == 1


def test_native_setup_downloads_only_native_models_after_failed_verification(tmp_path, monkeypatch, capsys):
    bundle_fixture(tmp_path)
    isolate_launcher(monkeypatch, tmp_path)
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    monkeypatch.setattr(hmong_launcher, 'check_dependencies', lambda: None)
    monkeypatch.setattr(hmong_launcher, 'check_audio_tools', lambda: None)
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=1 if command[-1] == '--verify-only' else 0)
    monkeypatch.setattr(hmong_launcher.subprocess, 'run', run)
    assert hmong_launcher.main(['--setup-only']) == 0
    assert [command for command, _ in calls] == [
        [sys.executable, str(tmp_path / 'prepare_hmong_native.py'), '--verify-only'],
        [sys.executable, str(tmp_path / 'prepare_hmong_native.py')]]
    assert calls[1][1]['check'] is True
    output = capsys.readouterr().out
    assert '580 MB' in output and '30×' in output and 'PASS:' in output
    assert '1,4 GB' not in output


def test_unknown_hmong_backend_fails_before_any_model_preparation(monkeypatch):
    monkeypatch.setenv('HMOOB_BACKEND', 'unknown')
    with pytest.raises(RuntimeError, match='HMOOB_BACKEND'):
        hmong_launcher.selected_backend()
