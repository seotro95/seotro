"""Complete-bundle integrity and post-QA publication boundaries."""
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

import build_complete_bundle as builder


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def write_tree(root, files):
    for name, payload in files.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)


def fixture(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    current = {name: ('current ' + name).encode() for name in builder.full._ROOT_SOURCE}
    current.update({'app/app.py': b"app = FastAPI(version='1.12.2')\n",
                    'app/launcher.py': b'current launcher', 'app/native_locale.py': b'CURRENT_LOCALE=True\n',
                    'app/static/index.html': b'current html', 'app/static/app.js': b'current js',
                    'app/static/style.css': b'current css', 'packaging/MO_TOOL.bat': b'current launcher bat',
                    'app/.data/jobs/private.json': b'never include',
                    'app/voice-library/private.wav': b'never include', 'app/test_hidden.py': b'never include'})
    current['HUONG_DAN_CAN_MOC.txt'] = b'Consult PORTABLE-QA.json for timing instructions.\n'
    write_tree(source, current)
    original = {name: ('retained ' + name).encode() for name in builder.clean._REQUIRED}
    original.update({'BUILD_INFO.json': json.dumps({'version': '1.12.1', 'encrypted_private_pack_bundled': True}).encode(),
                     'runtime/Lib/site-packages/numpy-2.0.dist-info/METADATA': b'Name: numpy\nVersion: 2.0\n',
                     'runtime/Lib/site-packages/numpy-2.0.dist-info/LICENSE': b'license remains',
                     'app/obsolete.py': b'old module must disappear',
                     'runtime/Lib/test/old.py': b'known junk', 'DOC_TRUOC.md': b'old guide'})
    original['MANIFEST.sha256'] = builder._manifest_bytes({name: sha(value) for name, value in original.items()
                                                         if name != 'MANIFEST.sha256'})
    base = tmp_path / 'base.zip'
    with zipfile.ZipFile(base, 'x') as archive:
        for name, value in original.items(): archive.writestr(builder.clean.SOURCE_NAME + '/' + name, value)
    extras = tmp_path / 'extras'
    extra = {'EXTRA-PACK-OWNER.json': builder._json(builder.models.OWNER),
             'EXTRA-MODEL-PINS.json': b'{"pins":"verified"}', 'EXTRA-MODEL-CPU-QA.json': b'{"actual":true}',
             'BUNDLED-QWEN-PACKAGES.txt': b'torch==2.8.0+cpu\n', 'runtime-qwen/python.exe': b'isolated runtime',
             'runtime-qwen/VOICE-STUDIO-QWEN.json': b'{"cpu":true}',
             'app/.data/models/omnivoice/model.gguf': b'omni public weights',
             'app/.data/models/omnivoice/LICENSE': b'omni license',
             'app/.data/models/native-asr/model.bin': b'asr public weights',
             'app/.data/models/qwen-customvoice/model.safetensors': b'qwen custom',
             'app/.data/models/qwen-base/model.safetensors': b'qwen base'}
    extra.update({name: b'{"marker":true}' for name in builder.EXTRA_MARKERS})
    extra[builder.EXTRA_MANIFEST] = builder._manifest_bytes({name: sha(value) for name, value in extra.items()})
    write_tree(extras, extra)
    # Assembly must invoke the real model-specific verifier. These synthetic
    # weights cannot pass model checks; the corresponding module tests cover them.
    validations = []
    monkeypatch.setattr(builder.models, 'validate_qa', lambda root, report: validations.append('qa'))
    monkeypatch.setattr(builder.models, 'validate_prepared_models', lambda root: validations.append('models'))
    return source, original, base, extras, validations


def assemble(tmp_path, monkeypatch):
    source, original, base, extras, validations = fixture(tmp_path, monkeypatch)
    stage = tmp_path / 'Voice-Studio-1.12.2-Full-Windows-x64'
    builder.stage(base, extras, stage, source_root=source, _expected_source_sha256=builder.clean.file_sha256(base))
    return stage, original, validations


def test_stage_uses_current_app_preserves_assets_and_labels_old_qa(tmp_path, monkeypatch):
    stage, original, validations = assemble(tmp_path, monkeypatch)
    assert validations == ['qa', 'models']
    assert (stage / 'app/native_locale.py').read_bytes() == b'CURRENT_LOCALE=True\n'
    assert b'1.12.2' in (stage / 'app/app.py').read_bytes()
    assert not (stage / 'app/obsolete.py').exists()
    assert not (stage / 'runtime/Lib/test/old.py').exists()
    assert not (stage / 'app/.data/jobs').exists()
    assert not (stage / 'app/voice-library').exists()
    for name in ('runtime/python.exe', 'runtime-native/cuda/audiocpp.dll', 'delivery/voices.vspack',
                 'app/.data/models/voxcpm2-native/voxcpm2-q8_0.gguf', 'ffmpeg/bin/ffmpeg.exe'):
        assert (stage / name).read_bytes() == original[name]
    assert not (stage / 'WINDOWS-NATIVE-VOXCPM-QA.json').exists()
    assert (stage / 'INHERITED-1.12.1-WINDOWS-NATIVE-VOXCPM-QA.json').is_file()
    info = json.loads((stage / 'BUILD_INFO.json').read_bytes())
    assert info['version'] == '1.12.2'
    assert info['windows_complete_package_qa'] == 'at-assembly-not-run'
    assert info['gpu_inference_test'] == 'not_run'
    assert not info['target_30x_guaranteed']
    assert 'numpy==2.0' in (stage / 'BUNDLED-PACKAGES.txt').read_text()
    assert (stage / 'requirements-runtime.txt').read_bytes().startswith(b'# Build recipe only;')
    timing = (stage / 'HUONG_DAN_CAN_MOC.txt').read_bytes()
    assert b'PORTABLE-QA.json' not in timing
    assert b'THONG_TIN/FINAL-WINDOWS-QA/WINDOWS-COMPLETE-QA.json' in timing
    guide = (stage / 'DOC_TRUOC.txt').read_text(encoding='utf-8')
    assert 'OmniVoice đang chọn\nvà dùng 8 bước' in guide
    assert 'VoxCPM2 native và dùng 4 bước' in guide
    files = builder._tree(stage)
    records = builder._parse_manifest((stage / 'MANIFEST.sha256').read_bytes())
    assert set(records) == set(files) - {builder.OWNER, 'MANIFEST.sha256'}
    assert all(builder.clean.file_sha256(files[name]) == value for name, value in records.items())


def test_archive_ignores_test_jobs_audio_logs_and_includes_exact_inventory(tmp_path, monkeypatch):
    stage, _, _ = assemble(tmp_path, monkeypatch)
    write_tree(stage, {'app/.data/jobs/private.json': b'private job', 'app/.data/audio/speech.wav': b'private speech',
                       'qa-audio/ko.wav': b'qa speech', 'runtime/Lib/__pycache__/generated.pyc': b'new cache'})
    qa = tmp_path / 'qa'
    write_tree(qa, {'COMPLETE-WINDOWS-QA.json': b'{"actual_windows":true}', 'audio/voice.wav': b'never publish',
                    'session.log': b'never publish'})
    output = tmp_path / 'full.zip'
    builder.archive(stage, output, qa_dir=qa)
    with zipfile.ZipFile(output) as archive:
        files = {name.split('/', 1)[1]: archive.read(name) for name in archive.namelist()}
    assert builder.OWNER not in files
    assert not any(name.startswith(('app/.data/jobs/', 'app/.data/audio/', 'qa-audio/')) for name in files)
    assert 'THONG_TIN/FINAL-WINDOWS-QA/COMPLETE-WINDOWS-QA.json' in files
    assert not any(name.endswith(('.wav', '.log', '.pyc')) for name in files)
    records = builder._parse_manifest(files['MANIFEST.sha256'])
    assert set(records) == set(files) - {'MANIFEST.sha256'}
    assert all(sha(files[name]) == digest for name, digest in records.items())
    assert Path(str(output) + '.sha256').read_text().split()[0] == builder.clean.file_sha256(output)


@pytest.mark.parametrize('name', ['app/native_locale.py', 'delivery/voices.vspack', 'MANIFEST.sha256'])
def test_archive_rejects_post_qa_mutation(tmp_path, monkeypatch, name):
    stage, _, _ = assemble(tmp_path, monkeypatch)
    (stage / name).write_bytes(b'altered after assembly')
    output = tmp_path / 'full.zip'
    with pytest.raises(ValueError, match='mismatch'): builder.archive(stage, output)
    assert not output.exists()


def test_manifest_covers_extras_unknown_paths_and_all_bytes(tmp_path, monkeypatch):
    source, _, base, extras, _ = fixture(tmp_path, monkeypatch)
    options = {'source_root': source, '_expected_source_sha256': builder.clean.file_sha256(base)}
    (extras / 'app/.data/models/qwen-base/model.safetensors').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='Extra-model SHA256 mismatch'):
        builder.stage(base, extras, tmp_path / 'stage', **options)
    assert not (tmp_path / 'stage').exists()
    (extras / 'unlisted.txt').write_bytes(b'unknown')
    with pytest.raises(ValueError, match='exactly'):
        builder.stage(base, extras, tmp_path / 'stage', **options)


def test_unknown_manifested_extra_path_is_rejected(tmp_path, monkeypatch):
    source, _, base, extras, _ = fixture(tmp_path, monkeypatch)
    name = 'app/.data/jobs/private.json'
    write_tree(extras, {name: b'private'})
    records = builder._parse_manifest((extras / builder.EXTRA_MANIFEST).read_bytes())
    records[name] = sha(b'private'); (extras / builder.EXTRA_MANIFEST).write_bytes(builder._manifest_bytes(records))
    with pytest.raises(ValueError, match='Unknown extra-model artifact'):
        builder.stage(base, extras, tmp_path / 'stage', source_root=source,
                      _expected_source_sha256=builder.clean.file_sha256(base))


def test_stage_verifies_even_discarded_original_bytes(tmp_path, monkeypatch):
    source, original, base, extras, _ = fixture(tmp_path, monkeypatch)
    original['runtime/Lib/test/old.py'] = b'changed without updating manifest'
    base.unlink()
    with zipfile.ZipFile(base, 'x') as archive:
        for name, value in original.items(): archive.writestr(builder.clean.SOURCE_NAME + '/' + name, value)
    with pytest.raises(ValueError, match='Source manifest SHA256 mismatch'):
        builder.stage(base, extras, tmp_path / 'stage', source_root=source,
                      _expected_source_sha256=builder.clean.file_sha256(base))
    assert not (tmp_path / 'stage').exists()
    assert not list(tmp_path.glob('*.assembling'))


def test_existing_outputs_symlinks_and_wrong_source_pin_are_rejected(tmp_path, monkeypatch):
    source, _, base, extras, _ = fixture(tmp_path, monkeypatch)
    stage = tmp_path / 'stage'
    with pytest.raises(ValueError, match='Pinned full source ZIP'):
        builder.stage(base, extras, stage, source_root=source)
    stage.mkdir(); (stage / 'keep.txt').write_bytes(b'keep')
    with pytest.raises(FileExistsError): builder.stage(base, extras, stage, source_root=source)
    assert (stage / 'keep.txt').read_bytes() == b'keep'
    link = extras / 'runtime-qwen/link'
    try: link.symlink_to(extras / 'runtime-qwen/python.exe')
    except OSError: pytest.skip('Symlink creation unavailable')
    with pytest.raises(ValueError, match='Symlink'):
        builder.stage(base, extras, tmp_path / 'new', source_root=source,
                      _expected_source_sha256=builder.clean.file_sha256(base))


def test_case_collisions_and_windows_unsafe_extra_names_rejected(tmp_path):
    for name in ('../escape', 'runtime/CON.txt', 'runtime/a:stream', 'runtime/a.', 'runtime\\evil'):
        with pytest.raises(ValueError): builder._safe_name(name)
    with pytest.raises(ValueError, match='Duplicate'):
        builder._parse_manifest((sha(b'a') + '  runtime/A\n' + sha(b'b') + '  runtime/a\n').encode())


def test_extras_cleanup_retains_runtime_distributions_licenses_and_js(tmp_path, monkeypatch):
    source, _, base, extras, _ = fixture(tmp_path, monkeypatch)
    additions = {
        'runtime-qwen/Lib/site-packages/gradio/front/app.js.map': b'removable js map',
        'runtime-qwen/Lib/site-packages/gradio/front/app.css.map': b'removable css map',
        'runtime-qwen/Doc/html/index.html': b'offline documentation',
        'runtime-qwen/Lib/test/test_audio.py': b'stdlib test',
        'runtime-qwen/Lib/idlelib/idle_test/test_run.py': b'IDLE test',
        'runtime-qwen/Lib/site-packages/example/__pycache__/a.pyc': b'generated cache',
        'runtime-qwen/Lib/site-packages/gradio/front/app.js': b'required browser code',
        'runtime-qwen/Lib/site-packages/gradio-5.49.1.dist-info/METADATA': b'Name: gradio\nVersion: 5.49.1\n',
        'runtime-qwen/Lib/site-packages/gradio-5.49.1.dist-info/licenses/LICENSE': b'retained license',
        'runtime-qwen/Lib/site-packages/other/data.map': b'package map data',
        'runtime-qwen/Lib/site-packages/numpy/testing/helper.py': b'needed testing helper',
    }
    write_tree(extras, additions)
    records = builder._parse_manifest((extras / builder.EXTRA_MANIFEST).read_bytes())
    records.update({name: sha(value) for name, value in additions.items()})
    (extras / builder.EXTRA_MANIFEST).write_bytes(builder._manifest_bytes(records))
    stage = tmp_path / 'stage'
    builder.stage(base, extras, stage, source_root=source, _expected_source_sha256=builder.clean.file_sha256(base))
    removed = {name for name in additions if builder._extra_removal_reason(name)}
    for name, payload in additions.items():
        if name in removed: assert not (stage / name).exists()
        else: assert (stage / name).read_bytes() == payload
    report = json.loads((stage / 'CLEANUP-REPORT.json').read_bytes())
    assert report['extra_removed_file_count'] == len(removed) == 6
    assert {row['path'] for row in report['extra_removed_files']} == removed
    assert all(row['sha256'] == sha(additions[row['path']]) for row in report['extra_removed_files'])
    assert report['extra_removed_uncompressed_bytes'] == sum(len(additions[name]) for name in removed)
    assert report['total_removed_file_count'] == report['removed_file_count'] + len(removed)
    builder.archive(stage, tmp_path / 'cleaned-extra.zip')


def test_discarded_extra_source_map_still_requires_valid_sha256(tmp_path, monkeypatch):
    source, _, base, extras, _ = fixture(tmp_path, monkeypatch)
    name = 'runtime-qwen/Lib/site-packages/gradio/front/app.js.map'
    write_tree(extras, {name: b'changed after source manifest'})
    records = builder._parse_manifest((extras / builder.EXTRA_MANIFEST).read_bytes())
    records[name] = sha(b'original map')
    (extras / builder.EXTRA_MANIFEST).write_bytes(builder._manifest_bytes(records))
    with pytest.raises(ValueError, match='Extra-model SHA256 mismatch'):
        builder.stage(base, extras, tmp_path / 'stage', source_root=source,
                      _expected_source_sha256=builder.clean.file_sha256(base))
    assert not (tmp_path / 'stage').exists()
