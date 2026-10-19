"""Real FFmpeg checks for cleanup quality, timing and safe publication."""
from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np
import pytest

import audio_clean


pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is required")
RATE = 24_000


def write_wav(path, samples, rate=RATE, channels=1):
    values = np.asarray(samples)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(np.round(values * 32767).astype("<i2").tobytes())
    return path


def read_wav(path):
    with wave.open(str(path), "rb") as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, RATE)
        frames = audio.getnframes()
        samples = np.frombuffer(audio.readframes(frames), dtype="<i2").astype(float) / 32768
    return samples


def voice(seconds=3):
    time = np.arange(round(seconds * RATE)) / RATE
    return .2 * np.sin(2 * np.pi * 500 * time) + .07 * np.sin(2 * np.pi * 1500 * time)


@pytest.mark.parametrize("level", ["off", "light", "strong"])
def test_reference_accepts_stereo_mp3_and_caps_at_ten_seconds(tmp_path, level):
    source_wav = write_wav(tmp_path / "stereo.wav",
                           np.tile(voice(12.25)[:, None], (1, 2)), channels=2)
    source = tmp_path / "original.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(source_wav), str(source)], check=True)
    before = source.read_bytes()
    result = audio_clean.clean_reference(source, tmp_path / "clean.wav", level)
    samples = read_wav(result)
    assert len(samples) == 10 * RATE
    assert 0 < np.max(np.abs(samples)) < 1
    assert source.read_bytes() == before
    assert not list(tmp_path.glob(".audio-clean-*"))


def test_light_reduces_rumble_and_hiss_while_preserving_voice_harmonics(tmp_path):
    time = np.arange(8 * RATE) / RATE
    rng = np.random.default_rng(3)
    source = .06 * np.sin(2 * np.pi * 50 * time) + rng.normal(0, .003, len(time))
    source += ((time >= 2) & (time < 5)) * (
        .2 * np.sin(2 * np.pi * 500 * time) + .07 * np.sin(2 * np.pi * 1500 * time))
    original = write_wav(tmp_path / "noisy.wav", source)
    cleaned = read_wav(audio_clean.polish_audio(original, tmp_path / "clean.wav"))

    def amplitude(samples, frequency):
        section = slice(int(2.5 * RATE), int(4.5 * RATE))
        return abs(2 * np.mean(samples[section] * np.exp(-2j * np.pi * frequency * time[section])))

    assert amplitude(cleaned, 50) / amplitude(source, 50) < .72
    for harmonic in (500, 1500):
        assert .95 < amplitude(cleaned, harmonic) / amplitude(source, harmonic) < 1.05
    section = slice(6 * RATE, 7 * RATE)
    bins = np.fft.rfftfreq(RATE, 1 / RATE)
    hiss_band = (bins > 4000) & (bins < 10000)
    input_power = np.sum(abs(np.fft.rfft(source[section]))[hiss_band] ** 2)
    output_power = np.sum(abs(np.fft.rfft(cleaned[section]))[hiss_band] ** 2)
    assert 10 * np.log10(output_power / input_power) < -1.5
    assert len(cleaned) == len(source)


@pytest.mark.parametrize("level", ["light", "strong"])
def test_subtitle_gaps_and_exact_frame_count_survive_in_place(tmp_path, level):
    # Subtitles at 00:00:00,200 and 00:00:02,700; neither pauses nor tail
    # may disappear, and the limiter must compensate its lookahead delay.
    samples = np.zeros(4 * RATE + 137)
    samples[int(.2 * RATE):RATE] = voice(.8)
    samples[int(2.7 * RATE):int(3.5 * RATE)] = voice(.8)
    target = write_wav(tmp_path / "subtitles.wav", samples)
    assert audio_clean.polish_audio(target, target, level) == target
    result = read_wav(target)
    assert len(result) == len(samples)
    assert np.max(abs(result[:int(.15 * RATE)])) == 0
    assert np.max(abs(result[int(1.15 * RATE):int(2.65 * RATE)])) == 0
    assert np.max(abs(result[int(3.7 * RATE):])) == 0
    # Onsets keep the subtitle positions to within 1 ms at ordinary levels.
    for start in (.2, 2.7):
        section = result[int((start - .01) * RATE):int((start + .03) * RATE)]
        first = np.flatnonzero(abs(section) > .04)[0] / RATE
        assert abs(first - .01) < .001


def test_off_final_audio_is_byte_identical_and_reference_is_not_normalized(tmp_path):
    original = write_wav(tmp_path / "original.wav", voice())
    before = original.read_bytes()
    result = audio_clean.polish_audio(original, tmp_path / "copy.wav", "off")
    assert result.read_bytes() == before
    assert audio_clean.polish_audio(original, original, "off").read_bytes() == before
    reference = audio_clean.clean_reference(original, tmp_path / "ref.wav", "off")
    np.testing.assert_array_equal(read_wav(reference), read_wav(original))


@pytest.mark.parametrize("level", ["light", "strong"])
def test_denoiser_delay_compensation_keeps_last_five_ms_of_speech(tmp_path, level):
    samples = np.zeros(RATE + 17)
    samples[-2400:] = .3 * np.sin(np.arange(2400) * 2 * np.pi * 1500 / RATE)
    samples[-4] = .55  # A final sharp consonant-like transient near EOF.
    source = write_wav(tmp_path / "ending.wav", samples)
    result = read_wav(audio_clean.polish_audio(source, tmp_path / "clean.wav", level))
    assert len(result) == len(samples)
    assert result[-4] > .5
    assert np.corrcoef(samples[-120:], result[-120:])[0, 1] > .99
    ratio = np.sqrt(np.mean(result[-120:] ** 2) / np.mean(samples[-120:] ** 2))
    assert .98 < ratio < 1.02


def test_reference_loudness_is_consistent_without_clipping(tmp_path):
    rms = []
    for index, gain in enumerate((.03, 1.8)):
        original = write_wav(tmp_path / f"input{index}.wav", voice() * gain)
        samples = read_wav(audio_clean.clean_reference(original, tmp_path / f"ref{index}.wav"))
        rms.append(np.sqrt(np.mean(samples ** 2)))
        assert np.max(abs(samples)) < .97
    assert abs(20 * np.log10(rms[0] / rms[1])) < .5


@pytest.mark.parametrize("level", ["invalid", "LIGHT", "", None])
def test_levels_are_strict(tmp_path, level):
    with pytest.raises(ValueError):
        audio_clean.clean_reference(tmp_path / "missing", tmp_path / "out.wav", level)
    with pytest.raises(ValueError):
        audio_clean.polish_audio(tmp_path / "missing", tmp_path / "out.wav", level)


@pytest.mark.parametrize("maximum", [0, .5, 10.1, float("inf"), float("nan"), True])
def test_reference_length_is_limited(tmp_path, maximum):
    with pytest.raises(ValueError):
        audio_clean.clean_reference(tmp_path / "missing", tmp_path / "out.wav", max_seconds=maximum)


@pytest.mark.parametrize("kind", ["corrupt", "silent", "short"])
def test_invalid_reference_never_replaces_existing_output(tmp_path, kind):
    source = tmp_path / "original.wav"
    if kind == "corrupt":
        source.write_bytes(b"not an audio file")
    else:
        write_wav(source, np.zeros(2 * RATE) if kind == "silent" else voice(.5))
    destination = tmp_path / "existing.wav"
    destination.write_bytes(b"keep this old result")
    with pytest.raises((RuntimeError, ValueError)):
        audio_clean.clean_reference(source, destination)
    assert destination.read_bytes() == b"keep this old result"
    assert not list(tmp_path.glob(".audio-clean-*"))


def test_reference_cannot_overwrite_original_or_exceed_size_limit(tmp_path):
    source = write_wav(tmp_path / "original.wav", voice())
    original = source.read_bytes()
    with pytest.raises(ValueError, match="khác"):
        audio_clean.clean_reference(source, source)
    assert source.read_bytes() == original
    with source.open("wb") as handle:
        handle.truncate(audio_clean.MAX_REFERENCE_BYTES + 1)
    with pytest.raises(ValueError, match="200 MB"):
        audio_clean.clean_reference(source, tmp_path / "result.wav")


@pytest.mark.parametrize("failure", [subprocess.CalledProcessError(1, "ffmpeg"), KeyboardInterrupt()])
def test_failure_and_cancellation_preserve_old_audio_and_remove_temp(tmp_path, monkeypatch, failure):
    target = write_wav(tmp_path / "finished.wav", voice())
    before = target.read_bytes()

    def fail(command, **kwargs):
        Path(command[-1]).write_bytes(b"unpublished partial result")
        raise failure

    monkeypatch.setattr(audio_clean.subprocess, "run", fail)
    with pytest.raises((RuntimeError, KeyboardInterrupt)):
        audio_clean.polish_audio(target, target)
    assert target.read_bytes() == before
    assert not list(tmp_path.glob(".audio-clean-*"))


def test_wrong_filter_frame_count_fails_without_truncating_audio(tmp_path, monkeypatch):
    target = write_wav(tmp_path / "finished.wav", voice())
    before = target.read_bytes()

    def wrong_length(command, folder, timeout):
        write_wav(Path(command[-1]), voice(2))

    monkeypatch.setattr(audio_clean, "_run_ffmpeg", wrong_length)
    with pytest.raises(RuntimeError, match="thời lượng"):
        audio_clean.polish_audio(target, target)
    assert target.read_bytes() == before


def test_long_audio_is_streamed_without_read_bytes(tmp_path, monkeypatch):
    source = tmp_path / "long.wav"
    block = np.round(voice(1) * 32767).astype("<i2").tobytes()
    with wave.open(str(source), "wb") as audio:
        audio.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        for _ in range(120):
            audio.writeframesraw(block)

    def forbid_read_bytes(self):
        raise AssertionError("Long audio must be streamed")

    monkeypatch.setattr(Path, "read_bytes", forbid_read_bytes)
    target = audio_clean.polish_audio(source, tmp_path / "long-clean.wav")
    with wave.open(str(target), "rb") as audio:
        assert audio.getnframes() == 120 * RATE


def test_local_protocol_whitelist_is_used(tmp_path, monkeypatch):
    source = write_wav(tmp_path / "source.wav", voice())
    calls = []
    real_run = audio_clean.subprocess.run

    def record(command, **kwargs):
        calls.append(command)
        return real_run(command, **kwargs)

    monkeypatch.setattr(audio_clean.subprocess, "run", record)
    audio_clean.clean_reference(source, tmp_path / "reference.wav")
    audio_clean.polish_audio(source, tmp_path / "result.wav")
    assert all(command[command.index("-protocol_whitelist") + 1] == "file,pipe" for command in calls)
    assert all("-nostdin" in command and "-xerror" in command for command in calls)
    with pytest.raises(ValueError):
        audio_clean.clean_reference("https://example.test/voice.mp3", tmp_path / "remote.wav")
