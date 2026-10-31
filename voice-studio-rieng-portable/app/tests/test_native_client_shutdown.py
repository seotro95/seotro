"""A normal native-client shutdown must run its child's resource finalizers."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fast_multilingual import _BackendClient


class NativeClientShutdownTests(unittest.TestCase):
    def client(self, process):
        client = _BackendClient.__new__(_BackendClient)
        client.process, client.log = process, io.StringIO()
        return client

    def test_stdio_eof_releases_real_child_hardlink_before_returning(self):
        with tempfile.TemporaryDirectory(prefix='native-shutdown-test-') as temporary:
            root = Path(temporary).resolve()
            if not str(root).isascii():
                self.skipTest('The hard-link fixture needs an ASCII temporary parent')
            model_dir = root / 'giọng nói Tiếng Việt !'
            model_dir.mkdir()
            model = model_dir / 'model.gguf'
            original = b'GGUF public model shutdown fixture'
            model.write_bytes(original)
            app_dir = Path(__file__).resolve().parents[1]
            child = (
                'import json,pathlib,sys;sys.path.insert(0,sys.argv[1]);'
                'import native_paths as p;'
                'p._on_windows=lambda:True;'
                'p._windows_short_path=lambda _:None;'
                'p._candidate_parents=lambda _:iter([pathlib.Path(sys.argv[3])]);'
                '\nwith p.native_model_path(pathlib.Path(sys.argv[2])) as encoded:\n'
                ' print(json.dumps({"alias":encoded.decode("ascii")}),flush=True)\n'
                ' sys.stdin.read()\n'
            )
            process = subprocess.Popen([sys.executable, '-s', '-X', 'utf8', '-c', child,
                                        str(app_dir), str(model), str(root)],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, encoding='utf-8')
            client = self.client(process)
            try:
                ready = process.stdout.readline()
                if not ready:
                    self.fail('The resource-owning child did not start: ' + process.stderr.read())
                alias = Path(json.loads(ready)['alias'])
                self.assertTrue(os.path.samefile(model, alias))
                with mock.patch.object(process, 'terminate', wraps=process.terminate) as terminate, \
                        mock.patch.object(process, 'kill', wraps=process.kill) as kill:
                    client.close()
                    terminate.assert_not_called()
                    kill.assert_not_called()
                self.assertEqual(process.returncode, 0)
                self.assertFalse(alias.exists(), 'Normal close must remove the model alias')
                self.assertFalse(alias.parent.exists(), 'Normal close must remove its owned temp directory')
                self.assertEqual(model.read_bytes(), original)
                self.assertTrue(client.log.closed)
                self.assertTrue(process.stdin.closed)
                self.assertTrue(process.stdout.closed)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()

    def test_hung_server_terminates_then_kills_after_bounded_grace_periods(self):
        process = mock.Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('native', 5),
                                    subprocess.TimeoutExpired('native', 5), 0]
        client = self.client(process)
        client.close()
        events = process.mock_calls
        first_close = events.index(mock.call.stdin.close())
        first_wait = events.index(mock.call.wait(timeout=5))
        terminate = events.index(mock.call.terminate())
        kill = events.index(mock.call.kill())
        self.assertLess(first_close, first_wait)
        self.assertLess(first_wait, terminate)
        self.assertLess(terminate, kill)
        self.assertEqual(process.wait.call_count, 3)
        self.assertTrue(client.log.closed)
        process.stdout.close.assert_called_once()

    def test_already_exited_or_partly_constructed_client_can_close_twice(self):
        process = SimpleNamespace(poll=lambda: 0)
        client = self.client(process)
        client.close()
        client.close()
        self.assertTrue(client.log.closed)
        empty = _BackendClient.__new__(_BackendClient)
        empty.close()


if __name__ == '__main__':
    unittest.main()
