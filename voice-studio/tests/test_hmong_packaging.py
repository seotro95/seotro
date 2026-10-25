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
    for name in ('app.py', 'worker.py', 'bundle_check.py', 'caption_markers.py', 'runtime_instance.py',
                 'character_cast.py', 'longform.py', 'reference_quality.py', 'hmong_acceleration.py',
                 'hmong_engine.py', 'hmong_expression.py', 'hmong_f5.py', 'hmong_health.py', 'voice_errors.py',
                 'hmong_native.py', 'hmong_native_models.py', 'prepare_hmong_native.py',
                 'hmong_reference.py', 'hmong_text.py', 'hmong_assets.py', 'prepare_hmong.py',
                 'hmong_launcher.py', 'studio_variant.py'):
        (root / name).write_text('# app\n', encoding='utf-8')
    for name in ('HMONG-README.md', 'requirements-hmong.txt'):
        (root / name).write_text('Hmong-only instructions\n', encoding='utf-8')
    for name in ('README.md', 'requirements.txt', 'requirements-qwen.txt', 'requirements-tested.txt',
                 'install.bat', 'start.bat', 'download_models.bat', 'VALIDATION.md'):
        (root / name).write_text('unrelated Vietnamese environment\n', encoding='utf-8')
    for name in ('docs/HMONG-NATIVE.md', 'docs/HUONG-DAN-HMONG.md', 'docs/HUONG-DAN-HMONG.html', 'static/app.js', 'static/text-import.js', 'assets/hmong/female.wav', 'assets/hmong/male.wav',
                 'assets/hmong/source-female.mp3', 'assets/hmong/source-male.mp3',
                 'assets/hmong/voices.json', 'assets/hmong/additional-voices.json',
                 'assets/hmong/source-ngoc-huyen.mp3', 'assets/hmong/ngoc-huyen.wav',
                 'assets/hmong/source-female-3.mp3', 'assets/hmong/female-3.wav', '.data/voices/personal.wav',
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
    for name in ('additional-voices.json', 'source-ngoc-huyen.mp3', 'ngoc-huyen.wav',
                 'source-female-3.mp3', 'female-3.wav'):
        assert (output / 'assets/hmong' / name).is_file()
    assert (output / 'static/text-import.js').is_file()
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
    assert (output / 'docs/HUONG-DAN-HMONG.md').is_file()
    assert (output / 'docs/HUONG-DAN-HMONG.html').is_file()
    assert (output / 'hmong_health.py').is_file()
    assert (output / 'voice_errors.py').is_file()
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
    root = tmp_path / 'Voice-Studio-Hmong-1.6.4'
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
    names = ('fresh-start.json', 'native-smoke.json', 'f5-smoke.json', 'browser-smoke.json', 'model-sources.json',
             'first-run-male.wav', 'first-run-female.wav',
             'external-english-reference.wav', 'external-clone-reference.wav',
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
    caption = {**copy.deepcopy(cases[0]), 'case': 'caption_metadata_as_txt',
               'job_id': 'caption-qa', 'success': True, 'input_format': 'txt',
               'text': ('\ufeff1\n"00:04:28,533 --> 00:04:29,333"\nNyob zoo.\n'
                        '2\n99:59.500 --> 100:00.300\nKuv muaj 2 tug me nyuam.\n'),
               'exported_spoken_text': 'Nyob zoo. Kuv muaj ob tug me nyuam.',
               'timestamps_not_spoken': True, 'cue_indices_not_spoken': True,
               'continuous_txt_duration': True}
    clone_identity = hashlib.sha256(json.dumps({'version': 1, 'audio_sha256': 'f' * 64,
        'transcript': ''}, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode('utf-8')).hexdigest()
    clone = {**copy.deepcopy(cases[0]), 'case': 'external_english_reference_to_hmong',
             'job_id': 'clone-qa', 'voice_id': 'a' * 32, 'post_voice_id': 'a' * 32,
             'speaker': None, 'success': True, 'source_language': 'en', 'output_language': 'mww',
             'reference_conditioning': 'audio', 'no_transcript': True,
             'cross_language_reference': True, 'auto_selected': True,
             'source_sha256': 'e' * 64, 'reference_audio_sha256': 'f' * 64,
             'reference_seconds': 5, 'independent_reference_fingerprint': clone_identity,
             'hmong_reference_fingerprint': clone_identity, 'default_fallback': False,
             'text': 'Nyob zoo. Ua tsaug rau koj mloog.',
             'perceptual_similarity_evaluated': False}
    additional_expected = packaging.expected_additional_reference_fingerprints()
    metadata = json.loads((PACKAGING.parent / 'assets/hmong/additional-voices.json').read_text(encoding='utf-8'))
    additional = {ident: {**copy.deepcopy(cases[0]),
        'case': 'additional_preset_' + ident, 'voice_id': ident, 'post_voice_id': ident,
        'speaker': ident, 'job_id': 'additional-' + ident, 'success': True,
        'hmong_reference_fingerprint': additional_expected[ident],
        'source_sha256': metadata[ident]['sha256'],
        'reference_audio_sha256': metadata[ident]['reference_sha256'],
        'reference_conditioning': 'audio', 'no_transcript': True,
        'preset_button_checked': True, 'full_source_preview_checked': True}
        for ident in additional_expected}
    srt_only = {**copy.deepcopy(cases[0]), 'case': 'quoted_217_srt_speech_only',
        'job_id': 'srt-only-217', 'success': True, 'input_format': 'srt', 'subtitle_timing': False,
        'text': '"217\n00:06:07,200 --> 00:06:08,400\nTae-yong cov ntaub ntawv tus kheej "',
        'exported_spoken_text': 'Tae-yong cov ntaub ntawv tus kheej',
        'generated_srt': '1\n00:00:00,000 --> 00:00:01,000\nTae-yong cov ntaub ntawv tus kheej\n',
        'generated_timing_checked': True, 'timestamps_not_spoken': True,
        'cue_indices_not_spoken': True, 'continuous_srt_duration': True}
    return {'success': True, 'platform': 'win32', 'native_windows_validation': True,
            'real_ui_synthesis': True, 'engine': 'hmong_native',
            'cloned_filter_library_selection': True, 'cross_panel_selection': True,
            'hyphenated_text_preserved': True,
            'caption_metadata': caption,
            'external_clone': clone,
            'initial_voice_id': 'hmong-female-3',
            'expected_additional_reference_fingerprints': additional_expected,
            'additional_presets': additional,
            'srt_speech_only': srt_only,
            'click_recovery': {'success': True, 'real_ui_post': True, 'responses_mocked': False,
                'ui_entrypoint': '#generate', 'invalid_text': 'Nyob zoo https://example.com.',
                'request_text': 'Nyob zoo https://example.com.', 'request_voice_id': 'hmong-male',
                'request_language': 'mww', 'http_status': 422, 'request_count': 1,
                'error_detail': 'Write numbers as Hmong words.',
                'inline_error': 'Write numbers as Hmong words.',
                'output_error': 'Write numbers as Hmong words.',
                'output_error_title': 'Chưa tạo được bản thu',
                'inline_error_visible': True, 'output_error_visible': True,
                'button_unlocked': True, 'draft_preserved': True,
                'recovery_case': 'main_male_button', 'recovery_job_id': cases[0]['job_id'],
                'recovered_audio_sha256': cases[0]['sha256'], 'recovery_succeeded': True},
            'runtime': {'version': packaging.VERSION + '-hmong', 'backend': 'hmong_native'},
            'browser': {'channel': 'msedge', 'version': '142.0', 'responses_mocked': False},
            'script_sha256': hashlib.sha256((PACKAGING / 'browser_hmong_portable.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            'expected_reference_fingerprints': expected,
            'features_1_6': {'longform': {'success': True, 'million_character_editor': True,
                'million_character_synthesis_performed': False, 'real_archive': True,
                'chapter_selection': True, 'audio_playback_checked': True, 'download_verified': True,
                'archive_job_id': 'chapter-qa', 'archive_sha256': 'c' * 64, 'completed_chapters': 2},
                'character_cast': {'success': True, 'real_ui_post': True,
                    'reference_identities_verified': True, 'character_names_not_spoken': True,
                    'download_verified': True, 'status': 'done', 'voice_ids': ['hmong-male', 'hmong-female'],
                    'cue_count': 2, 'job_id': 'cast-qa', 'audio_bytes': 48044, 'audio_seconds': 1,
                    'sample_rate': 24000, 'peak_amplitude': .2, 'sha256': 'd' * 64}},
            'voices': {'hmong-male': cases[0], 'hmong-female': cases[1]}, 'cases': cases}


def native_feature_fixture():
    return {'platform': 'win32', 'native_windows_validation': True, 'reference_cache_limit': 16,
        'reference_quality_advisories': True, 'longform': {'success': True,
            'oversize_rejected': True, 'plan_preserved_all_segments': True,
            'real_synthesis': True, 'short_sample_plan_injected': True,
            'archive_contents_verified': True, 'chapter_routes_verified': True,
            'accepted_characters': 1_000_000, 'million_character_synthesis_performed': False,
            'planned_chapters': 101, 'completed_chapters': 2, 'sample_characters': 56,
            'archive_sha256': 'c' * 64, 'job_id': 'chapter-qa'},
        'character_cast': {'success': True, 'real_synthesis': True,
            'reference_identities_verified': True, 'original_srt_preserved': True,
            'voice_ids': ['hmong-male', 'hmong-female'], 'cue_characters': ['narrator', 'guest'],
            'audio_seconds': 24}}


def fresh_start_fixture():
    expected = packaging.expected_reference_fingerprints()
    voices = [{'id': ident, 'reference_fingerprint': expected[ident], 'sample_rate': 24000,
               'channels': 1, 'frames': 24000, 'duration_seconds': 1, 'peak': .2, 'rms': .05,
               'output_sha256': ('a' if ident == 'hmong-male' else 'b') * 64}
              for ident in ('hmong-male', 'hmong-female')]
    return {'success': True, 'platform': 'win32', 'version': packaging.VERSION,
            'native_windows_validation': True, 'actual_cmd_batch': True,
            'initial_data_absent': True, 'missing_models_rejected_offline': True,
            'models_prepared_from_empty_data': True, 'prepared_models_reused': False,
            'external_model_cache_used': False,
            'script_sha256': hashlib.sha256((PACKAGING / 'fresh_hmong_portable.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            'runtime_python_sha256': hashlib.sha256(b'packaged-python-fixture').hexdigest(),
            'model_manifest_sha256': 'c' * 64,
            'legacy_environment_recovery': {'requested_device': 'cuda', 'requested_precision': 'int8',
                'effective_device': 'cpu', 'effective_precision': 'fp32', 'fallback_notice': True,
                'int8_notice': True, 'real_synthesis': True},
            'steps': [{'argument': arg, 'offline': offline, 'exit_code': code,
                       'environment_overrides': {'HMOOB_DEVICE': 'cuda', 'HMOOB_PRECISION': 'int8'} if arg == '--test-voice' else {},
                       'output': 'Đang dùng bộ CPU để tạo giọng. Đã bỏ tùy chọn INT8 của F5 cũ.' if arg == '--test-voice' else ''}
                      for arg, offline, code in [
                ('--check', True, 1), ('--probe-runtime', True, 0), ('--setup-only', False, 0),
                ('--check', True, 0), ('--test-voice', True, 0)]],
            'runtime_health': {'ok': True, 'inference_tested': False, 'kind': 'runtime', 'backend': 'native',
                               'checks': [{'name': name, 'ok': True} for name in (
                                   'cpu-conv1d-numpy', 'wav-soxr-scipy-librosa',
                                   'import:hmong_native_vendor.vits.models',
                                   'import:hmong_native_vendor.openvoice.models',
                                   'import:hmong_native_vendor.watermark.models.my_model')]},
            'speech_check': {'ok': True, 'inference_tested': True, 'kind': 'speech', 'backend': 'native',
                             'device': 'cpu', 'configuration': {'precision': 'fp32'}, 'voices': voices},
            'independently_verified_voices': copy.deepcopy(voices)}


@pytest.mark.parametrize('failure', ['prepared_data', 'external_cache', 'no_missing_model_failure',
                                   'skip_setup', 'runtime_failure', 'no_runtime_math', 'no_inference',
                                   'silent', 'wrong_reference', 'changed_wav', 'one_voice', 'stale_script',
                                   'no_legacy_overrides', 'no_cuda_fallback', 'no_int8_notice', 'wrong_effective_device'])
def test_fresh_start_gate_rejects_prepared_only_or_incomplete_speech_evidence(failure):
    report = fresh_start_fixture()
    assert packaging.validate_fresh_start_report(report) is report
    if failure == 'prepared_data':
        report['prepared_models_reused'] = True
    elif failure == 'external_cache':
        report['external_model_cache_used'] = True
    elif failure == 'no_missing_model_failure':
        report['steps'][0]['exit_code'] = 0
    elif failure == 'skip_setup':
        report['steps'].pop(2)
    elif failure == 'runtime_failure':
        report['runtime_health']['ok'] = False
    elif failure == 'no_runtime_math':
        report['runtime_health']['checks'] = []
    elif failure == 'no_inference':
        report['speech_check']['inference_tested'] = False
    elif failure == 'silent':
        report['independently_verified_voices'][0]['rms'] = 0
    elif failure == 'wrong_reference':
        report['speech_check']['voices'][0]['reference_fingerprint'] = 'f' * 64
    elif failure == 'changed_wav':
        report['independently_verified_voices'][1]['output_sha256'] = 'f' * 64
    elif failure == 'one_voice':
        report['speech_check']['voices'].pop()
    elif failure == 'no_legacy_overrides':
        report['steps'][-1]['environment_overrides'] = {}
    elif failure == 'no_cuda_fallback':
        report['legacy_environment_recovery']['fallback_notice'] = False
    elif failure == 'no_int8_notice':
        report['steps'][-1]['output'] = 'Đang dùng bộ CPU để tạo giọng.'
    elif failure == 'wrong_effective_device':
        report['legacy_environment_recovery']['effective_device'] = 'cuda'
    else:
        report['script_sha256'] = 'f' * 64
    with pytest.raises(ValueError):
        packaging.validate_fresh_start_report(report)


def test_first_run_wave_measurement_reads_actual_pcm_and_rejects_silence(tmp_path):
    import math
    import struct
    import wave
    spec = importlib.util.spec_from_file_location('fresh_hmong', PACKAGING / 'fresh_hmong_portable.py')
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    path = tmp_path / 'speech.wav'
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, 24000, 24000, 'NONE', 'not compressed'))
        audio.writeframes(b''.join(struct.pack('<h', round(6000 * math.sin(index / 10))) for index in range(24000)))
    report = fresh.wave_evidence(path)
    assert report['frames'] == 24000 and report['duration_seconds'] == 1
    assert report['output_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert .1 < report['rms'] < .2
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, 24000, 24000, 'NONE', 'not compressed'))
        audio.writeframes(b'\x00' * 48000)
    with pytest.raises(RuntimeError, match='silent'):
        fresh.wave_evidence(path)


def test_first_run_qa_refuses_existing_data_without_modifying_it(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('fresh_hmong_preserve', PACKAGING / 'fresh_hmong_portable.py')
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    monkeypatch.setattr(fresh, 'os', SimpleNamespace(name='nt'))
    data = tmp_path / 'portable/voice-studio-hmong/.data'
    data.mkdir(parents=True)
    saved = data / 'personal-profile.json'
    saved.write_bytes(b'preserve this profile')
    with pytest.raises(ValueError, match='existing user or builder files are preserved'):
        fresh.run_first_start(tmp_path / 'portable', tmp_path / 'reports')
    assert saved.read_bytes() == b'preserve this profile'


def test_windows_browser_gate_accepts_all_actual_ui_synthesis_cases():
    report = browser_report_fixture()
    assert packaging.validate_browser_report(report) is report


@pytest.mark.parametrize('failure', ['missing', 'clock_leaked', 'index_leaked', 'source_lost',
        'clock_silence', 'wrong_reference', 'wrong_voice', 'unrelated_source',
        'reused_job', 'no_post', 'no_download', 'silent', 'no_playback'])
def test_windows_browser_gate_requires_real_timestamp_cleaned_txt(failure):
    report = copy.deepcopy(browser_report_fixture())
    caption = report['caption_metadata']
    if failure == 'missing':
        del report['caption_metadata']
    elif failure == 'clock_leaked':
        caption['exported_spoken_text'] = '00:04:28,533 Nyob zoo. Ua tsaug.'
    elif failure == 'index_leaked':
        caption['exported_spoken_text'] = '1 Nyob zoo. 2 Ua tsaug.'
    elif failure == 'source_lost':
        caption['original_text_preserved'] = False
    elif failure == 'clock_silence':
        caption['audio_seconds'] = 269.333
    elif failure == 'wrong_reference':
        caption['hmong_reference_fingerprint'] = 'b' * 64
    elif failure == 'wrong_voice':
        caption['speaker'] = 'hmong-female'
    elif failure == 'unrelated_source':
        caption['text'] = 'Nyob zoo.'
    elif failure == 'reused_job':
        caption['job_id'] = report['cases'][0]['job_id']
    elif failure == 'no_post':
        caption['real_ui_post'] = False
    elif failure == 'no_download':
        caption['download_verified'] = False
    elif failure == 'silent':
        caption['peak_amplitude'] = 0
    else:
        caption['playback']['current_time'] = 0
    with pytest.raises(ValueError):
        packaging.validate_browser_report(report)


@pytest.mark.parametrize('failure', ['missing', 'default', 'wrong_audio', 'wrong_identity',
        'no_cross_language', 'transcript_required', 'not_selected', 'wrong_language',
        'no_post', 'no_playback', 'no_download', 'silent', 'claimed_similarity'])
def test_windows_browser_gate_requires_external_audio_conditioned_clone(failure):
    report = copy.deepcopy(browser_report_fixture())
    clone = report['external_clone']
    if failure == 'missing':
        del report['external_clone']
    elif failure == 'default':
        clone['voice_id'] = clone['post_voice_id'] = clone['speaker'] = 'hmong-male'
    elif failure == 'wrong_audio':
        clone['reference_audio_sha256'] = 'b' * 64
    elif failure == 'wrong_identity':
        clone['hmong_reference_fingerprint'] = report['expected_reference_fingerprints']['hmong-male']
    elif failure == 'no_cross_language':
        clone['cross_language_reference'] = False
    elif failure == 'transcript_required':
        clone['no_transcript'] = False
    elif failure == 'not_selected':
        clone['auto_selected'] = False
    elif failure == 'wrong_language':
        clone['output_language'] = 'en'
    elif failure == 'no_post':
        clone['real_ui_post'] = False
    elif failure == 'no_playback':
        clone['playback']['ready_state'] = 0
    elif failure == 'no_download':
        clone['download_verified'] = False
    elif failure == 'silent':
        clone['peak_amplitude'] = 0
    else:
        clone['perceptual_similarity_evaluated'] = True
    with pytest.raises(ValueError):
        packaging.validate_browser_report(report)


@pytest.mark.parametrize('failure', ['missing', 'mocked', 'not_rejected', 'duplicate_post',
        'inline_offscreen', 'output_offscreen', 'locked', 'draft_lost', 'empty_error',
        'wrong_inline', 'wrong_output', 'idle_output', 'wrong_text', 'wrong_request',
        'wrong_voice', 'wrong_language', 'no_recovery', 'unrelated_job', 'unrelated_audio',
        'wrong_entrypoint', 'fifth_case', 'boolean_count', 'string_status'])
def test_windows_browser_gate_requires_real_click_error_and_same_job_recovery(failure):
    report = copy.deepcopy(browser_report_fixture())
    mutations = {
        'mocked': ('responses_mocked', True), 'not_rejected': ('http_status', 202),
        'duplicate_post': ('request_count', 2), 'inline_offscreen': ('inline_error_visible', False),
        'output_offscreen': ('output_error_visible', False), 'locked': ('button_unlocked', False),
        'draft_lost': ('draft_preserved', False), 'empty_error': ('error_detail', ''),
        'wrong_inline': ('inline_error', 'Different error'),
        'wrong_output': ('output_error', 'Different error'),
        'idle_output': ('output_error_title', 'Bản thu của bạn sẽ xuất hiện ở đây'),
        'wrong_text': ('invalid_text', 'Nyob zoo.'), 'wrong_request': ('request_text', 'Nyob zoo.'),
        'wrong_voice': ('request_voice_id', 'hmong-female'), 'wrong_language': ('request_language', 'vi'),
        'no_recovery': ('recovery_succeeded', False), 'unrelated_job': ('recovery_job_id', 'other-job'),
        'unrelated_audio': ('recovered_audio_sha256', 'b' * 64),
        'wrong_entrypoint': ('ui_entrypoint', '#another-button'),
        'boolean_count': ('request_count', True), 'string_status': ('http_status', '422')}
    if failure == 'missing':
        del report['click_recovery']
    elif failure == 'fifth_case':
        extra = copy.deepcopy(report['cases'][0])
        extra['job_id'] = 'job-5'
        report['cases'].append(extra)
    else:
        key, value = mutations[failure]
        report['click_recovery'][key] = value
    with pytest.raises(ValueError):
        packaging.validate_browser_report(report)


@pytest.mark.parametrize('failure', ['linux', 'skipped', 'library', 'workspace', 'speaker',
                                    'reference', 'missing_case', 'wrong_case', 'silent_audio',
                                    'no_playback', 'stale_script', 'hyphen_text',
                                    'no_chapter_download', 'no_million_editor', 'no_cast_routing'])
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
    elif failure == 'no_chapter_download':
        report['features_1_6']['longform']['download_verified'] = False
    elif failure == 'no_million_editor':
        report['features_1_6']['longform']['million_character_editor'] = False
    elif failure == 'no_cast_routing':
        report['features_1_6']['character_cast']['reference_identities_verified'] = False
    else:
        for case in report['cases']:
            case['text'] = 'Nyob zoo.'
    with pytest.raises(ValueError):
        packaging.validate_browser_report(report)


@pytest.mark.parametrize('failure', ['cache', 'missing', 'pretend_full_synthesis', 'no_real_speech', 'no_reference'])
def test_native_feature_gate_rejects_incomplete_or_misleading_evidence(failure):
    report = native_feature_fixture()
    assert packaging.validate_native_feature_report(report) is report
    if failure == 'cache':
        report['reference_cache_limit'] = 1
    elif failure == 'missing':
        report.pop('longform')
    elif failure == 'pretend_full_synthesis':
        report['longform']['million_character_synthesis_performed'] = True
    elif failure == 'no_real_speech':
        report['longform']['real_synthesis'] = False
    else:
        report['character_cast']['reference_identities_verified'] = False
    with pytest.raises(ValueError):
        packaging.validate_native_feature_report(report)


def test_publication_gate_reads_mandatory_browser_evidence_from_the_zip(tmp_path):
    root = tmp_path / ('Voice-Studio-Hmong-' + packaging.VERSION)
    packaging.write_launcher(root)
    report = browser_report_fixture()
    reports = root / 'reports'
    reports.mkdir()
    fresh = fresh_start_fixture()
    import math
    import struct
    import wave
    actual_voices = []
    for index, ident in enumerate(('hmong-male', 'hmong-female')):
        name = 'first-run-' + ident.removeprefix('hmong-') + '.wav'
        with wave.open(str(reports / name), 'wb') as audio:
            audio.setparams((1, 2, 24000, 24000, 'NONE', 'not compressed'))
            audio.writeframes(b''.join(struct.pack('<h', round(4000 * math.sin(sample / (10 + index))))
                                       for sample in range(24000)))
        measured = packaging.wave_evidence_bytes((reports / name).read_bytes(), name)
        actual_voices.append(dict(measured, id=ident,
                                  reference_fingerprint=packaging.expected_reference_fingerprints()[ident]))
    fresh['speech_check']['voices'] = actual_voices
    fresh['independently_verified_voices'] = copy.deepcopy(actual_voices)
    for name, field in (('external-english-reference.wav', 'source_sha256'),
                        ('external-clone-reference.wav', 'reference_audio_sha256')):
        with wave.open(str(reports / name), 'wb') as audio:
            audio.setparams((1, 2, 24000, 120000, 'NONE', 'not compressed'))
            audio.writeframes((reports / 'first-run-male.wav').read_bytes()[44:] * 5)
        report['external_clone'][field] = hashlib.sha256((reports / name).read_bytes()).hexdigest()
    clone_identity = hashlib.sha256(json.dumps({'version': 1,
        'audio_sha256': report['external_clone']['reference_audio_sha256'], 'transcript': ''},
        ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    report['external_clone']['independent_reference_fingerprint'] = clone_identity
    report['external_clone']['hmong_reference_fingerprint'] = clone_identity
    source_files = ('caption_markers.py', 'character_cast.py', 'longform.py', 'reference_quality.py', 'hmong_health.py', 'voice_errors.py',
                    'hmong_launcher.py', 'prepare_hmong.py', 'hmong_native.py', 'static/text-import.js',
                    'assets/hmong/additional-voices.json', 'assets/hmong/source-ngoc-huyen.mp3',
                    'assets/hmong/ngoc-huyen.wav', 'assets/hmong/source-female-3.mp3', 'assets/hmong/female-3.wav',
                    'docs/HUONG-DAN-HMONG.md', 'docs/HUONG-DAN-HMONG.html')
    for module in source_files:
        path = root / 'voice-studio-hmong' / module
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((packaging.SOURCE / module).read_bytes())
    source_hashes = {name: packaging.sha256(root / 'voice-studio-hmong' / name) for name in source_files}
    (root / 'HUONG-DAN-HMONG.html').write_bytes((packaging.SOURCE / 'docs/HUONG-DAN-HMONG.html').read_bytes())
    files = {'BUILD.json': {'version': packaging.VERSION, 'windows_browser_validation': True,
                           'fresh_windows_first_run_validation': True,
                           'runtime_python_sha256': fresh['runtime_python_sha256'],
                           'application_sha256': source_hashes},
             'reports/fresh-start.json': fresh,
             'reports/browser-smoke.json': report,
             'reports/native-smoke.json': {**native_feature_fixture(), 'success': True, 'main_launcher': {
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
    (root / 'runtime/python.exe').write_bytes(b'packaged-python-fixture')
    archive = tmp_path / 'release.zip'
    packaging.archive_package(root, archive)
    assert packaging.validate_release_archive(archive) == report
    health = root / 'voice-studio-hmong/hmong_health.py'
    original = health.read_bytes()
    health.write_bytes(b'outdated health checks\n')
    packaging.archive_package(root, archive)
    with pytest.raises(ValueError, match='application checksum mismatch'):
        packaging.validate_release_archive(archive)
    health.write_bytes(original)
    reference_path = reports / 'external-clone-reference.wav'
    reference_original = reference_path.read_bytes()
    reference_path.write_bytes(reference_original[:-2] + b'\x00\x00')
    packaging.archive_package(root, archive)
    with pytest.raises(ValueError, match='external reference differs'):
        packaging.validate_release_archive(archive)
    reference_path.write_bytes(reference_original)
    (root / 'runtime/python.exe').write_bytes(b'another-python')
    packaging.archive_package(root, archive)
    with pytest.raises(ValueError, match='exact runtime'):
        packaging.validate_release_archive(archive)
    (root / 'runtime/python.exe').write_bytes(b'packaged-python-fixture')
    fresh_path = reports / 'fresh-start.json'
    first_run = fresh_path.read_bytes()
    fresh_path.unlink()
    packaging.archive_package(root, archive)
    with pytest.raises(KeyError, match='fresh-start'):
        packaging.validate_release_archive(archive)
    fresh_path.write_bytes(first_run)
    first_wav = reports / 'first-run-male.wav'
    actual_wav = first_wav.read_bytes()
    first_wav.write_bytes((reports / 'first-run-female.wav').read_bytes())
    packaging.archive_package(root, archive)
    with pytest.raises(ValueError, match='differs from the tested WAV'):
        packaging.validate_release_archive(archive)
    first_wav.write_bytes(actual_wav)
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
    additional = packaging.expected_additional_reference_fingerprints()
    combined = {**expected, **additional}
    monkeypatch.setitem(sys.modules, 'hmong_assets', SimpleNamespace(reference_fingerprint=combined.__getitem__))
    report = browser_report_fixture()
    report['runtime']['url'] = 'http://127.0.0.1:8770'
    reports = tmp_path / 'reports'
    reports.mkdir()
    def run(command, **kwargs):
        if command[0] == 'ffmpeg':
            assert command[1:5] == ['-nostdin', '-v', 'error', '-i']
            assert Path(command[5]) == tmp_path / 'portable/runtime/Lib/site-packages/f5_tts/infer/examples/basic/basic_ref_en.wav'
            assert command[6:] == ['-t', '5', '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le',
                                   '-y', str(reports / 'external-english-reference.wav')]
            assert kwargs == {'check': True, 'capture_output': True, 'timeout': 30}
            return
        assert Path(command[0]) == interpreter
        assert Path(command[1]).name == 'browser_hmong_portable.py'
        assert command[2:4] == ['--url', report['runtime']['url']]
        assert command[4:6] == ['--reports', str(reports)]
        assert command[6] == '--expected-references'
        assert json.loads(command[7]) == expected
        assert command[8:10] == ['--external-reference', str(reports / 'external-english-reference.wav')]
        assert command[10] == '--expected-additional-references'
        assert json.loads(command[11]) == additional
        assert len(command) == 12 and '--allow-non-windows' not in command
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
                                 'prepare_hmong_native.py', 'runtime_instance.py', 'hmong_health.py', 'voice_errors.py',
                                 'character_cast.py', 'longform.py', 'reference_quality.py'])
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
    root = tmp_path / 'Relocated Hmong test with spaces' / 'Voice-Studio-Hmong-1.6.4'
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
                'root_id': 'qa-root', 'backend': engine, 'version': '1.6.4-hmong'}
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
