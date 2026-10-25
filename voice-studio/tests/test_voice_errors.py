import errno
import importlib
import subprocess

import pytest

import app
from test_app import studio  # noqa: F401
from voice_errors import describe_failure


@pytest.mark.parametrize(('error', 'expected'), [
    (ModuleNotFoundError("private-token", name='torch'), 'Thiếu thư viện tạo giọng (torch)'),
    (ImportError('private-token'), 'không tương thích'),
    (OSError(errno.ENOSPC, 'private-token'), 'đã đầy'),
    (PermissionError('private-token'), 'quyền đọc hoặc ghi'),
    (MemoryError('private-token'), 'RAM/VRAM'),
    (subprocess.CalledProcessError(1, ['ffmpeg', 'private-token.wav']), 'FFmpeg'),
    (RuntimeError('private-token'), 'nhật ký tác vụ'),
])
def test_failure_messages_are_actionable_without_echoing_exception_data(error, expected):
    message = describe_failure(error)
    assert expected in message
    assert 'private-token' not in message


def test_windows_dll_and_memory_exit_codes_have_specific_recovery():
    message = describe_failure(log_tail='OSError: [WinError 126] Error loading private-token.dll')
    assert 'Visual C++' in message and 'DLL' in message
    assert 'private-token' not in message
    assert 'RAM/VRAM' in describe_failure(returncode=0xc0000017)
    assert 'DLL' in describe_failure(returncode=-1073741515)  # STATUS_DLL_NOT_FOUND
    assert 'mã thoát -9' in describe_failure(returncode=-9)


def test_dead_worker_import_error_reaches_job_and_preserves_its_trace(studio, monkeypatch):
    _, root = studio
    runtime = root / 'runtime'
    runtime.mkdir()
    (runtime / 'worker.py').write_text(
        "raise ModuleNotFoundError(\"No module named 'torch'; private-token\")\n")
    # A prior worker's reason must never misdiagnose this worker.
    (root / 'worker-startup.log').write_text('MemoryError: stale failure\n')
    monkeypatch.setattr(app, 'BASE', runtime)
    ident = 'a' * 32
    path = root / 'jobs' / (ident + '.json')
    app.write_json(path, {'id': ident, 'status': 'queued', 'format': 'wav'})
    app.run_job(ident)
    failed = app.read_json(path)
    assert failed['status'] == 'error'
    assert 'Thiếu thư viện tạo giọng (torch)' in failed['error']
    assert 'stale failure' not in failed['error'] and 'private-token' not in failed['error']
    assert str(root / 'jobs' / (ident + '.log')) in failed['error']
    log = (root / 'jobs' / (ident + '.log')).read_text()
    assert 'ModuleNotFoundError' in log and 'private-token' in log
    assert 'stale failure' not in log
    marker = app.read_json(root / 'parts' / ident / 'worker-done.json')
    assert marker['user_error'] == failed['error']
    assert app.warm_worker is None


def test_worker_spawn_permission_failure_has_recovery_and_job_log(studio, monkeypatch):
    _, root = studio
    ident = 'b' * 32
    path = root / 'jobs' / (ident + '.json')
    app.write_json(path, {'id': ident, 'status': 'queued', 'format': 'wav'})
    def denied(*args, **kwargs):
        raise PermissionError('private-token')
    monkeypatch.setattr(app.subprocess, 'Popen', denied)
    app.run_job(ident)
    failed = app.read_json(path)
    assert failed['status'] == 'error'
    assert 'quyền đọc hoặc ghi' in failed['error']
    assert 'private-token' not in failed['error']
    assert 'private-token' in (root / 'jobs' / (ident + '.log')).read_text()


def test_worker_errors_preserve_validation_and_describe_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    from hmong_engine import EngineError
    assert worker.voice_error(EngineError('HMOOB_PRECISION=auto hoặc fp32')) == 'HMOOB_PRECISION=auto hoặc fp32'
    assert worker.voice_error(ValueError('Câu SRT 3 quá dài')) == 'Câu SRT 3 quá dài'
    assert 'DLL' in worker.voice_error(OSError('DLL load failed: private-token'))
    assert 'private-token' not in worker.voice_error(OSError('DLL load failed: private-token'))
