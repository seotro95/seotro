"""Actual file measurement and TXT/SRT duration contracts, independent of language."""
import importlib
import json
import wave
from unittest.mock import patch

import numpy as np
import pytest

from export_duration import verify_audio_export
from language_catalog import LANGUAGES
from narration import PCMWriter
from subtitles import export_srt
from test_timeline_audio import tone, worker, timed_job  # noqa: F401
from test_timeline_api import studio  # noqa: F401


@pytest.mark.parametrize('extension', ['wav', 'mp3'])
@pytest.mark.parametrize('seconds', [1.001, 2.345])
def test_final_export_is_measured_after_encoding(worker, extension, seconds):
    job = timed_job(format=extension, timeline_seconds=seconds,
                    text=export_srt([{'start': 0, 'end': seconds, 'text': 'Hello.'}]))
    worker.render(job, lambda text, path: tone(path, .75))
    path = worker.DATA / 'audio' / ('timeline.' + extension)
    measured = verify_audio_export(path, worker.DATA, round(seconds*24000))
    result = json.loads((worker.DATA/'parts/timeline/result.json').read_text())
    assert measured['error_frames'] == 0 and result['duration_verified']
    assert result['duration_report']['sample_frames'] == round(seconds*24000)
    assert result['sync_report']['complete'] and result['sync_report']['actual_seconds'] == seconds


@pytest.mark.parametrize('language', list(LANGUAGES))
def test_same_target_samples_for_every_catalog_script(worker, language):
    text = LANGUAGES[language].split('·')[-1].strip() + ' 123'
    job = timed_job(engine='system', language=language, timeline_seconds=2.345,
                    text=export_srt([{'start': .123, 'end': 2.345, 'text': text}]))
    spoken = []
    def synthesize(value, path):
        spoken.append(value)
        tone(path, .6)
    worker.render(job, synthesize)
    assert spoken == [text]
    result = json.loads((worker.DATA/'parts/timeline/result.json').read_text())
    assert result['sync_ok'] and result['duration_report']['sample_frames'] == 56280


def test_bad_encoded_duration_does_not_publish_or_claim_sync(worker, monkeypatch):
    import export_duration
    def reject(*args):
        raise ValueError('File thực tế sai thời lượng.')
    monkeypatch.setattr(export_duration, 'verify_audio_export', reject)
    with pytest.raises(ValueError, match='sai thời lượng'):
        worker.render(timed_job(), lambda text, path: tone(path, .8))
    assert not (worker.DATA/'audio/timeline.wav').exists()
    assert not (worker.DATA/'parts/timeline/result.json').exists()
    assert not json.loads((worker.DATA/'parts/timeline/alignment.json').read_text())['sync_ok']


def test_wrong_target_is_detected_from_real_file(tmp_path):
    tone(tmp_path/'file.wav', 1)
    with pytest.raises(ValueError, match='khác thời lượng'):
        verify_audio_export(tmp_path/'file.wav', tmp_path, 2*24000)


def test_strict_pcm_rejects_both_word_and_pause_truncation(tmp_path):
    tone(tmp_path/'speech.wav', 1.002)
    writer = PCMWriter(tmp_path/'out.wav', max_seconds=1.001, strict=True)
    try:
        assert writer.limit == 24024
        with pytest.raises(ValueError, match='không cắt'):
            writer.append(tmp_path/'speech.wav')
        assert writer.frames == 0
        with pytest.raises(ValueError, match='Khoảng nghỉ'):
            writer.silence(1.002)
    finally:
        writer.close()


def test_plain_txt_and_srt_queue_the_same_target(studio):
    client, _, _ = studio
    text = 'Xin chào.'
    plain = client.post('/api/speech', json={'text': text, 'voice_id': 'nano-minhquan', 'timeline_seconds': 10}).json()
    srt = client.post('/api/speech', json={'text': export_srt([{'start': 0, 'end': 10, 'text': text}]),
                      'input_format': 'srt', 'voice_id': 'nano-minhquan'}).json()
    assert plain['timing_mode'] == srt['timing_mode'] == 'exact'
    assert plain['timeline_seconds'] == srt['timeline_seconds'] == 10


def test_requested_target_cannot_be_silently_ignored(studio):
    client, _, submit = studio
    response = client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'nano-minhquan',
                            'timeline_seconds': 10, 'timing_mode': 'natural'})
    assert response.status_code == 422 and 'thời lượng đích' in response.json()['detail']
    submit.assert_not_called()
