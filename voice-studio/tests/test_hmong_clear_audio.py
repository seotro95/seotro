"""Audio contract checks, not claims of pronunciation or speaker similarity."""
import importlib
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

import hmong_native as native
from narration import Segment


def test_marker_uses_one_second_at_16k_without_resampling_speech_or_splice_edges():
    torch = pytest.importorskip('torch')
    soxr = pytest.importorskip('soxr')
    t = np.arange(33075, dtype=np.float32) / native.SAMPLE_RATE
    # Include a 9 kHz component which would disappear if speech itself were
    # replaced by the 16 kHz round trip rather than adding only the residual.
    original = (.2 * np.sin(2*np.pi*210*t) + .05 * np.sin(2*np.pi*9000*t)).astype('float32')
    before = original.copy()
    seen = []
    def encode(signal, message):
        seen.append((signal.detach().numpy().copy(), message.detach().numpy().copy()))
        residual = .0005 * torch.sin(torch.arange(16000) * (2*np.pi*900/16000))
        return signal + residual.unsqueeze(0)
    result = native._mark_clear_audio(original, SimpleNamespace(encode=encode), 'cpu')
    assert len(seen) == 1 and seen[0][0].shape == (1, 16000)
    np.testing.assert_allclose(seen[0][0][0], soxr.resample(before[:22050], 22050, 16000, quality='HQ'))
    np.testing.assert_array_equal(seen[0][1][0], np.unpackbits(np.frombuffer(b'SEOT', dtype=np.uint8)))
    np.testing.assert_array_equal(original, before)
    np.testing.assert_array_equal(result[22050:], before[22050:])
    assert result[0] == before[0] and result[22049] == before[22049]
    assert result.dtype == np.float32 and np.isfinite(result).all()
    assert 0 < np.max(np.abs(result-before)) < .001


@pytest.mark.parametrize('failure', ['nonfinite', 'wrong-length', 'excessive-noise', 'isolated-peak'])
def test_corrupt_or_audibly_destructive_marker_fails_instead_of_being_saved(failure):
    torch = pytest.importorskip('torch')
    def encode(signal, message):
        result = signal.clone()
        if failure == 'nonfinite':
            result[0, 0] = float('nan')
        elif failure == 'wrong-length':
            return result[:, :-1]
        elif failure == 'excessive-noise':
            result += .1
        else:
            result[0, 8000] += .9
        return result
    with pytest.raises(native.EngineError):
        native._mark_clear_audio(np.full(22050, .2, dtype='float32'), SimpleNamespace(encode=encode), 'cpu')


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, '_cached_key', None)
    monkeypatch.setattr(module, '_cached_synth', None)
    monkeypatch.setattr(module, '_cast_synthesizers', module.OrderedDict())
    monkeypatch.setattr(module, '_cast_synth_engine', None)
    return module


def native_job(**changes):
    return {'engine': 'hmong_native', 'voice_id': 'hmong-female-3',
            'speaker': 'hmong-female-3', 'language': 'mww', 'input_format': 'txt',
            **changes}


def test_float_intermediate_preserves_peaks_until_final_pcm_normalization(worker, tmp_path, monkeypatch):
    received = []
    t = np.arange(4410, dtype=np.float32) / 22050
    source = (1.2 * np.sin(2*np.pi*200*t)).astype('float32')
    class Engine:
        def set_progress_callback(self, callback):
            pass
        def synthesize(self, *args, **kwargs):
            received.append(kwargs['audio_profile'])
            return source, 22050
    monkeypatch.setattr(worker, '_hmong_native_instance', Engine())
    raw, output = tmp_path/'raw.wav', tmp_path/'final.wav'
    worker.load_synthesizer(native_job(hmong_audio_profile='clear-v1'))('Nyob zoo.', raw)
    assert received == ['clear-v1'] and sf.info(raw).subtype == 'FLOAT'
    np.testing.assert_array_equal(sf.read(raw, dtype='float32')[0], source)
    worker.normalize_audio(raw, output, 1, 1, audio_profile='clear-v1')
    result, rate = sf.read(output, dtype='float32')
    assert sf.info(output).subtype == 'PCM_16' and rate == 24000
    assert .94 < np.max(np.abs(result)) <= .951
    # Unclipped crest factor remains that of the source sine.
    assert np.max(np.abs(result))/np.sqrt(np.mean(result**2)) == pytest.approx(np.sqrt(2), abs=.015)
    legacy = tmp_path/'legacy.wav'
    worker.load_synthesizer(native_job())('Nyob zoo.', legacy)
    assert received[-1] == 'legacy-v1' and sf.info(legacy).subtype == 'PCM_16'


@pytest.mark.parametrize('cast', [False, True])
def test_cached_closures_cannot_cross_audio_profile(worker, monkeypatch, cast):
    monkeypatch.setattr(worker, 'load_synthesizer', lambda job: object())
    job = native_job(character_cast={'version': 1} if cast else None)
    legacy = worker.get_synthesizer(job)
    assert worker.get_synthesizer({**job, 'hmong_audio_profile': 'legacy-v1'}) is legacy
    clear = worker.get_synthesizer({**job, 'hmong_audio_profile': 'clear-v1'})
    assert clear is not legacy
    assert worker.get_synthesizer({**job, 'hmong_audio_profile': 'clear-v1'}) is clear


def test_checkpoint_profile_is_bound_without_invalidating_legacy_job(worker):
    job = native_job(hmong_voice_snapshot={'id': 'frozen'})
    segment = Segment(text='Nyob zoo.')
    legacy = worker._chunk_identity(job, segment)
    assert legacy == worker._chunk_identity({**job, 'hmong_audio_profile': None}, segment)
    assert legacy == worker._chunk_identity({**job, 'hmong_audio_profile': 'legacy-v1'}, segment)
    assert legacy != worker._chunk_identity({**job, 'hmong_audio_profile': 'clear-v1'}, segment)
    old_unfrozen = native_job()
    assert worker._chunk_identity(old_unfrozen, segment) is None
    assert worker._chunk_identity({**old_unfrozen, 'hmong_audio_profile': 'clear-v1'}, segment)


@pytest.mark.parametrize('profile', ['', False, [], 'unknown'])
def test_invalid_persisted_profile_is_rejected_before_loading_a_model(worker, monkeypatch, profile):
    monkeypatch.setattr(worker, '_hmong_native_instance', None)
    with pytest.raises(ValueError, match='xử lý âm thanh'):
        worker.load_synthesizer(native_job(hmong_audio_profile=profile))
    assert worker._hmong_native_instance is None


def test_tempo_branch_does_not_add_limiter_makeup_gain(worker, tmp_path):
    t = np.arange(24000, dtype=np.float32)/24000
    raw = tmp_path/'source.wav'
    sf.write(raw, .2*np.sin(2*np.pi*200*t), 24000, subtype='FLOAT')
    clear, legacy = tmp_path/'clear.wav', tmp_path/'legacy.wav'
    worker.normalize_audio(raw, clear, .94, 1, audio_profile='clear-v1')
    worker.normalize_audio(raw, legacy, .94, 1)
    clear_samples = sf.read(clear)[0]
    legacy_samples = sf.read(legacy)[0]
    assert len(clear_samples) == len(legacy_samples)
    ratio = np.sqrt(np.mean(legacy_samples**2)/np.mean(clear_samples**2))
    assert ratio == pytest.approx(1/.95, abs=.001)
