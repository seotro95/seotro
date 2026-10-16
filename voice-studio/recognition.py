"""Cache immutable-video recognition so retries/translations avoid repeating ASR."""
import hashlib
import json
import os
from pathlib import Path


def recognize(source,model_path,job,work,meta,update):
    from dubbing import run_ffmpeg
    from subtitles import parse_srt,export_srt
    if not (model_path/'model.bin').exists():raise ValueError('Chưa tải model nhận dạng Whisper. Dùng bản Portable mới hoặc chạy download_subtitle_model.bat.')
    signature={'video':str(source),'size':source.stat().st_size,'mtime':source.stat().st_mtime_ns,'model':(model_path/'model.bin').stat().st_mtime_ns,'language':job.get('source_language','').split('-')[0],'accurate':job.get('accurate',True)}
    cache=source.parent.parent/'asr_cache'/source.stem/f'{hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()}.srt'
    if cache.exists():
        try:
            cues=parse_srt(cache.read_text(encoding='utf-8'));update(59,'Đã dùng lại phụ đề nhận dạng trước đó');return cues
        except (ValueError,OSError):pass
    run_ffmpeg(['ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe','-i',str(source),'-vn','-ac','1','-ar','16000','-y',str(work/'speech.wav')],work,meta['duration'],1,5,'Đang tách âm thanh')
    update(5,'Đang nạp mô hình nhận dạng Whisper')
    from faster_whisper import WhisperModel
    model=WhisperModel(str(model_path),device='cpu',compute_type='int8',cpu_threads=min(4,os.cpu_count() or 2))
    segments,_=model.transcribe(str(work/'speech.wav'),language=signature['language'] or None,beam_size=5 if signature['accurate'] else 1,vad_filter=True,condition_on_previous_text=False)
    cues=[]
    for segment in segments:
        start=max(cues[-1]['end'] if cues else 0,round(segment.start,3));end=min(meta['duration'],round(segment.end,3))
        if segment.text.strip() and end>start:cues.append({'start':start,'end':end,'text':segment.text.strip()})
        update(min(59,5+int(54*segment.end/meta['duration'])),'Đang nhận dạng lời nói')
    if not cues:raise ValueError('Không nhận dạng được lời nói. Chọn đúng ngôn ngữ gốc hoặc kiểm tra âm thanh.')
    try:
        cache.parent.mkdir(parents=True,exist_ok=True)
        temp=work/'recognition-cache.tmp';temp.write_text(export_srt(cues),encoding='utf-8');temp.replace(cache)
    except OSError:
        pass  # An optional cache must never prevent a successful subtitle job.
    return cues
