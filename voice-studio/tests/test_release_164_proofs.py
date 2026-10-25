"""Reject release evidence that omits the new voices or only-spoken SRT."""
import copy

import pytest

from bundle_check import BundleError, validate_bundle
from test_hmong_packaging import browser_report_fixture, packaging
from test_hmong_startup import bundle_fixture


@pytest.mark.parametrize('failure', [
    'initial-default', 'missing-extra', 'wrong-ref', 'wrong-source', 'default-speaker',
    'no-real-post', 'no-playback', 'duplicate-job', 'spoken-mode-absent',
    'spoken-still-timed', 'spoken-read-index', 'spoken-clock-silence',
    'spoken-old-srt-export', 'spoken-no-download',
])
def test_new_release_proofs_require_actual_selected_audio_and_continuous_speech(failure):
    report = copy.deepcopy(browser_report_fixture())
    ident = 'hmong-female-3'
    added = report['additional_presets'][ident]
    spoken = report['srt_speech_only']
    if failure == 'initial-default': report['initial_voice_id'] = 'hmong-male'
    elif failure == 'missing-extra': report['additional_presets'].pop(ident)
    elif failure == 'wrong-ref': added['hmong_reference_fingerprint'] = '0' * 64
    elif failure == 'wrong-source': added['source_sha256'] = '0' * 64
    elif failure == 'default-speaker': added['speaker'] = 'hmong-female'
    elif failure == 'no-real-post': added['real_ui_post'] = False
    elif failure == 'no-playback': added['playback']['current_time'] = 0
    elif failure == 'duplicate-job': added['job_id'] = report['cases'][0]['job_id']
    elif failure == 'spoken-mode-absent': report.pop('srt_speech_only')
    elif failure == 'spoken-still-timed': spoken['subtitle_timing'] = True
    elif failure == 'spoken-read-index': spoken['exported_spoken_text'] = '217 Tae-yong cov ntaub ntawv tus kheej'
    elif failure == 'spoken-clock-silence': spoken['audio_seconds'] = 368.4
    elif failure == 'spoken-old-srt-export': spoken['generated_srt'] = '217\n00:06:07,200 --> 00:06:08,400\nTae-yong cov ntaub ntawv tus kheej\n'
    elif failure == 'spoken-no-download': spoken['download_verified'] = False
    with pytest.raises(ValueError):
        packaging.validate_browser_report(report)


@pytest.mark.parametrize('relative', [
    'static/text-import.js', 'assets/hmong/additional-voices.json',
    'assets/hmong/source-ngoc-huyen.mp3', 'assets/hmong/female-3.wav',
])
def test_new_assets_are_mandatory_in_the_complete_bundle(tmp_path, relative):
    bundle_fixture(tmp_path)
    assert validate_bundle(tmp_path)['voice_checksums'] == 8
    (tmp_path / relative).unlink()
    with pytest.raises(BundleError, match='TOÀN BỘ ZIP'):
        validate_bundle(tmp_path)


def test_changed_new_reference_audio_fails_its_checksum(tmp_path):
    bundle_fixture(tmp_path)
    (tmp_path / 'assets/hmong/ngoc-huyen.wav').write_bytes(b'changed')
    with pytest.raises(BundleError, match='SHA256'):
        validate_bundle(tmp_path)
