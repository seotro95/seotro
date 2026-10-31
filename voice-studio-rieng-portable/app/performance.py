"""Report generated speech throughput; subtitle silence cannot inflate the result."""


def speed_report(audio_seconds, elapsed_seconds, spoken_seconds=None):
    measured=audio_seconds if spoken_seconds is None else max(0,min(audio_seconds,spoken_seconds))
    if measured <= 0 or elapsed_seconds <= 0:
        return None
    factor=measured/elapsed_seconds
    hour_seconds=3600/factor
    return {'realtime_multiplier':round(factor,2),'estimated_hour_seconds':round(hour_seconds,1),
            'target_30x_met_on_sample':hour_seconds<=120,
            'actual_hour_of_speech_generated':measured>=3600,
            'target_30x_verified_on_hour_or_longer':measured>=3600 and factor>=30,
            'measurement_audio_seconds':round(measured,2),'measurement_elapsed_seconds':round(elapsed_seconds,3),
            'output_timeline_seconds':round(audio_seconds,2),
            'excluded_silence_seconds':round(max(0,audio_seconds-measured),2),
            'includes_silence':False if spoken_seconds is not None else None,
            'estimate_only':True}
