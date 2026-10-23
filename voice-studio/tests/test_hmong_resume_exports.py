"""Protect resumed preset audio and export exactly the spoken SRT content."""
import importlib
import wave
from unittest.mock import Mock

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import app
import hmong_assets
from narration import plan_segments
from subtitles import parse_srt


@pytest.fixture
def studio(tmp_path, monkeypatch):
    for folder in ('voices', 'audio', 'jobs', 'models', 'parts'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'IS_HMONG', True)
    monkeypatch.setattr(app, 'LANGUAGES', {**app.LANGUAGES, 'mww': 'Hmong Trắng · Hmoob Daw'})
    monkeypatch.setattr(app, 'PRESETS', hmong_assets.presets())
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    monkeypatch.setattr(app, 'model_ready', lambda engine: True)
    with TestClient(app.app) as client:
        submit = Mock()
        monkeypatch.setattr(app.executor, 'submit', submit)
        yield client, tmp_path, submit


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, '_hmong_model_instance', None)
    monkeypatch.setattr(module, '_cached_key', None)
    monkeypatch.setattr(module, '_cached_synth', None)
    (tmp_path / 'audio').mkdir(exist_ok=True)
    return module


def pcm(path, value=1000, frames=12000):
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(int(value).to_bytes(2, 'little', signed=True) * frames)


def preset_job(**changes):
    return {'id': 'a' * 32, 'engine': 'f5_hmong', 'speaker': 'hmong-male',
            'voice_id': 'hmong-male', 'language': 'mww', 'status': 'cancelled',
            'segment_plan': 'hmong-packed-v1', 'text': 'Nyob zoo. ' * 25,
            'input_format': 'txt', 'paragraph_pause': 0, 'speed': 1, 'format': 'wav',
            'max_minutes': 1, 'delivery': 'natural', 'hmong_steps': 16, **changes}


def test_reference_fingerprint_binds_audio_and_exact_transcript(tmp_path, monkeypatch):
    path = tmp_path / 'reference.wav'
    pcm(path)
    words = ['Nyob zoo.']
    monkeypatch.setattr(hmong_assets, 'reference', lambda ident: (path, words[0]))
    initial = hmong_assets.reference_fingerprint('hmong-male')
    assert initial == hmong_assets.reference_fingerprint('hmong-male')
    words[0] += ' '
    assert initial != hmong_assets.reference_fingerprint('hmong-male')
    words[0] = 'Nyob zoo.'
    pcm(path, 5000)
    assert initial != hmong_assets.reference_fingerprint('hmong-male')


def test_new_preset_job_saves_fingerprint_and_matching_resume_keeps_cache(studio):
    client, root, submit = studio
    response = client.post('/api/speech', json={'text': 'Nyob zoo.', 'voice_id': 'hmong-male',
                                               'language': 'mww'})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['hmong_reference_fingerprint'] == hmong_assets.reference_fingerprint('hmong-male')
    job['status'] = 'cancelled'
    app.write_json(root / 'jobs' / (job['id'] + '.json'), job)
    work = root / 'parts' / job['id']
    work.mkdir()
    checkpoint = work / '000000.wav'
    pcm(checkpoint)
    before = checkpoint.read_bytes()
    (work / 'cancel.flag').touch()
    submit.reset_mock()
    resumed = client.post('/api/jobs/' + job['id'] + '/resume')
    assert resumed.status_code == 202, resumed.text
    assert resumed.json()['status'] == 'queued'
    assert checkpoint.read_bytes() == before
    assert not (work / 'cancel.flag').exists()
    submit.assert_called_once_with(app.run_job, job['id'])


@pytest.mark.parametrize('fingerprint', [None, 'old-preset-reference'])
def test_resume_rejects_missing_or_changed_preset_identity_without_touching_cache(studio, fingerprint):
    client, root, submit = studio
    job = preset_job()
    if fingerprint is not None:
        job['hmong_reference_fingerprint'] = fingerprint
    path = root / 'jobs' / (job['id'] + '.json')
    app.write_json(path, job)
    work = root / 'parts' / job['id']
    work.mkdir()
    pcm(work / '000000.wav')
    (work / 'cancel.flag').touch()
    before_job = path.read_bytes()
    before_checkpoint = (work / '000000.wav').read_bytes()
    response = client.post('/api/jobs/' + job['id'] + '/resume')
    assert response.status_code == 409, response.text
    assert 'Tạo tác vụ mới' in response.json()['detail']
    assert path.read_bytes() == before_job
    assert (work / '000000.wav').read_bytes() == before_checkpoint
    assert (work / 'cancel.flag').exists()
    submit.assert_not_called()


@pytest.mark.parametrize('fingerprint', [None, 'old-preset-reference'])
def test_worker_rejects_legacy_or_changed_identity_before_reusing_old_chunks(worker, tmp_path, fingerprint):
    job = preset_job()
    if fingerprint is not None:
        job['hmong_reference_fingerprint'] = fingerprint
    assert len(plan_segments(job)) == 2
    work = tmp_path / 'parts' / job['id']
    work.mkdir(parents=True)
    pcm(work / '000000.wav', 1000)
    before = (work / '000000.wav').read_bytes()
    calls = []
    def replacement_voice(text, path):
        calls.append(text)
        pcm(path, 5000)
    with pytest.raises(ValueError, match='Tạo tác vụ mới'):
        worker.render(job, synthesize=replacement_voice)
    assert not calls, 'Do not append new-preset speech after cached old-preset speech'
    assert (work / '000000.wav').read_bytes() == before
    assert not (work / 'assembled.wav').exists()
    assert not (tmp_path / 'audio' / (job['id'] + '.wav')).exists()


def test_worker_matching_identity_reuses_completed_chunk(worker, tmp_path):
    job = preset_job(hmong_reference_fingerprint=hmong_assets.reference_fingerprint('hmong-male'))
    work = tmp_path / 'parts' / job['id']
    work.mkdir(parents=True)
    pcm(work / '000000.wav')
    before = (work / '000000.wav').read_bytes()
    calls = []
    def matching_voice(text, path):
        calls.append(text)
        pcm(path)
    worker.render(job, synthesize=matching_voice)
    assert len(calls) == 1
    assert (work / '000000.wav').read_bytes() == before
    assert sf.info(str(tmp_path / 'audio' / (job['id'] + '.wav'))).frames == 24000


def test_warm_synthesizer_cache_includes_reference_fingerprint(worker, monkeypatch):
    loaded = []
    def load(job):
        loaded.append(job['hmong_reference_fingerprint'])
        return lambda *args: None
    monkeypatch.setattr(worker, 'load_synthesizer', load)
    first = preset_job(hmong_reference_fingerprint='previous')
    current = preset_job(hmong_reference_fingerprint='current')
    worker.get_synthesizer(first)
    worker.get_synthesizer(first)
    worker.get_synthesizer(current)
    assert loaded == ['previous', 'current']


SRT = ('1\n00:00:00,000 --> 00:00:00,250\n'
       '[emotion=warm]**Nyob zoo.**[pause=0.1]\n\n'
       '2\n00:00:02,000 --> 00:00:04,000\n'
       '[emotion=serious]Peb nyob ua ke.\n')


def expressive_srt_job(**changes):
    settings = {'text': SRT, 'input_format': 'srt', 'segment_plan': 'hmong-expression-v1',
                'emotion': 'neutral', 'emotion_strength': .65, 'auto_rhythm': True,
                'cue_fit': 'gap', 'timeline_seconds': 4,
                'hmong_reference_fingerprint': hmong_assets.reference_fingerprint('hmong-male')}
    return preset_job(**{**settings, **changes})


def assert_spoken_srt(text):
    assert '[emotion=' not in text and '[pause=' not in text and '**' not in text
    assert [cue['text'] for cue in parse_srt(text)] == ['Nyob zoo.', 'Peb nyob ua ke.']


def test_expressive_srt_exports_spoken_words_and_actual_cue_fit_times(studio, worker):
    client, root, _ = studio
    job = expressive_srt_job()
    original = job['text']
    calls = []
    def synthesize(text, path):
        calls.append(text)
        samples = .2 * np.sin(2 * np.pi * 220 * np.arange(16800) / 24000)
        sf.write(str(path), samples, 24000, subtype='PCM_16')
    worker.render(job, synthesize=synthesize)
    assert calls == ['Nyob zoo.', 'Peb nyob ua ke.']
    assert job['text'] == original
    spoken = (root / 'audio' / (job['id'] + '.srt')).read_text(encoding='utf-8')
    assert_spoken_srt(spoken)
    cues = parse_srt(spoken)
    assert cues[0]['start'] == 0 and .25 < cues[0]['end'] < 2
    assert (cues[1]['start'], cues[1]['end']) == (2, 4)
    job['status'] = 'done'
    app.write_json(root / 'jobs' / (job['id'] + '.json'), job)
    for suffix in ('export.srt', 'script.srt'):
        response = client.get('/api/jobs/' + job['id'] + '/' + suffix)
        assert response.status_code == 200, response.text
        assert response.text == spoken
    exported = client.get('/api/jobs/' + job['id'] + '/export.txt')
    assert exported.status_code == 200
    assert exported.text == 'Nyob zoo.\n\nPeb nyob ua ke.\n'
    assert client.get('/api/jobs/' + job['id']).json()['text'] == original
    project = client.post('/api/scripts/convert', json={'text': original,
        'input_format': 'srt', 'output_format': 'srt'})
    assert project.status_code == 200 and '[emotion=warm]' in project.json()['text']


def test_expressive_srt_planning_export_sanitizes_without_changing_saved_input(studio):
    client, root, _ = studio
    job = expressive_srt_job()
    path = root / 'jobs' / (job['id'] + '.json')
    app.write_json(path, job)
    before = path.read_bytes()
    response = client.get('/api/jobs/' + job['id'] + '/script.srt')
    assert response.status_code == 200, response.text
    assert_spoken_srt(response.text)
    assert parse_srt(response.text)[0]['end'] == .25
    assert path.read_bytes() == before


def test_legacy_srt_export_keeps_existing_raw_script_behavior(studio):
    client, root, _ = studio
    job = expressive_srt_job(segment_plan='hmong-packed-v1')
    app.write_json(root / 'jobs' / (job['id'] + '.json'), job)
    response = client.get('/api/jobs/' + job['id'] + '/script.srt')
    assert response.status_code == 200 and '[emotion=warm]' in response.text
