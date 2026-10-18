"""Native Windows proof of offline use with the relocated bundled interpreter."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(sys.argv[1]).resolve()
APP = ROOT / 'app'
DATA = APP / '.data'
RUNTIME = ROOT / 'runtime'
sys.path.insert(0, str(APP))


def wait_job(client, ident, timeout=300):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        response = client.get('/api/jobs/' + ident)
        assert response.status_code == 200, response.text
        job = response.json()
        if job['status'] not in {'queued', 'running', 'cancelling'}:
            assert job['status'] == 'done', job
            assert not job.get('duration_limited'), job
            return job
        time.sleep(.1)
    raise AssertionError('Real offline speech job timed out')


def main():
    assert os.name == 'nt', 'Native Windows is required'
    assert Path(sys.executable).resolve() == (RUNTIME / 'python.exe').resolve()
    assert Path(sys.prefix).resolve() == RUNTIME.resolve()
    assert ' ' in str(ROOT), 'Test the relocated bundle in a directory containing spaces'
    assert os.environ['HF_HUB_OFFLINE'] == '1'
    assert os.environ['TRANSFORMERS_OFFLINE'] == '1'
    # This temporary standard-library hook also applies to spawned workers.
    # Deny non-loopback connections, so missing models cannot download silently.
    hook = RUNTIME / 'Lib/sitecustomize.py'
    assert not hook.exists(), 'Do not overwrite a pre-existing runtime hook'
    hook.write_text('''import socket
_connect = socket.socket.connect
_getaddrinfo = socket.getaddrinfo
def _local_connect(self, address):
    if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
        raise OSError('Portable offline smoke: external network disabled')
    return _connect(self, address)
def _local_resolve(host, *args, **kwargs):
    if host not in (None, '127.0.0.1', '::1', 'localhost'):
        raise OSError('Portable offline smoke: external DNS disabled')
    return _getaddrinfo(host, *args, **kwargs)
socket.socket.connect = _local_connect
socket.getaddrinfo = _local_resolve
''', encoding='utf-8')
    exec(compile(hook.read_text(encoding='utf-8'), str(hook), 'exec'), {})
    try:
        verify_app()
        verify_launcher()
    finally:
        hook.unlink(missing_ok=True)
        for compiled in (RUNTIME / 'Lib/__pycache__').glob('sitecustomize.*.pyc'):
            compiled.unlink()
    print('PASS: native Windows relocated Python, bundled dependencies/FFmpeg, offline Nano/Turbo cloning, exports and portable launcher', flush=True)


def verify_app():
    import numpy as np
    import soundfile as sf
    import onnxruntime
    import vieneu
    import httpx
    from fastapi.testclient import TestClient
    import app
    for module in (np, sf, httpx, onnxruntime, vieneu):
        assert RUNTIME.resolve() in Path(module.__file__).resolve().parents, module.__file__
    for name in ('ffmpeg', 'ffprobe'):
        actual = Path(shutil.which(name)).resolve()
        assert ROOT.resolve() in actual.parents, str(actual)
        subprocess.run([str(actual), '-version'], check=True, stdout=subprocess.DEVNULL)
    # Generate a 3–30 second reference through the actual bundled preset API.
    with TestClient(app.app) as client:
        conf = client.get('/api/config').json()
        assert conf['version'] == '1.3.0' and conf['max_characters'] == 200000
        assert conf['nano_ready'] and conf['nano_clone_ready'] and conf['models']['vieneu']
        assert client.get('/').status_code == 200
        for asset in ('app.js', 'style.css'):
            assert client.get('/static/' + asset).status_code == 200
        preset = client.post('/api/speech', json={
            'text': 'Xin chào, đây là mẫu thử giọng nói tiếng Việt trong bản portable. Hôm nay chúng ta cùng kiểm tra chức năng nhân bản âm thanh.',
            'voice_id': 'nano-minhquan', 'language': 'vi', 'nano_steps': 4,
            'nano_parallel': 1, 'nano_threads': 1, 'paragraph_pause': 0, 'format': 'wav'})
        assert preset.status_code == 202, preset.text
        preset_job = wait_job(client, preset.json()['id'])
        sample = DATA / 'audio' / (preset_job['id'] + '.wav')
        assert 3 <= sf.info(str(sample)).duration <= 30
        with sample.open('rb') as source:
            response = client.post('/api/voices/clone', data={'name': 'Portable QA synthetic reference', 'language': 'vi', 'consent': 'true'},
                                   files={'file': ('reference.wav', source, 'audio/wav')})
        assert response.status_code == 201, response.text
        reference = response.json()
        registered = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == reference['id'])
        assert registered['ready_engines']['vieneu_nano']
        assert registered['ready_engines']['vieneu']
        payload = {'text': 'Xin chào, đây là giọng nhân bản trong bản portable. Cảm ơn bạn đã lắng nghe câu chuyện.',
                   'voice_id': reference['id'], 'language': 'vi',
                   'nano_parallel': 2, 'nano_threads': 1, 'paragraph_pause': 0, 'format': 'wav'}
        response = client.post('/api/speech', json=payload)
        assert response.status_code == 202, response.text
        job = wait_job(client, response.json()['id'])
        assert job['voice_id'] == reference['id'] and job['speaker'] is None
        assert job['engine'] == 'vieneu_nano' and job['reused_chunks'] == 0
        assert job['nano_steps'] == 4
        samples, rate = sf.read(DATA / 'audio' / (job['id'] + '.wav'))
        assert rate == 24000 and len(samples) > rate and np.max(np.abs(samples)) > .001
        for extension in ('wav', 'mp3', 'txt', 'srt'):
            result = client.get(f'/api/jobs/{job["id"]}/export.{extension}')
            assert result.status_code == 200 and len(result.content) > 10, result.text[:100]
        too_long = client.post('/api/speech', json={**payload, 'text': 'a' * 200001})
        assert too_long.status_code == 422
        verify_timeline(client, reference['id'], sf, np)
    # Exiting the lifespan kills the Nano worker tree before loading Turbo.
    with TestClient(app.app) as client:
        response = client.post('/api/speech', json={'text': 'Xin chào, đây là kiểm tra nhân bản giọng tiêu chuẩn.',
                              'voice_id': reference['id'], 'language': 'vi', 'clone_engine': 'standard',
                              'quality': 'standard', 'format': 'wav', 'paragraph_pause': 0})
        assert response.status_code == 202, response.text
        job = wait_job(client, response.json()['id'])
        assert job['engine'] == 'vieneu' and job['speaker'] is None
        samples, rate = sf.read(DATA / 'audio' / (job['id'] + '.wav'))
        assert len(samples) > rate and np.max(np.abs(samples)) > .001

    # Each bundled country voice must synthesize through the public API with
    # external networking denied, using only the relocated Windows runtime.
    from piper_catalog import DEMO_TEXTS
    with TestClient(app.app) as client:
        all_voices = client.get('/api/voices').json()['voices']
        international = [v for v in all_voices if v['engine'] == 'piper']
        assert len(international) == 16 and all(v['ready'] for v in international)
        for voice in international:
            language = voice['languages'][0]
            response = client.post('/api/speech', json={'text': DEMO_TEXTS[language],
                                   'voice_id': voice['id'], 'language': language})
            assert response.status_code == 202, response.text
            job = wait_job(client, response.json()['id'])
            assert job['engine'] == 'piper' and job['voice_id'] == voice['id']
            samples, rate = sf.read(DATA / 'audio' / (job['id'] + '.wav'))
            assert rate == 24000 and len(samples) > rate // 2 and np.max(np.abs(samples)) > .001
            assert client.get(f'/api/jobs/{job["id"]}/export.srt').status_code == 200
            print('OFFLINE COUNTRY VOICE:', language, voice['id'], flush=True)


def verify_timeline(client, reference_id, sf, np):
    """Real Windows clone synthesis, file decoding and exact WAV/SRT boundaries."""
    import wave
    from subtitles import export_srt, parse_srt
    cues = [{'start': 1.125, 'end': 9.875, 'text': 'Xin chào, hôm nay chúng ta cùng lắng nghe một câu chuyện.'},
            {'start': 11.250, 'end': 20.125, 'text': 'Cảm ơn bạn đã theo dõi, hẹn gặp lại trong phần tiếp theo.'}]
    script = export_srt(cues)
    uploaded = client.post('/api/scripts/import',
                           files={'file': ('Loi-Thoai.SRT', script.replace('\n', '\r\n').encode('utf-16'), 'text/plain')})
    assert uploaded.status_code == 200, uploaded.text
    imported = uploaded.json()
    assert imported['has_timeline'] and parse_srt(imported['text']) == cues
    response = client.post('/api/speech', json={'text': imported['text'], 'input_format': imported['input_format'],
                          'voice_id': reference_id, 'language': 'vi', 'timeline_seconds': 22.5,
                          'narration_quality': 'balanced', 'nano_parallel': 2, 'nano_threads': 1})
    assert response.status_code == 202, response.text
    job = wait_job(client, response.json()['id'])
    assert job['voice_id'] == reference_id and job['nano_steps'] == 8
    assert job['timing_mode'] == 'exact' and job['sync_ok'] and job['speed_report'] is None
    report = job['sync_report']
    assert report['complete'] and report['matched_cues'] == 2
    assert report['max_error_ms'] <= 1000 / 24000 and report['actual_seconds'] == 22.5
    path = DATA / 'audio' / (job['id'] + '.wav')
    with wave.open(str(path)) as audio:
        assert audio.getnframes() == round(22.5 * 24000)
    samples, rate = sf.read(path)
    assert not np.any(samples[:round(1.125 * rate)])
    assert not np.any(samples[round(9.875 * rate):round(11.250 * rate)])
    assert np.any(samples[round(1.125 * rate):round(9.875 * rate)])
    timed_srt = client.get(f'/api/jobs/{job["id"]}/export.srt')
    assert timed_srt.status_code == 200 and parse_srt(timed_srt.text) == cues
    timed_txt = client.get(f'/api/jobs/{job["id"]}/export.txt')
    roundtrip = client.post('/api/scripts/import', files={'file': ('timeline.txt', timed_txt.content, 'text/plain')})
    assert roundtrip.status_code == 200 and parse_srt(roundtrip.json()['text']) == cues
    mp3 = client.get(f'/api/jobs/{job["id"]}/export.mp3')
    assert mp3.status_code == 200
    decoded = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(DATA / 'audio' / (job['id'] + '.mp3')),
                              '-ac', '1', '-ar', '24000', '-f', 's16le', 'pipe:1'], capture_output=True, check=True)
    assert len(decoded.stdout) == round(22.5 * 24000) * 2
    pending = client.post('/api/scripts/import', files={'file': ('starts.txt', b'[00:01] Hello.\n[00:05] Goodbye.', 'text/plain')})
    assert pending.status_code == 200 and pending.json()['requires_total_duration']
    assert client.post('/api/speech', json={'text': script, 'input_format': 'srt', 'voice_id': reference_id,
                        'timeline_seconds': 7}).status_code == 422
    expressive = client.post('/api/speech', json={'text': '[thở dài] Xin chào, cảm ơn bạn đã lắng nghe câu chuyện.',
                         'voice_id': reference_id, 'narration_quality': 'expressive', 'nano_parallel': 1, 'nano_threads': 1})
    assert expressive.status_code == 202, expressive.text
    expressive_job = wait_job(client, expressive.json()['id'])
    assert expressive_job['nano_steps'] == 16 and expressive_job['voice_id'] == reference_id
    print('PASS: UTF-16 SRT import, exact cue/video length, timed TXT/SRT roundtrip, gapless MP3 and Nano16 cue', flush=True)


def verify_launcher():
    import httpx
    logfile = ROOT / 'portable-smoke-launcher.log'
    python = RUNTIME / 'python.exe'
    with logfile.open('w', encoding='utf-8') as output:
        process = subprocess.Popen([str(python), str(ROOT / 'portable_launcher.py'), '--no-browser'],
                                   cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        url = None
        try:
            with httpx.Client(trust_env=False, timeout=1) as client:
                for _ in range(120):
                    if process.poll() is not None:
                        raise AssertionError(logfile.read_text(encoding='utf-8'))
                    for port in range(8770, 8790):
                        try:
                            probe = client.get(f'http://127.0.0.1:{port}/api/config')
                            if probe.status_code == 200 and probe.json().get('version') == '1.3.0':
                                url = f'http://127.0.0.1:{port}'
                                break
                        except httpx.RequestError:
                            pass
                    if url:
                        break
                    time.sleep(.25)
                assert url, logfile.read_text(encoding='utf-8')
                assert client.get(url + '/').status_code == 200
        finally:
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                process.wait(timeout=20)
    logfile.unlink()


if __name__ == '__main__':
    main()
