"""First-run setup and prepared-runtime launch, with no network installation."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bootstrap


READY = {'ready': True, 'torch_pair_ready': True, 'versions': {'f5-tts': '1.1.22'}}


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hmoob bootstrap ')
        self.folder = Path(self.temporary.name)
        self.base = self.folder / 'hmoob-voicelab'
        self.base.mkdir()
        self.data = self.base / '.data'
        self.data.mkdir()
        self.saved = self.data / 'keep-user-job.json'
        self.saved.write_bytes(b'original user data')

    def tearDown(self):
        self.temporary.cleanup()

    def portable(self):
        python = self.folder / 'runtime' / 'python.exe'
        python.parent.mkdir()
        python.write_bytes(b'portable runtime fixture')
        return python

    def test_prepared_portable_launches_without_installing_and_preserves_arguments(self):
        python = self.portable()
        with patch.dict(os.environ, {'PYTHONHOME': '/inherited/wrong-python',
                                     'PYTHONPATH': '/inherited/wrong-packages'}), \
                patch('bootstrap.check_python'), patch('bootstrap.check_ffmpeg'), \
                patch('bootstrap.dependency_state', return_value=READY), \
                patch('bootstrap.models_ready', return_value=True), \
                patch('bootstrap.prepare_runtime', side_effect=AssertionError('must not install')), \
                patch('bootstrap.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            result = bootstrap.main(['--data-dir', str(self.data), '--no-browser', '--port', '0'],
                                    base=self.base)
        self.assertEqual(result, 0)
        command = run.call_args.args[0]
        self.assertEqual(command, [str(python), str(self.base / 'launch.py'), '--data-dir',
                                   str(self.data), '--no-browser', '--port', '0'])
        self.assertNotIn('shell', run.call_args.kwargs)
        environment = run.call_args.kwargs['env']
        self.assertNotIn('PYTHONHOME', environment)
        self.assertNotIn('PYTHONPATH', environment)
        self.assertEqual(environment['PYTHONNOUSERSITE'], '1')
        self.assertEqual(self.saved.read_bytes(), b'original user data')

    def test_portable_missing_only_models_downloads_models_without_pip_or_venv(self):
        python = self.portable()
        calls = []
        with patch('bootstrap.check_python'), patch('bootstrap.check_ffmpeg'), \
                patch('bootstrap.dependency_state', return_value=READY), \
                patch('bootstrap.models_ready', side_effect=[False, False, True]), \
                patch('bootstrap.run_step', side_effect=lambda command, *args: calls.append(command)):
            result = bootstrap.main(['--setup', '--data-dir', str(self.data)], base=self.base)
        self.assertEqual(result, 0)
        self.assertEqual(calls, [[str(python), self.base / 'setup_voice.py']])
        self.assertFalse((self.base / '.venv').exists())
        self.assertEqual(self.saved.read_bytes(), b'original user data')

    def test_source_setup_uses_private_environment_and_tested_cpu_pair(self):
        calls = []
        state = {'ready': False, 'torch_pair_ready': False}
        with patch('bootstrap.check_python'), patch('bootstrap.dependency_state', return_value=READY), \
                patch('bootstrap.models_ready', return_value=True), \
                patch('bootstrap.run_step', side_effect=lambda command, *args: calls.append(command)), \
                patch('bootstrap.subprocess.run', return_value=SimpleNamespace(returncode=0)):
            selected = bootstrap.prepare_runtime('source-python', 'system', self.base,
                                                 os.environ.copy(), state)
        self.assertEqual(calls[0], ['source-python', '-m', 'venv', self.base / '.venv'])
        self.assertIn('.venv', selected)
        torch_command = next(command for command in calls if 'torch==2.6.0' in command)
        self.assertIn('torchaudio==2.6.0', torch_command)
        if sys.platform != 'darwin':
            self.assertEqual(torch_command[-2:], ['--index-url', 'https://download.pytorch.org/whl/cpu'])
        self.assertEqual(self.saved.read_bytes(), b'original user data')

    def test_existing_incomplete_environment_is_not_overwritten(self):
        old = self.base / '.venv'
        old.mkdir()
        marker = old / 'existing-settings'
        marker.write_text('preserve')
        with patch('bootstrap.run_step', side_effect=AssertionError('must not mutate')):
            with self.assertRaisesRegex(bootstrap.SetupError, 'không xóa'):
                bootstrap.prepare_runtime('source-python', 'system', self.base, {},
                                          {'ready': False, 'torch_pair_ready': False})
        self.assertEqual(marker.read_text(), 'preserve')
        self.assertEqual(self.saved.read_bytes(), b'original user data')

    def test_model_verification_failure_does_not_launch_or_delete_data(self):
        self.portable()
        errors = io.StringIO()
        with patch('bootstrap.check_python'), patch('bootstrap.check_ffmpeg'), \
                patch('bootstrap.dependency_state', return_value=READY), \
                patch('bootstrap.models_ready', return_value=False), \
                patch('bootstrap.run_step') as install, \
                patch('bootstrap.subprocess.run', side_effect=AssertionError('must not launch')), \
                redirect_stderr(errors):
            result = bootstrap.main(['--data-dir', str(self.data)], base=self.base)
        self.assertEqual(result, 1)
        self.assertEqual(install.call_count, 1)
        self.assertIn('SHA-256', errors.getvalue())
        self.assertEqual(self.saved.read_bytes(), b'original user data')

    def test_check_reports_missing_models_without_setup_or_launch(self):
        self.portable()
        output = io.StringIO()
        with patch('bootstrap.check_python'), patch('bootstrap.check_ffmpeg'), \
                patch('bootstrap.dependency_state', return_value=READY), \
                patch('bootstrap.models_ready', return_value=False), \
                patch('bootstrap.prepare_runtime', side_effect=AssertionError('must not install')), \
                patch('bootstrap.subprocess.run', side_effect=AssertionError('must not launch')), \
                redirect_stdout(output):
            result = bootstrap.main(['--check', '--data-dir', str(self.data)], base=self.base)
        self.assertEqual(result, 1)
        report = json.loads(output.getvalue())
        self.assertFalse(report['ready'])
        self.assertTrue(report['dependencies']['ready'])
        self.assertFalse(report['models_verified'])

    def test_bundled_ffmpeg_pair_is_discovered_in_portable_parent(self):
        binaries = self.folder / 'ffmpeg' / 'bin'
        binaries.mkdir(parents=True)
        suffix = '.exe' if os.name == 'nt' else ''
        for name in ('ffmpeg', 'ffprobe'):
            (binaries / (name + suffix)).write_bytes(b'fixture')
        inherited = {'PATH': 'original-search-path', 'HMOOB_MODEL_DIR': 'custom-model-location'}
        environment = bootstrap.configure_environment(self.base, self.data, inherited)
        self.assertEqual(environment['PATH'].split(os.pathsep)[0], str(binaries))
        self.assertEqual(environment['HMOOB_MODEL_DIR'], 'custom-model-location')
        self.assertEqual(environment['PATH'].split(os.pathsep)[-1], 'original-search-path')
        self.assertEqual(inherited['PATH'], 'original-search-path')
        self.assertEqual(environment['HMOOB_DATA_DIR'], str(self.data))
        self.assertEqual(environment['HF_HUB_OFFLINE'], '1')

    def test_unsupported_python_is_rejected_before_installation(self):
        for version in ({'major': 3, 'minor': 13, 'bits': 64},
                        {'major': 3, 'minor': 12, 'bits': 32}):
            with self.subTest(version=version), patch('bootstrap._json_probe', return_value=version):
                with self.assertRaisesRegex(bootstrap.SetupError, '64-bit'):
                    bootstrap.check_python('python', {})

    def test_poisoned_python_paths_are_removed_but_proxy_and_tls_settings_survive(self):
        poison = self.folder / 'wrong site packages'
        poison.mkdir()
        (poison / 'json.py').write_text("raise RuntimeError('inherited package path was used')\n")
        inherited = {**os.environ, 'PYTHONHOME': str(self.folder / 'missing-python'),
                     'PYTHONPATH': str(poison), 'PYTHONNOUSERSITE': '0',
                     'HTTPS_PROXY': 'http://configured-proxy.invalid:8080',
                     'SSL_CERT_FILE': '/configured/trust.pem',
                     'REQUESTS_CA_BUNDLE': '/configured/requests-trust.pem'}
        environment = bootstrap.configure_environment(self.base, self.data, inherited)
        self.assertNotIn('PYTHONHOME', environment)
        self.assertNotIn('PYTHONPATH', environment)
        self.assertEqual(environment['PYTHONNOUSERSITE'], '1')
        for variable in ('HTTPS_PROXY', 'SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE'):
            self.assertEqual(environment[variable], inherited[variable])
        self.assertEqual(inherited['PYTHONPATH'], str(poison))
        # A real child interpreter would fail before startup with the poisoned
        # PYTHONHOME, or import the fake json.py if PYTHONPATH leaked through.
        bootstrap.check_python(sys.executable, environment)

    def test_real_interpreter_probe_uses_json_without_shell(self):
        if sys.version_info[:2] not in ((3, 10), (3, 11), (3, 12)):
            self.skipTest('Test interpreter must be a supported version')
        environment = bootstrap.configure_environment(self.base, self.data)
        bootstrap.check_python(sys.executable, environment)


if __name__ == '__main__':
    unittest.main()
