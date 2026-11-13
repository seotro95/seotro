"""Packaging boundaries tested without downloading or executing Windows code."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('build_windows', Path(__file__).with_name('build_windows.py'))
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class PackageTests(unittest.TestCase):
    def test_source_copy_excludes_private_data_and_environments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'portable'
            source.mkdir()
            for name in build.APP_FILES:
                (source / name).write_text(name)
            for folder in ('web', 'assets', '.data/jobs', '.venv', 'security'):
                (source / folder).mkdir(parents=True)
                (source / folder / 'private.txt').write_text('fixture')
            (source / '.env').write_text('fixture secret')
            build.copy_source(target, source)
            self.assertFalse((target / '.data').exists())
            self.assertFalse((target / '.venv').exists())
            self.assertFalse((target / '.env').exists())
            self.assertFalse((target / 'security').exists())
            self.assertTrue((target / 'web/private.txt').is_file())
            self.assertTrue((target / 'hmong_f5.py').is_file())

    def test_startup_guard_allows_inventory_but_blocks_real_import_and_is_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            site = root / 'runtime/Lib/site-packages'
            site.mkdir(parents=True)
            fake = site / 'torch'
            fake.mkdir()
            side_effect = root / 'native-module-executed'
            (fake / '__init__.py').write_text(
                'from pathlib import Path\nPath(' + repr(str(side_effect)) + ').touch()\n', encoding='utf-8')
            with build.startup_import_guard(root, root / 'reports') as log:
                code = ('import sys,site,importlib.util,importlib;sys.path.insert(0,' + repr(str(site)) + ');'
                        'site.addsitedir(' + repr(str(site)) + ');'
                        'assert importlib.util.find_spec("torch") is not None;'
                        'importlib.import_module("torch")')
                result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('CI startup guard blocked native AI import: torch', result.stderr)
                self.assertFalse(side_effect.exists())
                events = [json.loads(line) for line in log.read_text().splitlines()]
                self.assertTrue(any(event.get('event') == 'active' for event in events))
                self.assertTrue(any(event.get('event') == 'blocked' and event.get('module') == 'torch' for event in events))
            self.assertFalse((site / (build.STARTUP_GUARD_NAME + '.py')).exists())
            self.assertFalse((site / (build.STARTUP_GUARD_NAME + '.pth')).exists())
            self.assertFalse(list((site / '__pycache__').glob(build.STARTUP_GUARD_NAME + '.*.pyc')))

    def test_ffmpeg_archive_paths_reject_traversal_and_symlinks(self):
        for name in ('../escape', '/absolute', 'root/../../escape', 'root/C:/escape', 'root\\..\\escape'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                build.ffmpeg_relative(zipfile.ZipInfo(name))
        link = zipfile.ZipInfo('root/bin/linked.exe')
        link.external_attr = 0o120777 << 16
        with self.assertRaises(ValueError):
            build.ffmpeg_relative(link)
        self.assertEqual(build.ffmpeg_relative(zipfile.ZipInfo('root/bin/ffmpeg.exe')), Path('bin/ffmpeg.exe'))

    def test_archive_has_one_portable_root_and_matching_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'Voice Lab'
            root.mkdir()
            (root / 'start.bat').write_bytes(b'fixture')
            archive = root.parent / 'portable.zip'
            checksum = build.archive_package(root, archive)
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(package.namelist(), ['Voice Lab/start.bat'])
            self.assertEqual(checksum, build.sha256(archive))
            self.assertEqual(Path(str(archive) + '.sha256').read_text(), checksum + '  portable.zip\n')


if __name__ == '__main__':
    unittest.main()
