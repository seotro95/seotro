import struct
import wave

import pytest

from cue_audio import fit_cue_audio


def write_pcm(path, samples):
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(struct.pack('<'+'h'*len(samples), *samples))


def test_auto_fit_only_removes_exact_zero_boundary_samples(tmp_path):
    path = tmp_path/'cue.wav'
    # Quiet edge samples are still speech and must survive unchanged. The zero
    # inside the voice also stays; no silence threshold can consume low volume.
    voice = [1, 25, 100, 0, -100, -25, -1]
    write_pcm(path, [0]*20+voice+[0]*30)
    result = fit_cue_audio(path, len(voice))
    assert result['tempo'] == 1
    assert result['trimmed_frames'] == 50
    with wave.open(str(path)) as audio:
        assert audio.getnframes() == len(voice)
        assert audio.readframes(len(voice)) == struct.pack('<7h', *voice)


def test_auto_fit_rejects_silent_audio_without_replacing_it(tmp_path):
    path = tmp_path/'cue.wav'
    write_pcm(path, [0]*100)
    original = path.read_bytes()
    with pytest.raises(ValueError, match='im lặng'):
        fit_cue_audio(path, 50)
    assert path.read_bytes() == original
