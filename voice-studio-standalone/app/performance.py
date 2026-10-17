"""Measured estimates, never a promise of a fixed hardware-independent speed."""

def speed_report(audio_seconds, elapsed_seconds, *, complete=True):
    if audio_seconds <= 0 or elapsed_seconds <= 0:
        return None
    factor = audio_seconds / elapsed_seconds
    hour_seconds = 3600 / factor
    return {'realtime_multiplier': round(factor, 2), 'estimated_hour_seconds': round(hour_seconds, 1),
            'target_30x_met_on_sample': bool(complete and hour_seconds <= 120),
            'measurement_audio_seconds': round(audio_seconds, 2),
            'measurement_elapsed_seconds': round(elapsed_seconds, 3),
            'hour_target_verified': bool(complete and audio_seconds >= 3600 and elapsed_seconds <= 120),
            'sample_is_short': audio_seconds < 30,
            'complete_text': complete,
            'estimate_only': audio_seconds < 3600 or not complete,
            'scope': 'current_machine', 'excludes_added_silence': True}
