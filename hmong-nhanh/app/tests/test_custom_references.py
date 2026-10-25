import hashlib
import json
from pathlib import Path

from fastapi import HTTPException
import numpy as np
import pytest
import soundfile as sf

import builtin_references
import custom_references as refs


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path / 'data'))


def source(tmp_path, frequency=220, seconds=9, rate=24000, channels=1, fmt='WAV'):
    path = tmp_path / f'upload-{frequency}-{rate}-{channels}.{fmt.lower()}'
    wave = np.sin(np.arange(round(seconds * rate)) * (2 * np.pi * frequency / rate)) * .25
    if channels > 1:
        wave = np.repeat(wave[:, None], channels, axis=1)
    sf.write(str(path), wave, rate, format=fmt)
    return path


def selection(text='The original sample is in English.', start=0, end=4):
    return builtin_references.ReferenceSettings(text=text, start=start, end=end)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_external_voices_remain_distinct_with_exact_original_language_transcripts(tmp_path):
    first_source, second_source = source(tmp_path), source(tmp_path, frequency=460)
    first = refs.register(first_source, 'English speaker', '../../not-a-destination.mp3')
    second = refs.register(second_source, '中文说话人', 'C:\\untrusted\\recording.wav')
    assert refs.ID_PATTERN.fullmatch(first) and first != second
    assert refs.original(first).name == 'source.wav'
    assert digest(refs.original(first)) == digest(first_source)
    assert refs.name(first) == 'English speaker'
    assert refs.name(second) == '中文说话人'
    assert set(refs.list_ids()) == {first, second}
    refs.save(first, selection())
    refs.save(second, selection(text='这是样本中原本说的话。', start=4, end=8))
    first_sample, first_text = refs.selected(first)
    second_sample, second_text = refs.selected(second)
    assert first_text == 'The original sample is in English.'
    assert second_text == '这是样本中原本说的话。'
    assert first_sample != second_sample and digest(first_sample) != digest(second_sample)
    for sample in (first_sample, second_sample):
        audio = sf.info(str(sample))
        assert audio.samplerate == 24000 and audio.channels == 1 and audio.frames == 96000
    assert not (tmp_path / 'not-a-destination.mp3').exists()


def test_resaving_is_immutable_and_selection_persists_without_memory_cache(tmp_path):
    ident = refs.register(source(tmp_path), 'Sample', 'voice.wav')
    refs.save(ident, selection())
    first_path, first_text = refs.selected(ident)
    first_digest = digest(first_path)
    refs.save(ident, selection(text='Another precisely transcribed clip.', start=4, end=8))
    current_path, current_text = refs.selected(ident)
    assert current_path != first_path
    assert digest(first_path) == first_digest
    assert first_text == 'The original sample is in English.'
    assert current_text == 'Another precisely transcribed clip.'
    # No in-memory catalog: a fresh module reads the same saved identity/pair.
    import importlib
    importlib.reload(refs)
    assert refs.selected(ident) == (current_path, current_text)
    assert refs.list_ids() == [ident]


def test_unprepared_or_missing_external_reference_never_uses_builtin(tmp_path):
    ident = refs.register(source(tmp_path), 'My own voice', 'voice.wav')
    with pytest.raises(HTTPException) as error:
        refs.selected(ident)
    assert error.value.status_code == 422
    refs.save(ident, selection())
    sample, _ = refs.selected(ident)
    sample.unlink()
    assert 'sample' not in refs.settings(ident)
    with pytest.raises(HTTPException) as error:
        refs.selected(ident)
    assert error.value.status_code == 422


def test_silent_selected_clip_is_rejected_without_publishing_settings(tmp_path):
    path = tmp_path / 'silent.wav'
    sf.write(str(path), np.zeros(24000 * 5), 24000, subtype='PCM_16')
    ident = refs.register(path, 'Silent recording', 'silent.wav')
    with pytest.raises(HTTPException) as error:
        refs.save(ident, selection())
    assert error.value.status_code == 422 and 'im lặng' in error.value.detail
    assert not (refs.directory() / ident / 'settings.json').exists()
    assert not list((refs.directory() / ident).glob('reference-*.wav'))


@pytest.mark.parametrize('kwargs', [{'seconds': 2}, {'seconds': 601, 'rate': 8000},
                                   {'channels': 3}, {'rate': 4000}, {'rate': 192001}, {'fmt': 'AIFF'}])
def test_unsupported_audio_is_rejected_before_catalog_publication(tmp_path, kwargs):
    with pytest.raises(HTTPException) as error:
        refs.register(source(tmp_path, **kwargs), 'Invalid audio', 'upload.wav')
    assert error.value.status_code == 422
    assert refs.list_ids() == []


def test_size_limit_and_malformed_upload(tmp_path):
    big = tmp_path / 'large.wav'
    with big.open('wb') as output:
        output.truncate(refs.MAX_UPLOAD_BYTES + 1)
    with pytest.raises(HTTPException) as error:
        refs.register(big, 'Too large', 'large.wav')
    assert error.value.status_code == 413
    invalid = tmp_path / 'invalid.mp3'
    invalid.write_text('This is not an audio file.')
    with pytest.raises(HTTPException) as error:
        refs.register(invalid, 'Invalid', 'invalid.mp3')
    assert error.value.status_code == 422
    assert refs.list_ids() == []


@pytest.mark.parametrize('value', ['', 'x' * 81, 'one\ntwo', 'voice\0name'])
def test_bad_names_are_rejected(tmp_path, value):
    with pytest.raises(HTTPException) as error:
        refs.register(tmp_path / 'not-read.wav', value, 'voice.wav')
    assert error.value.status_code == 422


def test_real_mp3_upload_format_is_detected_from_content():
    original = builtin_references.original('hmong-white-male')
    ident = refs.register(original, 'Uploaded MP3', 'wrong-extension.wav')
    assert refs.original(ident).suffix == '.mp3'
    refs.save(ident, selection())
    assert sf.info(str(refs.selected(ident)[0])).frames == 96000


def test_corrupted_or_redirected_metadata_does_not_escape_library(tmp_path):
    ident = refs.register(source(tmp_path), 'Sample', 'voice.wav')
    metadata = refs.directory() / ident / 'metadata.json'
    data = json.loads(metadata.read_text())
    data['source'] = '../../outside.wav'
    metadata.write_text(json.dumps(data))
    with pytest.raises(HTTPException) as error:
        refs.original(ident)
    assert error.value.status_code == 422
    assert refs.list_ids() == []
    for value in ('../../outside', 'hmong-white-male', 'custom-ABC', None):
        with pytest.raises(HTTPException) as error:
            refs.selected(value)
        assert error.value.status_code == 404


def test_forged_reference_path_is_not_read(tmp_path):
    ident = refs.register(source(tmp_path), 'Sample', 'voice.wav')
    folder = refs.directory() / ident
    (folder / 'settings.json').write_text(json.dumps({
        'text': 'Words', 'start': 0, 'end': 4, 'sample': '../../outside.wav'}))
    with pytest.raises(HTTPException) as error:
        refs.selected(ident)
    assert error.value.status_code == 422


def test_stereo_high_rate_clip_is_normalized_without_changing_transcript(tmp_path):
    ident = refs.register(source(tmp_path, rate=48000, channels=2), 'Stereo', 'voice.wav')
    refs.save(ident, selection(text='  Tiếng Việt gốc trong mẫu.  ', start=1, end=5))
    sample, text = refs.selected(ident)
    assert text == 'Tiếng Việt gốc trong mẫu.'
    audio = sf.info(str(sample))
    assert audio.samplerate == 24000 and audio.channels == 1 and audio.frames == 96000
