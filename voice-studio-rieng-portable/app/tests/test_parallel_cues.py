"""Real WAV fitting with concurrent stand-in TTS, never a throughput claim."""
import importlib
import json
import pickle
import threading
import time
import wave
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pytest

from subtitles import parse_srt


RATE = 24000


def write_tone(path, seconds, frequency):
    clock = np.arange(round(seconds*RATE))/RATE
    samples = (6000*np.sin(2*np.pi*frequency*clock)).astype('<i2')
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        audio.writeframes(samples.tobytes())


def read_pcm(path):
    with wave.open(str(path)) as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, RATE)
        return np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2')


def pitch(samples):
    spectrum = abs(np.fft.rfft(samples*np.hanning(len(samples))))
    return np.fft.rfftfreq(len(samples), 1/RATE)[np.argmax(spectrum)]


def job(ident='parallel', **settings):
    return {'id': ident, 'engine': 'vieneu', 'speaker': 'Synthetic reference',
            'voice_id': 'synthetic', 'language': 'vi', 'quality': 'standard',
            'text': '1\n00:00:00,250 --> 00:00:00,750\nCâu đầu.\n\n'
                    '2\n00:00:01,500 --> 00:00:02,000\nCâu sau.',
            'input_format': 'srt', 'format': 'wav', 'speed': 1,
            'nano_parallel': 2, 'nano_threads': 1, 'nano_steps': 4,
            'cue_fit': 'auto', 'max_cue_tempo': 1.5, 'audio_fit_backend': 'ffmpeg',
            'delivery': 'natural', 'paragraph_pause': 0, **settings}


@pytest.fixture
def renderer(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    monkeypatch.setattr(worker, '_nano_pool', None)
    monkeypatch.setattr(worker, '_nano_pool_key', None)
    (tmp_path/'audio').mkdir()
    monkeypatch.setattr(worker, 'ProcessPoolExecutor', lambda max_workers, **kwargs:
                        ThreadPoolExecutor(max_workers=max_workers))
    calls = []
    def synthesize(text, output):
        calls.append(text)
        write_tone(output, .7, 220 if 'đầu' in text else 440)
    monkeypatch.setattr(worker, 'get_synthesizer', lambda settings: synthesize)
    yield worker, tmp_path, calls
    worker.close_nano_pool()


def test_fit_runs_in_parallel_but_pcm_and_original_cues_stay_ordered(renderer, monkeypatch):
    worker, data, calls = renderer
    fit = worker.fit_cue_audio
    barrier = threading.Barrier(2)
    fitting_threads = set()
    def concurrent_fit(*args, **kwargs):
        fitting_threads.add(threading.get_ident())
        barrier.wait(timeout=5)
        return fit(*args, **kwargs)
    monkeypatch.setattr(worker, 'fit_cue_audio', concurrent_fit)
    worker.render(job())
    assert len(fitting_threads) == 2 and len(calls) == 2
    samples = read_pcm(data/'audio/parallel.wav')
    assert len(samples) == 2*RATE
    assert not np.any(samples[:RATE//4])
    assert not np.any(samples[round(.75*RATE):round(1.5*RATE)])
    assert pitch(samples[round(.32*RATE):round(.65*RATE)]) == pytest.approx(220, abs=15)
    assert pitch(samples[round(1.57*RATE):round(1.9*RATE)]) == pytest.approx(440, abs=15)
    assert parse_srt((data/'audio/parallel.srt').read_text()) == parse_srt(job()['text'])
    alignment = json.loads((data/'parts/parallel/alignment.json').read_text())
    result = json.loads((data/'parts/parallel/result.json').read_text())
    assert alignment['sync_ok'] and [c['spoken_start'] for c in alignment['cues']] == [.25, 1.5]
    assert result['completed'] == result['total'] == 2
    assert result['spoken_audio_seconds'] <= 1
    assert result['execution_settings']['cue_fit_pipeline'] == 'parallel'


def test_wsola_auto_overlaps_main_process_fitting_with_chunk_workers(renderer, monkeypatch):
    worker, data, calls = renderer
    fit = worker.fit_cue_audio
    fitting_threads = set()
    def main_fit(*args, **kwargs):
        fitting_threads.add(threading.get_ident())
        return fit(*args, **kwargs)
    def unexpected(*args, **kwargs):
        pytest.fail('Fast automatic WSOLA must use chunk prefetch and main-process fitting.')
    monkeypatch.setattr(worker, 'fit_cue_audio', main_fit)
    monkeypatch.setattr(worker, 'prepare_cue', unexpected)
    worker.render(job('wsola-fast', audio_fit_backend='wsola'))
    assert fitting_threads == {threading.get_ident()} and len(calls) == 2
    result = json.loads((data/'parts/wsola-fast/result.json').read_text())
    assert result['execution_settings']['cue_fit_pipeline'] == 'serial'
    assert len(read_pcm(data/'audio/wsola-fast.wav')) == 2*RATE
    assert json.loads((data/'parts/wsola-fast/alignment.json').read_text())['sync_ok']


@pytest.mark.parametrize('backend', ['wsola', 'ffmpeg'])
def test_parallel_matches_sequential_timeline_and_complete_cue_chunks(renderer, monkeypatch, backend):
    worker, data, _ = renderer
    text = ('1\n00:00:00,250 --> 00:00:01,150\nCâu đầu.\nMột lời nữa.\n\n'
            '2\n00:00:01,500 --> 00:00:02,400\nCâu sau.')
    worker.render(job('sequential', text=text, nano_parallel=1, audio_fit_backend=backend))
    worker.render(job('concurrent', text=text, audio_fit_backend=backend))
    sequential = read_pcm(data/'audio/sequential.wav')
    concurrent = read_pcm(data/'audio/concurrent.wav')
    assert np.array_equal(sequential, concurrent)
    assert len(concurrent) == round(2.4*RATE)
    assert parse_srt((data/'audio/concurrent.srt').read_text()) == parse_srt(text)
    result = json.loads((data/'parts/concurrent/result.json').read_text())
    assert result['completed'] == result['total'] == 3
    assert result['execution_settings']['cue_fit_pipeline'] == ('serial' if backend == 'wsola' else 'parallel')
    alignment = json.loads((data/'parts/concurrent/alignment.json').read_text())
    assert alignment['sync_ok'] and len(alignment['cues']) == 2


def test_out_of_order_preparation_cannot_reorder_spoken_cues(renderer, monkeypatch):
    worker, data, _ = renderer
    original = worker.prepare_cue
    finished = []
    def delayed(settings, cue_index, *args):
        if cue_index == 0:time.sleep(.08)
        result = original(settings, cue_index, *args)
        finished.append(cue_index)
        return result
    monkeypatch.setattr(worker, 'prepare_cue', delayed)
    worker.render(job())
    assert finished == [1, 0]
    samples = read_pcm(data/'audio/parallel.wav')
    assert pitch(samples[round(.32*RATE):round(.65*RATE)]) == pytest.approx(220, abs=15)
    assert pitch(samples[round(1.57*RATE):round(1.9*RATE)]) == pytest.approx(440, abs=15)


@pytest.mark.parametrize('tamper', ['fitted_wave', 'metadata', 'input_part'])
def test_fitted_checkpoint_reuse_is_verified_and_invalidated_when_inputs_change(renderer, monkeypatch, tamper):
    worker, data, calls = renderer
    fit = worker.fit_cue_audio
    fitting = []
    def counted_fit(*args, **kwargs):
        fitting.append(args[0])
        return fit(*args, **kwargs)
    monkeypatch.setattr(worker, 'fit_cue_audio', counted_fit)
    worker.render(job())
    original = (data/'audio/parallel.wav').read_bytes()
    assert len(fitting) == 2 and len(calls) == 2
    worker.render(job())
    assert len(fitting) == 2 and len(calls) == 2
    assert (data/'audio/parallel.wav').read_bytes() == original
    work = data/'parts/parallel'
    if tamper == 'metadata':
        path = work/'fitted-cues/000000.json'
        value = json.loads(path.read_text()); value['result']['tempo'] = 99
        path.write_text(json.dumps(value))
    else:
        path = work/('fitted-cues/000000.wav' if tamper == 'fitted_wave' else '000000.wav')
        content = bytearray(path.read_bytes()); content[-1] ^= 1; path.write_bytes(content)
    worker.render(job())
    assert len(fitting) == 3 and len(calls) == 2
    assert len(read_pcm(data/'audio/parallel.wav')) == 2*RATE
    if tamper != 'input_part':assert (data/'audio/parallel.wav').read_bytes() == original


def test_changed_fit_mode_reuses_speech_but_refits_with_new_settings(renderer, monkeypatch):
    worker, data, calls = renderer
    worker.render(job('resume', cue_fit='strict', max_cue_tempo=2))
    assert len(calls) == 2
    fit = worker.fit_cue_audio
    fitting = []
    def counted_fit(*args, **kwargs):
        fitting.append(args[0])
        return fit(*args, **kwargs)
    monkeypatch.setattr(worker, 'fit_cue_audio', counted_fit)
    worker.render(job('resume', cue_fit='auto', max_cue_tempo=1.5))
    assert len(calls) == 2 and len(fitting) == 2
    assert json.loads((data/'parts/resume/alignment.json').read_text())['sync_ok']


def test_strict_failure_is_identified_without_publishing_partial_audio(renderer):
    worker, data, _ = renderer
    text = '1\n00:00:00,000 --> 00:00:00,200\nCâu đầu.\n\n2\n00:00:01,000 --> 00:00:02,000\nCâu sau.'
    with pytest.raises(ValueError, match='Câu SRT 1 đọc quá dài'):
        worker.render(job('strict-failure', text=text, cue_fit='strict'))
    assert not (data/'audio/strict-failure.wav').exists()
    alignment = json.loads((data/'parts/strict-failure/alignment.json').read_text())
    assert not alignment['sync_ok'] and alignment['failed_cue'] == 1
    assert alignment['cues'][0]['status'] == 'too_long'
    # The production pool serializes exceptions in the same way.
    error = worker.CuePreparationError('cue failed', {'cue': 1})
    restored = pickle.loads(pickle.dumps(error))
    assert str(restored) == 'cue failed' and restored.record == {'cue': 1}


def test_gap_mode_keeps_following_start_and_matches_sequential(renderer):
    worker, data, _ = renderer
    text = '1\n00:00:00,000 --> 00:00:00,250\nCâu đầu.\n\n2\n00:00:01,500 --> 00:00:01,750\nCâu sau.'
    worker.render(job('gap-one', text=text, cue_fit='gap', timeline_seconds=3, nano_parallel=1))
    worker.render(job('gap-many', text=text, cue_fit='gap', timeline_seconds=3))
    assert np.array_equal(read_pcm(data/'audio/gap-one.wav'), read_pcm(data/'audio/gap-many.wav'))
    exported = parse_srt((data/'audio/gap-many.srt').read_text())
    assert exported[0]['end'] == .7 and exported[1]['start'] == 1.5 and exported[1]['end'] == 2.2


def test_cancel_preserves_chunk_and_resume_uses_it_without_missing_words(renderer, monkeypatch):
    worker, data, calls = renderer
    first = True
    def synthesize(text, output):
        nonlocal first
        calls.append(text)
        write_tone(output, .7, 220 if 'đầu' in text else 440)
        if first and 'đầu' in text:
            first = False
            (data/'parts/cancel/cancel.flag').touch()
    monkeypatch.setattr(worker, 'get_synthesizer', lambda settings: synthesize)
    with pytest.raises(InterruptedError):worker.render(job('cancel'))
    assert (data/'parts/cancel/000000.wav').exists()
    assert not (data/'audio/cancel.wav').exists()
    (data/'parts/cancel/cancel.flag').unlink()
    worker.render(job('cancel'))
    assert calls.count('Câu đầu.') == 1
    assert json.loads((data/'parts/cancel/alignment.json').read_text())['sync_ok']
    assert len(read_pcm(data/'audio/cancel.wav')) == 2*RATE


def test_spawned_processes_fit_existing_speech_checkpoints_without_loading_ai(renderer, monkeypatch):
    worker, data, calls = renderer
    work = data/'parts/spawned'
    work.mkdir(parents=True)
    write_tone(work/'000000.wav', .7, 220)
    write_tone(work/'000001.wav', .7, 440)
    monkeypatch.setattr(worker, 'ProcessPoolExecutor', ProcessPoolExecutor)
    worker.render(job('spawned'))
    assert not calls
    assert len(read_pcm(data/'audio/spawned.wav')) == 2*RATE
    alignment = json.loads((work/'alignment.json').read_text())
    assert alignment['sync_ok'] and [c['spoken_start'] for c in alignment['cues']] == [.25, 1.5]
