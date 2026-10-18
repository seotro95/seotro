"""One loaded model per long job, reusable chunk checkpoints, bounded PCM output."""
import json
import gc
import contextlib
import traceback
import multiprocessing
import hashlib
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

from state_io import write_json_atomic,write_progress
from narration import PCMWriter, PROFILES, plan_segments
from nano_resources import RESERVED_BYTES, resolve_nano_settings

DATA = Path(os.environ['VOICE_STUDIO_DATA_DIR'])
LANGUAGES = {'en-US': 'English', 'en-GB': 'English', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese', 'fr': 'French', 'de': 'German', 'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian'}


def write_state(path, data):
    if path.name=='progress.json':
        return write_progress(path,data)
    return write_json_atomic(path,data)


def load_synthesizer(job):
    import soundfile as sf
    if job['engine'] == 'system':
        from system_voices import speak
        return lambda text, output: speak(text, job['speaker'], output)
    if job['engine'] == 'piper':
        from piper_voice import create_synthesizer
        from nano_resources import cpu_budget
        return create_synthesizer(DATA, job['speaker'], threads=min(4, max(1, cpu_budget())))
    if job['engine'] == 'vieneu_nano':
        from vieneu.v3nano import V3NanoVieNeuTTS
        steps = job.get('nano_steps', 8)
        model = V3NanoVieNeuTTS(steps=steps, threads=job.get('nano_threads', 2))
        if job.get('speaker'):
            voice = job['speaker']
        else:
            # Enroll the chosen user's reference once per warm worker. Passing
            # ref_audio to every infer call repeats the expensive encoders.
            reference = DATA / 'voices' / (job['voice_id'] + '.wav')
            from nano_voice import load_nano_reference
            voice = load_nano_reference(model, reference)
        def synthesize(text, output):
            model.save(model.infer(text, voice=voice, steps=steps, sway=-1), str(output))
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


def synthesis_key(job):
    key = tuple(job.get(k) for k in ('engine', 'voice_id', 'speaker', 'language', 'quality', 'nano_steps', 'nano_threads', 'nano_backend'))
    if job.get('engine') in {'vieneu_nano', 'vieneu', 'qwen_clone'} and not job.get('speaker') and job.get('voice_id'):
        reference = DATA / 'voices' / (job['voice_id'] + '.wav')
        stat = reference.stat()
        key += (str(reference.resolve()), stat.st_size, stat.st_mtime_ns)
    return key


def get_synthesizer(job):
    global _cached_key, _cached_synth
    key = synthesis_key(job)
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
_nano_pool_key = None
NANO_LOOKAHEAD_PER_WORKER = 2


def initialize_nano_worker(job):
    # These are set before this spawned process imports NumPy/ONNX. The model's
    # own thread setting also stays explicit; BLAS must not multiply it again.
    threads = str(job['nano_threads'])
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = threads
    get_synthesizer(job)


def create_nano_pool(job, workers):
    return ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn'), initializer=initialize_nano_worker, initargs=(job,))


def get_nano_pool(job, workers):
    global _nano_pool, _nano_pool_key
    key = (workers, synthesis_key(job))
    if _nano_pool is not None and _nano_pool_key != key:
        close_nano_pool()
    if _nano_pool is None:
        _nano_pool = create_nano_pool(job, workers)
        _nano_pool_key = key
    return _nano_pool


def close_nano_pool():
    global _nano_pool, _nano_pool_key
    if _nano_pool is not None:
        _nano_pool.shutdown(wait=True, cancel_futures=True)
        _nano_pool = None
    _nano_pool_key = None


def resolve_nano_runtime(job):
    job = resolve_nano_settings(job)
    if (job.get('engine') != 'vieneu_nano' or job.get('nano_requested_parallel') != 0
            or _nano_pool is None or _nano_pool_key is None or getattr(_nano_pool, '_broken', False)):
        return job
    warm_workers, warm_key = _nano_pool_key
    resources = job['nano_resources']
    memory = resources['available_memory_bytes']
    processes = getattr(_nano_pool, '_processes', None) or {}
    fully_started = len(processes) == warm_workers and all(process.is_alive() for process in processes.values())
    if (warm_key == synthesis_key(job) and warm_workers * job['nano_threads'] <= resources['cpu_budget']
            and fully_started and memory is not None and memory >= RESERVED_BYTES):
        # Available RAM already excludes these loaded models. Reusing their
        # existing processes needs no second model allocation; counting them
        # again would reduce concurrency on every repeated automatic job.
        job = {**job, 'nano_parallel': warm_workers,
               'nano_resources': {**resources, 'workers': warm_workers, 'reused_warm_pool': True}}
    return job


class EmptyVoiceError(ValueError):
    pass


def valid_checkpoint(part):
    """Validate PCM checkpoints in bounded memory, including leading silence."""
    try:
        with wave.open(str(part)) as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24000):
                return False
            while block := audio.readframes(65536):
                if any(block):
                    return True
    except (OSError, wave.Error, EOFError):
        pass
    return False


def prepare_checkpoints(job, segments, work):
    # Concurrency and thread counts may change on resume without discarding
    # completed audio. Text, voice, model quality and audible transforms may not.
    settings = {key: job.get(key) for key in ('engine', 'voice_id', 'speaker', 'language', 'quality', 'nano_steps', 'nano_backend', 'speed', 'delivery')}
    if job.get('voice_id') and not job.get('speaker') and job.get('engine') in {'vieneu_nano', 'vieneu', 'qwen_clone'}:
        settings['reference'] = synthesis_key(job)[-3:]
    payload = {'schema': 1, 'settings': settings, 'segments': [(s.text, s.pause, s.emphasis, s.cue) for s in segments]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    manifest = work / 'checkpoints.json'
    try:
        previous = json.loads(manifest.read_text(encoding='utf-8')).get('sha256')
    except (OSError, ValueError, AttributeError):
        previous = None
    if previous != digest:
        # Only our numbered generated chunks are invalidated. Other job files
        # and user files are untouched. Legacy jobs are rebuilt once because
        # their older checkpoints did not record the text/settings they contain.
        for part in work.glob('[0-9][0-9][0-9][0-9][0-9][0-9].wav'):
            part.unlink()
        write_json_atomic(manifest, {'schema': 1, 'sha256': digest})


def prepare_chunk(job, segment, index, work, synthesize=None):
    from narration import validate_voice_text
    import soundfile as sf
    import numpy as np
    label=f'Câu SRT {segment.cue+1}' if job.get('input_format')=='srt' else f'Đoạn {index+1}'
    validate_voice_text(segment.text,job.get('engine'),label)
    work = Path(work)
    part = work / f'{index:06d}.wav'
    if part.exists():
        if valid_checkpoint(part):
            return
        part.unlink()
    custom=synthesize is not None
    raw = work / f'raw-{index:06d}.wav'
    temporary = work / f'normalized-{index:06d}.wav'
    profile_speed = PROFILES[job.get('delivery', 'natural')][0]
    tempo = job['speed'] * profile_speed * (0.94 if segment.emphasis else 1)
    gain = 1.12 if segment.emphasis else 1
    for attempt in range(3):
        if (work / 'cancel.flag').exists():raise InterruptedError('Tác vụ đã dừng.')
        raw.unlink(missing_ok=True);temporary.unlink(missing_ok=True)
        if not custom:
            settings={**job,'nano_steps':max(16,job.get('nano_steps',8))} if attempt==2 and job.get('engine')=='vieneu_nano' else job
            synthesize=get_synthesizer(settings)
        try:
            synthesize(segment.text,raw)
            if not raw.is_file() or sf.info(str(raw)).frames==0:raise EmptyVoiceError('Model không tạo mẫu âm thanh.')
            normalize_audio(raw, temporary, tempo, gain)
            with wave.open(str(temporary)) as audio:
                samples=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2')
            if not len(samples) or not np.any(samples):raise EmptyVoiceError('Âm thanh rỗng hoặc chỉ có im lặng.')
        except EmptyVoiceError:
            if attempt<2:continue
            excerpt=segment.text[:100].replace('\n',' ')
            raise ValueError(f'{label}: giọng {job.get("speaker") or job.get("engine")} vẫn không tạo được âm thanh sau 3 lần thử. Lời: “{excerpt}”. Kiểm tra ngôn ngữ, sửa câu hoặc chọn giọng khác. Không bỏ qua câu này.') from None
        finally:
            raw.unlink(missing_ok=True)
        temporary.replace(part)
        return


def render(job, synthesize=None):
    global _cached_synth, _cached_key
    started = time.monotonic()
    if job.get('video_id'):
        raise ValueError('Gói này chỉ tạo âm thanh; không xử lý video.')
    job = resolve_nano_runtime(job)
    workers = job.get('nano_parallel', 1)
    parallel = job.get('engine') == 'vieneu_nano' and workers > 1 and synthesize is None
    if not parallel:
        close_nano_pool()
    elif _cached_synth is not None:
        _cached_synth = None
        _cached_key = None
        gc.collect()
    runtime_fields = {'nano_parallel': workers if job.get('engine') == 'vieneu_nano' else None,
                      'nano_threads': job.get('nano_threads') if job.get('engine') == 'vieneu_nano' else None,
                      'nano_resources': job.get('nano_resources')}
    work = DATA / 'parts' / job['id']
    work.mkdir(parents=True, exist_ok=True)
    segments = plan_segments(job)
    if not any(s.text for s in segments):
        raise ValueError('Không có nội dung đọc sau khi xử lý ký hiệu nhấn/nghỉ.')
    prepare_checkpoints(job, segments, work)
    maximum = job.get('max_minutes', 180) * 60
    from subtitles import parse_srt, export_srt
    cues = parse_srt(job['text']) if job.get('input_format') == 'srt' else None
    exact_timing = bool(cues) and job.get('timing_mode') == 'exact'
    target_frames = None
    if exact_timing:
        from timeline_audio import timeline_frames
        target_frames = timeline_frames(cues, job.get('timeline_seconds'), maximum)
    assembly = work / 'assembled.wav'
    writer = PCMWriter(assembly, max_seconds=maximum)
    write_state(work / 'progress.json', {**runtime_fields, 'completed': 0, 'total': len(segments), 'progress': 0, 'phase': 'Chuẩn bị mô hình; lần đầu có thể chậm hơn'})
    completed = 0
    clipped = False
    futures = {}
    next_submit = 0
    synthesized_seconds = 0.0
    reused_seconds = 0.0
    reused_chunks = 0
    checkpoint_indices = set()
    payload = {key: value for key, value in job.items() if key != 'text'}
    profile_speed, default_pause = PROFILES[job.get('delivery', 'natural')]
    gap = job.get('paragraph_pause', default_pause)
    timed = []
    alignment=[]
    def sync_report():
        if not exact_timing:
            return None
        requested = job.get('timeline_seconds')
        if requested is None:
            requested = cues[-1]['end']
        actual_seconds = writer.frames / writer.rate
        errors = [abs(actual_seconds - requested) * 1000]
        for entry in alignment:
            if entry['status'] == 'matched':
                errors.extend((abs(entry['start_frame'] / writer.rate - entry['start']) * 1000,
                               abs(entry['end_frame'] / writer.rate - entry['end']) * 1000))
        matched = sum(entry['status'] == 'matched' for entry in alignment)
        speech_seconds = sum(entry['spoken_end'] - entry['spoken_start'] for entry in alignment if entry['status'] == 'matched')
        return {'mode': 'exact', 'target_seconds': requested, 'actual_seconds': actual_seconds,
                'max_error_ms': round(max(errors), 6), 'matched_cues': matched,
                'total_cues': len(cues), 'complete': completed == len(segments) and matched == len(cues) and not clipped and writer.frames == target_frames,
                'fitted_audio_seconds': round(speech_seconds, 6),
                'padding_seconds': round(max(0, actual_seconds - speech_seconds), 6),
                'sample_rate': writer.rate, 'format': job['format'],
                'precision': 'PCM sample' if job['format'] == 'wav' else 'gapless decoded PCM; MP3 packet duration may include encoder padding'}
    def save_alignment(sync_ok=False,failed=None):
        write_state(work/'alignment.json',{'cues':alignment,'sync_ok':sync_ok,'failed_cue':failed,
                    'mode':'exact' if exact_timing else job.get('cue_fit','strict'),
                    'max_tempo':job.get('max_cue_tempo',2.0 if exact_timing else 1.5),
                    'min_tempo':job.get('min_cue_tempo',.65) if exact_timing else None,
                    'target_audio_seconds':target_frames / writer.rate if target_frames is not None else None,
                    'actual_audio_seconds':writer.frames / writer.rate, 'sync_report':sync_report()})
    if cues:save_alignment()
    cue_writer = None
    cue_path = work / 'cue.wav'
    progress_limit = 90
    def schedule_chunks():
        nonlocal next_submit
        # A second bounded wave keeps ready processes busy when an earlier
        # (longer) chunk delays ordered assembly. Results stay on disk; futures
        # only return None. Scan past pauses without occupying queue slots.
        lookahead = workers * NANO_LOOKAHEAD_PER_WORKER
        while next_submit < len(segments) and len(futures) < lookahead:
            ahead = next_submit
            next_submit += 1
            candidate = segments[ahead]
            if not candidate.text:
                continue
            if valid_checkpoint(work / f'{ahead:06d}.wav'):
                checkpoint_indices.add(ahead)
                continue
            futures[ahead] = get_nano_pool(payload, workers).submit(prepare_chunk, payload, candidate, ahead, str(work))

    try:
        for index, segment in enumerate(segments):
            if (work / 'cancel.flag').exists():
                raise InterruptedError('Tác vụ đã dừng; các đoạn đã tạo được giữ để tiếp tục.')
            if parallel:
                schedule_chunks()
            segment_start = writer.frames / writer.rate
            if cues and (index == 0 or segment.cue != segments[index-1].cue):
                cue_writer = PCMWriter(cue_path, max_seconds=10800)
            target_writer = cue_writer if cues else writer
            if segment.text:
                part = work / f'{index:06d}.wav'
                reused = index in checkpoint_indices if parallel else valid_checkpoint(part)
                if index in futures:
                    futures.pop(index).result()
                else:
                    prepare_chunk(job, segment, index, work, synthesize)
                with wave.open(str(part)) as part_audio:
                    part_seconds = part_audio.getnframes() / part_audio.getframerate()
                synthesized_seconds += part_seconds
                if reused:
                    reused_chunks += 1
                    reused_seconds += part_seconds
                clipped = target_writer.append(part)
                if exact_timing and clipped:
                    raise ValueError(f'Câu {segment.cue + 1}: lời đọc vượt giới hạn xử lý; tool không cắt mất lời.')
                spoken_end = writer.frames/writer.rate
                completed = index + 1
                if not clipped:
                    if not cues:
                        writer.silence(gap)
            else:
                target_writer.silence(segment.pause)
                completed = index + 1
            if cues and (index+1 == len(segments) or segments[index+1].cue != segment.cue):
                cue_writer.close()
                cue_writer = None
                cue = cues[segment.cue]
                if exact_timing:
                    from timeline_audio import fit_cue, fill_to_frame
                    start_frame = round(cue['start'] * writer.rate)
                    end_frame = round(cue['end'] * writer.rate)
                    fitted = work / 'cue-fit.wav'
                    with wave.open(str(cue_path)) as cue_audio:
                        actual = cue_audio.getnframes() / cue_audio.getframerate()
                    try:
                        fit = fit_cue(cue_path, fitted, end_frame - start_frame,
                                      min_tempo=job.get('min_cue_tempo', .65),
                                      max_tempo=job.get('max_cue_tempo', 2.0),
                                      cancel_flag=work / 'cancel.flag', cue_number=segment.cue + 1)
                    except ValueError:
                        alignment.append({'cue': segment.cue + 1, 'start': cue['start'], 'end': cue['end'],
                                          'raw_seconds': round(actual, 5), 'status': 'too_long'})
                        save_alignment(failed=segment.cue + 1)
                        raise
                    fill_to_frame(writer, start_frame)
                    if writer.append(fitted):
                        raise ValueError(f'Câu {segment.cue + 1}: âm thanh vượt giới hạn xuất; tool không cắt lời.')
                    spoken_end_frame = writer.frames
                    fill_to_frame(writer, end_frame)
                    alignment.append({'cue': segment.cue + 1, 'start': cue['start'], 'end': cue['end'],
                                      'start_frame': start_frame, 'end_frame': end_frame,
                                      'raw_seconds': round(actual, 5),
                                      'spoken_start': start_frame / writer.rate,
                                      'spoken_end': spoken_end_frame / writer.rate,
                                      'tempo': round(fit['tempo'], 6),
                                      'padding_seconds': fit['padding_frames'] / writer.rate,
                                      'status': 'matched'})
                    if len(alignment) % 16 == 0 or len(alignment) == len(cues):
                        save_alignment()
                else:
                    original_end=cue['end']
                    boundary=(cues[segment.cue+1]['start'] if segment.cue+1<len(cues) else (job.get('timeline_seconds') or original_end))
                    available=(max(original_end,boundary) if job.get('cue_fit')=='gap' else original_end)-cue['start']
                    with wave.open(str(cue_path)) as cue_audio:
                        actual = cue_audio.getnframes()/cue_audio.getframerate()
                    maximum_tempo=job.get('max_cue_tempo',1.5)
                    applied_tempo=1.0
                    if actual > available:
                        ratio = actual/available
                        if ratio > maximum_tempo:
                            alignment.append({'cue':segment.cue+1,'start':cue['start'],'end':original_end,'available':round(available,3),'raw_seconds':round(actual,3),'status':'too_long','required_tempo':round(ratio,3)})
                            save_alignment(failed=segment.cue+1)
                            raise ValueError(f'Câu SRT {segment.cue+1} đọc quá dài ({actual:.2f}s cho ô {available:.2f}s). Nới mốc, rút ngắn lời hoặc chọn nhịp nhanh hơn; không cắt mất lời.')
                        fitted = work / 'cue-fit.wav'
                        tempo = min(maximum_tempo, ratio*1.002)
                        for attempt in range(5):
                            if (work / 'cancel.flag').exists():
                                raise InterruptedError('Tác vụ đã dừng.')
                            normalize_audio(cue_path, fitted, tempo, 1)
                            with wave.open(str(fitted)) as fitted_audio:
                                fitted_seconds = fitted_audio.getnframes()/fitted_audio.getframerate()
                            if fitted_seconds <= available+.00001:
                                fitted.replace(cue_path)
                                applied_tempo=tempo
                                break
                            if tempo >= maximum_tempo or attempt == 4:
                                alignment.append({'cue':segment.cue+1,'start':cue['start'],'end':original_end,'available':round(available,3),'raw_seconds':round(actual,3),'status':'too_long','required_tempo':round(ratio,3)})
                                save_alignment(failed=segment.cue+1)
                                raise ValueError(f'Câu SRT {segment.cue+1} vẫn vượt ô ở mức căn nhịp tối đa; hãy nới mốc thời gian.')
                            # atempo has small frame/window rounding differences. Refit the
                            # original cue, never cut words or compound tempo transforms.
                            tempo = min(maximum_tempo, tempo*fitted_seconds/available*1.005)
                    if job.get('cue_fit')=='gap':
                        with wave.open(str(cue_path)) as fitted_audio:spoken_seconds=fitted_audio.getnframes()/fitted_audio.getframerate()
                        cue['end']=round(min(boundary,max(original_end,cue['start']+spoken_seconds)),3)
                    writer.silence(max(0, cue['start']-writer.frames/writer.rate))
                    actual_start=writer.frames/writer.rate
                    clipped = writer.append(cue_path) or clipped
                    actual_end=writer.frames/writer.rate
                    alignment.append({'cue':segment.cue+1,'start':cue['start'],'end':cue['end'],'raw_seconds':round(actual,3),'spoken_start':round(actual_start,5),'spoken_end':round(actual_end,5),'tempo':round(applied_tempo,4),'status':'matched' if abs(actual_start-cue['start'])<=.001 and actual_end<=cue['end']+.001 and not clipped else 'overflow'})
                    if len(alignment)%16==0 or len(alignment)==len(cues):save_alignment(sync_ok=all(c['status']=='matched' for c in alignment) and len(alignment)==len(cues))
                    writer.silence(max(0, cue['end']-writer.frames/writer.rate))
            elif not cues and segment.text:
                timed.append({'start': segment_start, 'end': spoken_end, 'text': segment.text})
            duration = writer.frames / writer.rate
            elapsed = time.monotonic() - started
            write_state(work / 'progress.json', {**runtime_fields, 'completed': completed, 'total': len(segments), 'audio_seconds': duration, 'synthesized_audio_seconds': synthesized_seconds, 'reused_chunks': reused_chunks, 'reused_audio_seconds': reused_seconds, 'elapsed_seconds': round(elapsed, 1), 'progress': min(progress_limit, round(progress_limit * completed / len(segments))), 'phase': f'Đã xử lý {completed}/{len(segments)} đoạn'})
            if writer.frames >= writer.limit:
                clipped = completed < len(segments) or clipped
                break
        if exact_timing:
            from timeline_audio import fill_to_frame
            if completed != len(segments):
                raise ValueError('Chưa đọc hết lời thoại; tool không xuất bản căn thời gian thiếu câu.')
            fill_to_frame(writer, target_frames)
            save_alignment(sync_ok=len(alignment) == len(cues) and all(c['status'] == 'matched' for c in alignment))
    finally:
        failure = sys.exc_info()[1]
        failed = failure is not None
        if cue_writer is not None:
            cue_writer.close()
        writer.close()
        for future in futures.values():
            if not future.cancel():
                try:
                    future.result()
                except Exception:
                    # Keep the original failure/cancellation. Errors in unused
                    # lookahead after the duration limit do not fail the output.
                    if not failed and not clipped:
                        raise
        if isinstance(failure, BrokenProcessPool):
            # A failed initializer or a crashed child cannot serve the next
            # queued job, even after the user fixes missing model files.
            close_nano_pool()
    if (work / 'cancel.flag').exists():
        raise InterruptedError('Tác vụ đã dừng.')
    destination = DATA / 'audio' / f"{job['id']}.{job['format']}"
    pending = work / ('finished.' + job['format'])
    write_state(work / 'progress.json', {**runtime_fields, 'completed': completed, 'total': len(segments), 'progress': progress_limit, 'phase': 'Đang xuất âm thanh'})
    if job['format'] == 'wav':
        assembly.replace(pending)
    else:
        from audio_processing import run_ffmpeg
        run_ffmpeg(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(assembly), '-codec:a', 'libmp3lame', '-b:a', '192k', '-y', str(pending)], work, writer.frames/writer.rate, progress_limit, 99, 'Đang xuất MP3', timeout=3600)
    pending.replace(destination)
    assembly.unlink(missing_ok=True)
    subtitle_text = export_srt(cues if cues else timed)
    (DATA / 'audio' / (job['id'] + '.srt')).write_text(subtitle_text, encoding='utf-8')
    write_state(work / 'result.json', {**runtime_fields, 'audio_seconds': writer.frames / writer.rate, 'synthesized_audio_seconds': round(synthesized_seconds, 5), 'reused_chunks': reused_chunks, 'reused_audio_seconds': round(reused_seconds, 5), 'duration_limited': clipped, 'timing_mode': 'exact' if exact_timing else job.get('timing_mode', 'legacy'), 'target_audio_seconds': target_frames / writer.rate if target_frames is not None else None, 'sync_ok': exact_timing and not clipped and writer.frames == target_frames, 'sync_report': sync_report(), 'completed': completed, 'total': len(segments), 'progress': 100, 'processing_seconds': round(time.monotonic()-started, 3)})


def voice_error(exc):
    if isinstance(exc,ValueError):return str(exc)
    if isinstance(exc,ModuleNotFoundError):return f'Thiếu thư viện giọng {exc.name}. Dùng gói Portable đầy đủ hoặc tải lại model trong tool.'
    if isinstance(exc,MemoryError) or 'out of memory' in str(exc).lower():return 'Không đủ RAM/VRAM để nạp giọng. Chọn Nano Việt hoặc giọng Windows; đóng bớt ứng dụng rồi tạo lại.'
    if isinstance(exc,FileNotFoundError):return 'Thiếu tệp mô hình hoặc công cụ âm thanh. Tải model giọng đã chọn hoặc giải nén đầy đủ gói Portable.'
    return f'Không tạo được voice ({type(exc).__name__}). Giữ cửa sổ tool mở và kiểm tra model giọng đã chọn.'


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
        user_error = None
        with (DATA / 'jobs' / (job['id'] + '.log')).open('a', encoding='utf-8') as errors:
            try:
                with contextlib.redirect_stderr(errors):
                    render(job)
            except Exception as exc:
                user_error = voice_error(exc)
                code = 1
                traceback.print_exc(file=errors)
        write_state(work / 'worker-done.json', {'code': code, 'user_error': user_error})


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--serve']:
            serve()
        else:
            render(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    finally:
        close_nano_pool()
