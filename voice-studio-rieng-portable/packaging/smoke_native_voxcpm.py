"""Exercise real native VoxCPM2 PCM with public reference audio on Windows CPU.

No ASR or human pronunciation claims are inferred from valid PCM. This test is
also useful on Linux, but only a real win32 report can attest Windows readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import wave

from build_full_update import _sources, application_digest


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
        report = {'format': 'native-voxcpm-windows-pcm-v1', 'platform': sys.platform,
                  'product_version': version, 'source_commit': os.environ.get('GITHUB_SHA'),
                  'app_source_sha256': application_digest(overlay),
                  'native_cpu_sha256': library_digest,
                  'native_model_sha256': marker['sha256'], 'native_smoke_passed': True,
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
