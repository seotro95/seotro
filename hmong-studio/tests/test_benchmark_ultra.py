"""Synthetic unit fixtures verify accounting, never serve as speed evidence."""
import asyncio
import json
import os
from pathlib import Path
import struct
from types import SimpleNamespace
import wave

import pytest

import benchmark_ultra as bench


def write_wave(path, seconds=2, *, silent=False, truncated=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(24000)
        pair = b'\0\0\0\0' if silent else struct.pack('<hh', -300, 300)
        writer.writeframes(pair * int(seconds * 24000 / 2))
        writer.writeframes(b'\0\0' * 3600)
    if truncated:
        path.write_bytes(path.read_bytes()[:-10])


def test_inventory_is_explicitly_unrun_without_loading_or_generating(tmp_path, monkeypatch):
    def should_not_run(*args):
        raise AssertionError('No target was authorized to run')
    monkeypatch.setattr(bench, 'worker', should_not_run)
    assert bench.main(['--output-dir', str(tmp_path)]) == 0
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['status'] == 'unrun'
    assert [row['target_minutes'] for row in report['targets']] == [1, 5, 15, 30, 60]
    assert all(row['status'] == 'unrun' and not row['target_duration_verified']
               for row in report['targets'])
    assert report['hardware'] is None and not report['target_2min_per_hour_verified']


def test_user_hmong_words_tones_and_order_are_not_rewritten(tmp_path):
    path = tmp_path / 'Hmoob Dawb.txt'
    original = 'Hmoob Dawb: Kuv hlub koj.\nKoj puas hnov kuv hais?\nTxhob hloov cov tsiaj ntawv!'
    path.write_text(original, encoding='utf-8')
    text, origin = bench.source_text(60, path)
    assert text == original
    assert origin == 'user_text_used_without_word_changes'
    builtin, _ = bench.source_text(1)
    assert len(builtin.split()) >= 180 and '-->' not in builtin


def test_timed_or_empty_input_cannot_inflate_new_speech_measurement(tmp_path):
    path = tmp_path / 'bad.txt'
    for text in (' ', '1\n00:00:00,200 --> 00:59:59,000\nNyob zoo.'):
        path.write_text(text)
        with pytest.raises(ValueError):
            bench.source_text(60, path)


def test_wav_accounting_excludes_only_known_inserted_pause(tmp_path):
    path = tmp_path / 'real-format-unit-fixture.wav'
    write_wave(path)
    result = bench.inspect_audio(path, .15)
    assert result['audio_seconds'] == pytest.approx(2.15)
    assert result['speech_seconds'] == pytest.approx(2)
    assert result['frames'] == 51600 and len(result['pcm_sha256']) == 64


@pytest.mark.parametrize('kwargs', [{'silent': True}, {'truncated': True}])
def test_invalid_audio_is_not_accepted_as_completed(tmp_path, kwargs):
    path = tmp_path / 'invalid.wav'
    write_wave(path, **kwargs)
    with pytest.raises(ValueError):
        bench.inspect_audio(path, .15)


def test_cache_read_control_is_restored_even_after_failure(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_AUDIO_CACHE_DIR', 'previous-cache')
    monkeypatch.delenv('HMONG_AUDIO_CACHE_READS', raising=False)
    with pytest.raises(RuntimeError):
        with bench.cache_environment(tmp_path, 0):
            assert os.environ['HMONG_AUDIO_CACHE_DIR'] == str(tmp_path)
            assert os.environ['HMONG_AUDIO_CACHE_READS'] == '0'
            raise RuntimeError('Interrupted benchmark')
    assert os.environ['HMONG_AUDIO_CACHE_DIR'] == 'previous-cache'
    assert 'HMONG_AUDIO_CACHE_READS' not in os.environ


@pytest.fixture
def fake_runtime(monkeypatch):
    clock = SimpleNamespace(value=0)
    engine = SimpleNamespace(_sentences=lambda text: [text])
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    monkeypatch.setattr(bench, '_seed', lambda torch: None)

    class App:
        Speech = SimpleNamespace
        force_hit = False
        requests = []

        @staticmethod
        async def generate_speech(payload, *, progress, output_path):
            App.requests.append(payload)
            clock.value += 4
            cached = App.force_hit or (payload.compute_mode == 'ultra'
                                       and os.getenv('HMONG_AUDIO_CACHE_READS') == '1')
            progress({'synthesized_seconds': 0 if cached else 2,
                      'reused_seconds': 2 if cached else 0,
                      'cache_hits': 1 if cached else 0})
            write_wave(output_path)

    return App, engine, torch, clock


def test_cold_uses_actual_new_seconds_and_warm_never_reports_generation_speed(tmp_path, fake_runtime):
    app, engine, torch, clock = fake_runtime
    with bench.cache_environment(tmp_path / 'cache', 0):
        cold = asyncio.run(bench.measure_run(app, engine, torch, 'Nyob zoo.', tmp_path / 'cold.wav',
                           label='ultra_cold', max_seconds=30, clock=lambda: clock.value))
    with bench.cache_environment(tmp_path / 'cache', 1):
        warm = asyncio.run(bench.measure_run(app, engine, torch, 'Nyob zoo.', tmp_path / 'warm.wav',
                           label='ultra_warm', max_seconds=30, clock=lambda: clock.value))
    assert cold['status'] == warm['status'] == 'completed'
    assert cold['synthesized_new_seconds'] == 2 and cold['elapsed_seconds'] == 4
    assert cold['new_voice_speed_multiplier'] == .5 and cold['real_time_factor'] == 2
    assert warm['synthesized_new_seconds'] == 0 and warm['cache_hits'] == 1
    assert warm['new_voice_speed_multiplier'] == 0 and warm['real_time_factor'] is None
    assert warm['cached_playback_throughput'] == .5
    assert all(p.speed == 1 and p.cleanup == 'light' and p.emotion == 'review'
               for p in app.requests)


def test_unexpected_cold_cache_hit_invalidates_measurement(tmp_path, fake_runtime):
    app, engine, torch, clock = fake_runtime
    app.force_hit = True
    row = asyncio.run(bench.measure_run(app, engine, torch, 'Nyob zoo.', tmp_path / 'bad-cold.wav',
                       label='ultra_cold', max_seconds=30, clock=lambda: clock.value))
    assert row['status'] == 'failed' and row['audio_path'] is None
    assert not row['target_2min_per_hour_verified']


def test_budget_stops_at_checkpoint_without_claiming_completed_audio(tmp_path, fake_runtime):
    app, engine, torch, clock = fake_runtime
    row = asyncio.run(bench.measure_run(app, engine, torch, 'Nyob zoo.', tmp_path / 'partial.wav',
                       label='standard', max_seconds=3, clock=lambda: clock.value))
    assert row['status'] == 'budget_exceeded'
    assert row['elapsed_seconds'] == 4 and row['synthesized_new_seconds'] == 2
    assert row['audio_path'] is None and not (tmp_path / 'partial.wav').exists()


def completed_row(label, *, new=2, elapsed=4, hits=0, reused=0):
    return {'label': label, 'status': 'completed', 'synthesized_new_seconds': new,
            'elapsed_seconds': elapsed, 'cache_hits': hits, 'reused_seconds': reused,
            'pcm_sha256': 'unit-test-only-hash', 'new_voice_speed_multiplier': new / elapsed}


def test_short_actual_audio_cannot_verify_nominal_minute_or_hour_even_with_fast_warm():
    target = bench.inventory([60])[0]
    target['runs'] = [completed_row('standard'), completed_row('ultra_cold'),
                      completed_row('ultra_warm', new=0, elapsed=.01, hits=500, reused=3600)]
    bench.evaluate_target(target)
    assert target['status'] == 'incomplete'
    assert not target['target_duration_verified'] and not target['target_2min_per_hour_verified']
    assert target['pcm_identical_before_after'] is True


def test_hour_claim_requires_both_full_new_speech_runs_and_actual_120_second_cold():
    target = bench.inventory([60])[0]
    target['runs'] = [completed_row('standard', new=3600, elapsed=10000),
                      completed_row('ultra_cold', new=3600, elapsed=121)]
    bench.evaluate_target(target)
    assert target['target_duration_verified'] and not target['target_2min_per_hour_verified']
    target['runs'][1] = completed_row('ultra_cold', new=3600, elapsed=120)
    bench.evaluate_target(target)
    assert target['target_2min_per_hour_verified']
    target['runs'][1]['cache_hits'] = 1
    bench.evaluate_target(target)
    assert not target['target_duration_verified'] and not target['target_2min_per_hour_verified']


def test_running_studio_blocks_explicit_benchmark_without_installing(monkeypatch):
    class Connected:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(bench.socket, 'create_connection', lambda *a, **kw: Connected())
    assert bench.main(['--target-minutes', '1']) == 2


def test_atomic_report_failure_preserves_previous_report_and_removes_owned_temp(tmp_path, monkeypatch):
    path = tmp_path / 'report.json'
    path.write_bytes(b'previous report')
    original = Path.replace
    def locked(source, target):
        if Path(target) == path:
            raise PermissionError('Windows file lock')
        return original(source, target)
    monkeypatch.setattr(Path, 'replace', locked)
    with pytest.raises(PermissionError):
        bench.write_report(path, {'status': 'incomplete'})
    assert path.read_bytes() == b'previous report'
    assert not list(tmp_path.glob('.benchmark-*'))
