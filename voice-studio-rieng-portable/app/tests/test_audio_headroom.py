import numpy as np
import pytest
import soundfile as sf
from audio_processing import pcm_with_headroom


def harmonic_energy(samples, frequency=440, rate=24000):
    spectrum=np.abs(np.fft.rfft(samples))
    hz=np.fft.rfftfreq(len(samples),1/rate)
    fundamental=spectrum[np.argmin(abs(hz-frequency))]
    harmonics=[spectrum[np.argmin(abs(hz-frequency*i))] for i in range(2,10)]
    return np.linalg.norm(harmonics)/fundamental


def test_hot_pcm_keeps_waveform_and_reduces_clipping_harmonics(tmp_path):
    source=(1.8*np.sin(2*np.pi*440*np.arange(24000)/24000)).astype('float32')
    clean=pcm_with_headroom(source)
    path=tmp_path/'headroom.wav';sf.write(path,clean,24000,subtype='PCM_16')
    read,rate=sf.read(path)
    assert len(read)==len(source) and rate==24000
    assert np.max(abs(read))<=.951
    assert harmonic_energy(read)<.0001
    assert harmonic_energy(np.clip(source,-.95,.95))>.1
    np.testing.assert_allclose(clean,source*(.95/np.max(abs(source))),atol=1e-7)


def test_clean_pcm_is_not_boosted_or_flattened():
    source=np.array([0,.1,-.4,.5,-.8],dtype='float32')
    np.testing.assert_array_equal(pcm_with_headroom(source),source)
    np.testing.assert_allclose(pcm_with_headroom(source,gain=.5),source*.5)


@pytest.mark.parametrize('samples',[[],[float('nan')],[float('inf')]])
def test_invalid_pcm_is_rejected(samples):
    with pytest.raises(ValueError):pcm_with_headroom(samples)
