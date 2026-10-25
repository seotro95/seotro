"""Both user uploads remain intact; native-only references retain their audio."""
import array
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import pytest


ROOT = Path(__file__).resolve().parents[1] / 'assets/hmong'
EXPECTED = {
    'hmong-ngoc-huyen': (
        'aea67355902f6d57949e7a9dbac9c41b6d127b2fac0df81d3c540a302731cf9d',
        'e074215d0ffdb0855efa4951fbaf7f7eec274f9b2e384fcb6262b6eab936b8ce',
        7.78,
    ),
    'hmong-female-3': (
        'aec83955c0c81abe7355167c779c7ca4c6c4b51422b4ba1018b7ff8f6b30fb1b',
        'ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17',
        7.44,
    ),
}


def manifest():
    return json.loads((ROOT / 'additional-voices.json').read_text(encoding='utf-8'))


def pcm(path):
    with wave.open(str(path), 'rb') as audio:
        assert audio.getparams()[:3] == (1, 2, 24000)
        assert audio.getcomptype() == 'NONE'
        result = array.array('h', audio.readframes(audio.getnframes()))
    if sys.byteorder != 'little':
        result.byteswap()
    return result


def test_new_manifest_keeps_both_user_uploads_and_never_invents_reference_words():
    records = manifest()
    assert records.keys() == EXPECTED.keys()
    for ident, (source_sha, reference_sha, seconds) in EXPECTED.items():
        item = records[ident]
        assert hashlib.sha256((ROOT / item['file']).read_bytes()).hexdigest() == source_sha == item['sha256']
        assert hashlib.sha256((ROOT / item['reference_file']).read_bytes()).hexdigest() == reference_sha == item['reference_sha256']
        assert item['engine'] == 'hmong_native'
        assert item['reference_conditioning'] == 'audio'
        assert item['reference_text_verified'] is False and item['reference']['text'] == ''
        assert item['reference_text_source'] == 'not_provided_audio_only'
        assert item['reference']['start'] == 0 and item['reference']['end'] == seconds
        samples = pcm(ROOT / item['reference_file'])
        assert len(samples) == round(seconds * 24000)
        assert 0 < max(abs(value) for value in samples) < 32767
        assert abs(20 * math.log10(max(abs(value) for value in samples) / 32768) + 3) < .001
        assert item['audio_processing']['denoise'] is False
        assert item['audio_processing']['pitch_shift'] is False
        assert item['audio_processing']['time_stretch'] is False


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='Reference waveform provenance needs FFmpeg')
@pytest.mark.parametrize('ident', EXPECTED)
def test_reference_waveform_is_the_selected_upload_with_only_constant_gain(ident):
    item = manifest()[ident]
    result = subprocess.run([
        'ffmpeg', '-nostdin', '-v', 'error', '-i', str(ROOT / item['file']),
        '-ac', '1', '-ar', '24000', '-f', 'f32le', 'pipe:1',
    ], check=True, capture_output=True, timeout=30)
    original = array.array('f', result.stdout)
    if sys.byteorder != 'little':
        original.byteswap()
    samples = pcm(ROOT / item['reference_file'])
    gain = 10 ** (item['audio_processing']['constant_gain_db'] / 20)
    # Independent sample comparison rules out inserted speech, denoising,
    # time/pitch edits and clipping. Allow one PCM16 quantization step.
    assert max(abs(samples[index] / 32768 - value * gain)
               for index, value in enumerate(original[:len(samples)])) <= 1 / 32768
