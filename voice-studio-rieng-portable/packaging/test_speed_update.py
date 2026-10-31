"""A code overlay preserves installation data and carries verifiable checksums."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


SPEC = importlib.util.spec_from_file_location('speed_update_builder', Path(__file__).with_name('build_speed_update.py'))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


@pytest.fixture
def source(tmp_path):
    root = tmp_path / 'source'
    files = {
        'app/app.py': "app = FastAPI(version='1.11.1')\n",
        'app/worker.py': '# application source\n',
        'app/system_speech.ps1': '# Windows application source\n',
        'app/static/index.html': '<html>Voice Studio</html>',
        'app/static/app.js': 'console.log("1.11.1");',
        'app/static/style.css': 'body {color:black}',
        'app/static/assets/helpers.js': 'const mode = "Nhanh";',
        'packaging/benchmark_international_packing.py':
            "from pathlib import Path\nAPP = Path(__file__).resolve().parents[1] / 'app'\n",
        'BUILD_INFO.json': '{"version":"1.10.0","do_not_replace":true}',
        'MANIFEST.sha256': 'original installation manifest',
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    return root


def archive_files(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        return {name.removeprefix(builder.ROOT_NAME + '/'): archive.read(name)
                for name in archive.namelist()}


def test_code_update_checksums_metadata_and_existing_installation_files(source, tmp_path):
    output, checksum = builder.build_update(tmp_path / 'update.zip', source_root=source)
    files = archive_files(output)
    for name in ('app/app.py', 'app/worker.py', 'app/system_speech.ps1',
                 'app/static/index.html', 'app/static/app.js', 'app/static/style.css',
                 'app/static/assets/helpers.js'):
        assert files[name] == (source / name).read_bytes()
    assert files['tools/benchmark_international_packing.py'] == (
        source / 'packaging/benchmark_international_packing.py').read_bytes()
    assert 'BUILD_INFO.json' not in files and 'MANIFEST.sha256' not in files
    assert json.loads((source / 'BUILD_INFO.json').read_text())['version'] == '1.10.0'
    assert (source / 'MANIFEST.sha256').read_text() == 'original installation manifest'
    metadata = json.loads(files['UPDATE_INFO.json'])
    assert metadata['version'] == '1.11.1'
    assert metadata['base_source_commit'] == '888d1dbbb7153177dbaa31a213efd8ffc428b012'
    assert metadata['existing_installation_required']
    for key in ('native_runtimes_bundled', 'model_weights_bundled', 'private_voice_data_bundled',
                'standalone_windows_runtime', 'native_windows_qa_run_in_this_session',
                'gpu_qa_run_in_this_session', 'turbo_speed_parity_verified',
                'existing_build_info_and_manifest_replaced', 'real_speech_qa_included'):
        assert metadata[key] is False
    entries = {}
    for line in files[builder.MANIFEST_NAME].decode('utf-8').splitlines():
        digest, name = line.split('  ', 1)
        entries[name] = digest
        assert hashlib.sha256(files[name]).hexdigest() == digest
    assert set(entries) == set(files) - {builder.MANIFEST_NAME}
    assert checksum.read_text() == hashlib.sha256(output.read_bytes()).hexdigest() + '  update.zip\n'
    guide = files['DOC_CAP_NHAT.txt'].decode('utf-8')
    for required in ('MO_TOOL.bat', 'sao lưu', 'thư mục tạm', 'runtime-international',
                     'app\\.data', 'app\\voice-library', 'paragraph_pause=0', '1 tiến trình',
                     'Không có cam kết nhanh ngang Turbo', 'BUILD_INFO.json', 'MANIFEST.sha256'):
        assert required.casefold() in guide.casefold()


def test_private_data_models_tests_and_local_runtimes_are_not_bundled(source, tmp_path):
    excluded = (
        'app/.data/jobs/private.json', 'app/.data/models/model.gguf',
        'app/voice-library/voices/reference.wav', 'app/models/secret.py',
        'app/tests/test_private.py', 'app/__pycache__/app.pyc', 'app/test_secret.py',
        'app/.private.py', 'app/static/.data/private.json', 'app/static/models/model.json',
        'app/static/tests/test.js', 'app/static/.hidden.js', 'app/static/assets/reference.wav',
        'app/static/assets/private.json',
        'runtime/python.exe', 'runtime-international/python.exe', 'runtime-native/cpu/native.dll',
    )
    for name in excluded:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'private sentinel must not leave installation')
    output, _ = builder.build_update(tmp_path / 'safe.zip', source_root=source)
    files = archive_files(output)
    assert all(name not in files for name in excluded)
    assert all(b'private sentinel' not in payload for payload in files.values())
    assert all((source / name).is_file() for name in excluded)


def test_optional_real_speech_report_is_copied_exactly_and_in_manifest(source, tmp_path):
    report = tmp_path / 'cpu-real-speech.json'
    payload = {
        'format': 'international-packing-real-speech-v1',
        'private_reference_audio_included': False,
        'device': 'cpu', 'gtx1060_tested': False,
        'results': [{'language': 'fr', 'throughput_ratio': 1.2}],
    }
    report.write_text(json.dumps(payload), encoding='utf-8')
    output, _ = builder.build_update(tmp_path / 'with-qa.zip', report, source_root=source)
    files = archive_files(output)
    assert files[builder.QA_NAME] == report.read_bytes()
    metadata = json.loads(files['UPDATE_INFO.json'])
    assert metadata['real_speech_qa_included'] and metadata['qa_report'] == builder.QA_NAME
    assert not metadata['native_windows_qa_run_in_this_session']
    assert not metadata['turbo_speed_parity_verified']
    assert builder.QA_NAME in files[builder.MANIFEST_NAME].decode()


@pytest.mark.parametrize('payload', [b'not JSON', b'[]', b'{"format":"other-report"}',
                                    b'{"format":"international-packing-real-speech-v1","private_reference_audio_included":true,"results":[{}]}'])
def test_invalid_or_wrong_qa_report_is_rejected_before_writing(source, tmp_path, payload):
    report = tmp_path / 'invalid.json'
    report.write_bytes(payload)
    output = tmp_path / 'not-created.zip'
    with pytest.raises(ValueError, match='QA report'):
        builder.build_update(output, report, source_root=source)
    assert not output.exists() and not Path(str(output) + '.sha256').exists()


@pytest.mark.parametrize('version', ['1.10.0', '1.11.0', '9.9.9'])
def test_wrong_source_version_does_not_create_update(source, tmp_path, version):
    (source / 'app/app.py').write_text(f"app = FastAPI(version={version!r})\n")
    output = tmp_path / 'wrong-version.zip'
    with pytest.raises(ValueError, match='version 1.11.1'):
        builder.build_update(output, source_root=source)
    assert not output.exists()


@pytest.mark.parametrize('relative,is_directory', [('app/external.py', False),
                                                  ('app/static/external.js', False),
                                                  ('app/static/external-assets', True)])
def test_symlinks_to_external_private_files_or_directories_are_rejected(source, tmp_path, relative, is_directory):
    external = tmp_path / ('private-directory' if is_directory else 'private-file')
    if is_directory:
        external.mkdir()
        (external / 'private.js').write_text('private data')
    else:
        external.write_text('private data')
    try:
        (source / relative).symlink_to(external, target_is_directory=is_directory)
    except (OSError, NotImplementedError):
        pytest.skip('Symlinks are not supported by this platform')
    output = tmp_path / 'unsafe.zip'
    with pytest.raises(ValueError, match='symlink'):
        builder.build_update(output, source_root=source)
    assert not output.exists()


def test_existing_output_or_checksum_is_preserved(source, tmp_path):
    output = tmp_path / 'existing.zip'
    output.write_bytes(b'previous archive')
    with pytest.raises(FileExistsError):
        builder.build_update(output, source_root=source)
    assert output.read_bytes() == b'previous archive'
    other = tmp_path / 'other.zip'
    checksum = Path(str(other) + '.sha256')
    checksum.write_text('previous checksum')
    with pytest.raises(FileExistsError):
        builder.build_update(other, source_root=source)
    assert not other.exists() and checksum.read_text() == 'previous checksum'


def test_cli_output_and_benchmark_location_match_update_layout(source, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(builder, 'SOURCE_ROOT', source)
    output = tmp_path / 'cli.zip'
    builder.main(['--output', str(output)])
    assert capsys.readouterr().out.splitlines() == [str(output), str(output) + '.sha256']
    files = archive_files(output)
    with zipfile.ZipFile(output) as archive:
        extracted = tmp_path / 'extracted'
        archive.extractall(extracted)
    installed = extracted / builder.ROOT_NAME
    namespace = {'__file__': str(installed / 'tools/benchmark_international_packing.py')}
    exec(files['tools/benchmark_international_packing.py'], namespace)
    assert namespace['APP'] == installed / 'app'


def test_missing_static_asset_rejects_incomplete_source(source, tmp_path):
    (source / 'app/static/app.js').unlink()
    with pytest.raises(ValueError, match='static asset'):
        builder.build_update(tmp_path / 'incomplete.zip', source_root=source)
