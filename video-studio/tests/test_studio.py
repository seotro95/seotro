import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

TEST_ROOT = tempfile.TemporaryDirectory(prefix='video-studio-tests-')
os.environ['VIDEO_STUDIO_DATA'] = str(Path(TEST_ROOT.name) / 'data')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi.testclient import TestClient
import app
import engine
from subtitles import parse_srt, to_srt

SRT = '1\n00:00:00,000 --> 00:00:01,000\nXin chào Việt Nam!\n\n2\n00:00:01,000 --> 00:00:02,000\nMột câu chuyện mới.\n'


def wait_job(job_id, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = next(j for j in engine.jobs() if j['id'] == job_id)
        if job['status'] in ('done', 'error', 'cancelled', 'interrupted'):
            return job
        time.sleep(.05)
    raise AssertionError('Job did not finish: ' + job_id)


class SubtitleTests(unittest.TestCase):
    def test_unicode_round_trip_and_timestamp_validation(self):
        cues = parse_srt('\ufeff' + SRT.replace('\n', '\r\n'))
        self.assertEqual(parse_srt(to_srt(cues)), cues)
        self.assertIn('Việt Nam', cues[0]['text'])
        for text in ('', '1\n00:70:00,000 --> 00:71:00,000\nx', '1\n00:00:02,000 --> 00:00:01,000\nx', '1\n00:00:00,000 --> 00:00:01,000\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_srt(text)


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app.app)
        cls.video = Path(TEST_ROOT.name) / 'video.mp4'
        subprocess.run([engine.executable('ffmpeg'), '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=size=320x180:rate=10', '-f', 'lavfi', '-i', 'sine=frequency=440',
                        '-t', '2', '-c:v', 'libx264', '-threads', '2', '-c:a', 'aac', str(cls.video)], check=True)
        with cls.video.open('rb') as f:
            response = cls.client.post('/api/upload', files={'file': ('sample.mp4', f, 'video/mp4')})
        assert response.status_code == 201, response.text
        cls.source_id = response.json()['asset_id']
        response = cls.client.post('/api/subtitles', json={'name': 'tieng_viet.srt', 'text': SRT})
        assert response.status_code == 201, response.text
        cls.subtitle_id = response.json()['asset_id']

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_upload_health_range_and_invalid_media(self):
        health = self.client.get('/api/health').json()
        self.assertTrue(health['ffmpeg'] and health['ffprobe'])
        self.assertEqual(self.client.get('/').status_code, 200)
        rows = self.client.get('/api/assets').json()
        item = next(a for a in rows if a['id'] == self.source_id)
        self.assertEqual(item['metadata']['width'], 320)
        self.assertNotIn('path', item)
        response = self.client.get(f'/api/assets/{self.source_id}/file', headers={'Range': 'bytes=0-99'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(len(response.content), 100)
        response = self.client.post('/api/upload', files={'file': ('bad.mp4', b'not a movie', 'video/mp4')})
        self.assertEqual(response.status_code, 422)

    def test_render_subtitle_title_trim_speed_audio_and_batch(self):
        payload = {'asset_ids': [self.source_id, self.source_id], 'subtitle_id': self.subtitle_id,
                   'start': .5, 'end': 1.5, 'speed': 2, 'height': 360,
                   'title': 'Tiếng Việt 100%: câu chuyện', 'subtitle_color': '#ffd080'}
        response = self.client.post('/api/render', json=payload)
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(len(response.json()['job_ids']), 2)
        for job_id in response.json()['job_ids']:
            job = wait_job(job_id)
            self.assertEqual(job['status'], 'done', job)
            output = engine.asset(job['result']['asset_ids'][0])
            meta = engine.probe(output['path'])
            self.assertEqual(meta['height'], 360)
            self.assertAlmostEqual(meta['duration'], .5, delta=.15)
            self.assertTrue(meta['has_audio'])
            shifted = parse_srt((engine.DATA / 'jobs' / job_id / 'subtitle.srt').read_text())
            self.assertEqual(shifted[0]['start'], 0)
            self.assertEqual(shifted[-1]['end'], .5)
            subprocess.run([engine.executable('ffmpeg'), '-nostdin', '-v', 'error', '-i', output['path'], '-f', 'null', '-'], check=True)

    def test_replace_audio_pads_short_audio_and_preserves_duration(self):
        audio = engine.DATA / 'short.wav'
        subprocess.run([engine.executable('ffmpeg'), '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=880', '-t', '0.2', str(audio)], check=True)
        audio_id = engine.register(audio)
        response = self.client.post('/api/render', json={'asset_ids': [self.source_id], 'audio_id': audio_id})
        job = wait_job(response.json()['job_ids'][0])
        self.assertEqual(job['status'], 'done', job)
        output = engine.asset(job['result']['asset_ids'][0])
        self.assertAlmostEqual(engine.probe(output['path'])['duration'], 2, delta=.2)

    def test_cancel_kills_real_process_and_keeps_source(self):
        before = self.video.read_bytes()
        script = Path(TEST_ROOT.name) / 'sleep.py'
        script.write_text('import time\ntime.sleep(60)\n')
        original = engine.perform
        def slow(job, action, payload, folder):
            if action == 'slow_fixture':
                engine.command(job, [sys.executable, str(script)], timeout=90)
                return []
            return original(job, action, payload, folder)
        with patch.object(engine, 'perform', slow):
            job_id = engine.enqueue('slow_fixture', 'cancel fixture', {})
            deadline = time.monotonic() + 5
            process = None
            while time.monotonic() < deadline:
                process = engine.PROCESSES.get(job_id)
                if process:
                    break
                time.sleep(.03)
            self.assertIsNotNone(process)
            self.assertEqual(self.client.post('/api/jobs/' + job_id + '/cancel').status_code, 202)
            self.assertEqual(wait_job(job_id)['status'], 'cancelled')
            self.assertIsNotNone(process.poll())
            self.assertEqual(self.video.read_bytes(), before)

    def test_no_key_required_and_invalid_inputs_and_cross_origin(self):
        response = self.client.get('/api/config')
        self.assertEqual(response.json()['default_mode'], 'local')
        self.assertNotIn('api_key', response.json())
        self.assertEqual(self.client.post('/api/config', json={'api_key':'unused'}).status_code, 422)
        self.assertEqual(self.client.post('/api/tts', json={'text':'xin chào', 'voice':'invalid'}).status_code, 422)
        self.assertEqual(self.client.post('/api/translate', json={'asset_ids':[self.subtitle_id], 'language':'invalid'}).status_code, 422)
        self.assertEqual(self.client.post('/api/subtitles', headers={'Origin':'https://example.com'}, json={'text':SRT}).status_code, 403)
        self.assertEqual(self.client.post('/api/render', json={'asset_ids':[self.source_id], 'speed':0}).status_code, 422)
        self.assertEqual(self.client.post('/api/download', json={'urls':['https://127.0.0.1/video.mp4']}).status_code, 422)

    def test_settings_persist_without_credentials(self):
        response = self.client.post('/api/config', json={'auto_update':False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['auto_update'])
        script = 'import updater,json;print(json.dumps(updater.settings()))'
        result = json.loads(subprocess.check_output([sys.executable,'-c',script], cwd=str(Path(__file__).resolve().parents[1])))
        self.assertFalse(result['auto_update'])
        self.assertNotIn('api_key', result)

    def test_editor_runs_without_any_http_provider(self):
        with patch('httpx.Client', side_effect=AssertionError('No network allowed')):
            response = self.client.post('/api/ai', json={'prompt':'  Xin   chào  , Việt Nam !  ', 'task':'tidy'})
            self.assertEqual(response.status_code, 202)
            job = wait_job(response.json()['job_ids'][0])
            self.assertEqual(job['status'], 'done', job)
            output = engine.asset(job['result']['asset_ids'][0])
            self.assertEqual(Path(output['path']).read_text(), 'Xin chào, Việt Nam!')

    def test_completed_jobs_and_assets_survive_new_process(self):
        script = 'import json,engine;print(json.dumps({"assets":engine.list_assets(),"jobs":engine.jobs()}))'
        result = json.loads(subprocess.check_output([sys.executable, '-c', script], cwd=str(Path(__file__).resolve().parents[1])))
        self.assertIn(self.source_id, [a['id'] for a in result['assets']])
        self.assertFalse(any(j['status'] in ('running', 'queued') for j in result['jobs']))


if __name__ == '__main__':
    unittest.main()
