"""Signal-based suggestions select real samples, without transcript/quality claims."""
import numpy as np
import pytest
import soundfile as sf

from hmong_reference import (
    ReferenceError, crop_reference, decode_upload, describe_reference,
    select_reference, suggest_audio_reference,
)


def recording(tmp_path, *, duration=20, start=9, end=16, amplitude=.2):
    rate = 24000
    samples = np.zeros(round(duration * rate), dtype='float32')
    count = round((end - start) * rate)
    samples[round(start * rate):round(end * rate)] = amplitude * np.sin(np.arange(count) * 2 * np.pi * 220 / rate)
    path = tmp_path / 'unknown.wav'
    sf.write(path, samples, rate, subtype='PCM_16')
    return path


def test_native_long_recording_suggests_and_uses_later_signal_instead_of_first_silent_eight_seconds(tmp_path):
    decoded = recording(tmp_path)
    source = decoded.read_bytes()
    info = describe_reference(source, 20, require_transcript=False, decoded=decoded)
    assert info['known_preset'] is None and info['automatic'] is False
    assert info['requires_transcript'] is False and info['requires_selection'] is False
    assert info['automatic_selection'] is True and info['selection_source'] == 'signal_energy'
    assert info['reference_start'] > 8 and 3 <= info['reference_end'] - info['reference_start'] <= 8
    assert info['transcript'] == '' and info['transcript_verified'] is False
    selected = select_reference(source, 20, '', require_transcript=False, decoded=decoded)
    assert selected['reference_start'] == info['reference_start']
    assert selected['reference_end'] == info['reference_end']
    assert selected['automatic_selection'] is True and selected['automatic_reference'] is False
    output = tmp_path / 'selected.wav'
    crop_reference(decoded, output, selected['reference_start'], selected['reference_end'])
    samples, rate = sf.read(output)
    assert len(samples) / rate <= 8 and np.mean(samples ** 2) > .01


def test_manual_native_crop_remains_authoritative(tmp_path):
    decoded = recording(tmp_path)
    selected = select_reference(decoded.read_bytes(), 20, '', 10, 13,
                                require_transcript=False, decoded=decoded)
    assert (selected['reference_start'], selected['reference_end']) == (10, 13)
    assert selected['automatic_reference'] is False


def test_f5_still_requires_manual_long_crop_and_exact_words(tmp_path):
    decoded = recording(tmp_path)
    info = describe_reference(decoded.read_bytes(), 20, decoded=decoded)
    assert info['requires_selection'] and info['requires_transcript']
    assert info['automatic_selection'] is False and info['selection_source'] == 'manual'
    with pytest.raises(ReferenceError, match='dài hơn 8'):
        select_reference(decoded.read_bytes(), 20, 'Nyob zoo.', decoded=decoded)
    with pytest.raises(ReferenceError, match='Nhập đúng lời Hmong'):
        select_reference(decoded.read_bytes(), 20, '', 10, 13, decoded=decoded)


@pytest.mark.parametrize('duration,start,end', [(3, 0, 3), (3.001, .01, 2.99), (30, 25, 25.3)])
def test_short_or_sparse_signal_keeps_valid_sample_aligned_bounds(tmp_path, duration, start, end):
    decoded = recording(tmp_path, duration=duration, start=start, end=end)
    selected = suggest_audio_reference(decoded, duration)
    assert selected['start'] >= 0 and selected['end'] <= duration
    assert 3 <= selected['end'] - selected['start'] <= 8
    assert selected['start'] <= start < end <= selected['end']
    frames = round((selected['end'] - selected['start']) * 24000)
    assert frames >= 72000


def test_silent_or_mismatched_decoded_audio_does_not_get_a_fake_selection(tmp_path):
    decoded = recording(tmp_path, amplitude=0)
    with pytest.raises(ReferenceError, match='tín hiệu'):
        suggest_audio_reference(decoded, 20)
    decoded = recording(tmp_path)
    with pytest.raises(ReferenceError, match='Thời lượng'):
        suggest_audio_reference(decoded, 21)


def test_original_two_project_crops_and_text_remain_exact_with_auto_selection_available(tmp_path):
    from hmong_assets import ROOT, references
    for gender, item in references().items():
        source = (ROOT / item['file']).read_bytes()
        info = describe_reference(source, item['duration'], require_transcript=False, decoded=ROOT / item['reference_file'])
        assert info['known_preset'] == 'hmong-' + gender
        assert info['selection_source'] == 'verified_project_interval'
        assert info['reference_start'] == item['reference']['start']
        assert info['reference_end'] == item['reference']['end']
        assert info['transcript'] == item['reference']['text']


def test_decode_preserves_float_overshoot_with_constant_gain_before_pcm16_conversion(tmp_path):
    rate = 24000
    # Test-only sine proves normalization, not a speaker or voice quality.
    samples = 1.5 * np.sin(np.arange(4 * rate) * 2 * np.pi * 221 / rate)
    source = tmp_path / 'loud-float.wav'
    sf.write(source, samples, rate, subtype='FLOAT')
    output = tmp_path / 'normalized.wav'
    assert decode_upload(source, output) == 4
    normalized, actual_rate = sf.read(output)
    assert actual_rate == rate
    assert .949 < max(abs(normalized)) <= .951
    assert np.max(np.abs(normalized - samples * .95 / 1.5)) < 4e-5
    assert not list(tmp_path.glob('*.float.wav'))


def test_decode_does_not_change_safe_pcm16_audio_levels(tmp_path):
    source = recording(tmp_path, duration=4, start=0, end=4)
    output = tmp_path / 'normal.wav'
    decode_upload(source, output)
    before, _ = sf.read(source, dtype='int16')
    after, _ = sf.read(output, dtype='int16')
    np.testing.assert_array_equal(before, after)


def test_decode_rejection_removes_float_temporary(tmp_path):
    source = tmp_path / 'bad.mp3'
    source.write_bytes(b'not audio')
    with pytest.raises(ReferenceError, match='Không đọc được'):
        decode_upload(source, tmp_path / 'bad.wav')
    assert not list(tmp_path.glob('*.float.wav'))
