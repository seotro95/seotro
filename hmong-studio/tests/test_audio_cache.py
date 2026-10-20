import hashlib
import json
import os
from pathlib import Path
import struct
import wave

import pytest

import audio_cache
from audio_cache import AudioCache


def voice(path, value=125, frames=400, rate=24000):
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(struct.pack('<hh', value, -value) * (frames // 2))
    return path


def test_exact_unicode_tones_and_all_render_inputs_change_key():
    inputs = dict(text='Kuv hais lus Hmoob.', reference='reference-hash', emotion='review',
                  speed=1, cleanup='light', revision='pinned', device='cpu', precision='float32',
                  torch='2.6.0', algorithm='v1')
    expected = AudioCache.key(**inputs)
    assert len(expected) == 64 and expected == AudioCache.key(**dict(reversed(list(inputs.items()))))
    for name, changed in (('text', 'Kuv hais lus Hmoov.'), ('text', 'Kuv hais lus Hmoob!'),
                          ('text', 'kuv hais lus Hmoob.'), ('reference', 'other-reference'),
                          ('emotion', 'warm'), ('speed', 1.1), ('cleanup', 'off'),
                          ('revision', 'new-model'), ('device', 'cuda'), ('precision', 'float16'),
                          ('torch', 'another-torch'), ('algorithm', 'v2')):
        assert AudioCache.key(**{**inputs, name: changed}) != expected


def test_valid_entry_roundtrip_preserves_source_and_metadata_has_no_script(tmp_path):
    source = voice(tmp_path / 'source.wav')
    original = source.read_bytes()
    cache = AudioCache(tmp_path / 'cache')
    key = cache.key(text='Nyob zoo, kuv hais lus Hmoob.', reference='sha')
    assert cache.store(key, source)
    result = cache.read(key)
    assert result is not None and result.read_bytes() == original == source.read_bytes()
    metadata = (cache.root / (key + '.json')).read_text()
    assert 'Hmoob' not in metadata and 'Nyob' not in metadata
    assert json.loads(metadata)['sha256'] == hashlib.sha256(original).hexdigest()
    assert not list(cache.root.glob('.cache-entry-*'))


@pytest.mark.parametrize('damage', ['pcm', 'truncated', 'metadata', 'missing-metadata', 'format'])
def test_corrupt_entries_are_removed_and_report_miss(tmp_path, damage):
    cache = AudioCache(tmp_path / 'cache')
    source = voice(tmp_path / 'source.wav')
    key = cache.key(text='Hmoob')
    assert cache.store(key, source)
    audio, metadata = cache._paths(key)
    if damage == 'pcm':
        with audio.open('r+b') as stream:
            stream.seek(45)
            stream.write(b'\x01\x02')
    elif damage == 'truncated':
        with audio.open('r+b') as stream:
            stream.truncate(80)
    elif damage == 'metadata':
        metadata.write_text('{')
    elif damage == 'missing-metadata':
        metadata.unlink()
    else:
        voice(audio, rate=16000)
    assert cache.read(key) is None
    assert not audio.exists() and not metadata.exists()


def test_silent_and_wrong_format_source_are_not_cached(tmp_path):
    cache = AudioCache(tmp_path / 'cache')
    key = cache.key(text='Hmoob')
    for rate, value in ((24000, 0), (16000, 125)):
        source = voice(tmp_path / 'source.wav', value=value, rate=rate)
        before = source.read_bytes()
        assert not cache.store(key, source)
        assert source.read_bytes() == before
    assert cache.read(key) is None


def test_lru_entries_and_byte_budget_are_bounded(tmp_path):
    cache = AudioCache(tmp_path / 'cache', max_entries=2, max_bytes=3000)
    source = voice(tmp_path / 'source.wav')
    keys = [cache.key(text=str(i)) for i in range(4)]
    assert cache.store(keys[0], source)
    assert cache.store(keys[1], source)
    os.utime(cache._paths(keys[1])[0], (1, 1))
    assert cache.read(keys[0])
    assert cache.store(keys[2], source)
    assert cache.read(keys[1]) is None
    assert cache.read(keys[0]) and cache.read(keys[2])
    assert len(list(cache.root.glob('*.wav'))) == 2
    assert sum(path.stat().st_size for path in cache.root.iterdir()) <= cache.max_bytes


def test_byte_budget_evicts_even_when_entry_count_has_room(tmp_path):
    cache = AudioCache(tmp_path / 'cache', max_entries=10, max_bytes=1400)
    source = voice(tmp_path / 'source.wav')
    first, second = cache.key(text='first'), cache.key(text='second')
    assert cache.store(first, source)
    assert cache.store(second, source)
    assert cache.read(first) is None and cache.read(second)
    assert sum(path.stat().st_size for path in cache.root.iterdir()) <= 1400


def test_cache_failure_is_best_effort_and_temp_is_removed(tmp_path, monkeypatch):
    cache = AudioCache(tmp_path / 'cache')
    source = voice(tmp_path / 'source.wav')
    def locked(*args):
        raise PermissionError('Windows holds cache file')
    monkeypatch.setattr(audio_cache.os, 'replace', locked)
    assert not cache.store(cache.key(text='Hmoob'), source)
    assert not list(cache.root.glob('.cache-entry-*'))


def test_disabled_cache_and_custom_directory_do_not_read_or_write(tmp_path, monkeypatch):
    source = voice(tmp_path / 'source.wav')
    monkeypatch.setenv('HMONG_AUDIO_CACHE_DIR', str(tmp_path / 'private'))
    monkeypatch.setenv('HMONG_AUDIO_CACHE_DISABLED', '1')
    cache = AudioCache()
    assert cache.root == (tmp_path / 'private').resolve()
    assert not cache.store(cache.key(text='Hmoob'), source)
    assert cache.read(cache.key(text='Hmoob')) is None
    assert not cache.root.exists()


def test_cold_benchmark_can_bypass_reads_but_still_populate(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_AUDIO_CACHE_READS', '0')
    cache = AudioCache(tmp_path / 'cache')
    key = cache.key(text='Hmoob')
    assert cache.store(key, voice(tmp_path / 'source.wav'))
    assert cache.read(key) is None
    monkeypatch.setenv('HMONG_AUDIO_CACHE_READS', '1')
    assert AudioCache(cache.root).read(key)


@pytest.mark.parametrize('key', ['../outside', '', 'a' * 63, 'A' * 64, 'a/' + 'b' * 64])
def test_keys_cannot_escape_cache_directory(tmp_path, key):
    cache = AudioCache(tmp_path / 'cache')
    with pytest.raises(ValueError):
        cache.read(key)


def test_symlink_entry_never_changes_outside_audio(tmp_path):
    source = voice(tmp_path / 'source.wav')
    original = source.read_bytes()
    cache = AudioCache(tmp_path / 'cache')
    key = cache.key(text='Hmoob')
    assert cache.store(key, source)
    audio, metadata = cache._paths(key)
    audio.unlink()
    try:
        audio.symlink_to(source)
    except OSError:
        pytest.skip('symlinks not permitted')
    assert cache.read(key) is None
    assert source.read_bytes() == original


def test_reference_hash_checks_content_instead_of_only_filename_or_mtime(tmp_path):
    reference = tmp_path / 'reference.mp3'
    reference.write_bytes(b'first reference')
    timestamp = reference.stat().st_mtime_ns
    before = audio_cache.reference_digest(reference)
    reference.write_bytes(b'other reference')
    os.utime(reference, ns=(timestamp, timestamp))
    assert audio_cache.reference_digest(reference) != before
