"""Native routing and real PCM plumbing; model inference is stubbed in these tests."""
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import app
import hmong_assets
from hmong_engine import EngineError
from hmong_native import validate_text as validate_native_text
from narration import plan_segments
from state_io import read_progress
from subtitles import parse_srt


@pytest.fixture
def native_studio(tmp_path, monkeypatch):
    for folder in ('voices', 'audio', 'jobs', 'models', 'parts', 'videos'):
        (tmp_path / folder).mkdir()
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'IS_HMONG', True)
    monkeypatch.setattr(app, 'LANGUAGES', {**app.LANGUAGES, 'mww': 'Hmong Trắng · Hmoob Daw'})
    monkeypatch.setattr(app, 'CORE_LANGUAGES', {'mww': 'Hmong Trắng · Hmoob Daw'})
    monkeypatch.setattr(app, 'PRESETS', hmong_assets.presets())
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    monkeypatch.setattr(app, 'model_ready', lambda engine: engine == 'hmong_native')
    with TestClient(app.app) as client:
        submit = Mock()
        monkeypatch.setattr(app.executor, 'submit', submit)
        yield client, tmp_path, submit


def speech_request(**changes):
    return {'text': 'Nyob zoo. Ua tsaug.', 'voice_id': 'hmong-male', 'language': 'mww',
            'delivery': 'story', 'emotion': 'warm', 'paragraph_pause': 0,
            'hmong_phrase_context': True, **changes}


def test_native_config_and_presets_report_the_active_backend(native_studio):
    client, _, _ = native_studio
    config = client.get('/api/config').json()
    assert config['hmong_engine'] == 'hmong_native'
    assert config['hmong_backend'] == 'native' and config['hmong_steps'] is None
    assert config['hmong_ready'] is True
    assert config['models'] == {'hmong_native': True, 'f5_hmong': False}
    assert config['auto_rhythm'] is False and config['hmong_phrase_context'] is True
    voices = client.get('/api/voices').json()['voices']
    assert {voice['id'] for voice in voices} == {'hmong-male', 'hmong-female', 'hmong-female-3', 'hmong-ngoc-huyen'}
    assert config['default_voice_id'] == 'hmong-female-3'
    assert all(voice['engine'] == 'hmong_native' and voice['native_language'] == 'mww'
               and voice['ready'] for voice in voices)
    assert all(voice['reference_text_verified'] for voice in voices if voice['id'] in {'hmong-male', 'hmong-female'})
    assert all(not voice['reference_text_verified'] and voice['reference_conditioning'] == 'audio'
               for voice in voices if voice['id'] in {'hmong-female-3', 'hmong-ngoc-huyen'})


def test_male_and_female_share_one_consistent_model_readiness_snapshot(native_studio, monkeypatch):
    client, _, _ = native_studio
    # A model download may finish while the voice list is being refreshed.
    # Both preset choices must reflect the same snapshot of their shared model.
    readiness = Mock(side_effect=[True, False])
    monkeypatch.setattr(app, 'model_ready', readiness)
    voices = client.get('/api/voices').json()['voices']
    assert {voice['id']: voice['ready'] for voice in voices} == {
        'hmong-male': True, 'hmong-female': True, 'hmong-female-3': True, 'hmong-ngoc-huyen': True}
    readiness.assert_called_once_with('hmong_native')


@pytest.mark.parametrize('steps', [None, 4, 16, 32])
def test_native_job_omits_diffusion_steps_and_binds_reference_identity(native_studio, steps):
    client, root, submit = native_studio
    response = client.post('/api/speech', json=speech_request(hmong_steps=steps, quality='fast'))
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['engine'] == 'hmong_native' and job['hmong_steps'] is None
    assert job['hmong_backend'] == 'vits_openvoice_v2' and job['quality'] == 'standard'
    assert job['segment_plan'] == 'hmong-expression-v1' and job['total'] == 1
    assert job['hmong_reference_fingerprint'] == hmong_assets.reference_fingerprint('hmong-male')
    assert app.read_json(root / 'jobs' / (job['id'] + '.json')) == job
    submit.assert_called_once_with(app.run_job, job['id'])


def test_native_legacy_profile_presentation_and_new_job_do_not_rewrite_profile(native_studio):
    client, root, _ = native_studio
    ident = 'b' * 32
    reference, words = hmong_assets.reference('hmong-female')
    profile = {'id': ident, 'name': 'Legacy clone', 'engine': 'f5_hmong',
               'category': 'cloned', 'languages': ['mww'], 'transcript': words}
    path = root / 'voices' / (ident + '.json')
    app.write_json(path, profile)
    (root / 'voices' / (ident + '.wav')).write_bytes(reference.read_bytes())
    original = path.read_bytes()
    voice = next(item for item in client.get('/api/voices').json()['voices'] if item['id'] == ident)
    assert voice['engine'] == 'hmong_native' and voice['native_language'] == 'mww'
    response = client.post('/api/speech', json=speech_request(voice_id=ident))
    assert response.status_code == 202, response.text
    assert response.json()['engine'] == 'hmong_native'
    assert path.read_bytes() == original


@pytest.mark.parametrize('engine,steps', [('f5_hmong', 16), ('hmong_native', None)])
def test_resume_keeps_the_stored_backend_in_the_fast_launcher(native_studio, engine, steps):
    client, root, submit = native_studio
    ident = 'c' * 32
    job = {'id': ident, 'engine': engine, 'hmong_steps': steps, 'speaker': 'hmong-male',
           'voice_id': 'hmong-male', 'status': 'cancelled', 'created_at': app.now(),
           'format': 'wav', 'hmong_reference_fingerprint': hmong_assets.reference_fingerprint('hmong-male')}
    app.write_json(root / 'jobs' / (ident + '.json'), job)
    response = client.post('/api/jobs/' + ident + '/resume')
    assert response.status_code == 202, response.text
    assert response.json()['engine'] == engine and response.json()['hmong_steps'] == steps
    submit.assert_called_once_with(app.run_job, ident)


@pytest.mark.parametrize('engine', ['f5_hmong', 'hmong_native'])
@pytest.mark.parametrize('speaker', ['hmong-male', 'hmong-female'])
def test_resume_rejects_an_outdated_reference_without_altering_checkpoints(native_studio, engine, speaker):
    client, root, submit = native_studio
    ident = 'c' * 32
    job = {'id': ident, 'engine': engine, 'speaker': speaker, 'voice_id': speaker,
           'status': 'cancelled', 'created_at': app.now(), 'format': 'wav',
           'hmong_reference_fingerprint': 'old-reference'}
    path = root / 'jobs' / (ident + '.json')
    app.write_json(path, job)
    work = root / 'parts' / ident
    work.mkdir()
    checkpoint = work / '000000.wav'
    sf.write(str(checkpoint), np.ones(2400, dtype=np.float32) * .1, 24000)
    (work / 'cancel.flag').touch()
    before = (path.read_bytes(), checkpoint.read_bytes())
    response = client.post('/api/jobs/' + ident + '/resume')
    assert response.status_code == 409 and 'Tạo tác vụ mới' in response.text, response.text
    assert (path.read_bytes(), checkpoint.read_bytes()) == before
    assert (work / 'cancel.flag').exists()
    submit.assert_not_called()


def test_native_clone_keeps_the_exact_supplied_reference_words(native_studio):
    client, root, _ = native_studio
    source = hmong_assets.source('hmong-female')
    _, words = hmong_assets.reference('hmong-female')
    response = client.post('/api/voices/clone',
        data={'name': 'Kuv lub suab', 'language': 'mww', 'consent': 'true', 'transcript': words},
        files={'file': ('sample.mp3', source.read_bytes(), 'audio/mpeg')})
    assert response.status_code == 201, response.text
    profile = response.json()
    assert profile['engine'] == 'hmong_native' and profile['transcript'] == words
    assert profile['reference_start'] == 0 and abs(profile['reference_end'] - 4.7) < .03
    assert app.read_json(root / 'voices' / (profile['id'] + '.json')) == profile
    assert sf.info(str(root / 'voices' / (profile['id'] + '.wav'))).samplerate == 24000


@pytest.mark.parametrize('text,detail', [
    ('Nyob zoo 你好', 'RPA'),
    ('Kuv ua123', 'Mô hình không có'),
    ('Nyob/zoo.', 'Mô hình không có'),
])
def test_native_unsupported_text_is_rejected_before_queue(native_studio, text, detail):
    client, root, submit = native_studio
    response = client.post('/api/speech', json=speech_request(text=text))
    assert response.status_code == 422 and detail in response.text, response.text
    submit.assert_not_called()
    assert not list((root / 'jobs').iterdir())


def test_native_validation_keeps_the_original_script_case_and_rpa_tone_letters(native_studio):
    client, root, _ = native_studio
    script = 'UA thaj QAB faib ROV ris. POB POJ POS POV POM POG POD PO'
    response = client.post('/api/speech', json=speech_request(text=script))
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['text'] == script
    assert app.read_json(root / 'jobs' / (job['id'] + '.json'))['text'] == script
    assert [segment.text for segment in plan_segments(job)] == [script]


def test_native_prose_numbers_queue_original_source_and_plan_hmong_words(native_studio):
    client, root, submit = native_studio
    script = 'Kuv muaj 2 tug me nyuam thiab 200.000 nyiaj.'
    response = client.post('/api/speech', json=speech_request(text=script))
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['text'] == script
    assert app.read_json(root / 'jobs' / (job['id'] + '.json'))['text'] == script
    assert ' '.join(segment.text for segment in plan_segments(job)) == 'Kuv muaj ob tug me nyuam thiab ob puas txhiab nyiaj.'
    submit.assert_called_once_with(app.run_job, job['id'])


@pytest.mark.parametrize('speaker', ['hmong-male', 'hmong-female'])
def test_native_hyphenated_script_queues_with_exact_original_text_and_selected_reference(native_studio, speaker):
    client, root, submit = native_studio
    script = 'Nyob-zoo, kuv rov‑los tsev. POB–POJ POS—POV POM-POG POD-PO'
    response = client.post('/api/speech', json=speech_request(text=script, voice_id=speaker))
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['text'] == script and job['voice_id'] == job['speaker'] == speaker
    assert job['hmong_reference_fingerprint'] == hmong_assets.reference_fingerprint(speaker)
    assert app.read_json(root / 'jobs' / (job['id'] + '.json'))['text'] == script
    assert ' '.join(validate_native_text(segment.text) for segment in plan_segments(job)) == (
        'nyob zoo, kuv rov los tsev. pob poj pos pov pom pog pod po')
    submit.assert_called_once_with(app.run_job, job['id'])


@pytest.fixture
def native_worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    for name in ('_hmong_model_instance', '_hmong_native_instance', '_cached_key', '_cached_synth'):
        monkeypatch.setattr(module, name, None)
    (tmp_path / 'audio').mkdir(exist_ok=True)
    return module


def worker_job(**changes):
    return {'id': 'd' * 32, 'engine': 'hmong_native', 'speaker': 'hmong-male',
            'voice_id': 'hmong-male', 'language': 'mww', 'text': 'Nyob zoo.',
            'segment_plan': 'hmong-expression-v1', 'hmong_phrase_context': True,
            'auto_rhythm': False, 'emotion': 'warm', 'emotion_strength': .65,
            'input_format': 'txt', 'paragraph_pause': 0, 'speed': 1, 'format': 'wav',
            'max_minutes': 1, 'delivery': 'natural', 'hmong_steps': None,
            'hmong_reference_fingerprint': hmong_assets.reference_fingerprint('hmong-male'), **changes}


def engine_probe(calls, label):
    class Probe:
        def __init__(self):
            calls.append((label, 'load'))
            self._model = SimpleNamespace(precision='fp32', backend='vits_openvoice_v2')
            self.device = 'cpu'

        def set_progress_callback(self, callback):
            self.callback = callback

        def synthesize(self, text, reference, words, speed=1, quality='fast'):
            calls.append((label, text, Path(reference), words, speed, quality))
            self.callback('Đang tạo âm thanh native')
            return (.1 * np.sin(np.arange(2205, dtype=np.float32) * .1)).astype(np.float32), 22050
    return Probe


def test_worker_switches_backends_without_crossing_cached_models(native_worker, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, 'hmong_native', SimpleNamespace(
        SpeechEngine=engine_probe(calls, 'native'), validate_text=validate_native_text, EngineError=EngineError))
    monkeypatch.setitem(sys.modules, 'hmong_engine', SimpleNamespace(SpeechEngine=engine_probe(calls, 'f5')))
    job = worker_job()
    native_worker.get_synthesizer(job)('Nyob zoo.', tmp_path / 'native.wav')
    native_worker.get_synthesizer(job)('Ua tsaug.', tmp_path / 'native-again.wav')
    native_worker.get_synthesizer({**job, 'engine': 'f5_hmong', 'hmong_steps': 16})(
        'Nyob zoo.', tmp_path / 'f5.wav')
    assert native_worker._hmong_native_instance is None
    native_worker.get_synthesizer(job)('Nyob zoo.', tmp_path / 'native-return.wav')
    assert native_worker._hmong_model_instance is None
    assert [call for call in calls if call[1] == 'load'] == [('native', 'load'), ('f5', 'load'), ('native', 'load')]
    assert [(call[0], call[-2:]) for call in calls if call[1] != 'load'] == [
        ('native', (1.0, 'standard')), ('native', (1.0, 'standard')),
        ('f5', (.9, 'fast')), ('native', (1.0, 'standard'))]
    _, words = hmong_assets.reference('hmong-male')
    assert all(call[3] == words for call in calls if call[1] != 'load')
    assert read_progress(tmp_path / 'progress.json')['phase'] == 'Đang tạo âm thanh native'


def test_native_worker_outputs_pcm_and_actual_inference_metadata(native_worker, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, 'hmong_native', SimpleNamespace(
        SpeechEngine=engine_probe(calls, 'native'), validate_text=validate_native_text, EngineError=EngineError))
    job = worker_job()
    native_worker.render(job)
    result = json.loads((tmp_path / 'parts' / job['id'] / 'result.json').read_text())
    assert result['hmong_steps'] is None and result['hmong_precision'] == 'fp32'
    assert result['hmong_device'] == 'cpu' and result['hmong_backend'] == 'vits_openvoice_v2'
    assert result['expression']['phrase_context'] is True
    assert result['expression']['emotion_counts'] == {'warm': 1}
    output = tmp_path / 'audio' / (job['id'] + '.wav')
    samples, rate = sf.read(str(output))
    assert rate == 24000 and len(samples) > 0 and np.all(np.isfinite(samples)) and np.any(samples)
    assert result['spoken_audio_seconds'] > 0


def test_native_srt_expression_export_contains_only_the_spoken_words(native_studio, native_worker, monkeypatch):
    client, root, _ = native_studio
    monkeypatch.setitem(sys.modules, 'hmong_native', SimpleNamespace(
        SpeechEngine=engine_probe([], 'native'), validate_text=validate_native_text, EngineError=EngineError))
    script = ('1\n00:00:00,000 --> 00:00:01,000\n'
              '[emotion=warm]**Nyob zoo.**[pause=0.1]\n\n'
              '2\n00:00:02,000 --> 00:00:03,000\n'
              '[emotion=serious]Ua tsaug.\n')
    response = client.post('/api/speech', json=speech_request(text=script, input_format='srt'))
    assert response.status_code == 202, response.text
    job = response.json()
    native_worker.render(job)
    app.write_json(root / 'jobs' / (job['id'] + '.json'), {**job, 'status': 'done'})
    response = client.get('/api/jobs/' + job['id'] + '/script.srt')
    assert response.status_code == 200, response.text
    cues = parse_srt(response.text)
    assert [cue['text'] for cue in cues] == ['Nyob zoo.', 'Ua tsaug.']
    response = client.get('/api/jobs/' + job['id'] + '/export.txt')
    assert response.status_code == 200 and response.text == 'Nyob zoo.\n\nUa tsaug.\n'


@pytest.mark.parametrize('speaker', ['hmong-male', 'hmong-female'])
def test_native_worker_rejects_changed_preset_before_reusing_pcm(native_worker, tmp_path, speaker):
    job = worker_job(speaker=speaker, hmong_reference_fingerprint='previous-reference')
    work = tmp_path / 'parts' / job['id']
    work.mkdir(parents=True)
    checkpoint = work / '000000.wav'
    sf.write(str(checkpoint), np.ones(2400, dtype=np.float32) * .1, 24000)
    before = checkpoint.read_bytes()
    synthesize = Mock()
    with pytest.raises(ValueError, match='Tạo tác vụ mới'):
        native_worker.render(job, synthesize=synthesize)
    assert checkpoint.read_bytes() == before
    synthesize.assert_not_called()
    assert not (tmp_path / 'audio' / (job['id'] + '.wav')).exists()


@pytest.mark.parametrize('engine,script', [('hmong_native', 'prepare_hmong_native.py'),
                                         ('f5_hmong', 'prepare_hmong.py')])
def test_model_preparation_dispatches_to_the_recorded_hmong_backend(tmp_path, monkeypatch, engine, script):
    import subprocess
    import video_tasks
    path = tmp_path / 'video_tasks' / ('e' * 32) / 'job.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'action': 'prepare_voice', 'engine': engine}))
    run = Mock()
    monkeypatch.setattr(subprocess, 'run', run)
    video_tasks.run(path)
    run.assert_called_once()
    args, kwargs = run.call_args
    assert Path(args[0][1]).name == script and len(args[0]) == 2
    assert kwargs['check'] is True and kwargs['env']['VOICE_STUDIO_DATA_DIR'] == str(tmp_path)
    assert read_progress(path.parent / 'progress.json')['progress'] == 100


def test_unset_backend_preserves_f5_presets(monkeypatch):
    monkeypatch.delenv('HMOOB_BACKEND', raising=False)
    assert hmong_assets.active_engine() == 'f5_hmong'
    assert all(voice['engine'] == 'f5_hmong' for voice in hmong_assets.presets())


def test_native_model_readiness_delegates_to_the_native_manifest(monkeypatch):
    availability = Mock(return_value={'ready': False})
    monkeypatch.setitem(sys.modules, 'hmong_native', SimpleNamespace(availability=availability))
    assert app.model_ready('hmong_native') is False
    availability.return_value = {'ready': True}
    assert app.model_ready('hmong_native') is True
    assert availability.call_count == 2
