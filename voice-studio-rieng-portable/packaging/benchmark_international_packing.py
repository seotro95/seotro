"""Measure real VoxCPM speech, comparing sentence requests with packed requests.

Run with runtime-international/python.exe, an already prepared model and a
reference you can use. Nothing is downloaded. Reference paths/audio and source
recordings are not included in the JSON report. All generated audio stays in
the selected data directory for listening; measurements exclude model loading
and never count artificial silence as speech.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time


TEXTS = {
    'fr': 'Bonjour. Cette phrase présente le studio. Nous gardons la même voix.',
    'ja': 'こんにちは。音声スタジオへようこそ。同じ声で次の文を読みます。',
    'ko': '안녕하세요. 음성 스튜디오에 오신 것을 환영합니다. 같은 목소리로 다음 문장을 읽습니다.',
}


def measure(model, reference, directory, text, language, steps, packed, seed):
    import numpy as np
    import soundfile as sf
    import torch
    from narration import plan_segments
    from voxcpm_backend import _generate

    job = {'text': text, 'engine': 'voxcpm', 'input_format': 'txt',
           'paragraph_pause': 0,
           'segment_plan': 'international-packed-v1' if packed else 'classic-v1'}
    segments = plan_segments(job)
    torch.manual_seed(seed)
    np.random.seed(seed)
    audio_seconds, elapsed = 0., 0.
    for index, segment in enumerate(segments):
        destination = directory / f'{language}-{"packed" if packed else "classic"}-{index:03d}.wav'
        started = time.perf_counter()
        _generate(model, segment.text, reference, destination, steps=steps)
        elapsed += time.perf_counter() - started
        samples, rate = sf.read(destination, dtype='float32')
        if (samples.ndim != 1 or rate != 24000 or not samples.size
                or not np.isfinite(samples).all() or np.max(np.abs(samples)) <= 1e-5):
            raise ValueError('Speech check returned invalid or silent PCM.')
        audio_seconds += len(samples) / rate
    return {'plan': job['segment_plan'], 'model_requests': len(segments),
            'processing_seconds': elapsed, 'audio_seconds': audio_seconds,
            'realtime_multiplier': audio_seconds / elapsed,
            'valid_pcm_audio': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--languages', nargs='+', choices=tuple(TEXTS), default=['fr', 'ja'])
    parser.add_argument('--steps', type=int, choices=[4, 8, 10], default=8)
    parser.add_argument('--threads', type=int, choices=range(1, 9), default=4)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--order', choices=['classic-first', 'packed-first'], default='classic-first')
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS=str(args.threads))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
    from voxcpm_backend import _load_model, _generate, prepared_model

    data = args.data_dir.resolve()
    reference = args.reference.resolve()
    if not reference.is_file():
        parser.error('The reference WAV is missing.')
    output = args.output.resolve()
    audio = data / 'benchmarks' / ('international-packing-' + str(time.time_ns()))
    audio.mkdir(parents=True)
    started = time.perf_counter()
    model = _load_model(prepared_model(data), args.threads, precision='fp32')
    loading = time.perf_counter() - started
    # Prime both the runtime and the reference encoder; both measured plans use
    # this exact model and cached reference, with identical inference settings.
    _generate(model, 'Bonjour.', reference, audio / 'warmup.wav', steps=args.steps)
    report = {'format': 'international-packing-real-speech-v1',
              'engine': 'voxcpm2', 'device': 'cpu', 'precision': 'fp32',
              'threads': args.threads, 'steps': args.steps, 'seed': args.seed,
              'execution_order': args.order,
              'load_seconds': loading, 'includes_model_load': False,
              'same_model_reference_and_steps': True, 'model_warm_and_reference_cached': True,
              'private_reference_audio_included': False,
              'human_pronunciation_reviewed': False, 'gtx1060_tested': False,
              'turbo_speed_equivalence_established': False,
              'limitation': 'Short public-text samples; valid PCM alone does not establish pronunciation, voice similarity or performance on another machine.',
              'results': []}
    output.parent.mkdir(parents=True, exist_ok=True)
    for language in args.languages:
        modes = {packed: measure(model, reference, audio, TEXTS[language], language,
                                args.steps, packed, args.seed)
                 for packed in ((False, True) if args.order == 'classic-first' else (True, False))}
        report['results'].append({'language': language, 'text': TEXTS[language],
                                  'classic': modes[False], 'packed': modes[True],
                                  'throughput_ratio': modes[True]['realtime_multiplier'] / modes[False]['realtime_multiplier']})
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report['results'][-1], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
