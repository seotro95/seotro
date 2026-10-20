"""Auditable local before/after benchmarks. No arguments records unrun targets.

Targets are text-duration estimates. Only real, newly synthesized speech can
verify coverage. Warm-cache reuse never proves generation of new speech at30x.
"""
from __future__ import annotations

import argparse
import array
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import socket
import sys
import tempfile
import time
import uuid
import wave

BASE = Path(__file__).resolve().parent
TARGETS = (1, 5, 15, 30, 60)
SEED = 1986
BUILTIN_TEXT = (
    'Nyob zoo, kuv hais lus Hmoob. Hnub no peb sib tham txog peb lub neej thiab tsev neeg. '
    'Peb yuav ua tib zoo mloog thiab qhia zaj dab neeg no kom meej. '
    'Thaum sawv ntxov, peb mus ua hauj lwm thiab rov los tsev thaum tsaus ntuj.'
)


class BenchmarkBudgetExceeded(RuntimeError):
    pass


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    group = result.add_mutually_exclusive_group()
    group.add_argument('--target-minutes', type=int, choices=TARGETS)
    group.add_argument('--all', action='store_true', help='Run every target; may take hours on CPU.')
    result.add_argument('--text-file', type=Path, help='UTF-8 Hmong TXT, used without rewriting words.')
    result.add_argument('--include-warm', action='store_true', help='Measure reuse separately from new speech.')
    result.add_argument('--max-seconds', type=float, default=600,
                        help='Per-mode budget checked at model checkpoints; default600s.')
    result.add_argument('--output-dir', type=Path)
    result.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    return result


def inventory(targets=TARGETS):
    return [{'target_minutes': minute, 'status': 'unrun', 'runs': [],
             'target_duration_verified': False, 'target_2min_per_hour_verified': False}
            for minute in targets]


def source_text(target_minutes, path=None):
    if path is None:
        repeats = math.ceil(target_minutes * 180 / len(BUILTIN_TEXT.split()))
        # Repeat TEXT, never audio. Cold runs disable all cache reads.
        text = '\n'.join([BUILTIN_TEXT] * repeats)
        origin = 'builtin_text_repeated_to_estimate_180_words_per_minute'
    else:
        path = Path(path)
        if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('Can Hmong TXT UTF-8, toi da8MB.')
        text = path.read_text(encoding='utf-8-sig')
        origin = 'user_text_used_without_word_changes'
        if '-->' in text:
            raise ValueError('Benchmark loi moi can TXT, khong dung SRT/khoang lang de tinh toc do.')
    if not text.strip() or len(text) > 1_000_000:
        raise ValueError('Kich ban benchmark can1-1.000.000ky tu.')
    return text, origin


def inspect_audio(path, pause_seconds):
    digest = hashlib.sha256()
    with wave.open(str(path), 'rb') as reader:
        rate, frames = reader.getframerate(), reader.getnframes()
        if ((reader.getnchannels(), reader.getsampwidth(), rate, reader.getcomptype())
                != (1, 2, 24000, 'NONE') or frames <= 0):
            raise ValueError('Benchmark can WAV PCM16 mono24kHz co du lieu.')
        read_frames, low, high = 0, 32767, -32768
        while chunk := reader.readframes(65536):
            digest.update(chunk)
            samples = array.array('h')
            samples.frombytes(chunk)
            if sys.byteorder != 'little':
                samples.byteswap()
            read_frames += len(samples)
            low, high = min(low, min(samples)), max(high, max(samples))
        if read_frames != frames or high - low < 2:
            raise ValueError('WAV benchmark bi cat, im lang hoac khong hop le.')
    seconds = frames / rate
    if not math.isfinite(pause_seconds) or not 0 <= pause_seconds < seconds:
        raise ValueError('Khoang lang benchmark khong hop le.')
    return {'frames': frames, 'audio_seconds': seconds, 'inserted_pause_seconds': pause_seconds,
            'speech_seconds': seconds - pause_seconds, 'pcm_sha256': digest.hexdigest()}


@contextmanager
def cache_environment(directory, reads):
    changes = {'HMONG_AUDIO_CACHE_DIR': str(directory), 'HMONG_AUDIO_CACHE_READS': str(reads)}
    previous = {key: os.environ.get(key) for key in changes}
    os.environ.update(changes)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _seed(torch):
    import numpy as np
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)


def _synchronize(torch):
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def _budget_error(error):
    pending, seen = [error], set()
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, BenchmarkBudgetExceeded):
            return True
        pending.extend(value for value in (item.__cause__, item.__context__)
                       if isinstance(value, BaseException))
    return False


async def measure_run(app, engine, torch, text, output, *, label, max_seconds,
                      clock=time.perf_counter):
    units = len(list(engine._sentences(text)))
    payload = app.Speech(text=text, dialect='mww', voice='hmong-white-female', emotion='review',
                         speed=1, cleanup='light', input_format='text',
                         compute_mode='standard' if label == 'standard' else 'ultra')
    latest = {}
    _seed(torch)
    _synchronize(torch)
    began = clock()

    def progress(info):
        latest.update(info)
        if clock() - began > max_seconds:
            raise BenchmarkBudgetExceeded('Da het ngan sach tai checkpoint; chua tao xong voice.')

    row = {'label': label, 'status': 'running', 'seed': SEED,
           'target_2min_per_hour_verified': False}
    try:
        await app.generate_speech(payload, progress=progress, output_path=output)
        _synchronize(torch)
        elapsed = clock() - began
        info = inspect_audio(output, units * .15)
        hits, reused = latest.get('cache_hits', 0), latest.get('reused_seconds', 0)
        new_seconds = latest.get('synthesized_seconds', info['speech_seconds'] - reused)
        if (not units or not math.isfinite(elapsed) or elapsed <= 0
                or isinstance(hits, bool) or not isinstance(hits, int) or hits < 0
                or any(isinstance(n, bool) or not isinstance(n, (int, float))
                       or not math.isfinite(n) or n < 0 for n in (reused, new_seconds))
                or abs(new_seconds + reused - info['speech_seconds']) > .02):
            raise ValueError('So do loi moi/cache khong khop WAV; chua cong nhan benchmark.')
        if label in {'standard', 'ultra_cold'} and (hits or reused):
            raise ValueError('Cold co cachehit, khong phai toc do tao loi moi.')
        row.update(info, elapsed_seconds=elapsed, cache_hits=hits, reused_seconds=reused,
                   synthesized_new_seconds=new_seconds, new_voice_speed_multiplier=new_seconds / elapsed,
                   real_time_factor=elapsed / new_seconds if new_seconds else None,
                   cached_playback_throughput=(reused / elapsed if label == 'ultra_warm' else None),
                   audio_path=str(Path(output).resolve()),
                   status='completed' if elapsed <= max_seconds else 'budget_exceeded_after_completion')
    except Exception as error:
        row.update(status='budget_exceeded' if _budget_error(error) else 'failed',
                   elapsed_seconds=max(0, clock() - began), error_type=type(error).__name__,
                   synthesized_new_seconds=latest.get('synthesized_seconds', 0),
                   reused_seconds=latest.get('reused_seconds', 0),
                   cache_hits=latest.get('cache_hits', 0), audio_path=None)
    return row


def evaluate_target(target):
    rows = {row['label']: row for row in target['runs']}
    cold = [rows.get(label) for label in ('standard', 'ultra_cold')]
    verified = all(row is not None and row.get('status') == 'completed'
                   and row.get('synthesized_new_seconds', 0) >= target['target_minutes'] * 60
                   and row.get('cache_hits') == 0 and row.get('reused_seconds') == 0 for row in cold)
    target.update(target_duration_verified=verified, status='completed' if verified else 'incomplete')
    finished = all(row is not None and row.get('status') == 'completed' for row in cold)
    target['pcm_identical_before_after'] = (cold[0]['pcm_sha256'] == cold[1]['pcm_sha256'] if finished else None)
    target['target_2min_per_hour_verified'] = bool(
        verified and target['target_minutes'] == 60 and cold[1]['elapsed_seconds'] <= 120)
    if finished:
        target['cold_new_voice_speedup_before_after'] = (
            cold[1]['new_voice_speed_multiplier'] / cold[0]['new_voice_speed_multiplier'])


def write_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.benchmark-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def hardware(torch):
    cuda = bool(torch.cuda.is_available())
    result = {'platform': platform.platform(), 'python': platform.python_version(),
              'cpu_count_reported_by_os': os.cpu_count(), 'torch': str(torch.__version__),
              'torch_threads': torch.get_num_threads(), 'cuda_available': cuda,
              'cuda_runtime': str(torch.version.cuda), 'gpu': None, 'vram_bytes': None}
    if cuda:
        properties = torch.cuda.get_device_properties(torch.cuda.current_device())
        result.update(gpu=properties.name, vram_bytes=properties.total_memory)
    return result


def new_report(args):
    selected = TARGETS if args.all else ((args.target_minutes,) if args.target_minutes else TARGETS)
    return {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'unrun', 'targets': inventory(selected), 'hardware': None,
            'notes': ['Nominal duration is a text estimate; never pad or loop audio.',
                      'Only newly synthesized seconds qualify for cold speed and duration coverage.',
                      'Warm-cache reuse is separate and cannot verify30x generation of new speech.',
                      'max_seconds is per mode and checked at model checkpoints, not inside GPU kernels.',
                      'White Hmong tone/word accuracy and voice similarity require listening.'],
            'target_2min_per_hour_verified': False}


async def run_suite(app, engine, torch, args, folder, report):
    report_file = Path(folder) / 'report.json'
    for target in report['targets']:
        text, origin = source_text(target['target_minutes'], args.text_file)
        target.update(status='running', text_source=origin, text_characters=len(text),
                      text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
        write_report(report_file, report)
        output_dir = Path(folder) / f"{target['target_minutes']}-minute"
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='hmong-ultra-benchmark-cache-') as cache:
            labels = ['standard', 'ultra_cold'] + (['ultra_warm'] if args.include_warm else [])
            for label in labels:
                if label == 'ultra_warm' and target['runs'][-1].get('status') != 'completed':
                    target['runs'].append({'label': label, 'status': 'unrun', 'reason': 'cold_run_incomplete'})
                    break
                print(f"TARGET {target['target_minutes']}min / {label}: creating REAL speech...", flush=True)
                with cache_environment(cache, 1 if label == 'ultra_warm' else 0):
                    row = await measure_run(app, engine, torch, text, output_dir / (label + '.wav'),
                                            label=label, max_seconds=args.max_seconds)
                target['runs'].append(row)
                print('RESULT ' + json.dumps({key: row.get(key) for key in
                      ('label', 'status', 'elapsed_seconds', 'speech_seconds', 'synthesized_new_seconds',
                       'reused_seconds', 'cache_hits', 'new_voice_speed_multiplier')}), flush=True)
                write_report(report_file, report)
        evaluate_target(target)
        write_report(report_file, report)
    report['status'] = ('completed' if all(target['target_duration_verified'] for target in report['targets'])
                        else 'incomplete')
    report['target_2min_per_hour_verified'] = any(target['target_2min_per_hour_verified'] for target in report['targets'])
    write_report(report_file, report)
    return 0 if report['status'] == 'completed' else 2


def worker(args, folder, report):
    import torch
    import app
    import cosy_engine as engine
    report.update(hardware=hardware(torch), model_revision=engine.REVISION,
                  style='review', cleanup='light', voice='hmong-white-female', seed=SEED)
    if not engine.availability()['ready']:
        report['status'] = 'blocked_model_not_ready'
        write_report(Path(folder) / 'report.json', report)
        print('Mo hinh cuc bo chua san sang; khong goi API thay the.', flush=True)
        return 2
    began = time.perf_counter()
    engine._load_engine(engine.model_dir())
    _synchronize(torch)
    report.update(model_load_seconds=time.perf_counter() - began, hardware=hardware(torch), status='running')
    write_report(Path(folder) / 'report.json', report)
    return asyncio.run(run_suite(app, engine, torch, args, folder, report))


def main(argv=None):
    raw_args = sys.argv[1:] if argv is None else list(argv)
    args = parser().parse_args(raw_args)
    if not math.isfinite(args.max_seconds) or not 1 <= args.max_seconds <= 86400:
        raise ValueError('--max-seconds can1-86400giay moi mode.')
    if args.text_file is not None and args.target_minutes is None and not args.all:
        raise ValueError('Chi ro --target-minutes hoac --all de chay that voi TXT.')
    if not args.worker and (args.target_minutes is not None or args.all):
        try:
            with socket.create_connection(('127.0.0.1', 8090), timeout=.5):
                print('Dong Studio bang Ctrl+C truoc khi benchmark de khong tranh CPU/VRAM.', flush=True)
                return 2
        except OSError:
            pass
        import clone_runtime
        executable = clone_runtime.selected_python(BASE)
        return clone_runtime._run([executable, '-X', 'utf8', str(Path(__file__).resolve()),
                                   *raw_args, '--worker'], BASE)
    folder = Path(args.output_dir or BASE / '.data' / 'benchmarks' / (
        datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]))
    report = new_report(args)
    write_report(folder / 'report.json', report)
    if args.target_minutes is None and not args.all:
        print('1/5/15/30/60phut: CHUA CHAY. Khong co so do gia.', flush=True)
        print('Chay that: BENCHMARK-ULTRA.bat --target-minutes 1 --include-warm', flush=True)
        print('Tat ca: BENCHMARK-ULTRA.bat --all --max-seconds 86400', flush=True)
        print('Inventory: ' + str(folder / 'report.json'), flush=True)
        return 0
    try:
        result = worker(args, folder, report)
    except BaseException as error:
        report['status'] = 'interrupted' if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else 'failed'
        report['error_type'] = type(error).__name__
        write_report(folder / 'report.json', report)
        raise
    print('Bao cao that: ' + str(folder / 'report.json'), flush=True)
    print('Chi nhan verified neu da tao du loi moi. Nghe WAV de kiem tra tieng Hmong.', flush=True)
    return result


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as error:
        print('Benchmark chua xac nhan thanh cong: ' + type(error).__name__, file=sys.stderr, flush=True)
        raise SystemExit(1)
