"""Private updater boundaries, integrity and rollback with synthetic recordings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave


SPEC = importlib.util.spec_from_file_location('private_voice_updater', Path(__file__).with_name('install_voice_update.py'))
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(path, voices):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'schema_version': 1, 'count': len(voices), 'voices': voices}), encoding='utf-8')


def synthetic_voice(root, ident='a' * 32, language='en-US'):
    wav = root/'voices'/f'{ident}.wav'
    mp3 = root/'originals'/f'{ident}.mp3'
    wav.parent.mkdir(parents=True, exist_ok=True)
    mp3.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav), 'wb') as output:
        output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        output.writeframes(b'\x10\x00\xf0\xff' * 36000)
    mp3.write_bytes(b'Synthetic original preserved byte-for-byte')
    return {'id': ident, 'name': 'Synthetic reference', 'language': language,
            'reference_audio': f'voices/{ident}.wav', 'original_audio': f'originals/{ident}.mp3',
            'reference_sha256': digest(wav), 'source_sha256': digest(mp3),
            'reference_frames': 72000, 'reference_sample_rate': 24000, 'duration': 3.0,
            'source_bytes': mp3.stat().st_size}


class PrivateUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.package, self.target = self.root/'update', self.root/'portable'
        (self.package/'payload/app/static').mkdir(parents=True)
        (self.package/'payload/app/app.py').write_bytes(b'updated application')
        (self.package/'payload/app/static/app.js').write_bytes(b'updated UI')
        (self.package/'payload/TAI_GIONG_DA_NGON_NGU.bat').write_bytes(b'installer')
        self.voice = synthetic_voice(self.package/'voice-pack')
        self.manifest = self.package/'voice-pack/manifest.json'
        write_manifest(self.manifest, [self.voice])
        (self.target/'runtime').mkdir(parents=True)
        (self.target/'runtime/python.exe').write_bytes(b'existing embedded runtime')
        (self.target/'runtime-international').mkdir()
        (self.target/'runtime-international/python.exe').write_bytes(b'existing international runtime')
        (self.target/'app/.data/jobs').mkdir(parents=True)
        (self.target/'app/.data/models').mkdir()
        (self.target/'app/.data/voices').mkdir()
        (self.target/'app/app.py').write_bytes(b'previous application')
        (self.target/'app/.data/jobs/history.json').write_bytes(b'private history')
        (self.target/'app/.data/models/existing.ready').write_bytes(b'existing model')
        (self.target/'app/.data/voices/personal.wav').write_bytes(b'existing personal recording')

    def tearDown(self):
        self.temporary.cleanup()

    def install(self):
        return updater.install_update(self.package, self.target)

    def test_installs_and_preserves_runtimes_history_models_and_personal_voices(self):
        watched = ['runtime/python.exe', 'runtime-international/python.exe',
                   'app/.data/jobs/history.json', 'app/.data/models/existing.ready',
                   'app/.data/voices/personal.wav']
        before = {relative: (self.target/relative).read_bytes() for relative in watched}
        result = self.install()
        self.assertEqual(result['installed_voices'], 1)
        self.assertEqual((self.target/'app/app.py').read_bytes(), b'updated application')
        self.assertEqual((Path(result['backup'])/'files/app/app.py').read_bytes(), b'previous application')
        for relative, value in before.items():
            self.assertEqual((self.target/relative).read_bytes(), value, relative)
        original = self.target/'app/voice-library'/self.voice['original_audio']
        self.assertEqual(digest(original), self.voice['source_sha256'])
        self.assertEqual(json.loads((Path(result['backup'])/'journal.json').read_text())['status'], 'complete')

    def test_merges_other_existing_defaults_and_is_idempotent(self):
        existing = synthetic_voice(self.target/'app/voice-library', 'b' * 32, 'th')
        write_manifest(self.target/'app/voice-library/manifest.json', [existing])
        first = self.install()
        second = self.install()
        self.assertEqual(first['catalog_voices'], 2)
        self.assertEqual(second['updated_files'], 0)
        self.assertIsNone(second['backup'])
        catalog = json.loads((self.target/'app/voice-library/manifest.json').read_text())
        self.assertEqual([record['id'] for record in catalog['voices']], ['b' * 32, 'a' * 32])
        self.assertEqual(len(list((self.target/'update-backups').iterdir())), 1)

    def test_voice_tamper_fails_before_code_or_library_changes(self):
        (self.package/'voice-pack'/self.voice['reference_audio']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            self.install()
        self.assertEqual((self.target/'app/app.py').read_bytes(), b'previous application')
        self.assertFalse((self.target/'app/voice-library').exists())
        self.assertFalse((self.target/'update-backups').exists())

    def test_original_tamper_is_rejected_and_legacy_hash_key_is_supported(self):
        self.voice['original_sha256'] = self.voice.pop('source_sha256')
        write_manifest(self.manifest, [self.voice])
        (self.package/'voice-pack'/self.voice['original_audio']).write_bytes(b'tampered original')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            self.install()
        (self.package/'voice-pack'/self.voice['original_audio']).write_bytes(b'Synthetic original preserved byte-for-byte')
        self.assertEqual(self.install()['installed_voices'], 1)

    def test_rejects_forged_wav_metadata(self):
        self.voice['reference_frames'] = 1
        write_manifest(self.manifest, [self.voice])
        with self.assertRaisesRegex(ValueError, 'WAV'):
            self.install()
        self.assertFalse((self.target/'update-backups').exists())

    def test_valid_hash_still_rejects_truncated_pcm(self):
        wav = self.package/'voice-pack'/self.voice['reference_audio']
        wav.write_bytes(wav.read_bytes()[:-12])
        self.voice['reference_sha256'] = digest(wav)
        write_manifest(self.manifest, [self.voice])
        with self.assertRaisesRegex(ValueError, 'PCM'):
            self.install()

    def test_duplicate_ids_and_traversal_are_rejected(self):
        write_manifest(self.manifest, [self.voice, self.voice])
        with self.assertRaises(ValueError):
            self.install()
        self.voice['reference_audio'] = '../outside.wav'
        write_manifest(self.manifest, [self.voice])
        with self.assertRaises(ValueError):
            self.install()

    def test_payload_cannot_modify_data_or_runtime(self):
        for relative in ['runtime/python.exe', 'app/.data/jobs/private.json', 'app/voice-library/manifest.json']:
            path = self.package/'payload'/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'not allowed')
            with self.assertRaisesRegex(ValueError, 'phạm vi'):
                self.install()
            path.unlink()
        self.assertEqual((self.target/'app/app.py').read_bytes(), b'previous application')

    @unittest.skipUnless(hasattr(Path, 'symlink_to'), 'symlink support is required')
    def test_rejects_source_and_destination_symlinks(self):
        path = self.package/'payload/app/linked.py'
        path.symlink_to(self.root/'outside.py')
        with self.assertRaisesRegex(ValueError, 'liên kết'):
            self.install()
        path.unlink()
        (self.target/'app/static').symlink_to(self.root/'external-static', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'liên kết'):
            self.install()
        self.assertFalse((self.root/'external-static').exists())
        self.assertEqual((self.target/'app/app.py').read_bytes(), b'previous application')

    def test_running_server_lock_prevents_changes(self):
        with updater.installation_lock(self.target):
            with self.assertRaisesRegex(RuntimeError, 'đang chạy'):
                self.install()
        self.assertEqual((self.target/'app/app.py').read_bytes(), b'previous application')
        self.assertFalse((self.target/'update-backups').exists())

    def test_partial_update_rolls_back_code_and_removes_added_files(self):
        replace = updater.os.replace
        failed = False

        def fail_once(source, destination):
            nonlocal failed
            if Path(destination) == self.target/'app/static/app.js' and not failed:
                failed = True
                raise OSError('simulated interrupted write')
            return replace(source, destination)

        with patch.object(updater.os, 'replace', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'simulated'):
                self.install()
        self.assertTrue(failed)
        self.assertEqual((self.target/'app/app.py').read_bytes(), b'previous application')
        self.assertFalse((self.target/'TAI_GIONG_DA_NGON_NGU.bat').exists())
        self.assertFalse((self.target/'app/static').exists())
        self.assertFalse((self.target/'app/voice-library').exists())
        journals = list((self.target/'update-backups').glob('*/journal.json'))
        self.assertEqual(json.loads(journals[0].read_text())['status'], 'rolled-back')

    def test_rejects_incomplete_target_without_touching_it(self):
        (self.target/'runtime/python.exe').unlink()
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse((self.target/'update-backups').exists())


if __name__ == '__main__':
    unittest.main()
