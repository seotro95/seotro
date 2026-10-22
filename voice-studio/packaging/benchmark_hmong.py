"""Compare actual steady-state baseline and fast synthesis on one machine."""
import gc
import json
from pathlib import Path
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
    text = 'Nyob zoo. Kuv xav nrog nej tham txog zaj dab neeg no.'
    timings = {}
    for label, steps, precision in [('baseline', 8, 'fp32'), ('fast', 4, 'auto')]:
        model = load_local_model(Path(model_root), 'cpu', precision=precision)
        torch.manual_seed(42)
        started = time.monotonic()
        audio, result_rate = infer_batch(ref, words + '. ', text, model,
                                        steps=steps, speed=1, device='cpu')
        elapsed = time.monotonic() - started
        assert result_rate == 24000 and audio.size > 24000 / 3
        assert np.isfinite(audio).all() and abs(audio).max() > .001
        timings[label] = {'seconds': round(elapsed, 4), 'steps': steps,
                          'precision': model.precision,
                          'audio_seconds': len(audio) / result_rate}
        print('Real performance measurement:', label, json.dumps(timings[label]), flush=True)
        del model
        gc.collect()
    timings['speedup'] = round(timings['baseline']['seconds'] / timings['fast']['seconds'], 3)
    timings['model_loading_included'] = False
    timings['pronunciation_evaluated'] = False
    # This gates the fast claim on the actual Windows release machine.
    assert timings['speedup'] > 1, 'Fast mode did not improve the measured sample on this host'
    if report:
        Path(report).write_text(json.dumps(timings, indent=2), encoding='utf-8')
    return timings


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    compare(sys.argv[1], sys.argv[2])
