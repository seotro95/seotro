"""One loaded model per long job, reusable chunk checkpoints, bounded PCM output."""
import json
import gc
import contextlib
import traceback
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

from narration import PCMWriter, PROFILES, plan_segments

DATA = Path(os.environ['VOICE_STUDIO_DATA_DIR'])
LANGUAGES = {'en-US': 'English', 'en-GB': 'English', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese', 'fr': 'French', 'de': 'German', 'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian'}


def write_state(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.05)


def load_synthesizer(job):
    import soundfile as sf
    if job['engine'] == 'vieneu_nano':
        from vieneu.v3nano import V3NanoVieNeuTTS
        steps = job.get('nano_steps', 8)
        model = V3NanoVieNeuTTS(steps=steps, threads=job.get('nano_threads', 2))
        def synthesize(text, output):
            model.save(model.infer(text, voice=job['speaker'], steps=steps, sway=-1), str(output))
        return synthesize
    if job['engine'] == 'vieneu':
        from local_vieneu import LocalVieneu
        precision = 'int8' if job.get('quality') == 'fast' else 'fp32'
        if precision == 'int8':
            from hardware import supports_int8
            if not supports_int8():
                raise RuntimeError('CPU không hỗ trợ VNNI cho chế độ nhanh.')
        model = LocalVieneu(backend='onnx', device='cpu', precision=precision, threads=int(os.environ.get('OMP_NUM_THREADS', '4')))
        # VieNeu caches reference encoding once for subsequent chunks.
        options = {'voice': job['speaker']} if job.get('speaker') else {'ref_audio': str(DATA / 'voices' / (job['voice_id'] + '.wav')), 'denoise': False}
        def synthesize(text, output):
            model.save(model.infer(text, **options), str(output))
        return synthesize
    import torch
    from qwen_tts import Qwen3TTSModel
    from huggingface_hub import snapshot_download
    torch.set_num_threads(int(os.environ.get('OMP_NUM_THREADS', '4')))
    gpu = torch.cuda.is_available()
    suffix = 'Base' if job['engine'] == 'qwen_clone' else 'CustomVoice'
    model_path = snapshot_download(f'Qwen/Qwen3-TTS-12Hz-0.6B-{suffix}', local_files_only=True)
    model = Qwen3TTSModel.from_pretrained(model_path, device_map='cuda:0' if gpu else 'cpu', dtype=torch.bfloat16 if gpu else torch.float32, attn_implementation='sdpa')
    prompt = None
    if job['engine'] == 'qwen_clone':
        voice = json.loads((DATA / 'voices' / (job['voice_id'] + '.json')).read_text(encoding='utf-8'))
        reference_text = voice.get('transcript', '').strip()
        prompt = model.create_voice_clone_prompt(ref_audio=str(DATA / 'voices' / (job['voice_id'] + '.wav')), ref_text=reference_text or None, x_vector_only_mode=not bool(reference_text))
    def synthesize(text, output):
        options = {'text': text, 'language': LANGUAGES[job['language']], 'max_new_tokens': 2048}
        if job.get('quality') == 'fast':
            options.update(do_sample=False, subtalker_dosample=False)
        if prompt is not None:
            samples, rate = model.generate_voice_clone(**options, voice_clone_prompt=prompt)
        else:
            samples, rate = model.generate_custom_voice(**options, speaker=job['speaker'])
        sf.write(str(output), samples[0], rate)
    return synthesize


_cached_key = None
_cached_synth = None


def get_synthesizer(job):
    global _cached_key, _cached_synth
    key = tuple(job.get(k) for k in ('engine', 'voice_id', 'speaker', 'language', 'quality', 'nano_steps', 'nano_threads'))
    if _cached_key != key or _cached_synth is None:
        _cached_synth = None
        _cached_key = None
        gc.collect()
        if 'torch' in sys.modules and sys.modules['torch'].cuda.is_available():
            sys.modules['torch'].cuda.empty_cache()
        _cached_synth = load_synthesizer(job)
        _cached_key = key
    return _cached_synth


def normalize_audio(raw, temporary, tempo, gain):
    # Avoid spawning FFmpeg for each natural-speed chunk, especially on Windows.
    if abs(tempo - 1) < 1e-6:
        import numpy as np
        import soundfile as sf
        import soxr
        samples, rate = sf.read(str(raw), dtype='float32', always_2d=False)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        if rate != 24000:
            samples = soxr.resample(samples, rate, 24000)
        samples = np.clip(samples * gain, -0.95, 0.95)
        sf.write(str(temporary), samples, 24000, subtype='PCM_16')
    else:
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(raw), '-vn', '-ac', '1', '-ar', '24000', '-af', f'atempo={tempo},volume={gain},alimiter=limit=0.95', '-codec:a', 'pcm_s16le', '-y', str(temporary)], check=True, timeout=120)


_nano_pool = None


def close_nano_pool():
    global _nano_pool
    if _nano_pool is not None:
        _nano_pool.shutdown(wait=True, cancel_futures=True)
        _nano_pool = None


def prepare_chunk(job, segment, index, work, synthesize=None):
    work = Path(work)
    part = work / f'{index:06d}.wav'
    if part.exists():
        return
    if (work / 'cancel.flag').exists():
        raise InterruptedError('Tác vụ đã dừng.')
    synthesize = synthesize or get_synthesizer(job)
    raw = work / f'raw-{index:06d}.wav'
    temporary = work / f'normalized-{index:06d}.wav'
    synthesize(segment.text, raw)
    profile_speed = PROFILES[job.get('delivery', 'natural')][0]
    tempo = job['speed'] * profile_speed * (0.94 if segment.emphasis else 1)
    gain = 1.12 if segment.emphasis else 1
    normalize_audio(raw, temporary, tempo, gain)
    with wave.open(str(temporary)) as audio:
        if audio.getnframes() == 0:
            raise ValueError('Mô hình trả đoạn âm thanh rỗng.')
    temporary.replace(part)
    raw.unlink(missing_ok=True)


def render(job, synthesize=None):
    global _nano_pool, _cached_synth, _cached_key
    parallel = job.get('engine') == 'vieneu_nano' and job.get('nano_parallel', 1) == 2 and synthesize is None
    if not parallel:
        close_nano_pool()
    elif _cached_synth is not None:
        _cached_synth = None
        _cached_key = None
        gc.collect()
    work = DATA / 'parts' / job['id']
    work.mkdir(parents=True, exist_ok=True)
    segments = plan_segments(job)
    if not any(s.text for s in segments):
        raise ValueError('Không có nội dung đọc sau khi xử lý ký hiệu nhấn/nghỉ.')
    maximum = job.get('max_minutes', 180) * 60
    assembly = work / 'assembled.wav'
    writer = PCMWriter(assembly, max_seconds=maximum)
    started = time.monotonic()
    write_state(work / 'progress.json', {'completed': 0, 'total': len(segments), 'progress': 0, 'phase': 'Chuẩn bị mô hình; lần đầu có thể chậm hơn'})
    completed = 0
    clipped = False
    futures = {}
    payload = {key: value for key, value in job.items() if key != 'text'}
    profile_speed, default_pause = PROFILES[job.get('delivery', 'natural')]
    gap = job.get('paragraph_pause', default_pause)
    try:
        for index, segment in enumerate(segments):
            if (work / 'cancel.flag').exists():
                raise InterruptedError('Tác vụ đã dừng; các đoạn đã tạo được giữ để tiếp tục.')
            if parallel:
                for ahead in range(index, min(index+2, len(segments))):
                    candidate = segments[ahead]
                    if candidate.text and ahead not in futures and not (work / f'{ahead:06d}.wav').exists():
                        if _nano_pool is None:
                            _nano_pool = ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn'))
                        futures[ahead] = _nano_pool.submit(prepare_chunk, payload, candidate, ahead, str(work))
            if segment.text:
                part = work / f'{index:06d}.wav'
                if index in futures:
                    futures.pop(index).result()
                elif not part.exists():
                    if synthesize is None:
                        synthesize = get_synthesizer(job)
                    prepare_chunk(job, segment, index, work, synthesize)
                clipped = writer.append(part)
                completed = index + 1
                if not clipped:
                    writer.silence(gap)
            else:
                writer.silence(segment.pause)
                completed = index + 1
            duration = writer.frames / writer.rate
            elapsed = time.monotonic() - started
            write_state(work / 'progress.json', {'completed': completed, 'total': len(segments), 'audio_seconds': duration, 'elapsed_seconds': round(elapsed, 1), 'progress': min(99, round(100 * completed / len(segments))), 'phase': f'Đã xử lý {completed}/{len(segments)} đoạn'})
            if writer.frames >= writer.limit:
                clipped = completed < len(segments) or clipped
                break
    finally:
        writer.close()
        for future in futures.values():
            if not future.cancel():
                future.result()
    if (work / 'cancel.flag').exists():
        raise InterruptedError('Tác vụ đã dừng.')
    destination = DATA / 'audio' / f"{job['id']}.{job['format']}"
    pending = work / ('finished.' + job['format'])
    if job['format'] == 'wav':
        assembly.replace(pending)
    else:
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(assembly), '-codec:a', 'libmp3lame', '-b:a', '192k', '-y', str(pending)], check=True, timeout=3600)
    pending.replace(destination)
    assembly.unlink(missing_ok=True)
    write_state(work / 'result.json', {'audio_seconds': writer.frames / writer.rate, 'duration_limited': clipped, 'completed': completed, 'total': len(segments), 'progress': 100, 'processing_seconds': round(time.monotonic()-started, 3)})


def serve():
    # Only the application's serialized queue writes this private pipe.
    for line in sys.stdin:
        path = Path(line.strip()).resolve()
        if path.parent != (DATA / 'jobs').resolve() or path.suffix != '.json':
            continue
        job = json.loads(path.read_text(encoding='utf-8'))
        work = DATA / 'parts' / job['id']
        work.mkdir(parents=True, exist_ok=True)
        code = 0
        with (DATA / 'jobs' / (job['id'] + '.log')).open('a', encoding='utf-8') as errors:
            try:
                with contextlib.redirect_stderr(errors):
                    render(job)
            except Exception:
                code = 1
                traceback.print_exc(file=errors)
        write_state(work / 'worker-done.json', {'code': code})


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--serve']:
            serve()
        else:
            render(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    finally:
        close_nano_pool()
