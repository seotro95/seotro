"""Measure sentence joining at the same 16-step FP32 setting on one machine.

This optional diagnostic is not a release gate or a pronunciation evaluation.
It reports the measured time and actual transformer evaluations, including when
joining is slower. Model loading and a common warm-up are outside the timings.
"""
import json
from pathlib import Path
import platform
import time


def compare(model_root, report=None):
    import numpy as np
    import soundfile as sf
    import torch
    from hmong_assets import reference
    from hmong_f5 import load_local_model, infer_batch

    torch.set_num_threads(4)
    path, words = reference('hmong-female')
    samples, rate = sf.read(str(path), dtype='float32', always_2d=True)
    ref = (torch.from_numpy(samples.T.copy()), rate)
    # Both sentences exceed the short-text guard, so joining does not change
    # their requested pace or total generated duration, apart from rounding.
    sentences = ('Kuv zoo siab tau ntsib nej.', 'Ua tsaug rau koj mloog zaj dab neeg no.')
    model = load_local_model(Path(model_root), 'cpu', precision='fp32')
    if model.precision != 'fp32':
        raise RuntimeError('Benchmark requires FP32 for both strategies')
    counts = {'nfe': 0}
    def count_evaluation(_module, _inputs):
        counts['nfe'] += 1
    hook = model.ema_model.transformer.register_forward_pre_hook(count_evaluation)
    timings = {'same_settings': {'steps': 16, 'precision': 'fp32', 'speed': 1,
                                'reference': 'hmong-female', 'text': ' '.join(sentences),
                                'cpu_threads': torch.get_num_threads(), 'platform': platform.platform()},
               'model_loading_included': False, 'warmup_included': False,
               'pronunciation_evaluated': False, 'speedup_required': False}
    try:
        # Warm the same loaded model before either measured strategy. Each
        # strategy then receives the same words, reference, pace and precision.
        torch.manual_seed(42)
        infer_batch(ref, words, ' '.join(sentences), model, steps=16, speed=1, device='cpu')
        for label, parts in [('sequential_sentences', sentences), ('joined_paragraph', (' '.join(sentences),))]:
            torch.manual_seed(42)
            before_nfe = counts['nfe']
            audio_seconds = 0
            started = time.monotonic()
            for text in parts:
                audio, result_rate = infer_batch(ref, words, text, model,
                                                steps=16, speed=1, device='cpu')
                assert result_rate == 24000 and audio.size > 24000 / 3
                assert np.isfinite(audio).all() and abs(audio).max() > .001
                audio_seconds += len(audio) / result_rate
            elapsed = time.monotonic() - started
            timings[label] = {'seconds': round(elapsed, 4), 'steps': 16, 'precision': 'fp32',
                              'audio_seconds': round(audio_seconds, 4), 'render_calls': len(parts),
                              'nfe': counts['nfe'] - before_nfe,
                              'real_time_factor': round(elapsed / audio_seconds, 4)}
            print('Real performance measurement:', label, json.dumps(timings[label]), flush=True)
    finally:
        hook.remove()
    timings['sequential_over_joined_wall_ratio'] = round(
        timings['sequential_sentences']['seconds'] / max(timings['joined_paragraph']['seconds'], 0.0001), 3)
    timings['audio_duration_difference_seconds'] = round(abs(
        timings['sequential_sentences']['audio_seconds'] - timings['joined_paragraph']['audio_seconds']), 4)
    if report:
        Path(report).write_text(json.dumps(timings, indent=2), encoding='utf-8')
    return timings


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    compare(sys.argv[1], sys.argv[2])
