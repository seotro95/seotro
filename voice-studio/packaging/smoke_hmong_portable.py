"""Exercise the relocated Windows Hmong bundle with real offline F5 synthesis.

Run only on a fresh builder-owned directory. This script creates QA jobs but
never deletes personal data; the builder removes its own QA directory afterward.
"""
from __future__ import annotations

import io
import hashlib
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
    from hmong_assets import references
    voice_metadata = references()
    for binary in ('ffmpeg', 'ffprobe'):
        subprocess.run([binary, '-version'], check=True, stdout=subprocess.DEVNULL)
    results = {'success': False, 'platform': sys.platform, 'voices': {}, 'clone': False,
               'full_source_previews': {}, 'source_clones': {}, 'manual_crop': False,
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
        assert config['hmong_steps'] == 4 and config['default_voice_id'] == 'hmong-male'
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
            metadata = voice_metadata[ident.removeprefix('hmong-')]
            source = app_root / 'assets/hmong' / metadata['file']
            assert source.suffix == '.mp3', 'Preset preview must retain the complete approved MP3'
            assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata['sha256']
            preview = client.get(preset['sample_url'])
            assert preview.status_code == 200
            assert hashlib.sha256(preview.content).hexdigest() == metadata['sha256']
            results['full_source_previews'][ident] = {'sha256': metadata['sha256'],
                                                     'source_seconds': metadata['duration']}
            started = time.monotonic()
            job = render(client, {'text': text, 'language': 'mww', 'voice_id': ident,
                                 'format': 'wav', 'speed': 1,
                                 'delivery': delivery, 'paragraph_pause': 0})
            results['voices'][ident] = {'audio_seconds': job['audio_seconds'],
                                      'wall_seconds': round(time.monotonic() - started, 3),
                                      'steps': job['hmong_steps'], 'precision': job['hmong_precision']}
            assert job['hmong_steps'] == 4
            txt = client.get('/api/jobs/' + job['id'] + '/script.txt')
            srt = client.get('/api/jobs/' + job['id'] + '/script.srt')
            assert txt.status_code == srt.status_code == 200
            assert text in txt.text and '-->' in srt.text and 'Nyob zoo' in srt.text
            results['txt_srt'] = True
        mp3 = client.get('/api/jobs/' + job['id'] + '/export.mp3')
        assert mp3.status_code == 200 and len(mp3.content) > 1000, mp3.text[:200]
        results['mp3'] = True

        for gender in ('female', 'male'):
            metadata = voice_metadata[gender]
            source = app_root / 'assets/hmong' / metadata['file']
            with source.open('rb') as audio:
                response = client.post('/api/voices/clone', data={'name': 'Native QA source ' + gender,
                    'language': 'mww', 'transcript': '', 'consent': 'true'},
                    files={'file': (source.name, audio, 'audio/mpeg')})
            assert response.status_code == 201, response.text
            personal = response.json()
            assert personal['engine'] == 'f5_hmong'
            assert personal['automatic_reference'] is True
            assert personal['known_preset'] == 'hmong-' + gender
            assert personal['source_sha256'] == metadata['sha256']
            assert personal['source_duration'] > 8
            assert personal['transcript'] == metadata['reference']['text']
            assert abs(personal['reference_start'] - metadata['reference']['start']) < .01
            assert abs(personal['reference_end'] - metadata['reference']['end']) < .01
            assert 3 <= personal['duration'] <= 8.001
            started = time.monotonic()
            clone = render(client, {'text': 'Kuv zoo siab tau ntsib nej hnub no.', 'language': 'mww',
                                   'voice_id': personal['id'], 'hmong_steps': 4,
                                   'format': 'wav', 'paragraph_pause': 0})
            assert clone['engine'] == 'f5_hmong'
            results['source_clones'][gender] = {
                'source_sha256': personal['source_sha256'], 'source_seconds': personal['source_duration'],
                'reference_seconds': personal['duration'], 'automatic_reference': True,
                'audio_seconds': clone['audio_seconds'],
                'wall_seconds': round(time.monotonic() - started, 3)}
        results['clone'] = True

        # A different long file needs an explicit excerpt and matching words.
        # Prefix approved speech with one second of silence so the chosen
        # 1.0..6.3s interval contains exactly the approved female reference.
        female = voice_metadata['female']
        source = app_root / 'assets/hmong' / female['file']
        altered = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source),
            '-af', 'adelay=1000:all=1', '-t', '12', '-ac', '1', '-ar', '24000',
            '-codec:a', 'pcm_s16le', '-f', 'wav', 'pipe:1'], timeout=45)
        assert hashlib.sha256(altered).hexdigest() not in {v['sha256'] for v in voice_metadata.values()}
        fields = {'name': 'Native QA manual crop', 'language': 'mww', 'consent': 'true'}
        files = {'file': ('different-long.wav', altered, 'audio/wav')}
        missing = client.post('/api/voices/clone', data=fields, files=files)
        assert missing.status_code == 422, 'Unknown long audio must not guess words or reference bounds'
        fields.update(transcript=female['reference']['text'], reference_start='1',
                      reference_end=str(1 + female['reference']['end']))
        response = client.post('/api/voices/clone', data=fields, files=files)
        assert response.status_code == 201, response.text
        manual = response.json()
        assert manual['engine'] == 'f5_hmong' and manual['automatic_reference'] is False
        assert manual['transcript'] == female['reference']['text']
        assert abs(manual['reference_start'] - 1) < .01
        assert abs(manual['duration'] - female['reference']['end']) < .05
        manual_job = render(client, {'text': 'Peb zoo siab tau nyob ua ke.', 'language': 'mww',
                                    'voice_id': manual['id'], 'hmong_steps': 4,
                                    'format': 'wav', 'paragraph_pause': 0})
        assert manual_job['engine'] == 'f5_hmong'
        results['manual_crop'] = True
        srt_text = '1\n00:00:00,000 --> 00:00:12,000\nNyob zoo, kuv yog ib tug Hmoob.\n'
        aligned = render(client, {'text': srt_text, 'input_format': 'srt', 'language': 'mww',
                                 'voice_id': 'hmong-female', 'hmong_steps': 4,
                                 'format': 'wav', 'paragraph_pause': 0, 'max_cue_tempo': 2})
        assert abs(aligned['audio_seconds'] - 12) < .1
        saved = client.get('/api/jobs/' + aligned['id'] + '/script.srt')
        assert saved.status_code == 200 and '00:00:12,000' in saved.text
        results['srt_timeline'] = True

    from benchmark_hmong import compare
    results['speed_benchmark'] = compare(studio.DATA / 'models')
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
    print('PASS: complete MP3 previews, real offline female/male Hmong, both source-MP3 clones, manual excerpt, TXT/SRT/MP3 and normal startup.', flush=True)


if __name__ == '__main__':
    main()
