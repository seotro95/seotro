"""A short fast clip or subtitle gaps cannot prove the user's hour-long goal."""
from performance import speed_report


def test_short_fast_sample_is_only_an_estimate():
    report = speed_report(30, 1, spoken_seconds=30)
    assert report['target_30x_met_on_sample']
    assert not report['actual_hour_of_speech_generated']
    assert not report['target_30x_verified_on_hour_or_longer']


def test_artificial_srt_silence_cannot_verify_an_hour_of_speech():
    report = speed_report(3600, 120, spoken_seconds=30)
    assert not report['actual_hour_of_speech_generated']
    assert not report['target_30x_verified_on_hour_or_longer']
    assert report['excluded_silence_seconds'] == 3570


def test_actual_hour_goal_uses_unrounded_measurement():
    assert speed_report(3600, 120, spoken_seconds=3600)['target_30x_verified_on_hour_or_longer']
    assert not speed_report(3600, 120.001, spoken_seconds=3600)['target_30x_verified_on_hour_or_longer']
    assert not speed_report(3599.99, 110, spoken_seconds=3599.99)['target_30x_verified_on_hour_or_longer']


def test_long_slow_render_proves_duration_but_not_speed():
    report = speed_report(7200, 500, spoken_seconds=7200)
    assert report['actual_hour_of_speech_generated']
    assert not report['target_30x_verified_on_hour_or_longer']
