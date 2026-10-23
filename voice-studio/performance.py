"""Measured speech throughput, never a hardware-independent speed promise."""
import math


MIN_SUSTAINED_SPEECH_SECONDS = 60


def _positive_finite(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value) and value > 0
    except OverflowError:
        return False


def speed_report(audio_seconds, elapsed_seconds, *, spoken_audio_seconds=None):
    """Measure spoken chunks rather than silence inserted by the renderer.

    Spoken duration retains pauses produced *inside* a model chunk; it is not
    a voice-activity detector. Callers without that measurement retain the
    historical output-duration estimate, explicitly labelled as legacy.
    A short sample never qualifies as a sustained 30x run. Even a sustained
    sample does not verify the one-hour target unless a measured job actually
    contains at least one hour of spoken chunks and finishes within 120s.
    """
    if not _positive_finite(audio_seconds) or not _positive_finite(elapsed_seconds):
        return None
    measured_speech = spoken_audio_seconds is not None
    seconds = spoken_audio_seconds if measured_speech else audio_seconds
    if not _positive_finite(seconds):
        return None
    # Permit one sample of rounding at the lowest accepted audio rate. Bigger
    # discrepancies indicate corrupt/mismatched measurements, not speedups.
    if seconds > audio_seconds + 1 / 8000:
        return None
    seconds = min(seconds, audio_seconds)
    factor = seconds / elapsed_seconds
    if not math.isfinite(factor) or factor <= 0:
        return None
    hour_seconds = 3600 / factor
    if not math.isfinite(hour_seconds):
        return None
    sustained = seconds >= MIN_SUSTAINED_SPEECH_SECONDS
    verified_hour = measured_speech and seconds >= 3600 and elapsed_seconds <= 120
    return {
        'realtime_multiplier': round(factor, 2),
        'estimated_hour_seconds': round(hour_seconds, 1),
        'target_30x_met_on_sample': sustained and hour_seconds <= 120,
        'target_30x_verified_one_hour': verified_hour,
        'sustained_measurement': sustained,
        'minimum_sustained_speech_seconds': MIN_SUSTAINED_SPEECH_SECONDS,
        'measurement_audio_seconds': round(seconds, 2),
        'measurement_output_audio_seconds': round(audio_seconds, 2),
        'measurement_inserted_silence_seconds': round(max(0, audio_seconds - seconds), 2)
            if measured_speech else None,
        'measurement_elapsed_seconds': round(elapsed_seconds, 3),
        'measurement_basis': ('speech_chunks_excluding_inserted_silence' if measured_speech
                              else 'output_duration_legacy'),
        'estimate_only': not verified_hour,
    }
