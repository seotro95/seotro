"""Conservation and boundary tests for real-sized user documents."""
import unittest

from longform import CHUNK_CHARACTERS, MAX_CHARACTERS, plan, validate_text


class LongformTests(unittest.TestCase):
    def assert_conserved(self, text, limit=CHUNK_CHARACTERS):
        spans = plan(text, limit=limit)
        self.assertEqual(spans[0]['start'], 0)
        self.assertEqual(spans[-1]['end'], len(text))
        end = 0
        pieces = []
        for span in spans:
            self.assertEqual(span['start'], end)
            self.assertLess(span['start'], span['end'])
            self.assertLessEqual(span['end'] - span['start'], limit)
            pieces.append(text[span['start']:span['end']])
            end = span['end']
        self.assertEqual(''.join(pieces), text)
        self.assertEqual(plan(text, limit=limit), spans)
        return spans

    def test_exact_million_unicode_characters_and_over_limit(self):
        # Python characters, including non-BMP characters, are the API contract.
        text = '🙂' * MAX_CHARACTERS
        self.assertIs(validate_text(text), text)
        self.assert_conserved(text)
        with self.assertRaisesRegex(ValueError, '1.000.000'):
            validate_text(text + 'a')
        with self.assertRaises(ValueError):
            plan(text + 'a')

    def test_million_character_unbroken_document(self):
        spans = self.assert_conserved('x' * MAX_CHARACTERS)
        expected = (MAX_CHARACTERS + CHUNK_CHARACTERS - 1) // CHUNK_CHARACTERS
        self.assertEqual(len(spans), expected)

    def test_short_sentences_are_packed_into_useful_work_units(self):
        unit = 'Nyob zoo. Kuv nyob ntawm no! '
        text = (unit * (MAX_CHARACTERS // len(unit) + 1))[:MAX_CHARACTERS]
        spans = self.assert_conserved(text)
        self.assertLess(len(spans), 5000)
        self.assertGreater(len(spans), 3000)
        self.assertIn('Nyob zoo. Kuv nyob', text[spans[0]['start']:spans[0]['end']])

    def test_preserves_crlf_unicode_combining_marks_and_punctuation(self):
        text = ('  Nyob zoo!\r\nTiếng Việt, e\u0301, 日本語。🙂\t'
                'Kuv hlub koj?\r\n\r\n') * 200
        self.assert_conserved(text)

    def test_long_whitespace_runs_do_not_drop_later_words(self):
        text = 'Pib.\r\n' + (' \t\r\n' * 1000) + 'Xaus.'
        spans = self.assert_conserved(text)
        self.assertTrue(any(not text[s['start']:s['end']].strip() for s in spans))
        self.assertEqual(text[spans[-1]['start']:spans[-1]['end']].strip(), 'Xaus.')

    def test_boundaries_around_chunk_limit(self):
        for count in (1, 299, 300, 301, 599, 600, 601):
            with self.subTest(count=count):
                self.assert_conserved('a' * count)
        for punctuation_position in (148, 149, 298, 299, 300):
            with self.subTest(punctuation_position=punctuation_position):
                text = 'a' * punctuation_position + '.\r\n' + 'b' * 350
                self.assert_conserved(text)

    def test_rejects_empty_non_text_and_invalid_unicode(self):
        for text in ('', ' \r\n\t', None, 123, 'Nyob\ud800zoo'):
            with self.subTest(text=repr(text)):
                with self.assertRaises(ValueError):
                    validate_text(text)


if __name__ == '__main__':
    unittest.main()
