"""Real reference decoding stays exact, private, bounded and fresh per voice."""
import ctypes as C
import os

import numpy as np
import pytest
import soundfile as sf

import native_synthesis as native


@pytest.fixture
def session():
    # Native handles are irrelevant to reference decoding. No model, network or
    # native library is needed to exercise real libsndfile reads and WAV files.
    instance = native.NativeSession.__new__(native.NativeSession)
    instance.lib = None
    instance.registry = instance.model = instance.session = C.c_void_p()
    instance._dll_directory = None
    yield instance
    instance.close()


def tone(frames=2400, frequency=.07):
    return (np.sin(np.arange(frames, dtype=np.float32) * frequency) * .2).astype(np.float32)


def recording(path, samples=None, rate=24000):
    samples = tone() if samples is None else samples
    sf.write(path, samples, rate, subtype='FLOAT')
    return path


@pytest.fixture
def reads(monkeypatch):
    calls = []
    original = sf.read

    def tracked(path, *args, **kwargs):
        calls.append(str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(sf, 'read', tracked)
    return calls


def test_unchanged_wav_decodes_once_without_changing_samples_or_rate(session, tmp_path, reads):
    expected = tone()
    path = recording(tmp_path / 'same-speaker.wav', expected)
    first, rate = session._reference_audio(path)
    second, second_rate = session._reference_audio(path.parent / '.' / path.name)
    assert reads == [str(path.resolve())]
    assert first is second and rate == second_rate == 24000
    assert first.dtype == np.float32 and first.flags.c_contiguous
    assert not first.flags.writeable
    assert np.array_equal(first, expected)
    assert session._reference_cache_bytes == expected.nbytes


def test_stereo_uses_exact_existing_mono_mean_and_original_sample_rate(session, tmp_path, reads):
    source = np.column_stack((tone(), tone(frequency=.13)))
    path = recording(tmp_path / 'stereo.wav', source, rate=48000)
    samples, rate = session._reference_audio(path)
    again, _ = session._reference_audio(path)
    assert rate == 48000 and len(reads) == 1 and samples is again
    assert np.array_equal(samples, source.mean(axis=1))


def test_distinct_recordings_do_not_reuse_another_speakers_samples(session, tmp_path, reads):
    first, second = tone(), tone(frequency=.19)
    a = recording(tmp_path / 'voice-a.wav', first)
    b = recording(tmp_path / 'voice-b.wav', second)
    assert np.array_equal(session._reference_audio(a)[0], first)
    assert np.array_equal(session._reference_audio(b)[0], second)
    assert np.array_equal(session._reference_audio(a)[0], first)
    assert len(reads) == 2 and len(session._reference_cache) == 2


def test_same_path_edit_invalidates_previous_pcm(session, tmp_path, reads):
    path = recording(tmp_path / 'edited.wav')
    previous = session._reference_audio(path)[0]
    old_stat = path.stat()
    replacement = tone(frequency=.21)
    recording(path, replacement)
    # Explicitly advance mtime for filesystems with coarse timestamp resolution.
    os.utime(path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 1_000_000_000))
    fresh, _ = session._reference_audio(path)
    assert len(reads) == 2 and fresh is not previous
    assert np.array_equal(fresh, replacement)
    assert len(session._reference_cache) == 1
    assert session._reference_cache_bytes == replacement.nbytes


def test_replacement_with_equal_size_and_mtime_invalidates_pcm(session, tmp_path, reads):
    path = recording(tmp_path / 'replaced.wav')
    first, _ = session._reference_audio(path)
    original = path.stat()
    next_path = recording(tmp_path / 'incoming.wav', tone(frequency=.29))
    os.utime(next_path, ns=(original.st_atime_ns, original.st_mtime_ns))
    next_path.replace(path)
    assert path.stat().st_size == original.st_size
    assert path.stat().st_mtime_ns == original.st_mtime_ns
    fresh, _ = session._reference_audio(path)
    assert len(reads) == 2 and fresh is not first
    assert np.array_equal(fresh, tone(frequency=.29))
    assert len(session._reference_cache) == 1


@pytest.mark.parametrize('samples', [
    np.zeros(2400, dtype=np.float32),
    np.full(2400, np.nan, dtype=np.float32),
    np.full(2400, np.inf, dtype=np.float32),
    np.column_stack((tone(), -tone())),
])
def test_silent_nonfinite_and_stereo_cancellation_are_rejected_and_not_cached(session, tmp_path, samples):
    path = recording(tmp_path / 'invalid.wav', samples)
    with pytest.raises(ValueError, match='tiếng hợp lệ'):
        session._reference_audio(path)
    assert not session._reference_cache and session._reference_cache_bytes == 0


@pytest.mark.parametrize('samples,rate', [
    (np.empty(0, dtype=np.float32), 24000),
    (np.column_stack((tone(), tone(), tone())), 24000),
    (tone(), 4000),
    (tone(frames=24000 * 30 + 1), 24000),
])
def test_invalid_reference_metadata_is_rejected(session, tmp_path, samples, rate):
    path = recording(tmp_path / 'invalid-metadata.wav', samples, rate)
    with pytest.raises(ValueError, match='tối đa 30 giây'):
        session._reference_audio(path)
    assert not session._reference_cache and session._reference_cache_bytes == 0


def test_malformed_replacement_cannot_reuse_previously_valid_voice(session, tmp_path, reads):
    path = recording(tmp_path / 'valid-then-broken.wav')
    session._reference_audio(path)
    path.write_bytes(b'This is not an audio file')
    with pytest.raises((ValueError, RuntimeError)):
        session._reference_audio(path)
    assert len(reads) == 1
    assert not session._reference_cache and session._reference_cache_bytes == 0


def test_recording_changed_during_read_is_rejected_without_cache(session, tmp_path, monkeypatch):
    path = recording(tmp_path / 'changing.wav')
    original = sf.read

    def changing(*args, **kwargs):
        result = original(*args, **kwargs)
        recording(path, tone(frames=3600))
        return result

    monkeypatch.setattr(sf, 'read', changing)
    with pytest.raises(ValueError, match='thay đổi'):
        session._reference_audio(path)
    assert not session._reference_cache and session._reference_cache_bytes == 0


def test_cache_evicts_least_recently_used_voice_at_reference_limit(session, tmp_path, monkeypatch, reads):
    monkeypatch.setattr(native, '_REFERENCE_CACHE_MAX_ENTRIES', 2)
    a, b, c = [recording(tmp_path / f'{name}.wav') for name in ('a', 'b', 'c')]
    session._reference_audio(a)
    session._reference_audio(b)
    session._reference_audio(a)
    session._reference_audio(c)
    assert len(reads) == 3 and len(session._reference_cache) == 2
    assert [key[0] for key in session._reference_cache] == [str(a), str(c)]
    session._reference_audio(b)
    assert len(reads) == 4 and len(session._reference_cache) == 2


def test_retained_pcm_stays_within_memory_budget(session, tmp_path, monkeypatch, reads):
    size = tone().nbytes
    monkeypatch.setattr(native, '_REFERENCE_CACHE_MAX_ENTRIES', 8)
    monkeypatch.setattr(native, '_REFERENCE_CACHE_MAX_BYTES', size * 2)
    paths = [recording(tmp_path / f'{i}.wav') for i in range(3)]
    for path in paths:
        session._reference_audio(path)
        assert session._reference_cache_bytes <= size * 2
    assert len(session._reference_cache) == 2
    assert session._reference_cache_bytes == size * 2
    session._reference_audio(paths[0])
    assert len(reads) == 4 and session._reference_cache_bytes == size * 2


def test_valid_reference_over_budget_is_used_without_retaining_it(session, tmp_path, monkeypatch, reads):
    expected = tone()
    monkeypatch.setattr(native, '_REFERENCE_CACHE_MAX_BYTES', expected.nbytes - 1)
    path = recording(tmp_path / 'over-budget.wav', expected)
    for _ in range(2):
        samples, rate = session._reference_audio(path)
        assert np.array_equal(samples, expected) and rate == 24000
    assert len(reads) == 2
    assert not session._reference_cache and session._reference_cache_bytes == 0


def test_close_releases_all_cached_recordings(session, tmp_path, reads):
    path = recording(tmp_path / 'private.wav')
    session._reference_audio(path)
    assert session._reference_cache_bytes > 0
    session.close()
    assert not session._reference_cache and session._reference_cache_bytes == 0
    # A new request after cleanup must read and validate the reference afresh.
    session._reference_audio(path)
    assert len(reads) == 2
