"""Run with python -m unittest -v; requires a running app on port 8787."""
import json
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'http://127.0.0.1:8787'

class Workflow(unittest.TestCase):
    def test_export_and_reject_invalid_start(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / 'source.mp4'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x240:rate=12', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(video)], check=True)
            (root / 'sub.srt').write_text('1\n00:00:00,000 --> 00:00:01,500\nXin chào Việt Nam\n', encoding='utf-8')
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x64', '-frames:v', '1', str(root / 'logo.png')], check=True)
            def submit(start):
                result = subprocess.run(['curl', '-sf', '-F', f'video=@{video}', '-F', f'subtitles=@{root / "sub.srt"}', '-F', f'logo=@{root / "logo.png"}', '-F', f'music=@{video}', '-F', 'title=Mẹo hay 100%', '-F', 'product=Sản phẩm mẫu', '-F', 'link=https://example.com/product', '-F', 'duration=2', '-F', f'start={start}', BASE + '/api/jobs'], capture_output=True, check=True)
                return json.loads(result.stdout)['id']
            for start, expected in [(0, 'Hoàn tất'), (99, 'Lỗi')]:
                job_id = submit(start)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    rows = json.load(urllib.request.urlopen(BASE + '/api/jobs'))
                    job = next(j for j in rows if j['id'] == job_id)
                    if job['status'] in ('Hoàn tất', 'Lỗi'):
                        break
                    time.sleep(0.3)
                self.assertEqual(job['status'], expected, job)
                if expected == 'Hoàn tất':
                    output = root / 'result.mp4'
                    urllib.request.urlretrieve(BASE + f'/files/{job_id}/video.mp4', output)
                    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)]))
                    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                    self.assertEqual((stream['width'], stream['height']), (720, 1280))
                    self.assertAlmostEqual(float(probe['format']['duration']), 2, delta=0.3)
                    caption = urllib.request.urlopen(BASE + f'/files/{job_id}/caption.txt').read().decode('utf-8-sig')
                    self.assertIn('https://example.com/product', caption)
                    self.assertIn('hoa hồng', caption)
                else:
                    self.assertIn('Mốc bắt đầu', job['error'])
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(BASE + '/files/not-a-job/video.mp4')
            self.assertEqual(error.exception.code, 404)

if __name__ == '__main__':
    unittest.main()
