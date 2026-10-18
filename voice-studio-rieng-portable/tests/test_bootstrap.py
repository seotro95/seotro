"""Offline checks for installer trust and command plans; no Windows execution claim."""
from __future__ import annotations

import hashlib
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

MODULE_PATH = Path(__file__).resolve().parents[1] / 'bootstrap.py'
SPEC = importlib.util.spec_from_file_location('voice_standalone_bootstrap', MODULE_PATH)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def bundle_bytes(entries):
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w') as bundle:
        for name, body in entries:
            bundle.writestr(name, body)
    return content.getvalue()


class BootstrapTests(unittest.TestCase):
    def test_checksum_requires_the_exact_asset_and_64_hex_digits(self):
        digest = 'abcdef0123456789' * 4
        self.assertEqual(bootstrap.checksum_for_asset(f'{digest.upper()} *{bootstrap.FFMPEG_ASSET}\n'), digest)
        for manifest in (f'{digest} other.zip', f'{digest[:-1]} {bootstrap.FFMPEG_ASSET}', f'{"z" * 64} {bootstrap.FFMPEG_ASSET}'):
            with self.subTest(manifest=manifest), self.assertRaises(RuntimeError):
                bootstrap.checksum_for_asset(manifest)

    def test_archive_preserves_licenses_and_omits_ffplay(self):
        content = bundle_bytes([
            ('upstream/bin/ffmpeg.exe', b'ffmpeg'),
            ('upstream/bin/ffprobe.exe', b'ffprobe'),
            ('upstream/bin/ffplay.exe', b'unneeded player'),
            ('upstream/LICENSE.txt', b'upstream license'),
            ('upstream/doc/README.txt', b'upstream documentation'),
        ])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'installed'
            bootstrap.extract_ffmpeg(io.BytesIO(content), target)
            self.assertEqual((target / 'bin/ffmpeg.exe').read_bytes(), b'ffmpeg')
            self.assertTrue((target / 'bin/ffprobe.exe').is_file())
            self.assertFalse((target / 'bin/ffplay.exe').exists())
            self.assertTrue((target / 'LICENSE.txt').is_file())
            self.assertTrue((target / 'doc/README.txt').is_file())

    def test_archive_rejects_escaping_paths_and_windows_path_syntax(self):
        for name in ('../escape', 'root/../escape', '/absolute/escape', 'root\\bin\\escape', 'root/C:escape'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'stage'
                with self.assertRaises(RuntimeError):
                    bootstrap.extract_ffmpeg(io.BytesIO(bundle_bytes([(name, b'escape')])), target)
                self.assertFalse((Path(directory) / 'escape').exists())

    def test_archive_rejects_symlinks_and_missing_executables(self):
        link = zipfile.ZipInfo('upstream/bin/ffmpeg.exe')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                bootstrap.extract_ffmpeg(io.BytesIO(bundle_bytes([(link, b'/outside')])), Path(directory))
            with self.assertRaises(RuntimeError):
                bootstrap.extract_ffmpeg(io.BytesIO(bundle_bytes([('root/LICENSE.txt', b'license')])), Path(directory))

    def test_corrupt_download_is_never_extracted_or_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = hashlib.sha256(b'authentic upstream archive').hexdigest()
            manifest = f'{expected} {bootstrap.FFMPEG_ASSET}\n'.encode()
            with mock.patch.object(bootstrap, 'ROOT', root), \
                 mock.patch.object(bootstrap, 'os', SimpleNamespace(name='nt')), \
                 mock.patch.object(bootstrap, 'runtime_environment', return_value={'PATH': ''}), \
                 mock.patch.object(bootstrap.shutil, 'which', return_value=None), \
                 mock.patch.object(bootstrap.urllib.request, 'urlopen', side_effect=[io.BytesIO(manifest), io.BytesIO(b'corrupt archive')]), \
                 mock.patch.object(bootstrap, 'extract_ffmpeg') as extract:
                with self.assertRaisesRegex(RuntimeError, 'SHA256'):
                    bootstrap.ensure_ffmpeg()
                extract.assert_not_called()
            self.assertFalse((root / 'tools/ffmpeg').exists())
            self.assertEqual(list((root / 'tools').iterdir()), [])

    def test_international_plan_pins_matching_cpu_torch_and_both_models(self):
        with tempfile.TemporaryDirectory() as directory:
            venv = Path(directory)
            with mock.patch.object(bootstrap, 'VENV', venv), \
                 mock.patch.object(bootstrap, 'require_runtime'), \
                 mock.patch.object(bootstrap, 'ensure_ffmpeg'), \
                 mock.patch.object(bootstrap, 'run') as run:
                bootstrap.models('international')
            commands = [list(map(str, call.args[0])) for call in run.call_args_list]
            self.assertIn('torch==2.9.1', commands[0])
            self.assertIn('torchaudio==2.9.1', commands[0])
            self.assertEqual(commands[0][-2:], ['--index-url', 'https://download.pytorch.org/whl/cpu'])
            self.assertEqual(commands[1][-1], str(bootstrap.ROOT / 'requirements-qwen.txt'))
            self.assertEqual(commands[2][-2:], ['pip', 'check'])
            self.assertEqual([command[-1] for command in commands[3:]], ['qwen', 'qwen_clone'])
            self.assertTrue((venv / '.international-installed').is_file())

    def test_runtime_environment_selects_private_data_and_clears_python_path(self):
        with mock.patch.dict(bootstrap.os.environ, {'PYTHONHOME': 'old-home', 'PYTHONPATH': 'old-path', 'PATH': 'old-bin'}, clear=True):
            environment = bootstrap.runtime_environment()
        self.assertNotIn('PYTHONHOME', environment)
        self.assertNotIn('PYTHONPATH', environment)
        self.assertEqual(environment['PYTHONNOUSERSITE'], '1')
        self.assertEqual(environment['VOICE_STUDIO_DATA_DIR'], str(bootstrap.APP / '.data'))
        self.assertEqual(environment['HF_HOME'], str(bootstrap.APP / '.data/models/cache'))
        self.assertTrue(environment['PATH'].startswith(str(bootstrap.ROOT / 'tools/ffmpeg/bin')))


if __name__ == '__main__':
    unittest.main()
