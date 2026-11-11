from __future__ import annotations
import copy,json,time
from pathlib import Path
from .common import Context,digest,signature,save_json,valid_input
from .project import options,reindex,save,validate_project,change_fps
from .subtitles import read_srt,read_txt,align_txt,export,validate

def prepare(voice,media,output,settings=None,ctx=None):
    from .bootstrap import ensure_ffmpeg
    from .analysis import decode_voice,transcribe,SemanticModel
    from .media import inspect,index
    from .planner import make_plan,words_for
    from .languages import visual_reference
    ctx=ctx or Context();settings=options(settings);voice=valid_input(Path(voice));media=Path(media).resolve();output=Path(output).resolve()
    if not media.is_dir():raise ValueError('Chọn thư mục chứa ảnh/video.')
    ensure_ffmpeg(ctx);output.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    key=signature({'voice':digest(voice),'media':str(media),'subtitles':digest(Path(settings['subtitle_path'])) if settings['subtitle_path'] else '', 'visual_script':digest(Path(settings['visual_script_path'])) if settings['visual_script_path'] else '', 'quality':settings['quality'],'model':settings['whisper_model'],'language':settings['language'],'screen_minors':settings['screen_minors'],'multilingual_matching':1})[:12]
    job=output/f'AutoDoc2_{key}';job.mkdir(exist_ok=True)
    save_json(job/'PROJECT.json',{'app':'AutoDocStudio','version':'2.2.1','originals_modified':False})
    wav,duration,voice_sha=decode_voice(voice,job,ctx);sub=Path(settings['subtitle_path']) if settings['subtitle_path'] else None
    hmong_reference_only=settings['language']=='hmn' and not sub and settings.get('visual_script_path') and Path(settings['visual_script_path']).suffix.lower()=='.srt'
    skipped_asr=bool(sub and sub.suffix.lower()=='.srt') or bool(hmong_reference_only);ratio=None
    if hmong_reference_only:cues=read_srt(settings['visual_script_path'],duration);ctx.emit(13,'Dùng SRT tham chiếu Anh đúng mốc; không nhận dạng tự động H’Mông.')
    elif skipped_asr:cues=read_srt(sub,duration);ctx.emit(13,'Dùng mốc SRT cho lời gốc.')
    else:
        if settings['language']=='hmn':raise ValueError('H’Mông cần SRT tiếng Anh đúng mốc ở ô Tham chiếu Anh; phụ đề H’Mông dùng SRT riêng, không nhận dạng TXT H’Mông bằng Whisper.')
        recognized=transcribe(wav,job,ctx,settings['whisper_model'],settings['language'],settings['whisper_model_path'],settings['threads'],settings['quality']=='fast')
        if sub:
            if sub.suffix.lower()!='.txt':raise ValueError('Phụ đề đầu vào cần TXT hoặc SRT.')
            cues,ratio=align_txt(read_txt(sub),recognized,duration)
        else:cues=recognized
    visual_cues,language_info,language_warnings=visual_reference(wav,cues,job,settings,duration,ctx,not skipped_asr)
    files,skipped=inspect(media,job,ctx,excluded=[settings['logo_path']]);model=SemanticModel(ctx,Path(settings['clip_model_path']) if settings['clip_model_path'] else None,settings['threads'])
    candidates,features,scores=index(files,job,model,ctx,1 if settings['quality']=='fast' else 3)
    ctx.emit(51,'Tự xếp cảnh theo lời; chọn 10 cảnh mở đầu khi đủ nguồn.')
    plan=make_plan(visual_cues,files,candidates,features,scores,model,duration,fps=settings['fps'],screen_minors=settings['screen_minors']);del model
    plan['warnings'].extend(language_warnings)
    if hmong_reference_only:plan['warnings'].append('Lời hiển thị/phụ đề lấy từ bản tham chiếu Anh. Muốn phụ đề H’Mông, nhập thêm SRT H’Mông đúng mốc.')
    for s in plan['shots']:
        image=files[s['source_id']]['kind']=='image'
        s.update(effect='zoom_in' if image and settings['auto_effects'] else 'none',speed=1.,focus_x=.5,focus_y=.5)
        s['visual_text']=s['text'];s['text']=words_for(cues,s['start_frame']/plan['fps'],s['end_frame']/plan['fps'])
        if not settings['auto_transitions']:s['transition']='cut'
    if ratio is not None and ratio<.55:plan['warnings'].append(f'TXT chỉ khớp {ratio:.0%} từ nhận dạng; hãy sửa mốc phụ đề trên tool.')
    p={'schema':'autodoc-project-2','version':'2.2.1','job':str(job),'project_file':str(job/'project.autodoc.json'),'voice_source':str(voice),'voice_sha256':voice_sha,'voice_wav':str(wav),'media_folder':str(media),'settings':settings,'files':files,'cues':validate(cues,duration),'plan':plan,'skipped_files':skipped,'asr_skipped':skipped_asr,'txt_alignment_ratio':ratio,'prepare_seconds':round(time.monotonic()-start,3)}
    p.update(language_info,visual_cues=validate(visual_cues,duration))
    reindex(p);save(p);export(p['cues'],job/'LOI_DOC.srt');save_json(job/'EDIT_PLAN.json',plan);ctx.emit(54,'Dự án sẵn sàng: chọn cảnh để xem/sửa, sau đó bấm Xuất video.');return p

def run(voice,media,output,settings=None,ctx=None,prepare_only=False):
    if prepare_only:
        p=prepare(voice,media,output,settings,ctx)
        return {'project':p['project_file'],'prepared':True,'asr_skipped':p['asr_skipped']}
    return automatic(voice,media,output,settings,ctx)

def next_output(folder,name,extension):
    folder=Path(folder)
    for number in range(1,100000):
        stem=name if number==1 else f'{name}_{number:03d}'
        path=folder/f'{stem}.{extension}'
        if not any(x.exists() for x in [path,path.with_name(stem+'.checking.'+extension),path.with_suffix('.qa.json'),path.with_suffix('.autodoc.json')]):return path
    raise ValueError('Quá nhiều bản xuất trùng tên. Chọn tên video khác.')

def automatic(voice,media,output,settings=None,ctx=None):
    """One uninterrupted workflow, also used by the actual GUI button."""
    from .render import export_movie
    ctx=ctx or Context();settings=options(settings);ctx.emit(0,'Tự động edit: nhận lời → chọn cảnh → dựng → xuất và lưu dự án.')
    p=prepare(voice,media,Path(output)/'TU_DONG_EDIT',settings,ctx)
    out=next_output(p['job'],settings['auto_filename'],settings['export_format'])
    ctx.emit(54,'Đã xếp cảnh; tự động xuất ngay, không cần thao tác thêm.')
    result=export_movie(p,out,ctx)
    snapshot=copy.deepcopy(p);project_path=out.with_suffix('.autodoc.json');save(snapshot,project_path)
    result.update(project=str(project_path),workflow='automatic',asr_skipped=p['asr_skipped'])
    save_json(Path(p['job'])/'AUTO_LAST_RESULT.json',result);ctx.emit(100,'Tự động edit hoàn tất. Đã lưu video, phụ đề, dự án và báo cáo kiểm tra.')
    return result
