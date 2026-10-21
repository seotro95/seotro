"""The startup logger is tested with real small child processes, no AI imports."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('launch_logged', Path(__file__).resolve().parents[1] / 'launch_logged.py')
logged = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(logged)


class LoggedLauncherTests(unittest.TestCase):
    def test_real_child_output_errors_and_exit_are_visible_and_persisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'bootstrap.py').write_text(
                "import sys\nprint('Kiem tra giọng nữ', flush=True)\nprint('native DLL failed', file=sys.stderr, flush=True)\nraise SystemExit(7)\n", encoding='utf-8')
            output = io.StringIO()
            with patch.dict(os.environ, {'PYTHONUTF8': '1'}), patch('sys.stdout', output):
                code = logged.main(['--data-dir', str(root / 'saved data')], base=root)
            text = output.getvalue()
            log = (root / 'saved data/.logs/launch.log').read_text(encoding='utf-8')
            self.assertEqual(code, 7)
            self.assertIn('giọng nữ', text)
            self.assertIn('native DLL failed', text)
            self.assertIn('native DLL failed', log)
            self.assertIn('ma loi 7', log)

    def test_diagnostic_mode_keeps_child_check_json_and_creates_separate_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'bootstrap.py').write_text(
                "import json,sys\nassert '--check' in sys.argv\nprint(json.dumps({'ready': True}))\n", encoding='utf-8')
            output = io.StringIO()
            with patch('sys.stdout', output):
                code = logged.main(['--diagnose', '--data-dir', str(root / '.data')], base=root)
            values = []
            for line in output.getvalue().splitlines():
                try:values.append(json.loads(line))
                except ValueError:pass
            self.assertEqual(code, 0)
            self.assertIn({'ready': True}, values)
            self.assertTrue((root / '.data/.logs/diagnostic.log').is_file())
            self.assertFalse((root / '.data/.logs/launch.log').exists())

    def test_silent_child_produces_heartbeat_before_first_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'bootstrap.py').write_text(
                "import time\ntime.sleep(1.2)\nprint('ready', flush=True)\n", encoding='utf-8')
            output = io.StringIO()
            with patch('sys.stdout', output), patch.object(logged, 'HEARTBEAT_SECONDS', .05):
                code = logged.main(['--data-dir', str(root / '.data')], base=root)
            text = output.getvalue()
            self.assertEqual(code, 0)
            self.assertLess(text.index('Van dang chuan bi'), text.index('ready'))
            self.assertIn('Van dang chuan bi', (root / '.data/.logs/launch.log').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
