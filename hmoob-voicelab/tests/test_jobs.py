"""Exercise real checkpoint files and chapters with controlled inference."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import wave

from jobs import JobManager
from longform import MAX_CHARACTERS, plan
from voices import atomic_json


RATE = 8000


def write_reference(path, value=500):
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(value.to_bytes(2, 'little', signed=True) * RATE)


class FakeVoices:
    def __init__(self):
        self.text = 'Lời mẫu ban đầu'
        self.value = 500

    def snapshot(self, voice, destination):
        write_reference(destination, self.value)
        return {'text': self.text}


class FakeEngine:
    def __init__(self, block_call=None, fail_call=None):
        self.block_call = block_call
        self.fail_call = fail_call
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = []
        self.generated = []
        self.references = []

    def synthesize(self, text, reference_path, reference_text, *, speed, quality):
        self.calls.append(text)
        self.references.append((reference_text, Path(reference_path).read_bytes(), speed, quality))
        number = len(self.calls)
        if number == self.block_call:
            self.entered.set()
            if not self.release.wait(5):
                raise RuntimeError('Test did not release controlled inference')
        if number == self.fail_call:
            raise RuntimeError('Controlled model failure')
        self.generated.append(text)
        return [.1] * RATE, RATE


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.voices = FakeVoices()
        self.managers = []
        self.engines = []

    def tearDown(self):
        for engine in self.engines:
            engine.release.set()
        for manager in self.managers:
            manager.close()
        for manager in self.managers:
            if manager.thread:
                manager.thread.join(5)
                self.assertFalse(manager.thread.is_alive(), 'Worker did not shut down')
        self.temporary.cleanup()

    def manager(self, engine=None, **kwargs):
        engine = engine or FakeEngine()
        self.engines.append(engine)
        manager = JobManager(self.root, self.voices, engine, part_seconds=2.1,
                             minimum_free=0, **kwargs)
        self.managers.append(manager)
        return manager, engine

    def wait_for(self, manager, ident, statuses=('done',), timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = manager.get(ident)
            if job['status'] in statuses:
                return job
            if job['status'] == 'error':
                self.fail(job['error'])
            threading.Event().wait(.01)
        self.fail('Timed out waiting for ' + repr(statuses) + ': ' + repr(manager.get(ident)))

    def expected_speech(self, text):
        return [text[s['start']:s['end']].strip() for s in plan(text)
                if text[s['start']:s['end']].strip()]

    def assert_chapters(self, manager, job, seconds):
        folder = manager.folder(job['id'])
        durations = []
        for part in job['parts']:
            with wave.open(str(folder / 'parts' / part['name']), 'rb') as source:
                self.assertEqual(source.getnchannels(), 1)
                self.assertEqual(source.getsampwidth(), 2)
                durations.append(source.getnframes() / source.getframerate())
        self.assertEqual(sum(durations), seconds)
        self.assertTrue(all(0 < duration <= manager.part_seconds for duration in durations))
        self.assertEqual(job['audio_seconds'], seconds)

    def test_million_character_creation_is_bounded_and_preserves_original(self):
        manager, _ = self.manager()
        text = ('Nyob zoo.\r\n' * (MAX_CHARACTERS // 11 + 1))[:MAX_CHARACTERS]
        job = manager.create({'text': text})
        folder = manager.folder(job['id'])
        with (folder / 'text.txt').open(encoding='utf-8', newline='') as source:
            self.assertEqual(source.read(), text)
        self.assertEqual(job['characters'], MAX_CHARACTERS)
        self.assertEqual(job['total_segments'], len(plan(text)))
        for summary in (job, manager.get(job['id']), manager.list()[0]):
            self.assertNotIn('text', summary)
            self.assertNotIn('reference', summary)
            self.assertNotIn('spans', summary)
            self.assertLess(len(json.dumps(summary)), 3000)
        with self.assertRaisesRegex(ValueError, '1.000.000'):
            manager.create({'text': text + 'a'})
        self.assertEqual(len(manager.list()), 1)

    def test_chapter_rollover_reads_every_chunk_once_and_cleans_checkpoints(self):
        manager, engine = self.manager()
        text = ''.join(chr(65 + index) * 300 for index in range(5))
        job = manager.create({'text': text, 'voice': 'male', 'quality': 'standard', 'speed': 1.2})
        manager.start()
        done = self.wait_for(manager, job['id'])
        self.assertEqual(engine.generated, self.expected_speech(text))
        self.assertEqual(done['completed_characters'], len(text))
        self.assertEqual(done['completed_segments'], done['total_segments'])
        self.assertEqual(done['progress'], 100)
        self.assertEqual([part['name'] for part in done['parts']],
                         ['chapter-0001.wav', 'chapter-0002.wav', 'chapter-0003.wav'])
        self.assert_chapters(manager, done, 5)
        self.assertTrue(all(item[2:] == (1.2, 'standard') for item in engine.references))
        # The worker marks done just before removing redundant short WAVs.
        deadline = time.monotonic() + 2
        chunks = manager.folder(job['id']) / 'chunks'
        while list(chunks.glob('*.wav')) and time.monotonic() < deadline:
            threading.Event().wait(.01)
        self.assertEqual(list(chunks.glob('*.wav')), [])

    def test_cancelled_first_chunk_is_reused_without_lost_or_duplicate_text(self):
        engine = FakeEngine(block_call=1)
        manager, _ = self.manager(engine)
        text = ('Nyob zoo.\r\n' + 'a' * 290 + '\r\n' + 'b' * 300 + '\r\n' + 'c' * 300)
        job = manager.create({'text': text})
        manager.start()
        self.assertTrue(engine.entered.wait(2))
        self.assertEqual(manager.cancel(job['id'])['status'], 'cancelling')
        engine.release.set()
        cancelled = self.wait_for(manager, job['id'], ('cancelled',))
        self.assertEqual(cancelled['completed_segments'], 1)
        self.assertEqual(cancelled['completed_characters'], plan(text)[0]['end'])
        self.assertEqual(len(engine.generated), 1)
        self.assertTrue((manager.folder(job['id']) / 'chunks' / '0000000.wav').is_file())
        self.assertEqual(manager.resume(job['id'])['status'], 'queued')
        done = self.wait_for(manager, job['id'])
        self.assertEqual(engine.calls, self.expected_speech(text))
        self.assertEqual(engine.generated, self.expected_speech(text))
        self.assert_chapters(manager, done, len(engine.generated))
        self.assertEqual(done['completed_characters'], len(text))

    def test_cancel_before_worker_start_does_not_call_model(self):
        manager, engine = self.manager()
        job = manager.create({'text': 'Tsis txhob tsim suab no.'})
        self.assertEqual(manager.cancel(job['id'])['status'], 'cancelled')
        manager.start()
        self.assertEqual(manager.get(job['id'])['completed_segments'], 0)
        self.assertEqual(engine.calls, [])
        self.assertEqual(manager.resume(job['id'])['status'], 'queued')
        self.wait_for(manager, job['id'])
        self.assertEqual(engine.generated, ['Tsis txhob tsim suab no.'])

    def test_reference_audio_and_transcript_are_frozen_at_submission(self):
        manager, engine = self.manager()
        job = manager.create({'text': 'Nyob zoo.'})
        frozen = (manager.folder(job['id']) / 'reference.wav').read_bytes()
        self.voices.text = 'Đã sửa lời sau khi tạo tác vụ'
        self.voices.value = 900
        manager.start()
        self.wait_for(manager, job['id'])
        self.assertEqual(engine.references[0][0], 'Lời mẫu ban đầu')
        self.assertEqual(engine.references[0][1], frozen)

    def test_restart_recovers_incomplete_job_and_reuses_existing_chunk(self):
        manager, engine = self.manager()
        text = 'a' * 300 + 'b' * 300 + 'c' * 300
        job = manager.create({'text': text})
        folder = manager.folder(job['id'])
        write_reference(folder / 'chunks' / '0000000.wav')
        saved = json.loads((folder / 'job.json').read_text(encoding='utf-8'))
        saved.update(status='running', completed_segments=1, completed_characters=300)
        atomic_json(folder / 'job.json', saved)
        manager.close()
        restarted, fresh_engine = self.manager()
        recovered = restarted.get(job['id'])
        self.assertEqual(recovered['status'], 'cancelled')
        self.assertEqual(recovered['completed_segments'], 1)
        self.assertEqual(engine.calls, [])
        restarted.resume(job['id'])
        restarted.start()
        done = self.wait_for(restarted, job['id'])
        self.assertEqual(fresh_engine.generated, ['b' * 300, 'c' * 300])
        self.assert_chapters(restarted, done, 3)

    def test_model_error_preserves_successful_chunks_for_resume(self):
        manager, engine = self.manager(FakeEngine(fail_call=2))
        text = 'a' * 300 + 'b' * 300 + 'c' * 300
        job = manager.create({'text': text})
        manager.start()
        failed = self.wait_for(manager, job['id'], ('error',))
        self.assertIn('Controlled model failure', failed['error'])
        self.assertEqual(failed['completed_segments'], 1)
        self.assertEqual(engine.generated, ['a' * 300])
        manager.resume(job['id'])
        done = self.wait_for(manager, job['id'])
        self.assertEqual(engine.generated, self.expected_speech(text))
        self.assert_chapters(manager, done, 3)

    def test_resume_repairs_broken_checkpoints_and_preserves_later_valid_audio(self):
        manager, engine = self.manager(FakeEngine(block_call=4))
        text = ''.join(character * 300 for character in 'abcdef')
        job = manager.create({'text': text, 'voice': 'male', 'quality': 'standard', 'speed': 1.2})
        folder = manager.folder(job['id'])
        chunks = folder / 'chunks'
        frozen_reference = (folder / 'reference.wav').read_bytes()
        valid = {}
        for index, value in ((0, 500), (2, 900)):
            path = chunks / f'{index:07d}.wav'
            write_reference(path, value)
            valid[index] = (path.read_bytes(), path.stat().st_mtime_ns)
        (chunks / '0000001.wav').write_bytes(b'not a WAV checkpoint')
        truncated = chunks / '0000003.wav'
        write_reference(truncated)
        truncated.write_bytes(truncated.read_bytes()[:-20])
        with wave.open(str(chunks / '0000004.wav'), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes(b'')
        saved = json.loads((folder / 'job.json').read_text(encoding='utf-8'))
        saved.update(status='cancelled', completed_segments=5, completed_characters=1500,
                     audio_seconds=5, synthesis_seconds=2, new_audio_seconds=5)
        atomic_json(folder / 'job.json', saved)
        self.voices.text = 'Đã thay lời mẫu sau khi tác vụ được lưu'
        self.voices.value = 1000

        manager.resume(job['id'])
        manager.start()
        self.assertTrue(engine.entered.wait(2))
        # The final missing segment is blocked so checkpoints have not been
        # cleaned up yet. Every earlier broken file has been repaired in place.
        for index, identity in valid.items():
            path = chunks / f'{index:07d}.wav'
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), identity)
        for index in (1, 3, 4):
            with wave.open(str(chunks / f'{index:07d}.wav'), 'rb') as source:
                self.assertEqual(source.getnframes(), RATE)
                self.assertEqual(len(source.readframes(RATE)), RATE * 2)
        repairing = manager.get(job['id'])
        self.assertEqual(repairing['completed_segments'], 5)
        self.assertEqual(repairing['audio_seconds'], 5)
        self.assertEqual(repairing['new_audio_seconds'], 8)
        engine.release.set()
        done = self.wait_for(manager, job['id'])
        self.assertEqual(engine.generated, [character * 300 for character in 'bdef'])
        self.assertEqual(done['completed_segments'], 6)
        self.assertEqual(done['completed_characters'], len(text))
        self.assertEqual(done['progress'], 100)
        self.assertEqual(done['new_audio_seconds'], 9)
        self.assertGreater(done['synthesis_seconds'], 2)
        self.assert_chapters(manager, done, 6)
        self.assertTrue(all(reference == ('Lời mẫu ban đầu', frozen_reference, 1.2, 'standard')
                            for reference in engine.references))

    def test_failed_checkpoint_repair_can_be_resumed_again(self):
        manager, engine = self.manager(FakeEngine(fail_call=1))
        text = 'a' * 300 + 'b' * 300
        job = manager.create({'text': text})
        folder = manager.folder(job['id'])
        (folder / 'chunks' / '0000000.wav').write_bytes(b'RIFF')
        write_reference(folder / 'chunks' / '0000001.wav', 900)
        manager.start()
        failed = self.wait_for(manager, job['id'], ('error',))
        self.assertIn('Controlled model failure', failed['error'])
        self.assertEqual(failed['completed_segments'], 0)
        self.assertEqual(failed['new_audio_seconds'], 0)
        manager.resume(job['id'])
        done = self.wait_for(manager, job['id'])
        self.assertEqual(engine.generated, ['a' * 300])
        self.assertEqual(done['new_audio_seconds'], 1)
        self.assert_chapters(manager, done, 2)

    def test_whitespace_only_spans_advance_without_empty_inference(self):
        manager, engine = self.manager()
        text = 'Pib.\r\n' + ' \t\r\n' * 200 + 'Xaus.'
        job = manager.create({'text': text})
        manager.start()
        done = self.wait_for(manager, job['id'])
        self.assertEqual(engine.generated, self.expected_speech(text))
        self.assertTrue(all(item.strip() for item in engine.calls))
        self.assertEqual(done['completed_characters'], len(text))
        self.assertEqual(done['completed_segments'], len(plan(text)))
        self.assert_chapters(manager, done, len(engine.generated))


if __name__ == '__main__':
    unittest.main()
