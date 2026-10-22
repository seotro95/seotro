"""Narration modes must affect audio, while imported subtitle timing stays fixed."""
import importlib
import wave
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from narration import PROFILES
from subtitles import parse_srt
from test_app import studio  # noqa: F401


@pytest.mark.parametrize('delivery', ['review', 'advertising', 'tutorial'])
def test_new_delivery_is_preserved_in_queued_job(studio, delivery):
    client, root = studio
    (root / 'models' / 'vieneu.ready').touch()
    with patch('app.executor.submit'):
        response = client.post('/api/speech', json={
            'text': 'Đây là lời đọc thử.', 'voice_id': 'vi-maianh',
            'delivery': delivery, 'paragraph_pause': PROFILES[delivery][1],
        })
    assert response.status_code == 202, response.text
    assert response.json()['delivery'] == delivery


def test_review_tempo_and_tutorial_pause_apply_to_actual_audio(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    # One second of non-silent audio for each sentence, before delivery controls.
    def synth(text, output):
        sf.write(output, .3 * np.sin(np.arange(24000) * 2 * np.pi * 440 / 24000), 24000)
    measured = {}
    for delivery in ('review', 'tutorial'):
        job = {'id': delivery, 'text': 'Lời đầu. Lời sau.', 'engine': 'vieneu',
               'language': 'vi', 'format': 'wav', 'speed': 1, 'delivery': delivery}
        worker.render(job, synth)
        cues = parse_srt((tmp_path / 'audio' / (delivery + '.srt')).read_text())
        measured[delivery] = cues
        assert cues[1]['start'] - cues[0]['end'] == pytest.approx(PROFILES[delivery][1], abs=.002)
    assert measured['review'][0]['end'] < measured['tutorial'][0]['end']


def test_review_preserves_imported_srt_timeline(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    text = '1\n00:00:01,000 --> 00:00:03,000\nMột lời review.\n'
    def synth(text, output):
        sf.write(output, .3 * np.sin(np.arange(12000) * 2 * np.pi * 440 / 24000), 24000)
    worker.render({'id': 'review-srt', 'text': text, 'input_format': 'srt', 'engine': 'vieneu',
                   'format': 'wav', 'speed': 1, 'delivery': 'review', 'paragraph_pause': .28}, synth)
    assert parse_srt((tmp_path / 'audio/review-srt.srt').read_text()) == parse_srt(text)
    with wave.open(str(tmp_path / 'audio/review-srt.wav')) as audio:
        assert audio.getnframes() / audio.getframerate() == 3
