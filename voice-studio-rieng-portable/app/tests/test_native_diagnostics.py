import queue
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fast_multilingual import _BackendClient


class NativeDiagnosticsTests(unittest.TestCase):
    def test_stopped_child_reports_exit_and_only_its_current_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native.log'
            old = b'OLD UNRELATED JOB\n'
            path.write_bytes(old + b'\x1b[31mCUDA error: out of memory\x1b[0m\n')
            client = _BackendClient.__new__(_BackendClient)
            client.process = SimpleNamespace(poll=lambda: 42)
            client.responses = queue.Queue()
            client.responses.put(None)
            client._log_path, client._log_start = path, len(old)
            with self.assertRaises(ValueError) as error:
                client._response()
            self.assertIn('42', str(error.exception))
            self.assertIn('CUDA error: out of memory', str(error.exception))
            self.assertNotIn('OLD UNRELATED JOB', str(error.exception))
            self.assertNotIn('\x1b', str(error.exception))

    def test_missing_or_oversized_log_keeps_the_message_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            client = _BackendClient.__new__(_BackendClient)
            client.process = SimpleNamespace(poll=lambda: -11)
            client._log_path, client._log_start = Path(directory) / 'missing', 0
            self.assertIn('international-native-backend.log', client._stopped_message())
            client._log_path.write_bytes(b'x' * 100000 + b'LAST FAILURE')
            message = client._stopped_message()
            self.assertLess(len(message), 2200)
            self.assertIn('LAST FAILURE', message)


if __name__ == '__main__':
    unittest.main()
