"""Full portable reassembly preserves public binaries and provenance boundaries."""
import hashlib
import json
from pathlib import Path
import stat
import struct
import zipfile

import pytest

import build_full_update as builder


def source_tree(tmp_path):
    source = tmp_path / 'source'
    contents = {
        'app/app.py': b"app = FastAPI(version='1.11.1')\n",
        'app/launcher.py': b'current launcher',
        'app/worker.py': b'current worker',
        'app/static/index.html': b'current HTML',
        'app/static/app.js': b'current JS',
        'app/static/style.css': b'current CSS',
        'app/.data/jobs/private.json': b'never ship private history',
        'app/voice-library/private.wav': b'never ship decoded voice',
        'app/tests/test_example.py': b'no tests in portable',
        'app/static/private.wav': b'never ship recordings from source',
        'app/static/.data/hidden.js': b'never ship source hidden data',
        'packaging/MO_TOOL.bat': b'current portable launcher',
    }
    contents.update({name: ('current ' + name).encode() for name in builder._ROOT_SOURCE})
    for name, value in contents.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return source


def base_archive(tmp_path, monkeypatch, extra=()):
    base = tmp_path / 'base.zip'
    contents = {name: ('verified base ' + name).encode() for name in builder._REQUIRED_BASE}
    contents['BUILD_INFO.json'] = json.dumps({'version': '1.10.0', 'native_windows_offline_smoke': 'passed'}).encode()
    contents.update({
        'MANIFEST.sha256': b'old manifest of old source',
        'PORTABLE-QA.json': b'{"base_qa": true}',
        'SHARED-MODEL-QA.json': b'{"base_shared_qa": true}',
        'MO_TOOL.bat': b'old launcher',
        'app/app.py': b'old app',
        'app/old_module.py': b'old module not in new source',
        'app/static/old.css': b'old static',
        'app/.data/models/cache/hub/model/public.onnx': b'public weights',
        'app/.data/jobs/old-private.json': b'private job',
        'app/.data/audio/old-private.wav': b'private audio',
        'app/voice-library/voices/private.wav': b'private reference',
        'runtime/Lib/site-packages/.agents/instructions.txt': b'developer metadata',
        '.aws/credentials': b'never ship credentials',
        'THIRD_PARTY_LICENSE.txt': b'base notice',
    })
    with zipfile.ZipFile(base, 'w') as archive:
        for name, value in contents.items():
            archive.writestr('Old-Portable/' + name, value)
        for name, value in extra:
            archive.writestr(name, value)
    monkeypatch.setattr(builder, 'BASE_SHA256', hashlib.sha256(base.read_bytes()).hexdigest())
    return base, contents


def test_full_archive_keeps_verified_binaries_and_encrypted_delivery_not_private_data(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, original = base_archive(tmp_path, monkeypatch)
    output, checksum = builder.build_full(base, tmp_path / 'full.zip', source_root=source)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        root = 'Voice-Studio-1.11.1-Full-Windows-x64/'
        for name in ('runtime/python.exe', 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe',
                     'delivery/voices.vspack', 'delivery/manifest.json', 'install_secure_voices.ps1',
                     'app/.data/models/cache/hub/model/public.onnx', 'THIRD_PARTY_LICENSE.txt'):
            assert archive.read(root + name) == original[name]
        assert archive.read(root + 'app/app.py') == (source / 'app/app.py').read_bytes()
        assert archive.read(root + 'MO_TOOL.bat') == b'current portable launcher'
        names = archive.namelist()
        assert not any('private' in name or '/.aws/' in name or '/.agents/' in name for name in names)
        assert not any(name.endswith(('old.css', 'old_module.py', 'test_example.py')) for name in names)
        assert archive.read(root + 'BASE-1.10-BUILD_INFO.json') == original['BUILD_INFO.json']
        assert archive.read(root + 'BASE-1.10-MANIFEST.sha256') == original['MANIFEST.sha256']
        assert archive.read(root + 'BASE-1.10-PORTABLE-QA.json') == original['PORTABLE-QA.json']
        metadata = json.loads(archive.read(root + 'BUILD_INFO.json'))
        assert metadata['version'] == '1.11.1'
        assert metadata['base_native_windows_offline_smoke'] == 'passed'
        assert metadata['current_native_windows_offline_smoke'] == 'not_run'
        assert metadata['current_gpu_inference_test'] == 'not_run'
        assert metadata['target_30x_guaranteed'] is False
        assert metadata['international_runtime_bundled'] is False
        manifest = archive.read(root + 'MANIFEST.sha256').decode().splitlines()
        for line in manifest:
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(archive.read(root + name)).hexdigest() == digest
        assert len(manifest) == len(names) - 1
    assert checksum.read_text().split()[0] == hashlib.sha256(output.read_bytes()).hexdigest()


def test_changed_base_is_rejected_before_any_output(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    base.write_bytes(base.read_bytes() + b'changed')
    output = tmp_path / 'full.zip'
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        builder.build_full(base, output, source_root=source)
    assert not output.exists() and not list(tmp_path.glob('*.part'))


@pytest.mark.parametrize('name', ['Old-Portable/../escape', '/absolute', 'Old-Portable/app\\escape',
                                  'Old-Portable/C:/escape', 'Second-Root/extra'])
def test_even_hash_verified_archive_has_to_obey_path_and_root_rules(tmp_path, monkeypatch, name):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch, [(name, b'bad')])
    output = tmp_path / 'full.zip'
    with pytest.raises(ValueError):
        builder.build_full(base, output, source_root=source)
    assert not output.exists() and not list(tmp_path.glob('*.part'))


def test_case_colliding_windows_paths_are_rejected(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch, [('Old-Portable/RUNTIME/PYTHON.EXE', b'collision')])
    with pytest.raises(ValueError, match='case-colliding'):
        builder.build_full(base, tmp_path / 'full.zip', source_root=source)


def test_base_symlink_is_rejected_without_extracting_it(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    entry = zipfile.ZipInfo('Old-Portable/link')
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(base, 'a') as archive:
        archive.writestr(entry, '../../private')
    monkeypatch.setattr(builder, 'BASE_SHA256', hashlib.sha256(base.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match='symlinks'):
        builder.build_full(base, tmp_path / 'full.zip', source_root=source)


def test_existing_output_is_never_overwritten(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    output = tmp_path / 'existing.zip'
    output.write_bytes(b'preserve me')
    with pytest.raises(FileExistsError):
        builder.build_full(base, output, source_root=source)
    assert output.read_bytes() == b'preserve me'


def test_missing_runtime_or_delivery_blocks_a_full_package(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    replacement = tmp_path / 'missing.zip'
    with zipfile.ZipFile(base) as incoming, zipfile.ZipFile(replacement, 'w') as outgoing:
        for item in incoming.infolist():
            if not item.filename.endswith('/delivery/voices.vspack'):
                outgoing.writestr(item, incoming.read(item))
    monkeypatch.setattr(builder, 'BASE_SHA256', hashlib.sha256(replacement.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match='missing required files'):
        builder.build_full(replacement, tmp_path / 'full.zip', source_root=source)


def test_source_symlink_cannot_import_external_content(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    private = tmp_path / 'private.txt'
    private.write_text('private source outside checkout')
    (source / 'app/private.py').symlink_to(private)
    with pytest.raises(ValueError, match='symlinks'):
        builder.build_full(base, tmp_path / 'full.zip', source_root=source)


def test_semantic_version_is_read_from_current_source(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    (source / 'app/app.py').write_text("app = FastAPI(version='1.12.0')\n")
    base, _ = base_archive(tmp_path, monkeypatch)
    output, _ = builder.build_full(base, tmp_path / 'full.zip', source_root=source)
    with zipfile.ZipFile(output) as archive:
        info = json.loads(archive.read('Voice-Studio-1.12.0-Full-Windows-x64/BUILD_INFO.json'))
        assert info['version'] == '1.12.0'


def native_tree(tmp_path):
    runtime = tmp_path / 'runtime-native'
    for device in ('cpu', 'cuda'):
        directory = runtime / device
        directory.mkdir(parents=True)
        libraries = {'audiocpp.dll', 'vcruntime140.dll', 'msvcp140.dll', 'vcomp140.dll'}
        if device == 'cuda':
            libraries |= {'cudart64_12.dll', 'cublas64_12.dll', 'cublasLt64_12.dll', 'cufft64_11.dll'}
        checksums = {}
        for name in libraries:
            pe = bytearray(160)
            pe[:2] = b'MZ'
            struct.pack_into('<I', pe, 60, 64)
            pe[64:68] = b'PE\0\0'
            struct.pack_into('<H', pe, 68, 0x8664)
            struct.pack_into('<H', pe, 86, 0x2000)
            struct.pack_into('<H', pe, 88, 0x20b)
            pe[100:100+len(name)] = name.encode()
            (directory / name).write_bytes(pe)
            checksums[name] = hashlib.sha256(pe).hexdigest()
        (directory / 'audiocpp_gguf.exe').write_bytes(b'build-only converter must be omitted')
        (directory / 'native-build.json').write_text(json.dumps({
            'revision': builder.NATIVE_REVISION, 'device': device,
            'families': ['omnivoice', 'voxcpm2'], 'sha256': checksums,
            'cuda_toolkit_major': 12 if device == 'cuda' else None,
            'cuda_architectures': ['61', '75', '86'] if device == 'cuda' else [],
        }))
    data = tmp_path / 'native-model'
    folder = data / 'models/voxcpm2-native'
    folder.mkdir(parents=True)
    model = folder / 'voxcpm2-q8_0.gguf'
    model.write_bytes(b'GGUFsynthetic-test-model-not-inference')
    record = {'schema': 1, 'backend': 'voxcpm_native', 'repository': 'openbmb/VoxCPM2',
              'revision': builder.MODEL_REVISION, 'native_source_revision': builder.NATIVE_REVISION,
              'model_dir': 'voxcpm2-native', 'filename': model.name,
              'sha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'size': model.stat().st_size}
    (data / 'models/voxcpm-native.ready').write_text(json.dumps(record))
    (folder / 'LICENSE-APACHE-2.0.txt').write_text('verified public license fixture')
    return runtime, data


def test_native_package_requires_actual_x64_windows_libraries_and_verified_model(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    runtime, data = native_tree(tmp_path)
    output, _ = builder.build_full(base, tmp_path / 'native-full.zip', source_root=source,
                                   native_root=runtime, native_model=data)
    with zipfile.ZipFile(output) as archive:
        root = 'Voice-Studio-1.11.1-Full-Windows-x64/'
        assert archive.read(root + 'runtime-native/cpu/audiocpp.dll')[:2] == b'MZ'
        assert archive.read(root + 'runtime-native/cuda/cublas64_12.dll')[:2] == b'MZ'
        assert archive.read(root + 'app/.data/models/voxcpm2-native/voxcpm2-q8_0.gguf').startswith(b'GGUF')
        assert root + 'app/.data/models/voxcpm2-native/LICENSE-APACHE-2.0.txt' in archive.namelist()
        assert not any(name.endswith('audiocpp_gguf.exe') for name in archive.namelist())
        metadata = json.loads(archive.read(root + 'BUILD_INFO.json'))
        assert metadata['international_model_bundled'] and metadata['international_runtime_bundled']
        assert metadata['native_cpu_library_bundled'] and metadata['native_cuda_library_bundled']
        assert metadata['current_native_windows_offline_smoke'] == 'not_run'


def test_linux_library_renamed_as_dll_cannot_be_described_as_windows_runtime(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    runtime, data = native_tree(tmp_path)
    library = runtime / 'cpu/audiocpp.dll'
    library.write_bytes(b'\x7fELFnot-a-Windows-library')
    manifest_path = library.parent / 'native-build.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['sha256']['audiocpp.dll'] = hashlib.sha256(library.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='PE x64'):
        builder.build_full(base, tmp_path / 'full.zip', source_root=source,
                           native_root=runtime, native_model=data)


def test_native_model_corruption_blocks_build_before_output(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    runtime, data = native_tree(tmp_path)
    (data / 'models/voxcpm2-native/voxcpm2-q8_0.gguf').write_bytes(b'GGUFcorrupt')
    with pytest.raises(ValueError, match='SHA256/size'):
        builder.build_full(base, tmp_path / 'full.zip', source_root=source,
                           native_root=runtime, native_model=data)
    assert not (tmp_path / 'full.zip').exists()


def test_windows_qa_only_applies_to_exact_source_cpu_dll_and_model(tmp_path, monkeypatch):
    source = source_tree(tmp_path)
    base, _ = base_archive(tmp_path, monkeypatch)
    runtime, data = native_tree(tmp_path)
    overlay, _ = builder._sources(source)
    cpu = json.loads((runtime / 'cpu/native-build.json').read_text())
    model = json.loads((data / 'models/voxcpm-native.ready').read_text())
    report = {'format': 'native-voxcpm-windows-pcm-v1', 'platform': 'win32',
              'native_smoke_passed': True, 'private_reference_audio_included': False,
              'app_source_sha256': builder.application_digest(overlay),
              'native_cpu_sha256': cpu['sha256']['audiocpp.dll'],
              'native_model_sha256': model['sha256'],
              'requests': [{'valid_pcm_audio': True,
                            'execution': {'device': 'cpu', 'backend': 'voxcpm_native'}}] * 3}
    qa = tmp_path / 'Windows-QA.json'
    qa.write_text(json.dumps(report))
    output, _ = builder.build_full(base, tmp_path / 'verified-full.zip', source_root=source,
                                   native_root=runtime, native_model=data, windows_qa=qa)
    with zipfile.ZipFile(output) as archive:
        info = json.loads(archive.read('Voice-Studio-1.11.1-Full-Windows-x64/BUILD_INFO.json'))
        assert info['current_native_windows_offline_smoke'] == 'passed'
        assert info['current_gpu_inference_test'] == 'not_run'
    (source / 'app/worker.py').write_text('different source since the QA report')
    with pytest.raises(ValueError, match='exact source/runtime/model'):
        builder.build_full(base, tmp_path / 'unverified-full.zip', source_root=source,
                           native_root=runtime, native_model=data, windows_qa=qa)


def test_release_splits_round_trip_and_verify_complete_archive(tmp_path):
    source = tmp_path / 'Voice-Studio-1.12.0-Full.zip'
    source.write_bytes(bytes(range(256)) * 4)
    output = builder.split_release(source, tmp_path / 'release', part_bytes=333)
    record = json.loads((output / 'DOWNLOAD-PARTS.json').read_text())
    joined = b''.join((output / part['name']).read_bytes() for part in record['parts'])
    assert joined == source.read_bytes()
    assert len(record['parts']) == 4 and all(part['size'] <= 333 for part in record['parts'])
    assert hashlib.sha256(joined).hexdigest() == record['archive_sha256']
    for part in record['parts']:
        assert hashlib.sha256((output / part['name']).read_bytes()).hexdigest() == part['sha256']
    launcher = (output / 'GHEP_GOI.cmd').read_bytes().decode('ascii')
    assert record['archive_sha256'] in launcher and 'Get-FileHash' in launcher
    assert 'ExecutionPolicy' not in launcher
    assert launcher.index('Get-FileHash') < launcher.index('move /-y')


def test_release_splitting_preserves_existing_outputs(tmp_path):
    source = tmp_path / 'Full.zip'
    source.write_bytes(b'zip data')
    output = tmp_path / 'release'
    output.mkdir()
    (output / 'keep.txt').write_text('existing output')
    with pytest.raises(FileExistsError):
        builder.split_release(source, output, part_bytes=4)
    assert (output / 'keep.txt').read_text() == 'existing output'
