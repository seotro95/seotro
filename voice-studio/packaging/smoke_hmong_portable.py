"""Exercise the relocated Windows Hmong bundle with real offline F5 synthesis.

Run only on a fresh builder-owned directory. This script creates QA jobs but
never deletes personal data; the builder removes its own QA directory afterward.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request


def main():
    root = Path(sys.argv[1]).resolve()
    reports = Path(sys.argv[2]).resolve()
    app_root = root / 'voice-studio-hmong'
    assert Path(sys.executable).resolve().parent == root / 'runtime', 'Use the packaged interpreter'
    assert Path(sys.prefix).resolve() == root / 'runtime', 'Interpreter did not relocate'
    sys.path.insert(0, str(app_root))
    import numpy as np
    import soundfile as sf
    import httpx
    from fastapi.testclient import TestClient
    for module in (np, sf, httpx):
        assert (root / 'runtime') in Path(module.__file__).resolve().parents, 'Dependency escaped bundled runtime'
    import app as studio
    from hmong_assets import reference
    for binary in ('ffmpeg', 'ffprobe'):
        subprocess.run([binary, '-version'], check=True, stdout=subprocess.DEVNULL)
    results = {'success': False, 'platform': sys.platform, 'voices': {}, 'clone': False,
               'txt_srt': False, 'mp3': False, 'normal_launcher': False,
               'native_windows_validation': os.name == 'nt'}
    text = 'Nyob zoo, kuv yog ib tug Hmoob. Hnub no peb sib tham ua ke.'

    def render(client, payload):
        response = client.post('/api/speech', json=payload)
        assert response.status_code == 202, response.text
        job = response.json()
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            response = client.get('/api/jobs/' + job['id'])
            assert response.status_code == 200, response.text
            job = response.json()
            if job['status'] not in {'queued', 'running', 'cancelling'}:
                break
            time.sleep(.3)
        assert job['status'] == 'done', job
        response = client.get('/api/audio/' + job['id'])
        assert response.status_code == 200, response.text
        samples, rate = sf.read(io.BytesIO(response.content), dtype='float32')
        assert rate == 24000 and samples.size > rate / 3
        assert np.all(np.isfinite(samples)) and np.max(np.abs(samples)) > .001
        return job

    with TestClient(studio.app) as client:
        config = client.get('/api/config').json()
        assert config['variant'] == 'hmong' and config['default_language'] == 'mww'
        assert config['models']['f5_hmong'] and not config['nano_ready']
        assert config['subtitle_ready'] is False, 'Do not claim Hmong Whisper recognition'
        for asset in ('app.js', 'workspace.js', 'style.css'):
            assert client.get('/static/' + asset).status_code == 200
        assert 'Voice Studio Hmong' in client.get('/').text
        voices = client.get('/api/voices').json()['voices']
        assert {v['id'] for v in voices} == {'hmong-female', 'hmong-male'}
        for ident, delivery in [('hmong-female', 'review'), ('hmong-male', 'story')]:
            print('Real offline inference:', ident, delivery, flush=True)
            preset = next(v for v in voices if v['id'] == ident)
            assert client.get(preset['sample_url']).status_code == 200
            started = time.monotonic()
            job = render(client, {'text': text, 'language': 'mww', 'voice_id': ident,
                                 'hmong_steps': 8, 'format': 'wav', 'speed': 1,
                                 'delivery': delivery, 'paragraph_pause': 0})
            results['voices'][ident] = {'audio_seconds': job['audio_seconds'],
                                      'wall_seconds': round(time.monotonic() - started, 3)}
            txt = client.get('/api/jobs/' + job['id'] + '/script.txt')
            srt = client.get('/api/jobs/' + job['id'] + '/script.srt')
            assert txt.status_code == srt.status_code == 200
            assert text in txt.text and '-->' in srt.text and 'Nyob zoo' in srt.text
            results['txt_srt'] = True
        mp3 = client.get('/api/jobs/' + job['id'] + '/export.mp3')
        assert mp3.status_code == 200 and len(mp3.content) > 1000, mp3.text[:200]
        results['mp3'] = True

        path, transcript = reference('hmong-female')
        with path.open('rb') as audio:
            response = client.post('/api/voices/clone', data={'name': 'Native QA reference',
                'language': 'mww', 'transcript': transcript, 'consent': 'true'},
                files={'file': ('reference.wav', audio, 'audio/wav')})
        assert response.status_code == 201, response.text
        personal = response.json()
        assert personal['engine'] == 'f5_hmong'
        clone = render(client, {'text': 'Kuv zoo siab tau ntsib nej hnub no.', 'language': 'mww',
                               'voice_id': personal['id'], 'hmong_steps': 8,
                               'format': 'wav', 'paragraph_pause': 0})
        assert clone['engine'] == 'f5_hmong'
        results['clone'] = True
        srt_text = '1\n00:00:00,000 --> 00:00:12,000\nNyob zoo, kuv yog ib tug Hmoob.\n'
        aligned = render(client, {'text': srt_text, 'input_format': 'srt', 'language': 'mww',
                                 'voice_id': 'hmong-female', 'hmong_steps': 8,
                                 'format': 'wav', 'paragraph_pause': 0, 'max_cue_tempo': 2})
        assert abs(aligned['audio_seconds'] - 12) < .1
        saved = client.get('/api/jobs/' + aligned['id'] + '/script.srt')
        assert saved.status_code == 200 and '00:00:12,000' in saved.text
        results['srt_timeline'] = True

    subprocess.run([sys.executable, str(app_root / 'hmong_launcher.py'), '--check'],
                   check=True, cwd=app_root, timeout=180)
    print('Checking the normal Hmong launcher after relocation...', flush=True)
    process = subprocess.Popen([sys.executable, str(app_root / 'hmong_launcher.py'), '--no-browser'],
        cwd=app_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace')
    lines = queue.Queue()
    def read_output():
        for line in process.stdout:
            print(line.rstrip(), flush=True)
            lines.put(line)
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        deadline = time.monotonic() + 180
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Normal Hmong launcher exited: ' + str(process.returncode))
            try:
                line = lines.get(timeout=.25)
            except queue.Empty:
                continue
            match = re.search(r'Studio:\s*(http://127\.0\.0\.1:\d+)', line)
            if not match:
                continue
            with opener.open(match[1] + '/api/config', timeout=5) as response:
                live = json.load(response)
            assert live['variant'] == 'hmong' and live['models']['f5_hmong']
            results['normal_launcher'] = True
            break
        assert results['normal_launcher'], 'Normal launcher readiness timed out'
    finally:
        if process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                process.terminate()
            process.wait(timeout=30)
        reader.join(timeout=2)
    results['success'] = True
    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'native-smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: real offline female/male Hmong, cloned reference, TXT/SRT/MP3 and normal startup.', flush=True)


if __name__ == '__main__':
    main()
