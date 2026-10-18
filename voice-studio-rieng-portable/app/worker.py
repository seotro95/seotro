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

from state_io import write_json_atomic,write_progress
from narration import PCMWriter, PROFILES, plan_segments
from cue_audio import atempo_filter, fit_cue_audio

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
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(raw), '-vn', '-ac', '1', '-ar', '24000', '-af', f'{atempo_filter(tempo)},volume={gain},alimiter=limit=0.95', '-codec:a', 'pcm_s16le', '-y', str(temporary)], check=True, timeout=120)


_nano_pool = None


def close_nano_pool():
    global _nano_pool
    if _nano_pool is not None:
        _nano_pool.shutdown(wait=True, cancel_futures=True)
        _nano_pool = None


class EmptyVoiceError(ValueError):
    pass


def prepare_chunk(job, segment, index, work, synthesize=None):
    from narration import validate_voice_text
    import soundfile as sf
    import numpy as np
    label=f'Câu SRT {segment.cue+1}' if job.get('input_format')=='srt' else f'Đoạn {index+1}'
    validate_voice_text(segment.text,job.get('engine'),label)
    work = Path(work)
    part = work / f'{index:06d}.wav'
    if part.exists():
        try:
            with wave.open(str(part)) as audio:
                if audio.getnframes()>0 and any(audio.readframes(audio.getnframes())):return
        except (OSError,wave.Error,EOFError):pass
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
    global _nano_pool, _cached_synth, _cached_key
    if job.get('video_id'):
        raise ValueError('Gói này chỉ tạo âm thanh; không xử lý video.')
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
    maximum = job.get('max_minutes', 1440) * 60
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
    from subtitles import parse_srt, export_srt
    cues = parse_srt(job['text']) if job.get('input_format') == 'srt' else None
    timed = []
    alignment=[]
    def save_alignment(sync_ok=False,failed=None):
        write_state(work/'alignment.json',{'cues':alignment,'sync_ok':sync_ok,'failed_cue':failed,'mode':job.get('cue_fit','strict'),'max_tempo':job.get('max_cue_tempo',1.5)})
    if cues:save_alignment()
    cue_writer = None
    cue_path = work / 'cue.wav'
    progress_limit = 90
    try:
        for index, segment in enumerate(segments):
            if (work / 'cancel.flag').exists():
                raise InterruptedError('Tác vụ đã dừng; các đoạn đã tạo được giữ để tiếp tục.')
            if parallel:
                for ahead in range(index, min(index+2, len(segments))):
                    candidate = segments[ahead]
                    if candidate.text and ahead not in futures:
                        if _nano_pool is None:
                            _nano_pool = ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn'))
                        futures[ahead] = _nano_pool.submit(prepare_chunk, payload, candidate, ahead, str(work))
            segment_start = writer.frames / writer.rate
            if cues and (index == 0 or segment.cue != segments[index-1].cue):
                cue_writer = PCMWriter(cue_path, max_seconds=86400)
            target_writer = cue_writer if cues else writer
            if segment.text:
                part = work / f'{index:06d}.wav'
                if index in futures:
                    futures.pop(index).result()
                else:
                    prepare_chunk(job, segment, index, work, synthesize)
                clipped = target_writer.append(part) or clipped
                if cues and clipped:
                    raise ValueError(f'Câu SRT {segment.cue+1} có lời đọc vượt giới hạn WAV tạm; chia câu trước khi tạo lại. Không xuất câu bị cắt lời.')
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
                original_end=cue['end']
                boundary=(cues[segment.cue+1]['start'] if segment.cue+1<len(cues) else job.get('timeline_seconds',original_end))
                available=(max(original_end,boundary) if job.get('cue_fit')=='gap' else original_end)-cue['start']
                with wave.open(str(cue_path)) as cue_audio:
                    actual = cue_audio.getnframes()/cue_audio.getframerate()
                maximum_tempo=job.get('max_cue_tempo',1.5)
                applied_tempo=1.0
                fit_details = None
                if job.get('cue_fit') == 'auto':
                    target_frames=round(cue['end']*writer.rate)-round(cue['start']*writer.rate)
                    try:
                        fit_details=fit_cue_audio(cue_path,target_frames,work/'cancel.flag')
                    except ValueError as exc:
                        alignment.append({'cue':segment.cue+1,'start':cue['start'],'end':original_end,'available':round(available,3),'raw_seconds':round(actual,3),'status':'fit_failed','error':str(exc)})
                        save_alignment(failed=segment.cue+1)
                        raise ValueError(f'Câu SRT {segment.cue+1}: {exc}') from exc
                    applied_tempo=fit_details['tempo']
                elif actual > available:
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
                matched={'cue':segment.cue+1,'start':cue['start'],'end':cue['end'],'raw_seconds':round(actual,3),'spoken_start':round(actual_start,5),'spoken_end':round(actual_end,5),'tempo':round(applied_tempo,4),'status':'matched' if abs(actual_start-cue['start'])<=.001 and actual_end<=cue['end']+.001 and not clipped else 'overflow'}
                if fit_details is not None:
                    matched.update(auto_fitted=fit_details['fitted'],trimmed_silence_seconds=round(fit_details['trimmed_frames']/writer.rate,6))
                    if applied_tempo > 2:
                        matched['warning']='fast_tempo'
                alignment.append(matched)
                if len(alignment)%16==0 or len(alignment)==len(cues):save_alignment(sync_ok=all(c['status']=='matched' for c in alignment) and len(alignment)==len(cues))
                writer.silence(max(0, cue['end']-writer.frames/writer.rate))
            elif not cues and segment.text:
                timed.append({'start': segment_start, 'end': spoken_end, 'text': segment.text})
            duration = writer.frames / writer.rate
            elapsed = time.monotonic() - started
            write_state(work / 'progress.json', {'completed': completed, 'total': len(segments), 'audio_seconds': duration, 'elapsed_seconds': round(elapsed, 1), 'progress': min(progress_limit, round(progress_limit * completed / len(segments))), 'phase': f'Đã xử lý {completed}/{len(segments)} đoạn'})
            if writer.frames >= writer.limit:
                clipped = completed < len(segments) or clipped
                break
    finally:
        if cue_writer is not None:
            cue_writer.close()
        writer.close()
        for future in futures.values():
            if not future.cancel():
                future.result()
    if (work / 'cancel.flag').exists():
        raise InterruptedError('Tác vụ đã dừng.')
    if clipped or completed != len(segments):
        raise ValueError('Lời đọc vượt giới hạn thời lượng. Chia tệp hoặc tăng giới hạn rồi tạo lại; không xuất bản thu thiếu lời.')
    if cues and (len(alignment) != len(cues) or not all(c['status'] == 'matched' for c in alignment) or writer.frames != round(cues[-1]['end'] * writer.rate)):
        raise ValueError('Voice chưa khớp đầy đủ mốc phụ đề; không xuất bản thu sai thời gian.')
    destination = DATA / 'audio' / f"{job['id']}.{job['format']}"
    pending = work / ('finished.' + job['format'])
    write_state(work / 'progress.json', {'completed': completed, 'total': len(segments), 'progress': progress_limit, 'phase': 'Đang xuất âm thanh'})
    if job['format'] == 'wav':
        assembly.replace(pending)
    else:
        from audio_processing import run_ffmpeg
        run_ffmpeg(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(assembly), '-codec:a', 'libmp3lame', '-b:a', '192k', '-y', str(pending)], work, writer.frames/writer.rate, progress_limit, 99, 'Đang xuất MP3', timeout=86400)
    pending.replace(destination)
    assembly.unlink(missing_ok=True)
    subtitle_text = export_srt(cues if cues else timed)
    (DATA / 'audio' / (job['id'] + '.srt')).write_text(subtitle_text, encoding='utf-8')
    fit_warning_cues=[c['cue'] for c in alignment if c.get('warning')=='fast_tempo']
    write_state(work / 'result.json', {'audio_seconds': writer.frames / writer.rate, 'duration_limited': clipped, 'completed': completed, 'total': len(segments), 'progress': 100, 'processing_seconds': round(time.monotonic()-started, 3), 'auto_fitted_cues':sum(bool(c.get('auto_fitted')) for c in alignment), 'fit_warning_count':len(fit_warning_cues), 'fit_warning_cues':fit_warning_cues})


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
