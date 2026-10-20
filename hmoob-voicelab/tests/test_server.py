"""Real loopback HTTP, reference extraction and exports; inference is mocked.

These checks exercise application plumbing, not F5 pronunciation or throughput.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import wave
import zipfile

from server import make_server


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.gate = threading.Event()
        self.gate.set()

    def synthesize(self, text, reference_path, reference_text, speed=1, quality='fast'):
        self.calls.append((text, reference_text, speed, quality))
        if not self.gate.wait(5):
            raise RuntimeError('Test inference gate timed out')
        return [0.1] * 80, 8000


@unittest.skipUnless(shutil.which('ffmpeg'), 'Reference extraction requires FFmpeg')
class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name)
        self.engine = FakeEngine()
        self.ready = True
        self.server = make_server(self.data, port=0, engine=self.engine,
                                  engine_status=lambda: {'ready': self.ready, 'reason': 'model missing', 'device': 'cpu'})
        self.server.manager.part_seconds = 0.02
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.engine.gate.set()
        self.server.manager.close()
        self.server.manager.thread.join(5)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        self.temporary.cleanup()

    def request(self, path, payload=None, method=None, headers=None, raw=None):
        headers = dict(headers or {})
        data = raw
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers.setdefault('Content-Type', 'application/json')
        request = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            response = self.opener.open(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, dict(response.headers), response.read()

    def json_request(self, path, payload=None, **kwargs):
        code, headers, data = self.request(path, payload, **kwargs)
        return code, json.loads(data)

    def save_reference(self, text='Kuv nyob zoo hnub no.'):
        return self.json_request('/api/voices/female/reference',
                                 {'start': 0, 'end': 3, 'text': text})

    def wait_job(self, ident, terminal=('done', 'error', 'cancelled')):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            code, body = self.json_request('/api/jobs/' + ident)
            self.assertEqual(code, 200)
            if body['job']['status'] in terminal:
                return body['job']
            time.sleep(0.01)
        self.fail('Job did not reach terminal state')

    def test_editor_assets_and_status(self):
        for path, mime in [('/', 'text/html'), ('/web/app.js', 'text/javascript'), ('/web/style.css', 'text/css')]:
            with self.subTest(path=path):
                code, headers, body = self.request(path)
                self.assertEqual(code, 200)
                self.assertIn(mime, headers['Content-Type'])
                self.assertGreater(len(body), 100)
                self.assertIn('nosniff', headers['X-Content-Type-Options'])
        code, status = self.json_request('/api/status')
        self.assertEqual(code, 200)
        self.assertEqual(status['max_characters'], 1_000_000)
        self.assertTrue(status['engine']['ready'])

    def test_original_samples_range_and_head(self):
        code, body = self.json_request('/api/voices')
        self.assertEqual(code, 200)
        self.assertEqual([v['id'] for v in body['voices']], ['female', 'male'])
        sample = body['voices'][0]['sample_url']
        code, headers, audio = self.request(sample, headers={'Range': 'bytes=0-63'})
        self.assertEqual(code, 206)
        self.assertEqual(len(audio), 64)
        self.assertTrue(headers['Content-Range'].startswith('bytes 0-63/'))
        self.assertEqual(headers['Content-Type'], 'audio/mpeg')
        code, headers, audio = self.request(sample, method='HEAD')
        self.assertEqual(code, 200)
        self.assertEqual(audio, b'')
        self.assertGreater(int(headers['Content-Length']), 64)

    def test_unknown_paths_and_traversal_cannot_read_files(self):
        for path in ['/web/../engine.py', '/api/jobs/../../engine.py', '/api/voices/unknown/sample', '/unknown']:
            with self.subTest(path=path):
                code, body = self.json_request(path)
                self.assertIn(code, (404, 422))
                self.assertNotIn('Traceback', json.dumps(body))

    def test_cross_origin_and_rebinding_are_rejected(self):
        code, body = self.json_request('/api/status', headers={'Origin': 'https://example.org'})
        self.assertEqual(code, 403)
        code, body = self.json_request('/api/status', headers={'Host': 'example.org'})
        self.assertEqual(code, 403)
        code, body = self.json_request('/api/status', headers={'Origin': self.base})
        self.assertEqual(code, 200)

    def test_invalid_json_and_wrong_content_type(self):
        for raw, content_type in [(b'{', 'application/json'), (b'[]', 'application/json'),
                                   (b'{}', 'text/plain'), (b'{"text":"x", "speed":NaN}', 'application/json')]:
            with self.subTest(raw=raw):
                code, body = self.json_request('/api/jobs', raw=raw,
                                               headers={'Content-Type': content_type})
                self.assertEqual(code, 422)
                self.assertIn('error', body)

    def test_limit_is_checked_before_missing_model(self):
        self.ready = False
        code, body = self.json_request('/api/jobs', {'text': 'x' * 1_000_001})
        self.assertEqual(code, 422)
        self.assertIn('1.000.000', body['error'])
        code, body = self.json_request('/api/jobs', {'text': 'Nyob zoo.'})
        self.assertEqual(code, 503)
        self.assertEqual(body['error'], 'model missing')
        self.assertEqual(self.engine.calls, [])

    def test_reference_validation_and_persistence(self):
        for settings in [{'start': 0, 'end': 2, 'text': 'short'},
                         {'start': 0, 'end': 9, 'text': 'long'},
                         {'start': 20, 'end': 24, 'text': 'outside'},
                         {'start': 0, 'end': 3, 'text': ''},
                         {'start': True, 'end': 4, 'text': 'boolean'}]:
            code, body = self.json_request('/api/voices/female/reference', settings)
            self.assertEqual(code, 422)
        code, body = self.save_reference()
        self.assertEqual(code, 200)
        self.assertTrue(body['voice']['reference_ready'])
        code, body = self.json_request('/api/voices')
        self.assertEqual(body['voices'][0]['reference']['text'], 'Kuv nyob zoo hnub no.')
        self.assertTrue((self.data / 'references' / 'female.json').is_file())

    def test_missing_reference_never_starts_inference(self):
        code, body = self.json_request('/api/jobs', {'text': 'Nyob zoo.'})
        self.assertEqual(code, 422)
        self.assertEqual(self.engine.calls, [])
        code, body = self.json_request('/api/jobs')
        self.assertEqual(body['jobs'], [])

    def test_full_job_reference_snapshot_and_compact_polling(self):
        self.save_reference('Original reference words.')
        self.engine.gate.clear()
        text = ('Nyob zoo hnub no.\r\n' * 55) + 'Xaus.'
        code, body = self.json_request('/api/jobs', {'text': text, 'voice': 'female', 'quality': 'standard', 'speed': 1.2})
        self.assertEqual(code, 201)
        ident = body['job']['id']
        self.save_reference('Changed reference words.')
        self.engine.gate.set()
        job = self.wait_job(ident)
        self.assertEqual(job['status'], 'done', job.get('error'))
        self.assertEqual(job['characters'], len(text))
        self.assertEqual(job['completed_characters'], len(text))
        self.assertEqual(job['completed_segments'], job['total_segments'])
        self.assertGreater(len(job['parts']), 1)
        self.assertTrue(all(call[1:] == ('Original reference words.', 1.2, 'standard') for call in self.engine.calls))
        self.assertNotIn('text', job)
        self.assertNotIn('reference', job)
        code, history = self.json_request('/api/jobs')
        self.assertNotIn('text', history['jobs'][0])
        code, headers, original = self.request('/api/jobs/' + ident + '/text')
        self.assertEqual(code, 200)
        self.assertEqual(original, text.encode('utf-8'))

    def test_chapter_download_and_complete_zip(self):
        self.save_reference()
        text = 'a' * 901
        code, body = self.json_request('/api/jobs', {'text': text})
        self.assertEqual(code, 201)
        ident = body['job']['id']
        job = self.wait_job(ident)
        self.assertEqual(job['status'], 'done', job.get('error'))
        for part in job['parts']:
            code, headers, audio = self.request(part['url'])
            self.assertEqual(code, 200)
            self.assertEqual(headers['Content-Type'], 'audio/wav')
            with wave.open(io.BytesIO(audio)) as recording:
                self.assertEqual(recording.getframerate(), 8000)
                self.assertEqual(recording.getnchannels(), 1)
                self.assertGreater(recording.getnframes(), 0)
        code, headers, archive = self.request('/api/jobs/' + ident + '/archive')
        self.assertEqual(code, 200)
        self.assertEqual(headers['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(archive)) as files:
            self.assertEqual(files.read('script.txt'), text.encode('utf-8'))
            self.assertEqual(set(files.namelist()), {'script.txt', 'manifest.json'} | {p['name'] for p in job['parts']})
            manifest = json.loads(files.read('manifest.json'))
            self.assertEqual(manifest['status'], 'done')
            self.assertEqual(manifest['completed_characters'], len(text))
        # Receiving Content-Length bytes can precede the handler's final context
        # cleanup. Wait for that asynchronous cleanup, while still requiring that
        # every temporary export directory is removed within a bounded interval.
        deadline = time.monotonic() + 2
        while list((self.data / 'jobs' / ident).glob('download-*')) and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(list((self.data / 'jobs' / ident).glob('download-*')), [])

    def test_cancel_and_resume_api(self):
        self.save_reference()
        self.engine.gate.clear()
        code, body = self.json_request('/api/jobs', {'text': 'b' * 1000})
        self.assertEqual(code, 201)
        ident = body['job']['id']
        code, body = self.json_request('/api/jobs/' + ident + '/cancel', {})
        self.assertEqual(code, 200)
        self.assertIn(body['job']['status'], ('cancelling', 'cancelled'))
        self.engine.gate.set()
        job = self.wait_job(ident)
        self.assertEqual(job['status'], 'cancelled')
        code, body = self.json_request('/api/jobs/' + ident + '/archive')
        self.assertEqual(code, 422)
        code, body = self.json_request('/api/jobs/' + ident + '/resume', {})
        self.assertEqual(code, 200)
        job = self.wait_job(ident)
        self.assertEqual(job['status'], 'done', job.get('error'))
        self.assertEqual(job['completed_characters'], 1000)

    def test_full_million_character_job_reads_every_segment(self):
        """Scheduler/storage evidence only: FakeEngine is not a speech model."""
        self.save_reference()
        self.server.manager.part_seconds = 30
        text = 'a' * 1_000_000
        code, body = self.json_request('/api/jobs', {'text': text})
        self.assertEqual(code, 201)
        ident = body['job']['id']
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            job = self.server.manager.get(ident)
            if job['status'] in ('done', 'error', 'cancelled'):
                break
            time.sleep(0.02)
        else:
            self.fail('Million-character scheduler did not complete within test timeout')
        code, body = self.json_request('/api/jobs/' + ident)
        self.assertEqual(code, 200)
        job = body['job']
        self.assertEqual(job['status'], 'done', job.get('error'))
        self.assertEqual(job['characters'], 1_000_000)
        self.assertEqual(job['completed_characters'], 1_000_000)
        self.assertEqual(job['total_segments'], 3334)
        self.assertEqual(job['completed_segments'], 3334)
        self.assertEqual(len(self.engine.calls), 3334)
        self.assertEqual(''.join(call[0] for call in self.engine.calls), text)
        self.assertLess(len(json.dumps(job)), 5000)
        frames = 0
        for part in job['parts']:
            code, headers, audio = self.request(part['url'])
            self.assertEqual(code, 200)
            with wave.open(io.BytesIO(audio)) as recording:
                frames += recording.getnframes()
        self.assertEqual(frames, 3334 * 80)


if __name__ == '__main__':
    unittest.main()
