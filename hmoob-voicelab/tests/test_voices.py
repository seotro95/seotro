"""Confirmed built-in references and persistent user overrides; no AI inference."""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest
import wave

from voices import Voices


CONFIRMED = {
    'female': {'start': 0.0, 'end': 5.30,
               'text': 'tsis pom muaj neeg lawm ces, nws thiaj li los ze ze ntawm lawv lub tsev.'},
    'male': {'start': 0.0, 'end': 4.50,
             'text': 'hais tias ces Nraug Xyooj thiaj li tawm tau mus hauv kev mus lawm.'},
}


class VoicesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name)
        self.voices = Voices(self.data)

    def tearDown(self):
        self.temporary.cleanup()

    def test_fresh_data_uses_confirmed_ready_defaults_without_writing_overrides(self):
        for voice in self.voices.all():
            with self.subTest(voice=voice['id']):
                self.assertTrue(voice['reference_ready'])
                self.assertEqual(voice['reference'], CONFIRMED[voice['id']])
        self.assertFalse((self.data / 'references').exists())

    def test_saved_user_reference_takes_precedence_and_survives_reload(self):
        override = {'start': 1.0, 'end': 4.0, 'text': 'Kuv nyob zoo hnub no.'}
        self.voices.save('female', override)
        # Even a bad bundled reference cannot overwrite an existing valid one.
        self.voices.metadata['female']['reference'] = {'start': 0, 'end': 1, 'text': ''}
        self.assertEqual(self.voices.get('female')['reference'], override)
        reloaded = Voices(self.data)
        self.assertEqual(reloaded.get('female')['reference'], override)
        self.assertEqual(reloaded.get('male')['reference'], CONFIRMED['male'])

    def test_malformed_builtin_reference_is_rejected_instead_of_ready(self):
        for settings in (None, [], {'start': 0, 'end': 2, 'text': 'too short'},
                         {'start': 0, 'end': 3, 'text': ''},
                         {'start': 0, 'end': 30, 'text': 'outside recording'}):
            with self.subTest(settings=settings):
                self.voices.metadata['female']['reference'] = settings
                with self.assertRaises(ValueError):
                    self.voices.get('female')

    def test_voice_without_builtin_reference_still_requires_saved_words(self):
        self.voices.metadata['female'].pop('reference', None)
        voice = self.voices.get('female')
        self.assertFalse(voice['reference_ready'])
        self.assertEqual(voice['reference']['text'], '')
        with self.assertRaises(ValueError):
            self.voices.snapshot('female', self.data / 'unconfigured.wav')

    @unittest.skipUnless(shutil.which('ffmpeg'), 'Reference extraction requires FFmpeg')
    def test_builtin_snapshot_freezes_exact_clip_and_words_before_later_override(self):
        for ident, reference in CONFIRMED.items():
            with self.subTest(voice=ident):
                destination = self.data / f'{ident}-frozen.wav'
                frozen_reference = self.voices.snapshot(ident, destination)
                frozen_audio = destination.read_bytes()
                with wave.open(str(destination), 'rb') as recording:
                    self.assertEqual(recording.getnchannels(), 1)
                    self.assertEqual(recording.getsampwidth(), 2)
                    self.assertEqual(recording.getframerate(), 24000)
                    self.assertAlmostEqual(recording.getnframes() / 24000,
                                           reference['end'] - reference['start'], delta=1 / 24000)
                self.voices.save(ident, {'start': 1, 'end': 4, 'text': 'Updated saved words.'})
                self.assertEqual(frozen_reference, reference)
                self.assertEqual(destination.read_bytes(), frozen_audio)
                self.assertNotEqual(self.voices.get(ident)['reference'], frozen_reference)


if __name__ == '__main__':
    unittest.main()
