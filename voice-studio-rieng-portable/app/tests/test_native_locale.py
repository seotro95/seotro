"""Protect real multilingual letters and scoped native character handling."""
import ctypes
import locale
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_locale import native_character_locale, normalize_native_text


class NativeLocaleTests(unittest.TestCase):
    def test_hangul_and_chinese_continuation_bytes_are_not_replaced(self):
        for text in ('선택한 목소리의 속도를 측정하기 위해 짧은 글을 읽습니다.',
                     '你好。请保留我的声音。', 'مرحبا بالعالم', 'Bonjour, café!',
                     'こんにちは。', 'Γειά σου κόσμε'):
            with self.subTest(text=text):
                self.assertEqual(normalize_native_text(text).encode('utf-8'), text.encode('utf-8'))

    def test_normalizes_whitespace_by_codepoint_not_utf8_byte(self):
        text = '\t선\u00a0정\u3000你好\n\r안녕  '
        self.assertEqual(normalize_native_text(text), '선 정 你好 안녕')
        self.assertIn(b'\xa0', normalize_native_text(text).encode('utf-8'))

    def test_invalid_unicode_and_nul_are_rejected_without_partial_text(self):
        for text in ('good\x00hidden', 'wrong\ud800', None):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                normalize_native_text(text)

    def test_ctype_is_restored_after_success_and_native_failure(self):
        previous = locale.setlocale(locale.LC_CTYPE)
        with native_character_locale():
            self.assertEqual(locale.setlocale(locale.LC_CTYPE), 'C')
        self.assertEqual(locale.setlocale(locale.LC_CTYPE), previous)
        with self.assertRaisesRegex(RuntimeError, 'native failure'):
            with native_character_locale():
                raise RuntimeError('native failure')
        self.assertEqual(locale.setlocale(locale.LC_CTYPE), previous)

    def test_c_runtime_does_not_classify_a0_or_85_as_byte_whitespace(self):
        library = ctypes.CDLL('ucrtbase') if sys.platform == 'win32' else ctypes.CDLL(None)
        library.isspace.argtypes = [ctypes.c_int]
        library.isspace.restype = ctypes.c_int
        with native_character_locale():
            self.assertFalse(library.isspace(0xA0))
            self.assertFalse(library.isspace(0x85))
            self.assertTrue(library.isspace(ord(' ')))


if __name__ == '__main__':
    unittest.main()
