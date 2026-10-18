"""Portable archive trust and data-boundary checks; no model downloads."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('standalone_portable_builder', Path(__file__).with_name('build_windows.py'))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def archive(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as output:
        for name, value in entries:
            output.writestr(name, value)
    return stream.getvalue()


class BaseArchiveTests(unittest.TestCase):
    def test_selective_base_reuse_keeps_models_licenses_and_omits_history(self):
        content = archive([
            ('Voice-Studio/runtime/python.exe', b'python'),
            ('Voice-Studio/runtime/LICENSE.txt', b'python license'),
            ('Voice-Studio/ffmpeg/bin/ffmpeg.exe', b'ffmpeg'),
            ('Voice-Studio/ffmpeg/UPSTREAM-SHA256.txt', b'upstream checksum'),
            ('Voice-Studio/MODEL-APACHE-2.0-LICENSE.txt', b'model license'),
            ('Voice-Studio/voice-studio/.data/models/vieneu_nano.ready', b'ready'),
            ('Voice-Studio/voice-studio/.data/models/cache/hub/models--pnnbao-ump--VieNeu-TTS-v3-Nano/snapshots/revision/README.md', b'model card'),
            ('Voice-Studio/voice-studio/.data/models/cache/.agent_harnesses.json', b'local metadata'),
            ('Voice-Studio/voice-studio/.data/models/cache/token', b'do not include'),
            ('Voice-Studio/voice-studio/.data/audio/private.wav', b'personal recording'),
            ('Voice-Studio/voice-studio/.data/jobs/private.json', b'private history'),
            ('Voice-Studio/voice-studio/app.py', b'old code'),
        ])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'base.zip'
            source.write_bytes(content)
            destination = root/'new'
            builder.extract_verified_base(source, destination, hashlib.sha256(content).hexdigest())
            self.assertEqual((destination/'runtime/python.exe').read_bytes(), b'python')
            self.assertTrue((destination/'BASE-MODEL-APACHE-2.0-LICENSE.txt').is_file())
            self.assertTrue(list((destination/'app/.data/models/cache/hub').rglob('README.md')))
            for name in ('token', '.agent_harnesses.json', 'private.wav', 'private.json', 'app.py'):
                self.assertFalse(list(destination.rglob(name)), name)

    def test_bad_checksum_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'base.zip'
            source.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                builder.extract_verified_base(source, root/'new')
            self.assertFalse((root/'new').exists())

    def test_verified_archive_still_rejects_path_traversal(self):
        content = archive([('Voice-Studio/runtime/python.exe', b'python'), ('Voice-Studio/../escape', b'bad')])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'base.zip'
            source.write_bytes(content)
            with self.assertRaisesRegex(ValueError, 'Unsafe archive'):
                builder.extract_verified_base(source, root/'new', hashlib.sha256(content).hexdigest())
            self.assertFalse((root/'escape').exists())

    def test_launch_environment_is_offline_and_does_not_reuse_python_paths(self):
        from unittest.mock import patch
        with patch.dict(builder.os.environ, {'PYTHONHOME': 'foreign', 'PYTHONPATH': 'foreign'}, clear=True):
            env = builder.runtime_environment(Path('bundle'), offline=True)
        self.assertNotIn('PYTHONHOME', env)
        self.assertNotIn('PYTHONPATH', env)
        self.assertEqual(env['HF_HUB_OFFLINE'], '1')
        self.assertEqual(env['HF_HUB_CACHE'], str(Path('bundle/app/.data/models/cache/hub')))


if __name__ == '__main__':
    unittest.main()
