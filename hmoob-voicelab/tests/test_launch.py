import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime_lock import DataLock
from server import make_server


class LaunchTests(unittest.TestCase):
    def test_same_data_is_locked_until_server_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            server = make_server(directory, port=0, engine=object(),
                                 engine_status=lambda: {'ready': False, 'reason': 'test'})
            try:
                self.assertNotEqual(server.server_port, 8123)
                with self.assertRaisesRegex(ValueError, 'phiên'):
                    make_server(directory, port=0, engine=object(), engine_status=lambda: {})
            finally:
                server.server_close()
            with tempfile.TemporaryDirectory() as other:
                lock = DataLock(directory)
                lock.close()

    def test_launcher_uses_requested_ephemeral_port_and_restarts(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            for _ in range(2):
                process = subprocess.Popen([sys.executable, str(root / 'launch.py'), '--no-browser',
                                            '--port', '0', '--data-dir', directory],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                           env={**os.environ, 'PYTHONUNBUFFERED': '1'})
                try:
                    line = process.stdout.readline().strip()
                    self.assertIn('127.0.0.1:', line)
                    self.assertNotIn(':8123', line)
                finally:
                    process.terminate()
                    process.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main()
