"""Deterministic signal checks; these are not speaker or speech quality tests."""
import array
import json
import math
import sys
import wave

import pytest

from reference_quality import analyze_reference


def write_wave(path, samples, *, channels=1, rate=24000, width=2):
    data = array.array('h', samples)
    if sys.byteorder != 'little':
        data.byteswap()
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(channels)
        output.setsampwidth(width)
        output.setframerate(rate)
        output.writeframes(data.tobytes())


def tone(seconds, amplitude=4000):
    return [round(amplitude * math.sin(2 * math.pi * 200 * index / 24000))
            for index in range(round(seconds * 24000))]


def test_clean_reference_reports_measurements_without_claiming_speech_or_identity(tmp_path):
    path = tmp_path / 'clean.wav'
    write_wave(path, tone(4))
    original = path.read_bytes()
    result = analyze_reference(path)
    assert result['duration_seconds'] == result['active_audio_seconds'] == 4
    assert result['quiet_fraction'] == result['clipped_sample_ratio'] == 0
    assert -22 < result['rms_dbfs'] < -20
    assert -19 < result['peak_dbfs'] < -18
    assert not result['attention_recommended'] and result['advisories'] == []
    assert len(result['guidance']) == 3
    assert 'không xác nhận có tiếng nói' in result['analysis_note']
    assert path.read_bytes() == original
    json.dumps(result, allow_nan=False)


def test_quiet_intervals_are_measured_by_duration_and_warn_without_altering_audio(tmp_path):
    path = tmp_path / 'quiet.wav'
    write_wave(path, [0] * 48000 + tone(1))
    result = analyze_reference(path)
    assert result['duration_seconds'] == 3
    assert result['active_audio_seconds'] == 1
    assert result['quiet_fraction'] == pytest.approx(2 / 3, abs=.000001)
    assert any('nhiều khoảng âm lượng thấp' in item for item in result['advisories'])


def test_full_scale_samples_raise_clipping_advisory_without_identity_score(tmp_path):
    path = tmp_path / 'clipped.wav'
    write_wave(path, [32767, -32768] * 36000)
    result = analyze_reference(path)
    assert result['clipped_sample_ratio'] == 1
    assert result['peak_dbfs'] == 0
    assert result['attention_recommended']
    assert any('nếu nghe rè' in item for item in result['advisories'])
    assert not any('similarity' in key or 'snr' in key or 'score' in key for key in result)


def test_silence_has_finite_json_and_low_level_advice(tmp_path):
    path = tmp_path / 'silent.wav'
    write_wave(path, [0] * 72000)
    result = analyze_reference(path)
    assert result['peak_dbfs'] is None and result['rms_dbfs'] is None
    assert result['active_audio_seconds'] == 0 and result['quiet_fraction'] == 1
    assert any('Âm lượng bản thu thấp' in item for item in result['advisories'])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('options', [{'channels': 2}, {'rate': 22050}, {'width': 1}])
def test_non_normalized_wave_is_rejected(tmp_path, options):
    path = tmp_path / 'wrong-format.wav'
    write_wave(path, tone(3), **options)
    with pytest.raises(ValueError, match='WAV mono PCM'):
        analyze_reference(path)


def test_truncated_or_unreadable_wav_is_rejected(tmp_path):
    path = tmp_path / 'truncated.wav'
    write_wave(path, tone(3))
    path.write_bytes(path.read_bytes()[:-2])
    with pytest.raises(ValueError, match='Không đủ dữ liệu'):
        analyze_reference(path)
    path.write_bytes(b'not a wave')
    with pytest.raises(ValueError, match='Không đọc được WAV'):
        analyze_reference(path)
