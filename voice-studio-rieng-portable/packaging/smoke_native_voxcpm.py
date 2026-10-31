"""Exercise real native VoxCPM2 PCM with public reference audio on Windows CPU.

No ASR or human pronunciation claims are inferred from valid PCM. This test is
also useful on Linux, but only a real win32 report can attest Windows readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import wave

from build_full_update import _sources, application_digest


def app_http_smoke(app_dir, expected_version):
    """Start the current ASGI application and exercise its UI/API lifecycle.

    Uses the interpreter's installed FastAPI/Starlette/httpx, including when
    invoked with the bundled Windows Python. It does not enqueue synthesis,
    decrypt a voice library or claim that every bundled model was inferred.
    """
    from fastapi.testclient import TestClient

    app_dir = Path(app_dir).resolve()
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    application = importlib.import_module('app')
    if Path(application.__file__).resolve() != app_dir / 'app.py':
        raise ValueError('HTTP smoke imported a different application source')
    with TestClient(application.app) as client:
        root = client.get('/')
        if root.status_code != 200 or 'Voice Studio' not in root.text:
            raise ValueError('Current application HTML did not load')
        config_response = client.get('/api/config')
        if config_response.status_code != 200:
            raise ValueError('Current application configuration did not load')
        config = config_response.json()
        if config.get('version') != expected_version or config.get('edition') != 'standalone-voice':
            raise ValueError('HTTP configuration does not identify this application/version')
        script = client.get('/static/app.js')
        if script.status_code != 200 or script.content != (app_dir / 'static/app.js').read_bytes():
            raise ValueError('The HTTP UI script does not match the current source')
        voices_response = client.get('/api/voices')
        if voices_response.status_code != 200:
            raise ValueError('Current application voice catalog did not load')
        voices = voices_response.json().get('voices')
        if not isinstance(voices, list) or not voices:
            raise ValueError('Current application voice catalog is empty or malformed')
        conversion = client.post('/api/scripts/convert', json={
            'text': 'Bonjour. Merci.', 'input_format': 'txt', 'output_format': 'txt'})
        if conversion.status_code != 200 or conversion.json().get('text') != 'Bonjour. Merci.':
            raise ValueError('Current application TXT conversion did not preserve the text')
    return {'lifespan_started_and_stopped': True, 'ui_html': True,
            'current_ui_script': True, 'config_version': expected_version,
            'voice_catalog': True, 'voice_catalog_count': len(voices),
            'txt_conversion': True, 'private_voice_unlock_attempted': False,
            'additional_model_inference_attempted': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', required=True, type=Path)
    parser.add_argument('--native-root', required=True, type=Path)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--threads', type=int, choices=range(1, 9), default=4)
    parser.add_argument('--steps', type=int, choices=(4, 8, 10), default=8)
    args = parser.parse_args(argv)
    app_dir, data = args.app_dir.resolve(), args.data_dir.resolve()
    os.environ.update(VOICE_STUDIO_NATIVE_ROOT=str(args.native_root.resolve()),
                      VOICE_STUDIO_DATA_DIR=str(data), HF_HUB_OFFLINE='1',
                      TRANSFORMERS_OFFLINE='1')
    sys.path.insert(0, str(app_dir))
    import fast_multilingual
    import numpy as np
    import soundfile as sf

    reference = args.reference.resolve()
    if not reference.is_file():
        parser.error('Public reference WAV is missing')
    with reference.open('rb') as source:
        reference_digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if reference_digest != '32bf74dfb8342ccc8284f47a9e5fe1f41b458a983a00938ed170f76951ce638f':
        parser.error('Use the pinned public audio.cpp assets/resources/b.wav reference')
    overlay, version = _sources(app_dir.parent)
    marker = json.loads((data / 'models/voxcpm-native.ready').read_text(encoding='utf-8'))
    cpu_library = args.native_root / 'cpu/audiocpp.dll'
    if sys.platform != 'win32':
        cpu_library = fast_multilingual.library_path('cpu')
    with cpu_library.open('rb') as source:
        library_digest = hashlib.file_digest(source, 'sha256').hexdigest()
    audio_dir = data / 'qa-audio' / ('native-voxcpm-' + str(time.time_ns()))
    audio_dir.mkdir(parents=True)
    requests = []
    try:
        for index, (language, text) in enumerate((
            ('fr', 'Bonjour. Cette phrase vérifie la lecture en français.'),
            ('ja', 'こんにちは。これは日本語の音声テストです。'),
            ('fr', 'Le modèle reste chargé pour la phrase suivante.'),
        )):
            synthesize = fast_multilingual.create_synthesizer(
                reference, data, threads=args.threads, steps=args.steps,
                device='cpu', language=language, family='voxcpm2')
            output = audio_dir / f'{index}-{language}.wav'
            started = time.perf_counter()
            synthesize(text, output)
            elapsed = time.perf_counter() - started
            with wave.open(str(output)) as source:
                assert (source.getnchannels(), source.getsampwidth(), source.getframerate()) == (1, 2, 24000)
                duration = source.getnframes() / source.getframerate()
            audio, rate = sf.read(output, dtype='float32')
            assert rate == 24000 and audio.ndim == 1 and duration >= .2
            assert np.isfinite(audio).all() and np.max(np.abs(audio)) > 1e-4
            execution = fast_multilingual.execution_info()
            assert execution.get('backend') == 'voxcpm_native' and execution.get('device') == 'cpu'
            assert execution.get('model_family') == 'voxcpm2'
            requests.append({'language': language, 'text': text,
                             'audio_seconds': duration, 'processing_seconds': elapsed,
                             'realtime_multiplier': duration / elapsed,
                             'valid_pcm_audio': True, 'execution': execution})
        http_checks = app_http_smoke(app_dir, version)
        report = {'format': 'native-voxcpm-windows-pcm-v1', 'platform': sys.platform,
                  'product_version': version, 'source_commit': os.environ.get('GITHUB_SHA'),
                  'app_source_sha256': application_digest(overlay),
                  'native_cpu_sha256': library_digest,
                  'native_model_sha256': marker['sha256'], 'native_smoke_passed': True,
                  'app_http_smoke_passed': True, 'app_http_smoke': http_checks,
                  'public_reference_only': True, 'private_reference_audio_included': False,
                  'device': 'cpu', 'steps': args.steps, 'threads': args.threads,
                  'requests': requests, 'gpu_inference_tested': False,
                  'gtx1060_tested': False, 'full_hour_generated': False,
                  'target_30x_guaranteed': False, 'human_pronunciation_reviewed': False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        fast_multilingual.close_backends()


if __name__ == '__main__':
    main()
