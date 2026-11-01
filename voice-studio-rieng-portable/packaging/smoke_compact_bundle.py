"""Offline checks of the exact compact ZIP with its bundled Windows runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid

from smoke_clean_bundle import configure


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    runtime, data = configure(root)
    import numpy as np
    import onnxruntime
    import soundfile as sf
    import psutil
    import app
    from fastapi.testclient import TestClient
    from worker import render, close_nano_pool, close_international_backends

    assert Path(app.__file__).resolve() == root/'app/app.py'
    for module in (np, onnxruntime, sf, psutil):
        assert runtime in Path(module.__file__).resolve().parents, module.__name__
    for binary in ('ffmpeg', 'ffprobe'):
        assert Path(shutil.which(binary)).resolve().parent == root/'ffmpeg/bin'
        subprocess.run([binary, '-version'], stdout=subprocess.DEVNULL, check=True, timeout=30)
    subprocess.run([sys.executable, '-s', '-m', 'pip', 'check'], check=True, timeout=120)
    manifest = json.loads((root/'delivery/manifest.json').read_text(encoding='utf-8-sig'))
    private = root/'delivery/voices.vspack'
    assert private.stat().st_size == manifest['encrypted_size']
    assert digest(private) == manifest['encrypted_sha256']
    for folder in ('voices', 'audio', 'parts', 'jobs'):
        (data/folder).mkdir(exist_ok=True)
    rendered = []
    try:
        for engine, speaker, threads in [('vieneu_nano', 'Minh Quân', 2), ('vieneu', 'Mai Anh', 1)]:
            ident = 'compact-windows-' + uuid.uuid4().hex
            job = {'id': ident, 'text': 'Xin chào. Cảm ơn bạn đã lắng nghe.', 'engine': engine,
                   'speaker': speaker, 'voice_id': 'nano-minhquan' if engine == 'vieneu_nano' else 'vi-maianh',
                   'language': 'vi', 'format': 'wav', 'input_format': 'txt', 'quality': 'standard',
                   'speed': 1, 'delivery': 'natural', 'paragraph_pause': 0, 'model_memory': 'shared',
                   'nano_steps': 8, 'nano_threads': threads, 'nano_parallel': 1,
                   'render_mode': 'balanced', 'resource_profile': 'maximum'}
            started = time.perf_counter()
            render(job)
            elapsed = time.perf_counter()-started
            result = json.loads((data/'parts'/ident/'result.json').read_text())
            assert result['completed'] == result['total'] and not result.get('duration_limited')
            audio, rate = sf.read(data/'audio'/(ident+'.wav'))
            assert rate == 24000 and audio.ndim == 1 and len(audio) > rate*.3
            assert np.isfinite(audio).all() and np.max(np.abs(audio)) > .001
            rendered.append({'engine': engine, 'speaker': speaker, 'audio_seconds': len(audio)/rate,
                             'elapsed_seconds': elapsed, 'execution': result['execution_settings'],
                             'valid_pcm': True})
            close_nano_pool()
        with TestClient(app.app) as client:
            config = client.get('/api/config').json()
            assert config['distribution_profile'] == 'compact-19'
            assert config['default_resource_profile'] == 'maximum'
            assert config['models']['vieneu'] and config['nano_ready'] and not config['models']['qwen']
            assert not any(v['engine'] == 'qwen' for v in client.get('/api/voices').json()['voices'])
            assert client.get('/').status_code == 200
            assert 'Gọn 19' in client.get('/static/app.js').text
        # Verify the relocated launcher also exposes the local HTTP server.
        log = root/'compact-launcher.log'
        with log.open('w', encoding='utf-8') as output:
            process = subprocess.Popen([sys.executable, '-s', '-X', 'utf8', str(root/'app/launcher.py'), '--no-browser'],
                                       cwd=root, stdout=output, stderr=output)
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                deadline, ready = time.monotonic()+60, False
                while time.monotonic() < deadline and not ready:
                    assert process.poll() is None, log.read_text(encoding='utf-8', errors='replace')
                    for port in range(8770, 8790):
                        try:
                            with opener.open(f'http://127.0.0.1:{port}/api/config', timeout=.3) as response:
                                current = json.load(response)
                            if current.get('distribution_profile') == 'compact-19':
                                ready = True; break
                        except OSError:
                            pass
                    if not ready: time.sleep(.2)
                assert ready, 'Compact launcher HTTP readiness timeout'
            finally:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                process.wait(timeout=30)
        report = {'platform': sys.platform, 'bundled_python_relocated': True,
                  'offline_public_nano_turbo_synthesis_passed': True, 'requests': rendered,
                  'compact_catalog_passed': True, 'launcher_http_passed': True,
                  'encrypted_private_pack_preserved': True, 'encrypted_private_pack_sha256': digest(private),
                  'private_voice_unlock_attempted': False, 'gpu_inference_tested': False,
                  'whole_hour_generated': False, 'target_30x_guaranteed': False}
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        close_nano_pool(); close_international_backends()


if __name__ == '__main__':
    main()
