"""Local A/B selection uses valid WAV work and never claims a one-hour result."""
import asyncio
from pathlib import Path
import struct
from types import SimpleNamespace
import wave

import pytest

import benchmark_voice as benchmark


def write_wave(path, *, seconds=2, silent=False, truncate=False):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(24000)
        speech = (b'\0\0' if silent else struct.pack('<hhhh', -200, 100, 200, -100))
        count = int(seconds * 24000)
        stream.writeframes((speech * (count // (len(speech) // 2) + 1))[:count * 2])
        stream.writeframes(b'\0\0' * 3600)
    if truncate:
        path.write_bytes(path.read_bytes()[:-10])


def test_wave_validation_excludes_only_known_inserted_pause(tmp_path):
    path = tmp_path / 'voice.wav'
    write_wave(path, seconds=2)
    info = benchmark.inspect_audio(path)
    assert info['audio_seconds'] == pytest.approx(2.15)
    assert info['speech_seconds'] == pytest.approx(2)
    assert info['inserted_pause_seconds'] == .15 and info['peak_pcm'] == 200


@pytest.mark.parametrize('silent,truncate', [(True, False), (False, True)])
def test_silent_or_truncated_pcm_cannot_win_speed_test(tmp_path, silent, truncate):
    path = tmp_path / 'voice.wav'
    write_wave(path, silent=silent, truncate=truncate)
    with pytest.raises(ValueError):
        benchmark.inspect_audio(path)


class FakeOOM(RuntimeError):
    pass


@pytest.fixture
def runtime(monkeypatch):
    backend = SimpleNamespace(fp16=True, hift_cache_dict={}, tts_speech_token_dict={}, llm_end_dict={})
    events = []
    torch = SimpleNamespace(cuda=SimpleNamespace(
        synchronize=lambda: events.append('sync'),
        empty_cache=lambda: events.append('empty'),
        OutOfMemoryError=FakeOOM,
    ))
    monkeypatch.setattr(benchmark, '_seed', lambda torch: events.append('seed'))
    requests = []

    class App:
        fail_mode = None
        fail_type = None
        Speech = staticmethod(lambda **kwargs: kwargs)

        @staticmethod
        async def generate_speech(payload, output_path):
            mode = 'float16' if backend.fp16 else 'float32'
            requests.append((mode, output_path.name, payload))
            events.append('generate')
            if mode == App.fail_mode:
                if App.fail_type == 'oom':
                    backend.hift_cache_dict['failed'] = object()
                    try:
                        raise FakeOOM('CUDA out of memory')
                    except FakeOOM as exc:
                        raise RuntimeError('Wrapped by engine') from exc
                raise ValueError('Broken model, not a performance candidate')
            # Different token durations may result from precision. RTF compares
            # generated speech rather than merely rewarding shorter output.
            write_wave(output_path, seconds=1.5 if backend.fp16 else 2)

    return backend, torch, events, requests, App


def test_measured_rtf_selects_actual_fastest_and_restores_precision(tmp_path, runtime):
    backend, torch, events, requests, app = runtime
    ticks = iter([0, 4, 5, 8.5])
    result = asyncio.run(benchmark.measure(app, backend, torch, tmp_path, clock=lambda: next(ticks)))
    # FP16 finishes sooner (3.5 < 4 seconds), but produces less speech, so its
    # RTF is slower (3.5/1.5 > 4/2). Only measured requests enter the result.
    assert result['precision'] == 'float32'
    assert [item['elapsed_seconds'] for item in result['results']] == [4, 3.5]
    assert result['results'][0]['speech_seconds'] == 2
    assert len(requests) == 4 and backend.fp16 is True
    assert not list(tmp_path.glob('warmup-*'))
    assert result['one_hour_tested'] is False and result['target_2min_per_hour_verified'] is False
    assert all(request[2]['cleanup'] == 'light' and request[2]['emotion'] == 'review'
               and request[2]['compute_mode'] == 'standard' for request in requests)
    assert events.count('sync') == 6


def test_cuda_oom_can_exclude_one_mode_but_not_keep_failed_request_cache(tmp_path, runtime):
    backend, torch, events, _, app = runtime
    app.fail_mode, app.fail_type = 'float32', 'oom'
    ticks = iter([0, 2])
    result = asyncio.run(benchmark.measure(app, backend, torch, tmp_path, clock=lambda: next(ticks)))
    assert result['precision'] == 'float16' and len(result['results']) == 1
    assert result['failures'] == [{'precision': 'float32', 'reason': 'cuda_out_of_memory'}]
    assert events.count('empty') == 1 and backend.hift_cache_dict == {}
    assert backend.fp16 is True


def test_measurement_result_can_save_and_load_only_for_matching_gpu(tmp_path, runtime):
    import gpu_tuning
    backend, torch, _, _, app = runtime
    torch.__version__ = 'test-version'
    torch.version = SimpleNamespace(cuda='12.4')
    properties = SimpleNamespace(name='Synthetic adapter', total_memory=6 * 1024 ** 3, major=6, minor=1)
    torch.cuda.is_available = lambda: True
    torch.cuda.current_device = lambda: 0
    torch.cuda.get_device_properties = lambda index: properties
    ticks = iter([0, 4, 5, 8.5])
    result = asyncio.run(benchmark.measure(app, backend, torch, tmp_path, clock=lambda: next(ticks)))
    settings = tmp_path / 'gpu-tuning.json'
    gpu_tuning.save_choice(settings, torch, result['precision'], result['results'])
    assert gpu_tuning.load_choice(settings, torch) == 'float32'
    properties.total_memory = 8 * 1024 ** 3
    assert gpu_tuning.load_choice(settings, torch) is None


def test_unexpected_failure_aborts_instead_of_saving_previous_partial_winner(tmp_path, runtime):
    backend, torch, _, _, app = runtime
    app.fail_mode = 'float16'
    ticks = iter([0, 2])
    with pytest.raises(ValueError, match='Broken model'):
        asyncio.run(benchmark.measure(app, backend, torch, tmp_path, clock=lambda: next(ticks)))
    assert backend.fp16 is True
    assert (tmp_path / 'float32.wav').exists()


def test_bootstrap_reuses_selected_runtime_without_installing(tmp_path, monkeypatch):
    import clone_runtime
    calls = []
    executable = tmp_path / 'selected' / 'python.exe'
    monkeypatch.setattr(benchmark, 'BASE', tmp_path)
    monkeypatch.setattr(benchmark.socket, 'create_connection', lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(clone_runtime, 'selected_python', lambda root: executable)
    monkeypatch.setattr(clone_runtime, '_run', lambda command, root: calls.append((command, root)) or 0)
    assert benchmark.main([]) == 0
    command, root = calls[0]
    assert command[0] == executable and command[-1] == '--worker' and root == tmp_path


def test_open_studio_prevents_parallel_gpu_benchmark(monkeypatch):
    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass
    monkeypatch.setattr(benchmark.socket, 'create_connection', lambda *args, **kwargs: Connection())
    assert benchmark.main([]) == 2


def test_cpu_worker_does_not_load_model_or_change_saved_choice(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
    assert benchmark.worker() == 2


@pytest.mark.parametrize('unexpected_failure', [False, True])
def test_worker_only_saves_choice_after_successful_complete_measurement(tmp_path, monkeypatch, runtime,
                                                                     unexpected_failure):
    import json
    import sys
    backend, torch, _, _, app = runtime
    torch.cuda.is_available = lambda: True
    torch.cuda.get_device_name = lambda index: 'Synthetic test adapter'
    monkeypatch.setattr(benchmark, 'BASE', tmp_path)
    if unexpected_failure:
        app.fail_mode = 'float16'
    engine = SimpleNamespace(_sentences=lambda text: [text], model_dir=lambda: tmp_path,
                             _load_engine=lambda root: (None, backend, 24000), REVISION='pinned-test')
    choice = tmp_path / 'old-choice.json'
    choice.write_text('previous valid choice', encoding='utf-8')
    saved = []

    def save(path, actual_torch, precision, results):
        assert actual_torch is torch
        assert path == choice
        assert len(results) == 2
        assert precision in {item['precision'] for item in results}
        saved.append(precision)

    tuning = SimpleNamespace(settings_path=lambda: choice, hardware_key=lambda module: 'hardware-id',
                             save_choice=save)
    for name, module in [('torch', torch), ('app', app), ('cosy_engine', engine), ('gpu_tuning', tuning)]:
        monkeypatch.setitem(sys.modules, name, module)
    if unexpected_failure:
        with pytest.raises(ValueError, match='Broken model'):
            benchmark.worker()
        assert saved == []
    else:
        assert benchmark.worker() == 0
        assert len(saved) == 1
        reports = list((tmp_path / '.data' / 'runtime' / 'speed-test').glob('*/report.json'))
        report = json.loads(reports[0].read_text(encoding='utf-8'))
        assert report['one_hour_tested'] is False and report['target_2min_per_hour_verified'] is False
        assert len(report['results']) == 2 and report['precision'] == saved[0]
    assert choice.read_text(encoding='utf-8') == 'previous valid choice'
