"""Freeze every actor reference and never resume a chunk with another identity."""
import copy
import hashlib
import importlib
import json
import wave
from dataclasses import asdict

import numpy as np
import pytest
import soundfile as sf

import character_cast as cast
from narration import Segment


SRT = ('1\n00:00:00,000 --> 00:00:01,000\nNyob zoo.\n\n'
       '2\n00:00:01,000 --> 00:00:02,000\nPeb nyob ua ke.\n')


def pcm(path, value=1000, frames=2400):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(int(value).to_bytes(2, 'little', signed=True) * frames)


def personal_voice(root, ident, words='Nyob zoo.', value=1000):
    voice = {'id': ident, 'name': ident, 'engine': 'f5_hmong', 'languages': ['mww'],
             'transcript': words}
    directory = root / 'voices'
    directory.mkdir(exist_ok=True)
    (directory / (ident + '.json')).write_text(json.dumps(voice), encoding='utf-8')
    pcm(directory / (ident + '.wav'), value)
    return voice


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, '_cached_key', None)
    monkeypatch.setattr(module, '_cached_synth', None)
    monkeypatch.setattr(module, '_cast_synthesizers', module.OrderedDict())
    monkeypatch.setattr(module, '_cast_synth_engine', None)
    (tmp_path / 'audio').mkdir(exist_ok=True)
    return module


def cast_job(root):
    base = cast.make_voice_snapshot(personal_voice(root, 'base'), 'f5_hmong', 'mww', root)
    actor = cast.make_voice_snapshot(personal_voice(root, 'actor', value=2000), 'f5_hmong', 'mww', root)
    return {'id': 'a' * 32, 'engine': 'f5_hmong', 'voice_id': 'base', 'speaker': None,
            'language': 'mww', 'input_format': 'srt', 'text': SRT, 'format': 'wav',
            'speed': 1, 'paragraph_pause': 0, 'delivery': 'natural', 'cue_fit': 'strict',
            'max_cue_tempo': 1.5, 'hmong_steps': 16,
            'character_cast': {'version': 1, 'default_voice': base,
                               'voices': {'narrator': actor}, 'cues': ['narrator', None]}}


@pytest.mark.parametrize('voices,cues,count', [
    ([], [], 0), ({'person': 'voice'}, ['person'], 2),
    ({'person': 'voice'}, ['missing'], 1), ({'person': 'voice'}, [False], 1),
    ({'bad id': 'voice'}, [None], 1), ({'person': '../voice'}, [None], 1),
    ({'x' * 65: 'voice'}, [None], 1), ({str(n): 'voice' for n in range(33)}, [None], 1),
])
def test_public_assignments_reject_invalid_or_unmapped_cues(voices, cues, count):
    with pytest.raises(ValueError):
        cast.validate_cast_request(voices, cues, count)


def test_null_cue_preserves_selected_default_and_voice_deletion_guard(tmp_path):
    job = cast_job(tmp_path)
    assert cast.validate_cast(job) is job['character_cast']
    assert cast.settings_for_cue(job, 0)['voice_id'] == 'actor'
    default = cast.settings_for_cue(job, 1)
    assert default['voice_id'] == 'base' and default['character_id'] is None
    assert cast.cast_voice_ids(job) == {'base', 'actor'}


@pytest.mark.parametrize('changes', [{'engine': 'qwen_clone'}, {'engine': 'hmong_native'},
                                    {'languages': ['vi']}, {'transcript': None},
                                    {'transcript': ' '}, {'transcript': 'x' * 2001}])
def test_snapshot_rejects_incompatible_engine_language_and_reference(tmp_path, changes):
    voice = {**personal_voice(tmp_path, 'actor'), **changes}
    with pytest.raises(ValueError):
        cast.make_voice_snapshot(voice, 'f5_hmong', 'mww', tmp_path)


def test_snapshot_identity_binds_exact_words_and_recording(tmp_path):
    voice = personal_voice(tmp_path, 'actor')
    original = cast.make_voice_snapshot(voice, 'f5_hmong', 'mww', tmp_path)
    renamed = cast.make_voice_snapshot({**voice, 'name': 'Another name'}, 'f5_hmong', 'mww', tmp_path)
    assert original['hmong_reference_fingerprint'] == renamed['hmong_reference_fingerprint']
    changed_words = cast.make_voice_snapshot({**voice, 'transcript': 'Nyob zoo. '}, 'f5_hmong', 'mww', tmp_path)
    assert original['hmong_reference_fingerprint'] != changed_words['hmong_reference_fingerprint']
    pcm(tmp_path / 'voices' / 'actor.wav', 3000)
    changed_audio = cast.make_voice_snapshot(voice, 'f5_hmong', 'mww', tmp_path)
    assert original['hmong_reference_fingerprint'] != changed_audio['hmong_reference_fingerprint']


@pytest.mark.parametrize('damage', ['wrong_engine', 'wrong_language', 'missing_default',
                                    'missing_fingerprint', 'wrong_cue_count', 'empty_cast'])
def test_saved_cast_rejects_incomplete_or_mixed_snapshot(tmp_path, damage):
    job = cast_job(tmp_path)
    saved = job['character_cast']
    if damage == 'wrong_engine':
        saved['voices']['narrator']['engine'] = 'hmong_native'
    elif damage == 'wrong_language':
        saved['voices']['narrator']['language'] = 'vi'
    elif damage == 'missing_default':
        saved.pop('default_voice')
    elif damage == 'missing_fingerprint':
        saved['voices']['narrator'].pop('hmong_reference_fingerprint')
    elif damage == 'wrong_cue_count':
        saved['cues'].pop()
    else:
        job['character_cast'] = {}
    with pytest.raises(ValueError):
        cast.validate_cast(job)


@pytest.mark.parametrize('damage', ['words', 'audio', 'missing', 'malformed_metadata'])
def test_all_references_validate_before_render_mutates_existing_work(worker, tmp_path, damage):
    job = cast_job(tmp_path)
    unused = personal_voice(tmp_path, 'unused')
    job['character_cast']['voices']['unused'] = cast.make_voice_snapshot(unused, 'f5_hmong', 'mww', tmp_path)
    work = tmp_path / 'parts' / job['id']
    work.mkdir(parents=True)
    pcm(work / '000000.wav')
    (work / 'progress.json').write_text('{"preserve":true}')
    before = {path.name: path.read_bytes() for path in work.iterdir()}
    if damage == 'words':
        unused['transcript'] += ' '
        (tmp_path / 'voices' / 'unused.json').write_text(json.dumps(unused))
    elif damage == 'audio':
        pcm(tmp_path / 'voices' / 'unused.wav', 3000)
    elif damage == 'missing':
        (tmp_path / 'voices' / 'unused.wav').unlink()
    else:
        (tmp_path / 'voices' / 'unused.json').write_text('[]')
    calls = []
    with pytest.raises(ValueError, match='Tạo tác vụ mới'):
        worker.render(job, lambda *args: calls.append(args))
    assert calls == []
    assert {path.name: path.read_bytes() for path in work.iterdir()} == before
    assert list((tmp_path / 'audio').iterdir()) == []


def test_noncast_custom_snapshot_also_rejects_changed_words(worker, tmp_path):
    job = cast_job(tmp_path)
    snapshot = job.pop('character_cast')['default_voice']
    job.update(hmong_voice_snapshot=snapshot,
               hmong_reference_fingerprint=snapshot['hmong_reference_fingerprint'])
    record = json.loads((tmp_path / 'voices' / 'base.json').read_text())
    record['transcript'] = 'Peb nyob ua ke.'
    (tmp_path / 'voices' / 'base.json').write_text(json.dumps(record))
    with pytest.raises(ValueError, match='Tạo tác vụ mới'):
        worker.render(job)
    assert not (tmp_path / 'parts').exists()


def test_synthesizer_uses_frozen_custom_words(worker, tmp_path, monkeypatch):
    job = cast_job(tmp_path)
    snapshot = job['character_cast']['default_voice']
    record = json.loads((tmp_path / 'voices' / 'base.json').read_text())
    record['transcript'] = 'Mutable profile words must not replace the snapshot.'
    (tmp_path / 'voices' / 'base.json').write_text(json.dumps(record))
    received = []
    class Engine:
        def set_progress_callback(self, callback):
            pass

        def synthesize(self, text, path, words, **options):
            received.append(words)
            return np.full(2400, .1), 24000
    monkeypatch.setattr(worker, '_hmong_model_instance', Engine())
    single = {key: value for key, value in job.items() if key != 'character_cast'}
    single['hmong_voice_snapshot'] = snapshot
    worker.load_synthesizer(single)('Nyob zoo.', tmp_path / 'single.wav')
    worker.load_synthesizer(cast.settings_for_cue(job, 1))('Nyob zoo.', tmp_path / 'cast.wav')
    assert received == [snapshot['reference_text'], snapshot['reference_text']]


def test_render_uses_each_cast_voice_and_exports_assignments(worker, tmp_path, monkeypatch):
    job = cast_job(tmp_path)
    calls = []
    def load(settings):
        def synthesize(text, output):
            calls.append((settings['voice_id'], text))
            pcm(output, 2000 if settings['voice_id'] == 'actor' else 1000)
        return synthesize
    monkeypatch.setattr(worker, 'load_synthesizer', load)
    worker.render(job)
    assert calls == [('actor', 'Nyob zoo.'), ('base', 'Peb nyob ua ke.')]
    alignment = json.loads((tmp_path / 'parts' / job['id'] / 'alignment.json').read_text())
    assert [(cue['voice_id'], cue['character_id']) for cue in alignment['cues']] == [
        ('actor', 'narrator'), ('base', None)]
    assert alignment['sync_ok']


def test_chunk_reuses_only_matching_text_voice_settings_and_identity(worker, tmp_path):
    job = cast_job(tmp_path)
    segment = Segment(text='Nyob zoo.', cue=0)
    calls = []
    def synthesize(text, output):
        calls.append(text)
        pcm(output)
    worker.prepare_chunk(job, segment, 0, tmp_path, synthesize)
    worker.prepare_chunk(job, segment, 0, tmp_path, synthesize)
    assert len(calls) == 1
    changed = copy.deepcopy(job)
    changed['character_cast']['cues'][0] = None
    worker.prepare_chunk(changed, segment, 0, tmp_path, synthesize)
    assert len(calls) == 2
    worker.prepare_chunk(changed, Segment(text='Peb nyob ua ke.', cue=0), 0, tmp_path, synthesize)
    assert len(calls) == 3
    (tmp_path / '000000.identity.json').write_text('{broken')
    worker.prepare_chunk(changed, segment, 0, tmp_path, synthesize)
    assert len(calls) == 4


def test_every_cast_reference_and_audio_control_changes_checkpoint_identity(tmp_path):
    job = cast_job(tmp_path)
    segment = Segment(text='Nyob zoo.', cue=0)
    original = cast.checkpoint_identity(job, segment)
    for key, value in [('speed', 1.1), ('emotion_strength', .2), ('hmong_steps', 32)]:
        assert cast.checkpoint_identity({**job, key: value}, segment) != original
    changed = copy.deepcopy(job)
    changed['character_cast']['default_voice']['hmong_reference_fingerprint'] = 'f' * 64
    assert cast.checkpoint_identity(changed, segment) != original
    assert cast.checkpoint_identity(job, Segment(text='Nyob zoo.', cue=0, rhythm_pause=.2)) != original


def test_cast_cache_is_lru_and_backend_switch_releases_voices(worker, tmp_path, monkeypatch):
    job = cast_job(tmp_path)
    monkeypatch.setattr(worker, 'MAX_CAST_SYNTHESIZERS', 2)
    loads = []
    def load(settings):
        loads.append((settings['engine'], settings['voice_id']))
        return object()
    monkeypatch.setattr(worker, 'load_synthesizer', load)
    first = worker.get_synthesizer({**job, 'voice_id': 'one'})
    worker.get_synthesizer({**job, 'voice_id': 'two'})
    assert worker.get_synthesizer({**job, 'voice_id': 'one'}) is first
    worker.get_synthesizer({**job, 'voice_id': 'three'})
    assert len(worker._cast_synthesizers) == 2
    worker.get_synthesizer({**job, 'voice_id': 'two'})
    assert loads.count(('f5_hmong', 'two')) == 2
    worker.get_synthesizer({**job, 'engine': 'hmong_native', 'voice_id': 'native'})
    assert len(worker._cast_synthesizers) == 1
    worker.get_synthesizer({'engine': 'vieneu', 'voice_id': 'legacy'})
    assert not worker._cast_synthesizers


def chapter_job(**changes):
    return {'id': 'b' * 32, 'engine': 'f5_hmong', 'language': 'mww', 'voice_id': 'base',
            'input_format': 'txt', 'text': 'This display text must never be planned.',
            'format': 'wav', 'speed': 1, 'paragraph_pause': 0,
            '_longform_parent_id': 'c' * 32, '_longform_identity': 'd' * 64,
            '_PREPLANNED_SEGMENTS': [asdict(Segment(text='Nyob zoo.')),
                                     asdict(Segment(pause=.2)),
                                     asdict(Segment(text='Peb nyob ua ke.'))], **changes}


def test_private_chapter_uses_frozen_segments_and_reuses_matching_chunks(worker, tmp_path, monkeypatch):
    job = chapter_job()
    monkeypatch.setattr(worker, 'plan_segments', lambda job: pytest.fail('Do not reparse a frozen chapter'))
    calls = []
    def synthesize(text, output):
        calls.append(text)
        pcm(output)
    worker.render(job, synthesize)
    worker.render(job, synthesize)
    assert calls == ['Nyob zoo.', 'Peb nyob ua ke.']
    job['_PREPLANNED_SEGMENTS'][1]['pause'] = .3
    worker.render(job, synthesize)
    assert calls == ['Nyob zoo.', 'Peb nyob ua ke.'] * 2


@pytest.mark.parametrize('field,value', [('pause', float('nan')), ('pause', True),
    ('rhythm_pause', -1), ('emphasis', 'yes'), ('text', 'x' * 241),
    ('emotion', 'angry'), ('cue', 0), ('unexpected', 1)])
def test_private_segment_validation_precedes_checkpoint_mutation(worker, tmp_path, field, value):
    job = chapter_job()
    job['_PREPLANNED_SEGMENTS'][0][field] = value
    with pytest.raises(ValueError):
        worker.render(job)
    assert not (tmp_path / 'parts').exists()


def test_preplanned_segments_require_internal_chapter_identity(worker):
    job = chapter_job()
    job.pop('_longform_parent_id')
    with pytest.raises(ValueError):
        worker._planned_segments(job)


def test_private_chapter_rejects_truncated_final_pause(worker, tmp_path):
    job = chapter_job(max_minutes=.2 / 60)
    job['_PREPLANNED_SEGMENTS'] = [asdict(Segment(text='Nyob zoo.')),
                                  asdict(Segment(pause=.2))]
    with pytest.raises(ValueError, match='cắt khoảng nghỉ'):
        worker.render(job, lambda text, path: pcm(path, frames=2400))
    assert not (tmp_path / 'audio' / (job['id'] + '.wav')).exists()
    assert not (tmp_path / 'parts' / job['id'] / 'result.json').exists()


def test_worker_pipe_accepts_only_exact_private_chapter_identity(worker, tmp_path):
    job = chapter_job()
    parent, identity = job['_longform_parent_id'], job['_longform_identity']
    job['id'] = hashlib.sha256(f'longform-v1:{parent}:0001:{identity}'.encode()).hexdigest()[:32]
    path = tmp_path / 'parts' / parent / 'chapters' / '0001' / 'job.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(job))
    assert worker._load_worker_request(path) == job
    job['id'] = 'e' * 32
    path.write_text(json.dumps(job))
    assert worker._load_worker_request(path) is None
    assert worker._load_worker_request(tmp_path / 'outside.json') is None


@pytest.mark.parametrize('amplitude,gain', [(.9, 1.5), (.2, 1.12)])
def test_natural_speed_gain_keeps_waveform_ratios_without_clipping(worker, tmp_path, amplitude, gain):
    original = np.array([amplitude, amplitude / 2, -amplitude, -amplitude / 4] * 600,
                        dtype=np.float32)
    raw, normalized = tmp_path / 'raw.wav', tmp_path / 'normalized.wav'
    sf.write(raw, original, 24000, subtype='FLOAT')
    worker.normalize_audio(raw, normalized, 1, gain)
    samples, rate = sf.read(normalized)
    assert rate == 24000
    expected_gain = min(gain, .95 / amplitude)
    assert np.allclose(samples, original * expected_gain, atol=1 / 32768)
    assert abs(samples[0] / samples[1] - 2) < .001
    assert np.max(np.abs(samples)) <= .95004
