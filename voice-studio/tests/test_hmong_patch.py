"""Source-only repair validation, transaction safety and personal data preservation."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / 'packaging'
sys.path.insert(0, str(PACKAGING))
import apply_hmong_update as updater
import build_hmong_patch as builder


@pytest.fixture
def repair(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    for name in (*updater.REQUIRED_PAYLOAD, *updater.BASE_ASSETS):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    output = tmp_path / 'output'
    report = builder.build(source, output)
    extracted = tmp_path / 'patch'
    with zipfile.ZipFile(output / report['archive']) as archive:
        archive.extractall(extracted)
    install = tmp_path / 'portable installation'
    app = install / 'voice-studio-hmong'
    for name in updater.BASE_REQUIRED:
        target = app / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'# original 1.5.0 source\n')
    (app / 'studio_variant.py').write_text("APP_VERSION = '1.5.0-hmong' if IS_HMONG else '3.6.2'\n", encoding='utf-8')
    for name in updater.BASE_ASSETS:
        target = app / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    for name in ('runtime/python.exe', 'MO_HMONG_NHANH.bat'):
        target = install / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'original portable runtime or launcher')
    for name in ('models/native.bin', 'voices/personal.wav', 'jobs/running.json', 'server.lock'):
        target = app / '.data' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'personal data: ' + name.encode())
    return {'source': source, 'output': output, 'report': report, 'extracted': extracted,
            'patch': extracted / 'hmong-update', 'root': install, 'app': app}


def source_snapshot(app):
    return {name: (app / name).read_bytes() if (app / name).is_file() else None
            for name in updater.REQUIRED_PAYLOAD}


def private_snapshot(app):
    return {str(path.relative_to(app / '.data')): path.read_bytes()
            for path in (app / '.data').rglob('*')
            if path.is_file() and 'update-backups' not in path.parts}


def test_archive_is_deterministic_and_contains_only_the_repair(repair, tmp_path):
    output = repair['output']
    archive = output / repair['report']['archive']
    second = tmp_path / 'another build'
    report = builder.build(repair['source'], second)
    assert (second / report['archive']).read_bytes() == archive.read_bytes()
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report['sha256']
    assert archive.with_suffix('.zip.sha256').read_text().startswith(report['sha256'])
    assert json.loads((output / 'patch-build.json').read_text())['runtime_included'] is False
    with zipfile.ZipFile(archive) as zipped:
        expected = {'SUA_LOI_MO_TOOL.bat', 'hmong-update/apply_update.py', 'hmong-update/manifest.json'}
        expected.update('hmong-update/files/' + name for name in updater.REQUIRED_PAYLOAD)
        assert set(zipped.namelist()) == expected
        manifest = json.loads(zipped.read('hmong-update/manifest.json'))
        for name, record in manifest['files'].items():
            raw = zipped.read('hmong-update/files/' + name)
            assert len(raw) == record['bytes']
            assert hashlib.sha256(raw).hexdigest() == record['sha256']


def test_update_preserves_personal_data_and_only_backs_up_changed_sources(repair):
    app = repair['app']
    before = source_snapshot(app)
    private = private_snapshot(app)
    cache = app / '__pycache__'
    cache.mkdir()
    (cache / 'app.cpython-312.pyc').write_bytes(b'outdated app cache')
    (cache / 'hmong_native.cpython-312.pyc').write_bytes(b'unchanged native cache')
    result = updater.apply_update(repair['root'], repair['patch'])
    assert result['status'] == 'updated'
    assert updater.read_version(app / 'studio_variant.py') == '1.5.1'
    assert private_snapshot(app) == private
    backup = Path(result['backup'])
    assert backup.parent == app / '.data/update-backups'
    backed_up = {str(path.relative_to(backup)) for path in backup.rglob('*') if path.is_file()}
    assert backed_up == {name for name in result['changed'] if before[name] is not None}
    for name in backed_up:
        assert (backup / name).read_bytes() == before[name]
    assert not (cache / 'app.cpython-312.pyc').exists()
    assert (cache / 'hmong_native.cpython-312.pyc').read_bytes() == b'unchanged native cache'


def test_reapplying_is_idempotent_and_verify_only_does_not_write(repair):
    updater.apply_update(repair['root'], repair['patch'])
    backups = list((repair['app'] / '.data/update-backups').iterdir())
    assert updater.apply_update(repair['root'], repair['patch'])['status'] == 'already-current'
    assert updater.apply_update(repair['root'], repair['patch'], verify_only=True)['status'] == 'verified'
    assert list((repair['app'] / '.data/update-backups').iterdir()) == backups


def test_verify_only_rejects_an_unpatched_install_without_writing(repair):
    before = source_snapshot(repair['app'])
    with pytest.raises(RuntimeError, match='differs'):
        updater.apply_update(repair['root'], repair['patch'], verify_only=True)
    assert source_snapshot(repair['app']) == before
    assert not (repair['app'] / '.data/update-backups').exists()


@pytest.mark.parametrize('corruption', ['payload', 'checksum', 'traversal', 'asset'])
def test_all_validation_finishes_before_any_write(repair, corruption):
    before = source_snapshot(repair['app'])
    private = private_snapshot(repair['app'])
    manifest_path = repair['patch'] / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if corruption == 'payload':
        (repair['patch'] / 'files/app.py').write_bytes(b'corrupted payload')
    elif corruption == 'asset':
        (repair['app'] / updater.BASE_ASSETS[1]).write_bytes(b'wrong default voice')
    else:
        if corruption == 'checksum':
            manifest['files']['studio_variant.py']['sha256'] = '0' * 64
        else:
            manifest['files']['../.data/jobs/running.json'] = {'bytes': 1, 'sha256': '0' * 64}
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(RuntimeError):
        updater.apply_update(repair['root'], repair['patch'])
    assert source_snapshot(repair['app']) == before
    assert private_snapshot(repair['app']) == private
    assert not (repair['app'] / '.data/update-backups').exists()


def test_an_unsupported_base_is_rejected_without_writing(repair):
    (repair['app'] / 'studio_variant.py').write_text("APP_VERSION = '1.4.0-hmong'\n")
    before = source_snapshot(repair['app'])
    with pytest.raises(RuntimeError, match='Unsupported'):
        updater.apply_update(repair['root'], repair['patch'])
    assert source_snapshot(repair['app']) == before
    assert not (repair['app'] / '.data/update-backups').exists()


def test_replacement_failure_rolls_back_all_previously_changed_files(repair, monkeypatch):
    before = source_snapshot(repair['app'])
    private = private_snapshot(repair['app'])
    original = updater.atomic_write
    calls = 0

    def fail_once(path, raw):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError('simulated replacement failure')
        original(path, raw)

    monkeypatch.setattr(updater, 'atomic_write', fail_once)
    with pytest.raises(OSError, match='simulated'):
        updater.apply_update(repair['root'], repair['patch'])
    assert source_snapshot(repair['app']) == before
    assert private_snapshot(repair['app']) == private


def test_linked_install_target_is_rejected_before_any_write(repair, tmp_path):
    outside = tmp_path / 'outside.py'
    outside.write_bytes(b'keep this file')
    target = repair['app'] / 'app.py'
    target.unlink()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip('This account cannot create symbolic links.')
    with pytest.raises(RuntimeError, match='Linked'):
        updater.apply_update(repair['root'], repair['patch'])
    assert outside.read_bytes() == b'keep this file'
    assert not (repair['app'] / '.data/update-backups').exists()


def test_persistently_locked_target_does_not_prevent_earlier_files_from_rolling_back(repair, monkeypatch):
    before = source_snapshot(repair['app'])
    original = updater.atomic_write

    def locked_target(path, raw):
        if path.name == 'bundle_check.py':
            raise PermissionError('simulated Windows sharing lock')
        original(path, raw)

    monkeypatch.setattr(updater, 'atomic_write', locked_target)
    with pytest.raises(PermissionError, match='sharing lock'):
        updater.apply_update(repair['root'], repair['patch'])
    assert source_snapshot(repair['app']) == before


def test_extracted_updater_runs_standalone_with_no_launch(repair):
    result = subprocess.run([
        sys.executable, str(repair['patch'] / 'apply_update.py'),
        '--root', str(repair['root']), '--no-launch',
    ], cwd=repair['root'].parent, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS:' in result.stdout
    result = subprocess.run([
        sys.executable, str(repair['patch'] / 'apply_update.py'),
        '--root', str(repair['root']), '--verify-only',
    ], cwd=repair['root'].parent, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'verified' in result.stdout


@pytest.mark.parametrize('linked_folder', ['.data', '__pycache__'])
def test_linked_backup_or_cache_directory_is_rejected_before_changes(repair, tmp_path, linked_folder):
    before = source_snapshot(repair['app'])
    directory = repair['app'] / linked_folder
    outside = tmp_path / 'external directory'
    if directory.exists():
        directory.rename(outside)
    else:
        outside.mkdir()
    try:
        directory.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('This account cannot create directory symbolic links.')
    with pytest.raises(RuntimeError, match='Linked'):
        updater.apply_update(repair['root'], repair['patch'])
    assert source_snapshot(repair['app']) == before
    assert not (outside / 'update-backups').exists()
