"""Native filename identity/lifetime checks, requiring no model or extra wheels."""
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_paths as paths


class NativePathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='native-path-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.model = self.root / 'model.gguf'
        self.payload = b'GGUF public model fixture'
        self.model.write_bytes(self.payload)

    def unicode_model(self):
        parent = self.root / 'mẫu giọng Tiếng Việt !'
        parent.mkdir()
        model = parent / 'voxcpm2-q8_0.gguf'
        model.write_bytes(self.payload)
        return model

    def test_ascii_existing_model_is_used_without_link_or_short_path(self):
        if paths._ascii_bytes(self.model) is None:
            self.skipTest('This fixture directory itself is not ASCII')
        with mock.patch.object(paths, '_on_windows', return_value=True), \
                mock.patch.object(paths, '_windows_short_path') as short, \
                mock.patch.object(paths.os, 'link') as link:
            with paths.native_model_path(self.model) as encoded:
                self.assertEqual(encoded, str(self.model).encode('ascii'))
            short.assert_not_called()
            link.assert_not_called()
        self.assertEqual(self.model.read_bytes(), self.payload)

    def test_non_windows_preserves_unicode_filename_encoding(self):
        model = self.unicode_model()
        with mock.patch.object(paths, '_on_windows', return_value=False):
            with paths.native_model_path(model) as encoded:
                self.assertEqual(encoded, os.fsencode(model))

    def test_only_existing_same_file_ascii_short_alias_is_accepted(self):
        if paths._ascii_bytes(self.root) is None:
            self.skipTest('This fixture directory itself is not ASCII')
        model = self.unicode_model()
        alias = self.root / 'SHORT.GGU'
        os.link(model, alias)
        with mock.patch.object(paths, '_on_windows', return_value=True), \
                mock.patch.object(paths, '_windows_short_path', return_value=alias), \
                mock.patch.object(paths, '_candidate_parents') as candidates:
            with paths.native_model_path(model) as encoded:
                self.assertEqual(encoded, str(alias).encode('ascii'))
            candidates.assert_not_called()
        self.assertTrue(alias.exists(), 'An existing short alias is not owned by the context')
        self.assertEqual(model.read_bytes(), self.payload)

    def test_wrong_short_alias_is_rejected(self):
        model = self.unicode_model()
        other = self.root / 'other.gguf'
        other.write_bytes(b'not the model')
        with mock.patch.object(paths, '_windows_short_path', return_value=other):
            self.assertIsNone(paths._short_ascii_alias(model))
        self.assertEqual(other.read_bytes(), b'not the model')

    def test_hardlink_fallback_keeps_identity_then_removes_only_its_own_files(self):
        if paths._ascii_bytes(self.root) is None:
            self.skipTest('This fixture directory itself is not ASCII')
        model = self.unicode_model()
        user_file = self.root / 'user-keep.txt'
        user_file.write_bytes(b'keep')
        link = os.link
        with mock.patch.object(paths, '_on_windows', return_value=True), \
                mock.patch.object(paths, '_windows_short_path', return_value=model), \
                mock.patch.object(paths, '_candidate_parents', return_value=iter([self.root])), \
                mock.patch.object(paths.os, 'link', wraps=link) as create_link:
            with paths.native_model_path(model) as encoded:
                alias = Path(encoded.decode('ascii'))
                self.assertTrue(os.path.samefile(alias, model))
                self.assertEqual(alias.read_bytes(), self.payload)
                self.assertNotEqual(alias, model)
                directory = alias.parent
            self.assertFalse(alias.exists())
            self.assertFalse(directory.exists())
            self.assertEqual(create_link.call_count, 1)
        self.assertEqual(model.read_bytes(), self.payload)
        self.assertEqual(user_file.read_bytes(), b'keep')

    def test_hardlink_is_cleaned_after_native_load_or_session_failure(self):
        if paths._ascii_bytes(self.root) is None:
            self.skipTest('This fixture directory itself is not ASCII')
        model = self.unicode_model()
        with mock.patch.object(paths, '_on_windows', return_value=True), \
                mock.patch.object(paths, '_windows_short_path', return_value=None), \
                mock.patch.object(paths, '_candidate_parents', return_value=iter([self.root])):
            with self.assertRaisesRegex(RuntimeError, 'native load failed'):
                with paths.native_model_path(model) as encoded:
                    alias = Path(encoded.decode('ascii'))
                    raise RuntimeError('native load failed')
            self.assertFalse(alias.exists())
            self.assertEqual(model.read_bytes(), self.payload)

    def test_failed_links_do_not_overwrite_original_or_leave_temp_directories(self):
        if paths._ascii_bytes(self.root) is None:
            self.skipTest('This fixture directory itself is not ASCII')
        model = self.unicode_model()
        before = sorted(p.name for p in self.root.iterdir())
        with mock.patch.object(paths, '_on_windows', return_value=True), \
                mock.patch.object(paths, '_windows_short_path', return_value=None), \
                mock.patch.object(paths, '_candidate_parents', return_value=iter([self.root])), \
                mock.patch.object(paths.os, 'link', side_effect=OSError('no hardlinks')):
            with self.assertRaisesRegex(RuntimeError, 'NTFS'):
                with paths.native_model_path(model):
                    self.fail('An unavailable hardlink must not yield a path')
        self.assertEqual(before, sorted(p.name for p in self.root.iterdir()))
        self.assertEqual(model.read_bytes(), self.payload)

    def test_non_file_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            with paths.native_model_path(self.root):
                self.fail('A directory must not reach the native loader')

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows NTFS hard-link check')
    def test_windows_unicode_model_with_short_names_disabled(self):
        if paths._ascii_bytes(self.root) is None:
            self.skipTest('This fixture directory itself is not ASCII')
        model = self.unicode_model()
        with mock.patch.object(paths, '_windows_short_path', return_value=None), \
                mock.patch.object(paths, '_candidate_parents', return_value=iter([self.root])):
            with paths.native_model_path(model) as encoded:
                alias = Path(encoded.decode('ascii'))
                self.assertTrue(os.path.samefile(alias, model))
                self.assertEqual(alias.stat().st_ino, model.stat().st_ino)
                self.assertEqual(alias.read_bytes(), self.payload)
            self.assertFalse(alias.exists())
        self.assertEqual(model.read_bytes(), self.payload)


if __name__ == '__main__':
    unittest.main()
