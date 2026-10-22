import numpy as np
import pytest
import soundfile as sf

from prepare_models import validate_prepared_audio


@pytest.mark.parametrize('kind', ['empty', 'silent', 'nan', 'broken'])
def test_bad_preparation_audio_cannot_pass_readiness(tmp_path, kind):
    output = tmp_path / 'check.wav'
    if kind == 'broken':
        output.write_bytes(b'not a wave file')
    else:
        values = np.zeros(0 if kind == 'empty' else 24000)
        if kind == 'nan':
            values[:] = np.nan
        sf.write(output, values, 24000, subtype='FLOAT')
    with pytest.raises((RuntimeError, sf.LibsndfileError)):
        validate_prepared_audio(output)


def test_real_calibration_audio_has_measured_duration(tmp_path):
    output = tmp_path / 'check.wav'
    sf.write(output, .2 * np.sin(np.arange(48000) * 2 * np.pi * 220 / 24000), 24000)
    assert validate_prepared_audio(output) == 2
