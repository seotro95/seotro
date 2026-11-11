from __future__ import annotations
import json,time
from pathlib import Path
from .common import Context,digest,signature,save_json,valid_input
from .project import options,reindex,save,validate_project,change_fps
from .subtitles import read_srt,read_txt,align_txt,export,validate

def prepare(voice,media,output,settings=None,ctx=None):
    from .bootstrap import ensure_ffmpeg
    from .analysis import decode_voice,transcribe,SemanticModel
    from .media import inspect,index
    from .planner import make_plan
    ctx=ctx or Context();settings=options(settings);voice=valid_input(Path(voice));media=Path(media).resolve();output=Path(output).resolve()
    if not media.is_dir():raise ValueError('Chọn thư mục chứa ảnh/video.')
    ensure_ffmpeg(ctx);output.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    key=signature({'voice':digest(voice),'media':str(media),'subtitles':digest(Path(settings['subtitle_path'])) if settings['subtitle_path'] else '', 'quality':settings['quality'],'model':settings['whisper_model'],'language':settings['language'],'screen_minors':settings['screen_minors']})[:12]
    job=output/f'AutoDoc2_{key}';job.mkdir(exist_ok=True)
    save_json(job/'PROJECT.json',{'app':'AutoDocStudio','version':'2.0.1','originals_modified':False})
    wav,duration,voice_sha=decode_voice(voice,job,ctx);sub=Path(settings['subtitle_path']) if settings['subtitle_path'] else None
    skipped_asr=bool(sub and sub.suffix.lower()=='.srt');ratio=None
    if skipped_asr:cues=read_srt(sub,duration);ctx.emit(13,'Dùng mốc SRT: bỏ qua nhận dạng voice.')
    else:
        recognized=transcribe(wav,job,ctx,settings['whisper_model'],settings['language'],settings['whisper_model_path'],settings['threads'],settings['quality']=='fast')
        if sub:
            if sub.suffix.lower()!='.txt':raise ValueError('Phụ đề đầu vào cần TXT hoặc SRT.')
            cues,ratio=align_txt(read_txt(sub),recognized,duration)
        else:cues=recognized
    files,skipped=inspect(media,job,ctx,excluded=[settings['logo_path']]);model=SemanticModel(ctx,Path(settings['clip_model_path']) if settings['clip_model_path'] else None,settings['threads'])
    candidates,features,scores=index(files,job,model,ctx,1 if settings['quality']=='fast' else 3)
    ctx.emit(51,'Tự xếp cảnh theo lời; chọn 10 cảnh mở đầu khi đủ nguồn.')
    plan=make_plan(cues,files,candidates,features,scores,model,duration,fps=settings['fps'],screen_minors=settings['screen_minors']);del model
    for s in plan['shots']:
        image=files[s['source_id']]['kind']=='image'
        s.update(effect='zoom_in' if image and settings['auto_effects'] else 'none',speed=1.,focus_x=.5,focus_y=.5)
        if not settings['auto_transitions']:s['transition']='cut'
    if ratio is not None and ratio<.55:plan['warnings'].append(f'TXT chỉ khớp {ratio:.0%} từ nhận dạng; hãy sửa mốc phụ đề trên tool.')
    p={'schema':'autodoc-project-2','version':'2.0.1','job':str(job),'project_file':str(job/'project.autodoc.json'),'voice_source':str(voice),'voice_sha256':voice_sha,'voice_wav':str(wav),'media_folder':str(media),'settings':settings,'files':files,'cues':validate(cues,duration),'plan':plan,'skipped_files':skipped,'asr_skipped':skipped_asr,'txt_alignment_ratio':ratio,'prepare_seconds':round(time.monotonic()-start,3)}
    reindex(p);save(p);export(p['cues'],job/'LOI_DOC.srt');save_json(job/'EDIT_PLAN.json',plan);ctx.emit(54,'Dự án sẵn sàng: chọn cảnh để xem/sửa, sau đó bấm Xuất video.');return p

def run(voice,media,output,settings=None,ctx=None,prepare_only=False):
    p=prepare(voice,media,output,settings,ctx)
    if prepare_only:return {'project':p['project_file'],'prepared':True,'asr_skipped':p['asr_skipped']}
    from .render import export_movie
    return export_movie(p,Path(p['job'])/'VIDEO_HOAN_CHINH.mp4',ctx or Context())
