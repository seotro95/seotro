"""Mild rhythm and energy controls, without changing Hmong lexical pitch.

These are deterministic audio postprocessing presets, not neural emotion
instructions. Tempo uses the worker's pitch-preserving FFmpeg atempo path;
the optional energy envelope only multiplies PCM amplitude over time.
"""
from __future__ import annotations

import math


EMOTIONS = ('neutral', 'warm', 'joyful', 'sad', 'serious', 'suspense')
# tempo, gain, pause multiplier, smooth phrase-energy amount
_PROFILES = {
    'neutral': (1.0, 1.0, 1.0, 0.0),
    'warm': (.975, 1.025, 1.10, .025),
    'joyful': (1.045, 1.06, .85, .045),
    'sad': (.945, .96, 1.30, -.025),
    'serious': (.985, 1.025, 1.12, .015),
    'suspense': (.96, .985, 1.45, -.035),
}


def enabled(job):
    """Saved legacy jobs keep their exact previous segmentation/audio path."""
    return job.get('engine') == 'f5_hmong' and job.get('segment_plan') == 'hmong-expression-v1'


def validate_emotion(emotion):
    if emotion not in EMOTIONS:
        raise ValueError('Cảm xúc cần là neutral, warm, joyful, sad, serious hoặc suspense.')
    return emotion


def validate_strength(strength):
    if (isinstance(strength, bool) or not isinstance(strength, (int, float))
            or not math.isfinite(strength) or not 0 <= strength <= 1):
        raise ValueError('Cường độ cảm xúc cần từ 0 đến 1.')
    return float(strength)


def parameters(emotion='neutral', strength=.65):
    """Interpolate gently from neutral; zero strength changes no PCM energy."""
    emotion, strength = validate_emotion(emotion), validate_strength(strength)
    tempo, gain, pause, envelope = _PROFILES[emotion]
    return (1 + (tempo - 1) * strength, 1 + (gain - 1) * strength,
            1 + (pause - 1) * strength, envelope * strength)


def automatic_pause(text, emotion='neutral', strength=.65, *, paragraph=False):
    """A small gap after punctuation/paragraphs, without adding spoken sounds."""
    ending = text.rstrip().rstrip('\"\'’”)]}')
    if paragraph:
        base = .38
    elif ending.endswith('...'):
        base = .32
    elif ending.endswith('?'):
        base = .26
    elif ending.endswith('!'):
        base = .22
    elif ending.endswith('.'):
        base = .20
    elif ending.endswith((';', ':')):
        base = .13
    else:
        base = 0.0
    return min(.65, base * parameters(emotion, strength)[2])


def shape_phrase_energy(path, emotion='neutral', strength=.65):
    """Apply a bounded smooth amplitude envelope to normalized mono PCM.

    No resampling, pitch contour, vibrato, breath or laughter is introduced.
    Peak scaling avoids introducing clipping when an envelope adds energy.
    """
    depth = parameters(emotion, strength)[3]
    if not depth:
        return
    import numpy as np
    import soundfile as sf
    samples, rate = sf.read(str(path), dtype='float32', always_2d=False)
    if samples.ndim != 1 or rate != 24000 or not len(samples) or not np.isfinite(samples).all():
        raise ValueError('Âm thanh điều chỉnh nhịp cần là PCM mono 24 kHz hợp lệ.')
    envelope = 1 + depth * np.sin(np.linspace(0, np.pi, len(samples), dtype=np.float32))
    samples = samples * envelope
    peak = float(np.max(np.abs(samples)))
    if peak > .95:
        samples *= .95 / peak
    sf.write(str(path), samples, rate, subtype='PCM_16')
