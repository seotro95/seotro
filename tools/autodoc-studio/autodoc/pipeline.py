from __future__ import annotations
import csv,json,math,os,shutil
from dataclasses import asdict,dataclass
from pathlib import Path
from . import __version__
from .common import Context,binary,digest,save_json,signature,srt,valid_input
from .analysis import SemanticModel,decode_voice,inspect_videos,transcribe,visual_index
from .planner import make_plan
from .render import render_project,validate_output

@dataclass
class Settings:
    voice: str
    videos: str
    output: str
    resolution: int = 720
    language: str = 'en'
    whisper_model: str = 'base'
    embed_subtitles: bool = False
    screen_minors: bool = True
    threads: int = 2
    clip_model_path: str | None = None
    whisper_model_path: str | None = None

def run(settings: Settings,ctx: Context | None=None):
    ctx=ctx or Context();voice=valid_input(Path(settings.voice));folder=Path(settings.videos).expanduser().resolve();output=Path(settings.output).expanduser().resolve()
    if not folder.is_dir():raise ValueError('Chọn đúng thư mục video đầu vào.')
    if settings.resolution not in [720,1080]:raise ValueError('Chỉ hỗ trợ720p hoặc1080p.')
    if not 1<=settings.threads<=16:raise ValueError('Số luồng CPU không hợp lệ.')
    from .bootstrap import ensure_ffmpeg
    ensure_ffmpeg(ctx)
    binary('ffmpeg');binary('ffprobe');output.mkdir(parents=True,exist_ok=True)
    input_key=signature({'voice':str(voice),'voice_sha':digest(voice),'videos':str(folder),'settings':asdict(settings),'version':__version__})[:12]
    job=output/f'AutoDoc_{input_key}';job.mkdir(exist_ok=True)
    save_json(job/'settings.json',asdict(settings));save_json(job/'PROJECT.json',{'app':'AutoDocStudio','version':__version__,'input_voice':str(voice),'input_videos':str(folder),'originals_modified':False})
    try:
        ctx.emit(1,'Đọc voice và chuẩn bị dự án.')
        wav,duration,voice_sha=decode_voice(voice,job,ctx)
        estimate=max(150*1024**2,duration*((520000 if settings.resolution==1080 else 320000)*2+96000))
        # Once a completed movie exists we still validate it; no silent success based on file existence alone.
        if shutil.disk_usage(output).free<estimate:
            raise RuntimeError(f'Ổ xuất cần khoảng{estimate/1024**3:.1f}GBtrống cho video và cache. Chọn ổ còn dung lượng.')
        cues=transcribe(wav,job,ctx,settings.whisper_model,settings.language,settings.whisper_model_path,settings.threads)
        (job/'LOI_DOC.srt').write_text(srt(cues),encoding='utf-8-sig')
        model=SemanticModel(ctx,Path(settings.clip_model_path) if settings.clip_model_path else None,settings.threads)
        files,skipped=inspect_videos(folder,job,ctx)
        candidates,features,screen=visual_index(files,job,model,ctx)
        ctx.emit(51,'Xếp cảnh theo lời; chọn10cảnh mở đầu và giảm cảnh lặp.')
        plan=make_plan(cues,files,candidates,features,screen,model,duration,screen_minors=settings.screen_minors)
        plan['shots'][-1]['last']=True;save_json(job/'EDIT_PLAN.json',plan)
        del model
        with (job/'TIMELINE.csv').open('w',encoding='utf-8-sig',newline='') as f:
            fields=['index','start_seconds','end_seconds','source_name','source_in','semantic_score','transition','loop_source','text']
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            for row in plan['shots']:
                w.writerow({**{k:row[k] for k in fields if k in row},'start_seconds':row['start_frame']/plan['fps'],'end_seconds':row['end_frame']/plan['fps']})
        movie=render_project(plan,files,wav,job,ctx,settings.resolution,settings.embed_subtitles)
        report=validate_output(movie,wav,plan,job,ctx)
        report.update(source_audio_streams_removed=sum(f['audio_streams'] for f in files),original_voice_sha256=voice_sha,skipped_source_files=skipped,semantic_model='CLIPViT-B32quantizedONNX',transcription_model=settings.whisper_model,language=settings.language)
        save_json(job/'KIEM_TRA_VIDEO.json',report);save_json(job/'STATUS.json',{'status':'completed','output':str(movie),'report':'KIEM_TRA_VIDEO.json'})
        # Recoverable caches are separate from all source and delivery files.
        ctx.emit(100,'Hoàn tất! Video đã kiểm tra thời lượng,giải mã và đồng bộ voice.')
        return {'output':str(movie),'project':str(job),'report':report}
    except Exception as exc:
        save_json(job/'STATUS.json',{'status':'interrupted_or_failed','error':str(exc),'can_resume':True})
        raise
