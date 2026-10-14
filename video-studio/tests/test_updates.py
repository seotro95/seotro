import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import httpx
import offline_models
import updater


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'studio'
        self.data = self.root / 'data'
        self.root.mkdir()
        (self.root / 'version.json').write_text('{"version":"0.2.0"}')
        (self.root / 'app.py').write_text('user modified application')
        (self.root / 'unknown.txt').write_text('user notes')
        self.data.mkdir()
        (self.data / 'video.mp4').write_bytes(b'user video')
        (self.root / '.venv').mkdir()
        (self.root / '.venv' / 'marker').write_text('retained environment')
        self.root_patch = patch.object(updater, 'ROOT', self.root)
        self.data_patch = patch.object(updater, 'DATA', self.data)
        self.root_patch.start()
        self.data_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.data_patch.stop()
        self.temp.cleanup()

    def archive(self, extra=None):
        archive = Path(self.temp.name) / 'update.zip'
        files = {'app.py':'updated application','engine.py':'engine','launcher.py':'launcher',
                 'requirements.txt':'requirements','version.json':'{"version":"0.2.1"}',
                 'static/index.html':'updated frontend'}
        if extra:
            files.update(extra)
        with zipfile.ZipFile(archive,'w') as bundle:
            for name, text in files.items():
                bundle.writestr('video-studio/' + name, text)
        return archive

    def test_update_preserves_media_environment_unknown_files_and_backup(self):
        result = updater.apply_archive(self.archive(), {'version':'0.2.1'})
        self.assertIn('0.2.1', result)
        self.assertEqual(updater.local_version(),'0.2.1')
        self.assertEqual((self.root/'app.py').read_text(),'updated application')
        self.assertEqual((self.root/'unknown.txt').read_text(),'user notes')
        self.assertEqual((self.data/'video.mp4').read_bytes(),b'user video')
        self.assertEqual((self.root/'.venv'/'marker').read_text(),'retained environment')
        backups=list((self.data/'update-backups').glob('*/app.py'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_text(),'user modified application')

    def test_failed_update_rolls_back_files_and_version(self):
        original_replace = os.replace
        count = 0
        def fail_second(a,b):
            nonlocal count
            count += 1
            if count == 2:
                raise PermissionError('simulated locked Windows file')
            return original_replace(a,b)
        with patch.object(updater.os,'replace',fail_second), self.assertRaises(PermissionError):
            updater.apply_archive(self.archive(),{'version':'0.2.1'})
        self.assertEqual(updater.local_version(),'0.2.0')
        self.assertEqual((self.root/'app.py').read_text(),'user modified application')
        self.assertFalse(list(self.root.rglob('*.update-tmp')))

    def test_reject_traversal_and_data_overwrite(self):
        for name in ('../escaped.py','data/video.mp4','.venv/marker'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                updater.apply_archive(self.archive({name:'bad'}),{'version':'0.2.1'})
        self.assertEqual((self.data/'video.mp4').read_bytes(),b'user video')
        self.assertEqual(updater.local_version(),'0.2.0')

    def test_checksum_failure_never_applies_update(self):
        request_archive=self.archive()
        with patch.object(updater.urllib.request,'urlopen',return_value=request_archive.open('rb')):
            with self.assertRaises(ValueError):
                updater.download_archive({'filename':'VideoStudioVN-0.2.1.zip','sha256':'0'*64},Path(self.temp.name)/'download.zip')
        self.assertEqual(updater.local_version(),'0.2.0')

    def test_offline_check_continues_existing_version(self):
        with patch.object(updater,'remote_manifest',side_effect=OSError('offline')):
            result=updater.check_update()
            self.assertFalse(result['available'])
            self.assertEqual(result['current'],'0.2.0')
            self.assertIn('offline',result['message'])
            self.assertIn('tiếp tục',updater.startup_update(force=True))


class ModelDownloadTests(unittest.TestCase):
    def test_corrupt_download_preserves_existing_file(self):
        client=httpx.Client
        def bad_transport(request):
            return httpx.Response(200,content=b'corrupt')
        def fake_client(**kwargs):
            return client(transport=httpx.MockTransport(bad_transport),**kwargs)
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'model.bin'
            target.write_bytes(b'previous valid model')
            with patch.object(offline_models.httpx,'Client',fake_client), self.assertRaises(ValueError):
                offline_models.fetch('https://model.example/model.bin',target,expected_hash=hashlib.sha256(b'expected good model').hexdigest())
            self.assertEqual(target.read_bytes(),b'previous valid model')
            self.assertFalse(target.with_name('model.bin.part').exists())


if __name__ == '__main__':
    unittest.main()
