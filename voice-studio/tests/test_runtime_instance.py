"""Exercise server ownership across real processes without loading voice models."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

import runtime_instance


ROOT = Path(__file__).resolve().parents[1]


def instance(data, root=None, **kwargs):
    return runtime_instance.StudioInstance(
        data, root or ROOT, version='test-version', variant='hmong',
        backend='f5', **kwargs,
    )


def child_command(source, *args):
    return [sys.executable, '-u', '-c', source, *map(str, args)]


CHILD_HOLDER = """
import json
import sys
from runtime_instance import StudioInstance
with StudioInstance(sys.argv[1], sys.argv[2], version='test-version', variant='hmong', backend='f5') as owner:
    print(json.dumps(owner.public_identity()), flush=True)
    sys.stdin.read()
"""


CHILD_CONTENDER = """
import sys
from runtime_instance import StudioInstance
try:
    with StudioInstance(sys.argv[1], sys.argv[2], version='test-version', variant='hmong', backend='f5'):
        print('acquired', flush=True)
except RuntimeError:
    print('blocked', flush=True)
"""


CHILD_LEGACY_HOLDER = """
import json
import os
from pathlib import Path
import sys
data = Path(sys.argv[1])
data.mkdir(parents=True, exist_ok=True)
with (data / 'server.lock').open('a+b') as handle:
    handle.write(b'0')
    handle.flush()
    handle.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    print(json.dumps({'pid': os.getpid()}), flush=True)
    sys.stdin.read()
"""


@contextmanager
def holding_child(data, source=CHILD_HOLDER):
    process = subprocess.Popen(
        child_command(source, data, ROOT), cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    lines = queue.Queue()
    reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        line = lines.get(timeout=10)
        if not line:
            raise AssertionError(process.stderr.read())
        identity = json.loads(line)
        assert identity['pid'] == process.pid
        yield process, identity
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        for handle in (process.stdin, process.stdout, process.stderr):
            handle.close()
        reader.join(timeout=1)


@pytest.fixture
def runtime_endpoint():
    state = {'identity': {}, 'requests': []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state['requests'].append(self.path)
            status = 200
            if self.path.startswith('/api/voices/'):
                ident = self.path.split('/')[3]
                try:
                    body = (state['sample_dir'] / (ident + '.wav')).read_bytes()
                    state['sample_bytes'] = body
                    body = state.get('sample_override', body)
                except (KeyError, OSError):
                    body, status = b'not found', 404
            else:
                body = json.dumps(state['identity']).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    state['url'] = f'http://127.0.0.1:{server.server_port}'
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize('leftover', [b'', b'0', b'0' * 200])
def test_old_lock_file_does_not_mean_a_server_is_running(tmp_path, leftover):
    data = tmp_path / 'saved projects'
    data.mkdir()
    lock_file = data / 'server.lock'
    lock_file.write_bytes(leftover)
    for _ in range(2):
        with instance(data):
            assert lock_file.exists()
    assert lock_file.exists()


def test_another_process_cannot_acquire_the_active_data_directory(tmp_path):
    data = tmp_path / 'saved projects'
    with instance(data):
        record = (data / 'server-instance.json').read_bytes()
        result = subprocess.run(
            child_command(CHILD_CONTENDER, data, ROOT), cwd=ROOT,
            capture_output=True, text=True, check=True, timeout=10,
        )
        assert result.stdout.strip() == 'blocked'
        assert (data / 'server-instance.json').read_bytes() == record
    result = subprocess.run(
        child_command(CHILD_CONTENDER, data, ROOT), cwd=ROOT,
        capture_output=True, text=True, check=True, timeout=10,
    )
    assert result.stdout.strip() == 'acquired'


def test_legacy_file_lock_still_excludes_a_new_server(tmp_path):
    data = tmp_path / 'saved projects'
    with holding_child(data, CHILD_LEGACY_HOLDER):
        with pytest.raises(runtime_instance.StudioBusy):
            with instance(data):
                pytest.fail('A server started over the legacy process lock.')
        assert not (data / 'server-instance.json').exists()
    with instance(data):
        pass


def test_separate_data_directories_do_not_block_each_other(tmp_path):
    with instance(tmp_path / 'first'):
        result = subprocess.run(
            child_command(CHILD_CONTENDER, tmp_path / 'second', ROOT), cwd=ROOT,
            capture_output=True, text=True, check=True, timeout=10,
        )
        assert result.stdout.strip() == 'acquired'


def test_startup_lock_serializes_launchers_and_releases_after_exit(tmp_path):
    data = tmp_path / 'saved projects'
    contender = """
import sys
from runtime_instance import StartupLock
try:
    with StartupLock(sys.argv[1], timeout=.1):
        print('acquired', flush=True)
except RuntimeError:
    print('blocked', flush=True)
"""
    with runtime_instance.StartupLock(data, timeout=.1):
        result = subprocess.run(
            child_command(contender, data), cwd=ROOT,
            capture_output=True, text=True, check=True, timeout=10,
        )
        assert result.stdout.strip() == 'blocked'
    result = subprocess.run(
        child_command(contender, data), cwd=ROOT,
        capture_output=True, text=True, check=True, timeout=10,
    )
    assert result.stdout.strip() == 'acquired'


def test_process_crash_releases_lock_without_deleting_lock_file(tmp_path):
    data = tmp_path / 'saved projects'
    with holding_child(data) as (process, previous_identity):
        lock_file = data / 'server.lock'
        assert lock_file.exists()
        process.kill()
        process.wait(timeout=10)
        assert lock_file.exists()
        with instance(data) as replacement:
            assert replacement.public_identity()['instance_id'] != previous_identity['instance_id']
    assert lock_file.exists()


def test_shutdown_does_not_delete_another_owners_identity(tmp_path):
    data = tmp_path / 'saved projects'
    record = data / 'server-instance.json'
    with instance(data) as owner:
        replacement = dict(owner.public_identity(), instance_id='replacement-owner')
        record.write_text(json.dumps(replacement), encoding='utf-8')
    assert json.loads(record.read_text(encoding='utf-8'))['instance_id'] == 'replacement-owner'


def test_normal_shutdown_removes_own_identity_and_retains_lock_file(tmp_path):
    data = tmp_path / 'saved projects'
    with instance(data):
        assert (data / 'server-instance.json').is_file()
    assert not (data / 'server-instance.json').exists()
    assert (data / 'server.lock').is_file()


@pytest.mark.parametrize('contents', ['', '{', '[]', '{"pid": "invalid"}'])
def test_malformed_identity_is_ignored(tmp_path, contents):
    data = tmp_path / 'saved projects'
    data.mkdir()
    (data / 'server-instance.json').write_text(contents, encoding='utf-8')
    assert runtime_instance.discover_instance(data, ROOT) is None


def test_ids_use_resolved_paths(tmp_path):
    original = tmp_path / 'saved projects'
    alias = tmp_path / 'unused' / '..' / 'saved projects'
    assert runtime_instance.make_data_id(original) == runtime_instance.make_data_id(alias)
    assert runtime_instance.make_root_id(original) == runtime_instance.make_root_id(alias)


def test_discovery_requires_a_live_matching_http_identity(tmp_path, runtime_endpoint):
    data = tmp_path / 'saved projects'
    with instance(data, url=runtime_endpoint['url']) as owner:
        runtime_endpoint['identity'] = owner.public_identity()
        found = runtime_instance.discover_instance(data, ROOT)
        assert found is not None
        assert found['url'] == runtime_endpoint['url']
    assert runtime_endpoint['requests'] == ['/api/runtime']


@pytest.mark.parametrize('field,replacement', [
    ('instance_id', '0' * 32),
    ('pid', -1),
    ('create_time', 0),
    ('data_id', '0' * 64),
    ('root_id', '0' * 64),
    ('version', 'unrelated-version'),
    ('variant', 'another-product'),
    ('backend', 'another-backend'),
    ('url', 'http://127.0.0.1:1'),
])
def test_discovery_rejects_endpoint_identity_mismatch(tmp_path, runtime_endpoint, field, replacement):
    data = tmp_path / 'saved projects'
    with instance(data, url=runtime_endpoint['url']) as owner:
        runtime_endpoint['identity'] = dict(owner.public_identity(), **{field: replacement})
        assert runtime_instance.discover_instance(data, ROOT) is None


@pytest.mark.parametrize('field,replacement', [
    ('pid', -1),
    ('create_time', 0),
    ('data_id', '0' * 64),
    ('root_id', '0' * 64),
    ('url', 'https://example.invalid'),
    ('url', 'http://localhost.evil.invalid:8770'),
    ('url', 'http://127.0.0.1:8770/another/path'),
])
def test_untrusted_record_is_rejected_before_any_http_request(tmp_path, runtime_endpoint, field, replacement):
    data = tmp_path / 'saved projects'
    with instance(data, url=runtime_endpoint['url']) as owner:
        identity = owner.public_identity()
        runtime_endpoint['identity'] = identity
        record = dict(identity, **{field: replacement})
        (data / 'server-instance.json').write_text(json.dumps(record), encoding='utf-8')
        assert runtime_instance.discover_instance(data, ROOT) is None
        assert runtime_endpoint['requests'] == []


@pytest.mark.skipif(os.name == 'nt', reason='POSIX directory permissions exercise a real access failure.')
def test_unwritable_data_is_not_reported_as_an_already_running_server(tmp_path):
    if os.geteuid() == 0:
        pytest.skip('Root bypasses directory write permission bits.')
    data = tmp_path / 'read only projects'
    data.mkdir()
    data.chmod(0o555)
    try:
        with pytest.raises((OSError, RuntimeError)) as caught:
            with instance(data):
                pytest.fail('The lock was acquired in an unwritable directory.')
        assert not isinstance(caught.value, runtime_instance.StudioBusy)
        assert str(caught.value)
    finally:
        data.chmod(0o700)


class LegacyProcess:
    pid = 4321

    def __init__(self, data):
        self.info = {'pid': self.pid, 'cmdline': [
            sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1',
            '--port', '8777', '--no-access-log',
        ]}
        self.directory = ROOT
        self.environment = {'VOICE_STUDIO_DATA_DIR': str(data), 'VOICE_STUDIO_VARIANT': 'hmong'}
        self.checked_directory = self.checked_environment = False
        self.created = 123.0
        self.running = True

    def cwd(self):
        self.checked_directory = True
        return str(self.directory)

    def environ(self):
        self.checked_environment = True
        return dict(self.environment)

    def create_time(self):
        return self.created

    def is_running(self):
        return self.running


def legacy_process_only(monkeypatch, process):
    monkeypatch.setattr(runtime_instance.psutil, 'process_iter', lambda attrs: iter([process]))


def test_legacy_discovery_checks_process_and_data_before_http(tmp_path, monkeypatch):
    data = tmp_path / 'saved projects'
    process = LegacyProcess(data)
    legacy_process_only(monkeypatch, process)
    requests = []

    def config(url, **kwargs):
        assert process.checked_directory and process.checked_environment
        requests.append(url)
        return {'mode': 'local', 'variant': 'hmong', 'version': '1.5.0-hmong', 'hmong_engine': 'f5_hmong'}

    monkeypatch.setattr(runtime_instance, '_get_json', config)
    found = runtime_instance.legacy_discover(data, ROOT)
    assert found['pid'] == process.pid
    assert found['url'] == 'http://127.0.0.1:8777'
    assert found['backend'] == 'f5_hmong'
    assert found['data_id'] == runtime_instance.make_data_id(data)
    assert found['root_id'] == runtime_instance.make_root_id(ROOT)
    assert requests == ['http://127.0.0.1:8777/api/config']


def test_legacy_relative_data_directory_uses_the_server_working_directory(tmp_path, monkeypatch):
    root = tmp_path / 'program'
    root.mkdir()
    data = root / 'saved projects'
    process = LegacyProcess(data)
    process.directory = root
    process.environment['VOICE_STUDIO_DATA_DIR'] = 'saved projects'
    legacy_process_only(monkeypatch, process)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runtime_instance, '_get_json', lambda url, **kwargs: {
        'mode': 'local', 'variant': 'hmong', 'version': '1.5.0-hmong',
    })
    found = runtime_instance.legacy_discover(data, root)
    assert found is not None
    assert found['data_id'] == runtime_instance.make_data_id(data)


@pytest.mark.parametrize('mismatch', ['cwd', 'data', 'command', 'host', 'missing-port'])
def test_legacy_discovery_never_probes_an_unproven_process(tmp_path, monkeypatch, mismatch):
    data = tmp_path / 'saved projects'
    process = LegacyProcess(data)
    if mismatch == 'cwd':
        process.directory = tmp_path / 'foreign application'
    elif mismatch == 'data':
        process.environment['VOICE_STUDIO_DATA_DIR'] = str(tmp_path / 'other projects')
    elif mismatch == 'command':
        process.info['cmdline'] = [sys.executable, '-m', 'http.server', '8777']
    elif mismatch == 'host':
        process.info['cmdline'][5] = '0.0.0.0'
    else:
        process.info['cmdline'] = process.info['cmdline'][:6]
    legacy_process_only(monkeypatch, process)

    def forbidden(url, **kwargs):
        pytest.fail('An unproven process must not trigger any HTTP request.')

    monkeypatch.setattr(runtime_instance, '_get_json', forbidden)
    monkeypatch.setattr(runtime_instance, '_legacy_data_challenge', forbidden)
    assert runtime_instance.legacy_discover(data, ROOT) is None


def test_legacy_discovery_skips_process_with_unreadable_environment(tmp_path, monkeypatch):
    data = tmp_path / 'saved projects'
    process = LegacyProcess(data)
    legacy_process_only(monkeypatch, process)

    def denied():
        raise runtime_instance.psutil.AccessDenied(process.pid)

    def forbidden(url, **kwargs):
        pytest.fail('An unreadable process environment must prevent HTTP discovery.')

    monkeypatch.setattr(process, 'environ', denied)
    monkeypatch.setattr(runtime_instance, '_get_json', forbidden)
    assert runtime_instance.legacy_discover(data, ROOT) is None


@pytest.mark.parametrize('change', ['reused-pid', 'stopped', 'wrong-variant', 'foreign-service'])
def test_legacy_discovery_rejects_invalid_response_or_process_change(tmp_path, monkeypatch, change):
    data = tmp_path / 'saved projects'
    process = LegacyProcess(data)
    legacy_process_only(monkeypatch, process)

    def config(url, **kwargs):
        result = {'mode': 'local', 'variant': 'hmong', 'version': '1.5.0-hmong'}
        if change == 'reused-pid':
            process.created += 1
        elif change == 'stopped':
            process.running = False
        elif change == 'wrong-variant':
            result['variant'] = 'standard'
        else:
            result['mode'] = 'foreign'
        return result

    monkeypatch.setattr(runtime_instance, '_get_json', config)
    assert runtime_instance.legacy_discover(data, ROOT) is None


@pytest.mark.parametrize('denied', ['cwd', 'environment', 'both'])
@pytest.mark.parametrize('matches_data', [True, False])
def test_protected_legacy_process_requires_a_successful_data_challenge(tmp_path, monkeypatch, denied, matches_data):
    data = tmp_path / 'saved projects'
    process = LegacyProcess(data)
    legacy_process_only(monkeypatch, process)
    monkeypatch.setenv('VOICE_STUDIO_VARIANT', 'hmong')

    def access_denied():
        raise runtime_instance.psutil.AccessDenied(process.pid)

    if denied in {'cwd', 'both'}:
        monkeypatch.setattr(process, 'cwd', access_denied)
    if denied in {'environment', 'both'}:
        monkeypatch.setattr(process, 'environ', access_denied)
    calls = []

    def challenge(candidate_data, url):
        assert candidate_data == data
        assert url == 'http://127.0.0.1:8777'
        calls.append('challenge')
        return matches_data

    def config(url, **kwargs):
        assert matches_data
        assert calls == ['challenge']
        calls.append('config')
        return {'mode': 'local', 'variant': 'hmong', 'version': '1.5.0-hmong'}

    monkeypatch.setattr(runtime_instance, '_legacy_data_challenge', challenge)
    monkeypatch.setattr(runtime_instance, '_get_json', config)
    found = runtime_instance.legacy_discover(data, ROOT)
    assert (found is not None) is matches_data
    assert calls == (['challenge', 'config'] if matches_data else ['challenge'])


@pytest.mark.parametrize('response', ['matching', 'wrong-body', 'different-data'])
def test_real_data_challenge_cleans_up_its_own_temporary_sample(tmp_path, runtime_endpoint, response):
    data = tmp_path / 'saved projects'
    voices = data / 'voices'
    voices.mkdir(parents=True)
    personal = voices / 'personal.wav'
    personal.write_bytes(b'keep personal voice')
    runtime_endpoint['sample_dir'] = voices if response != 'different-data' else tmp_path / 'unrelated voices'
    if response == 'wrong-body':
        runtime_endpoint['sample_override'] = b'foreign service response'
    assert runtime_instance._legacy_data_challenge(data, runtime_endpoint['url']) is (response == 'matching')
    assert list(voices.iterdir()) == [personal]
    assert personal.read_bytes() == b'keep personal voice'
    assert len(runtime_endpoint['requests']) == 1
    assert runtime_endpoint['requests'][0].startswith('/api/voices/')
    assert runtime_endpoint['requests'][0].endswith('/sample')
    if response != 'different-data':
        assert runtime_endpoint['sample_bytes'].startswith(b'RIFF')


def test_data_challenge_never_overwrites_or_deletes_an_existing_sample(tmp_path, monkeypatch):
    data = tmp_path / 'saved projects'
    voices = data / 'voices'
    voices.mkdir(parents=True)
    ident = 'a' * 32
    existing = voices / (ident + '.wav')
    existing.write_bytes(b'keep existing sample')
    monkeypatch.setattr(runtime_instance.uuid, 'uuid4', lambda: SimpleNamespace(hex=ident))
    assert runtime_instance._legacy_data_challenge(data, 'http://127.0.0.1:8777') is False
    assert existing.read_bytes() == b'keep existing sample'
