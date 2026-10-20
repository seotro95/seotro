"""Measure local CUDA FP32/AMP inference before saving a hardware-specific choice.

The bootstrap process only reuses the selected clone runtime.  Four short local
generations (warm and measured for each precision) are not a one-hour benchmark.
"""
from __future__ import annotations

import array
import asyncio
from datetime import datetime
import gc
import json
import math
from pathlib import Path
import random
import socket
import sys
import tempfile
import time
import uuid
import wave

BASE = Path(__file__).resolve().parent
TEXT = 'Nyob zoo, kuv hais lus Hmoob.'
PRECISIONS = ('float32', 'float16')
INSERTED_PAUSE_SECONDS = .15


def inspect_audio(path):
    """Validate the PCM output, excluding only our known final inserted pause."""
    with wave.open(str(path), 'rb') as reader:
        rate, channels, width, frames = (reader.getframerate(), reader.getnchannels(),
                                         reader.getsampwidth(), reader.getnframes())
        if rate != 24000 or channels != 1 or width != 2 or not rate < frames <= 120 * rate:
            raise ValueError('WAV do toc do khong hop le: can PCM16 mono 24 kHz, 1-120 giay.')
        peak, minimum, maximum, read_frames = 0, 32767, -32768, 0
        while chunk := reader.readframes(65536):
            samples = array.array('h')
            samples.frombytes(chunk)
            if sys.byteorder != 'little':
                samples.byteswap()
            read_frames += len(samples)
            minimum, maximum = min(minimum, min(samples)), max(maximum, max(samples))
            peak = max(peak, abs(min(samples)), abs(max(samples)))
        if read_frames != frames or peak < 2 or minimum == maximum:
            raise ValueError('WAV do toc do bi cat, im lang hoac khong co tin hieu hop le.')
    seconds = frames / rate
    return {'audio_seconds': seconds, 'speech_seconds': seconds - INSERTED_PAUSE_SECONDS,
            'inserted_pause_seconds': INSERTED_PAUSE_SECONDS, 'frames': frames,
            'peak_pcm': peak}


def _cuda_oom(error, torch):
    classes = tuple(candidate for candidate in (
        getattr(torch.cuda, 'OutOfMemoryError', None), getattr(torch, 'OutOfMemoryError', None)
    ) if isinstance(candidate, type) and issubclass(candidate, BaseException))
    pending, seen = [error], set()
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if classes and isinstance(item, classes):
            return True
        # The HTTP adapter wraps the engine's exception; retain classification
        # across its explicit cause/context chain rather than treating all
        # RuntimeErrors or failed requests as an out-of-memory candidate.
        pending.extend(value for value in (item.__cause__, item.__context__)
                       if isinstance(value, BaseException))
    return False


def _recover_cuda_oom(backend, torch):
    # This standalone worker owns all requests. A failed upstream generator can
    # retain one UUID's mel state until it is explicitly discarded.
    for name in ('tts_speech_token_dict', 'llm_end_dict', 'hift_cache_dict'):
        value = getattr(backend, name, None)
        if isinstance(value, dict):
            value.clear()
    gc.collect()
    torch.cuda.empty_cache()


def _seed(torch):
    import numpy as np
    random.seed(1986)
    np.random.seed(1986)
    torch.manual_seed(1986)
    torch.cuda.manual_seed_all(1986)


async def measure(app, backend, torch, folder, *, clock=time.perf_counter):
    """Return only valid measured candidates; unexpected failures abort selection."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    previous_fp16 = backend.fp16
    results, failures = [], []
    payload = app.Speech(text=TEXT, dialect='mww', voice='hmong-white-female',
                         emotion='review', cleanup='light', compute_mode='standard',
                         speed=1, input_format='text')
    try:
        for precision in PRECISIONS:
            backend.fp16 = precision == 'float16'
            warmup = folder / ('warmup-' + precision + '.wav')
            output = folder / (precision + '.wav')
            ran_out_of_memory = False
            try:
                print('Lam am ' + precision + ' (khong tinh vao so do)...', flush=True)
                _seed(torch)
                await app.generate_speech(payload, output_path=warmup)
                torch.cuda.synchronize()
                inspect_audio(warmup)
                print('Dang do ' + precision + ' va loc on Nhe...', flush=True)
                _seed(torch)
                torch.cuda.synchronize()
                began = clock()
                await app.generate_speech(payload, output_path=output)
                torch.cuda.synchronize()
                elapsed = clock() - began
                if not math.isfinite(elapsed) or elapsed <= 0:
                    raise ValueError('Dong ho do toc do khong hop le.')
                info = inspect_audio(output)
                info.update(precision=precision, elapsed_seconds=elapsed,
                            real_time_factor=elapsed / info['speech_seconds'],
                            audio_path=str(output.resolve()))
                results.append(info)
                print(f"{precision}: {elapsed:.3f} giay / {info['speech_seconds']:.3f} giay loi doc; "
                      f"RTF {info['real_time_factor']:.4f}.", flush=True)
            except Exception as exc:
                if not _cuda_oom(exc, torch):
                    raise
                failures.append({'precision': precision, 'reason': 'cuda_out_of_memory'})
                print(precision + ': khong du VRAM; khong dung ket qua nay.', flush=True)
                ran_out_of_memory = True
            finally:
                warmup.unlink(missing_ok=True)
            if ran_out_of_memory:
                # Leave the except block before collecting: the exception's
                # traceback can otherwise keep failed CUDA tensors alive.
                _recover_cuda_oom(backend, torch)
                output.unlink(missing_ok=True)
        if not results:
            raise RuntimeError('Ca hai cau hinh deu khong du VRAM. Giu nguyen cau hinh cu.')
        selected = min(results, key=lambda item: item['real_time_factor'])['precision']
        return {'precision': selected, 'results': results, 'failures': failures,
                'one_hour_tested': False, 'target_2min_per_hour_verified': False}
    finally:
        backend.fp16 = previous_fp16


def _atomic_report(path, report):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='report-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def worker():
    import torch
    if not torch.cuda.is_available():
        print('Chua dung duoc CUDA. Chay CHAY-STUDIO.bat de cai GPU, roi dong Studio va do lai.', flush=True)
        return 2
    import app
    import cosy_engine as engine
    import gpu_tuning
    if len(list(engine._sentences(TEXT))) != 1:
        raise RuntimeError('Kich ban do phai chi co mot doan; chua luu ket qua.')
    print('GPU: ' + torch.cuda.get_device_name(0), flush=True)
    print('Do mau ngan FP32/FP16 voi Review + Loc on Nhe. Khong phai phep do tao 1 gio.', flush=True)
    began = time.perf_counter()
    _, backend, _ = engine._load_engine(engine.model_dir())
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - began
    folder = BASE / '.data' / 'runtime' / 'speed-test' / (
        datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    report = asyncio.run(measure(app, backend, torch, folder))
    report.update(schema=1, text=TEXT, cleanup='light', style='review',
                  model_revision=engine.REVISION, hardware=gpu_tuning.hardware_key(torch),
                  model_load_seconds=load_seconds)
    _atomic_report(folder / 'report.json', report)
    gpu_tuning.save_choice(gpu_tuning.settings_path(), torch, report['precision'], report['results'])
    print('Da luu cau hinh nhanh nhat trong phep do: ' + report['precision'], flush=True)
    print('WAV va ket qua: ' + str(folder), flush=True)
    print('CHUA xac nhan muc tieu 2 phut/1 gio. Hay nghe hai WAV de kiem tra giong.', flush=True)
    print('Chay CHAY-STUDIO.bat de dung cau hinh da do.', flush=True)
    return 0


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if args == ['--worker']:
        return worker()
    if args:
        raise RuntimeError('Tham so do toc do khong hop le.')
    # Avoid sharing 6 GB VRAM with an already-running local Studio. Do not stop
    # the user's process or install packages merely to run a measurement.
    try:
        with socket.create_connection(('127.0.0.1', 8090), timeout=.5):
            print('Dong cua so Studio (Ctrl+C) truoc khi chay DO-TOC-DO.bat.', flush=True)
            return 2
    except OSError:
        pass
    import clone_runtime
    executable = clone_runtime.selected_python(BASE)
    # The clone runtime's helper propagates Ctrl+C to its own subprocess tree.
    # It also sets UTF-8 and the bundled FFmpeg path for the child.
    return clone_runtime._run([executable, '-X', 'utf8', str(Path(__file__).resolve()), '--worker'], BASE)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as error:
        print('Chua luu cau hinh toc do moi: ' + str(getattr(error, 'detail', error) or 'Da dung.'),
              file=sys.stderr, flush=True)
        raise SystemExit(1)
