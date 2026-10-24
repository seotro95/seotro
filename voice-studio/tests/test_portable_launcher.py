"""A launcher owns only its child and reopens a proven server for its data."""
import io
from pathlib import Path
import threading

import pytest

import portable_launcher


class ReadyProcess:
    pid = 4321

    def __init__(self, returncode, *, interrupted=False):
        self.final_returncode = returncode
        self.returncode = None
        self.interrupted = interrupted
        self.wait_calls = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt
        self.returncode = self.final_returncode
        return self.returncode


def studio_record():
    return dict(url='http://127.0.0.1:8770', version='1.2.0', backend='standard',
                pid=4321, instance_id='instance-one', data_id='data-one',
                root_id='root-one', variant='standard')


@pytest.fixture(autouse=True)
def isolated_launcher(monkeypatch, tmp_path):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr(portable_launcher, 'IS_HMONG', False)
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: None)
    monkeypatch.setattr(portable_launcher, 'legacy_discover', lambda data, root: None)

    class StartupLock:
        held = False

        def __init__(self, data):
            self.data = data

        def __enter__(self):
            assert not self.held
            type(self).held = True
            return self

        def __exit__(self, *args):
            type(self).held = False

    monkeypatch.setattr(portable_launcher, 'StartupLock', StartupLock)
    return StartupLock


def launch_ready(monkeypatch, process):
    class LocalOpener:
        def open(self, url, timeout):
            assert url == 'http://127.0.0.1:8770/api/config'
            return io.BytesIO(b'{"mode":"local","version":"1.2.0"}')

    records = iter([None, studio_record()])
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: next(records))
    monkeypatch.setattr(portable_launcher, 'available_port', lambda: 8770)
    monkeypatch.setattr(portable_launcher.subprocess, 'Popen', lambda *args, **kwargs: process)
    monkeypatch.setattr(portable_launcher.urllib.request, 'build_opener', lambda *args: LocalOpener())


def forbid_spawn(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Reusing a running studio must not allocate a port or spawn/stop a process')

    monkeypatch.setattr(portable_launcher, 'available_port', forbidden)
    monkeypatch.setattr(portable_launcher.subprocess, 'Popen', forbidden)
    monkeypatch.setattr(portable_launcher.subprocess, 'run', forbidden)


def test_ready_server_failure_is_reported(monkeypatch):
    process = ReadyProcess(17)
    launch_ready(monkeypatch, process)
    with pytest.raises(RuntimeError, match='ma loi 17'):
        portable_launcher.main(open_browser=False)
    assert process.returncode == 17


def test_clean_server_exit_and_browser_fallback(monkeypatch, capsys):
    process = ReadyProcess(0)
    launch_ready(monkeypatch, process)
    opened = []
    monkeypatch.setattr(portable_launcher.webbrowser, 'open', lambda url: opened.append(url) or False)
    assert portable_launcher.main() == 0
    assert process.returncode == 0
    assert opened == ['http://127.0.0.1:8770/?v=1.2.0']
    assert 'Mo dia chi Studio ben tren' in capsys.readouterr().out


def test_ctrl_c_shutdown_is_not_reported_as_server_failure(monkeypatch):
    process = ReadyProcess(130, interrupted=True)
    launch_ready(monkeypatch, process)
    assert portable_launcher.main(open_browser=False) == 0
    assert process.wait_calls == [None, 8]
    assert process.returncode == 130


def test_reopens_verified_server_without_touching_its_locks(monkeypatch, tmp_path, capsys):
    data = tmp_path / 'data'
    data.mkdir()
    engine_lock = data / '.studio.lock'
    engine_lock.write_bytes(b'owned by the running server')
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: studio_record())
    forbid_spawn(monkeypatch)
    opened = []
    monkeypatch.setattr(portable_launcher.webbrowser, 'open', lambda url: opened.append(url) or True)
    assert portable_launcher.main() == 0
    assert opened == ['http://127.0.0.1:8770/?v=1.2.0']
    assert engine_lock.read_bytes() == b'owned by the running server'
    output = capsys.readouterr().out
    assert 'REUSED: existing Voice Studio' in output
    assert 'Studio: http://127.0.0.1:8770' in output


def test_reopens_proven_legacy_server(monkeypatch, capsys):
    monkeypatch.setattr(portable_launcher, 'legacy_discover', lambda data, root: studio_record())
    forbid_spawn(monkeypatch)
    assert portable_launcher.main(open_browser=False) == 0
    assert 'REUSED: existing Voice Studio' in capsys.readouterr().out


def test_reused_backend_mismatch_is_explained_without_switching(monkeypatch, capsys):
    record = studio_record()
    record['backend'] = 'f5_hmong'
    monkeypatch.setattr(portable_launcher, 'IS_HMONG', True)
    monkeypatch.setattr(portable_launcher, 'active_hmong_engine', lambda: 'hmong_native')
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: record)
    forbid_spawn(monkeypatch)
    assert portable_launcher.main(open_browser=False) == 0
    output = capsys.readouterr().out
    assert 'NOTICE:' in output and 'f5_hmong' in output and 'hmong_native' in output


def test_hmong_launcher_uses_variant_default_data_directory(monkeypatch, tmp_path):
    monkeypatch.delenv('VOICE_STUDIO_DATA_DIR')
    monkeypatch.setattr(portable_launcher, '__file__', str(tmp_path / 'portable_launcher.py'))
    monkeypatch.setattr(portable_launcher, 'DEFAULT_DATA_FOLDER', '.data-hmong')
    monkeypatch.setattr(portable_launcher, 'IS_HMONG', True)
    monkeypatch.setattr(portable_launcher, 'active_hmong_engine', lambda: 'f5_hmong')
    observed = []

    def discover(data, root):
        observed.append((data, root))
        return studio_record()

    monkeypatch.setattr(portable_launcher, 'discover_instance', discover)
    forbid_spawn(monkeypatch)
    assert portable_launcher.main(open_browser=False) == 0
    assert observed == [(tmp_path / '.data-hmong', tmp_path)]


def test_child_gets_canonical_data_and_url_and_waits_outside_startup_lock(monkeypatch, isolated_launcher):
    process = ReadyProcess(0)
    launch_ready(monkeypatch, process)
    calls = []

    def spawn(command, *, cwd, env):
        assert isolated_launcher.held
        calls.append((command, cwd, env))
        return process

    original_wait = process.wait

    def wait(timeout=None):
        assert not isolated_launcher.held
        return original_wait(timeout)

    monkeypatch.setattr(portable_launcher.subprocess, 'Popen', spawn)
    monkeypatch.setattr(process, 'wait', wait)
    assert portable_launcher.main(open_browser=False) == 0
    command, root, env = calls[0]
    assert root == Path(portable_launcher.__file__).resolve().parent
    assert command[1:4] == ['-m', 'uvicorn', 'app:app']
    assert env['VOICE_STUDIO_DATA_DIR'] == str(Path(env['VOICE_STUDIO_DATA_DIR']).resolve())
    assert env['VOICE_STUDIO_URL'] == 'http://127.0.0.1:8770'


@pytest.mark.parametrize('bad_identity', [{'pid': 9999}, {'url': 'http://127.0.0.1:8771'}])
def test_config_alone_cannot_make_another_process_ready(monkeypatch, bad_identity):
    process = ReadyProcess(0)
    launch_ready(monkeypatch, process)
    foreign = studio_record()
    foreign.update(bad_identity)
    records = iter([None, foreign, studio_record()])
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: next(records))
    sleeps = []
    monkeypatch.setattr(portable_launcher.time, 'sleep', sleeps.append)
    assert portable_launcher.main(open_browser=False) == 0
    # A config endpoint cannot establish readiness until identity matches the
    # child PID and assigned URL; the preceding mismatch must be retried.
    assert sleeps == [.25]


def test_unverified_local_config_is_never_adopted(monkeypatch):
    process = ReadyProcess(0)
    launch_ready(monkeypatch, process)
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: None)
    ticks = iter([0, 0, 61])
    monkeypatch.setattr(portable_launcher.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(portable_launcher.time, 'sleep', lambda delay: None)

    class ForeignOpener:
        def open(self, *args, **kwargs):
            pytest.fail('An unrelated config endpoint must not be queried or adopted')

    monkeypatch.setattr(portable_launcher.urllib.request, 'build_opener', lambda *args: ForeignOpener())
    with pytest.raises(RuntimeError, match='60 giay'):
        portable_launcher.main(open_browser=False)
    assert process.wait_calls == [8]


def test_child_losing_to_older_launcher_reopens_proven_winner(monkeypatch, capsys):
    process = ReadyProcess(1)
    process.returncode = 1
    launch_ready(monkeypatch, process)
    assert portable_launcher.main(open_browser=False) == 0
    assert process.wait_calls == []
    assert 'REUSED: existing Voice Studio' in capsys.readouterr().out


def test_reused_server_browser_error_keeps_url_available(monkeypatch, capsys):
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: studio_record())
    forbid_spawn(monkeypatch)

    def unavailable(url):
        raise portable_launcher.webbrowser.Error('browser unavailable')

    monkeypatch.setattr(portable_launcher.webbrowser, 'open', unavailable)
    assert portable_launcher.main() == 0
    output = capsys.readouterr().out
    assert 'Studio: http://127.0.0.1:8770' in output
    assert 'Mo dia chi Studio ben tren' in output


def test_concurrent_launchers_wait_for_readiness_and_start_only_one_server(monkeypatch):
    startup_lock = threading.Lock()
    entering_second = threading.Event()
    waiting_for_readiness = threading.Event()
    allow_readiness = threading.Event()
    reopened = threading.Event()
    shared = {'studio': None, 'spawns': 0, 'lock_owner': None}
    results = {}

    class SerializedLock:
        def __init__(self, data):
            self.data = data

        def __enter__(self):
            if threading.current_thread().name == 'reopener':
                entering_second.set()
            assert startup_lock.acquire(timeout=3)
            shared['lock_owner'] = threading.get_ident()

        def __exit__(self, *args):
            shared['lock_owner'] = None
            startup_lock.release()

    class OwningProcess(ReadyProcess):
        def wait(self, timeout=None):
            assert shared['lock_owner'] != threading.get_ident()
            if timeout is None:
                assert reopened.wait(timeout=3)
            return super().wait(timeout)

    process = OwningProcess(0)

    def spawn(*args, **kwargs):
        shared['spawns'] += 1
        shared['studio'] = studio_record()
        return process

    class ReadinessOpener:
        def open(self, url, timeout):
            waiting_for_readiness.set()
            assert allow_readiness.wait(timeout=3)
            return io.BytesIO(b'{"mode":"local","version":"1.2.0"}')

    def launch(name):
        try:
            results[name] = portable_launcher.main(open_browser=False)
        except BaseException as exc:
            results[name] = exc
        finally:
            if name == 'reopener':
                reopened.set()

    monkeypatch.setattr(portable_launcher, 'StartupLock', SerializedLock)
    monkeypatch.setattr(portable_launcher, 'discover_instance', lambda data, root: shared['studio'])
    monkeypatch.setattr(portable_launcher, 'available_port', lambda: 8770)
    monkeypatch.setattr(portable_launcher.subprocess, 'Popen', spawn)
    monkeypatch.setattr(portable_launcher.urllib.request, 'build_opener', lambda *args: ReadinessOpener())
    owner = threading.Thread(target=launch, args=('owner',), name='owner')
    second = threading.Thread(target=launch, args=('reopener',), name='reopener')
    owner.start()
    try:
        assert waiting_for_readiness.wait(timeout=3)
        second.start()
        assert entering_second.wait(timeout=3)
        assert shared['spawns'] == 1
        assert not reopened.is_set()
    finally:
        allow_readiness.set()
        owner.join(timeout=5)
        if second.ident is not None:
            second.join(timeout=5)
    assert not owner.is_alive() and not second.is_alive()
    assert results == {'owner': 0, 'reopener': 0}
    assert shared['spawns'] == 1
