"""Isolated local subtitle recognition, translation and logo processing."""
import asyncio
import json
import os
import sys
from pathlib import Path
from state_io import write_progress


def validate_logo(rect, meta):
    if rect is None:
        return None
    x, y, w, h = (int(rect[k]) for k in ('x', 'y', 'w', 'h'))
    if min(x, y) < 1 or min(w, h) < 2 or x+w >= meta['width'] or y+h >= meta['height']:
        raise ValueError('Vùng logo phải nằm trong khung hình, cách mép ít nhất 1 pixel.')
    return f'delogo=x={x}:y={y}:w={w}:h={h}'


def logo_filters(job,meta):
    import re
    regions=job.get('logos') or ([job['logo']] if job.get('logo') else [])
    if len(regions)>20:raise ValueError('Tối đa 20 vùng logo cùng lúc.')
    filters=[]
    for region in regions:
        mode=region.get('mode','delogo')
        if mode=='delogo':filters.append(validate_logo(region,meta))
        elif mode=='color':
            x,y,w,h=(int(region[k]) for k in ('x','y','w','h'))
            color=region.get('color','#000000')
            if x<0 or y<0 or min(w,h)<2 or x+w>meta['width'] or y+h>meta['height']:raise ValueError('Vùng màu phải nằm trong khung hình.')
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Chọn màu dạng #RRGGBB.')
            filters.append(f'drawbox=x={x}:y={y}:w={w}:h={h}:color=0x{color[1:]}:t=fill')
        else:raise ValueError('Chọn nội suy hoặc phủ màu cho vùng logo.')
    return ','.join(filters) or None


from translation import translate_cues

def run(path):
    from dubbing import run_ffmpeg, inspect_video
    from subtitles import export_srt, parse_srt
    job = json.loads(path.read_text(encoding='utf-8'))
    work = path.parent
    data = work.parent.parent
    if job['action']=='prepare_voice':
        import subprocess,importlib.util
        engine=job['engine']
        if engine not in {'qwen','qwen_clone','vieneu','vieneu_nano','vieneu_nano_clone'}:raise ValueError('Model giọng không hợp lệ.')
        def prepare_update(value,phase):
            write_progress(work/'progress.json',{'progress':value,'phase':phase})
        env=dict(os.environ,VOICE_STUDIO_DATA_DIR=str(data),HF_HOME=str(data/'models'/'cache'),HF_HUB_DISABLE_XET='1')
        if engine.startswith('qwen'):
            if importlib.util.find_spec('torch') is None:
                prepare_update(5,'Đang cài PyTorch CPU · cần Internet và vài GB dung lượng')
                subprocess.run([sys.executable,'-m','pip','install','torch==2.6.0','torchaudio==2.6.0','--index-url','https://download.pytorch.org/whl/cpu'],check=True,env=env,timeout=1800)
            prepare_update(25,'Đang cài thư viện giọng quốc tế')
            subprocess.run([sys.executable,'-m','pip','install','-r',str(Path(__file__).parent/'requirements-qwen.txt')],check=True,env=env,timeout=1800)
        prepare_update(45,'Đang tải và kiểm tra model '+engine+' · có thể mất vài phút')
        subprocess.run([sys.executable,str(Path(__file__).parent/'prepare_models.py'),engine],check=True,env=env,timeout=3600)
        prepare_update(100,'Giọng đã sẵn sàng. Chọn giọng và tạo lại.');return
    if job['action']=='translate_text':
        text=job['text']
        parts=[]
        while text:
            end=min(1500,len(text))
            if end<len(text):
                boundary=text.rfind(' ',0,end)
                if boundary>end//2:end=boundary
            parts.append(text[:end]);text=text[end:].lstrip()
        cues=parse_srt(job['text']) if job.get('input_format')=='srt' else [{'text':part} for part in parts]
        def text_update(value,phase):
            write_progress(work/'progress.json',{'progress':value,'phase':phase})
        cues=translate_cues(cues,job['target_language'],job.get('model',''),text_update,job.get('provider','ollama'),job.get('source_language','auto'))
        output=export_srt(cues) if job.get('input_format')=='srt' else '\n'.join(c['text'] for c in cues)
        if len(output)>200000:raise ValueError('Bản dịch vượt 200.000 ký tự. Chia văn bản thành các phần ngắn hơn.')
        (work/'translated.txt').write_text(output,encoding='utf-8');text_update(100,'Đã dịch xong văn bản voice');return
    meta = json.loads((data/'videos'/f"{job['video_id']}.json").read_text(encoding='utf-8'))
    source = data/'videos'/f"{job['video_id']}.source"
    meta.update(inspect_video(source))
    def update(progress, phase):
        write_progress(work/'progress.json',{'progress':progress,'phase':phase})
    if job['action'] in {'logo','render','export','preview'}:
        from video_export import scale_filter,encoder_options
        preview=job['action']=='preview'
        start=job.get('preview_start',0) if preview else 0
        seconds=min(job.get('preview_seconds',10),meta['duration']-start) if preview else meta['duration']
        vf = logo_filters(job, meta)
        filters = [vf] if vf else []
        scale,size = scale_filter(meta,job.get('export_resolution','original'))
        if scale:
            filters.append(scale)
        if job['action']=='render' or (job['action']=='preview' and job.get('cues')):
            from video_editor import validate_cues, write_ass
            cues = validate_cues(job['cues'],meta['duration'])
            if preview:cues=[{**c,'start':max(0,c['start']-start),'end':min(seconds,c['end']-start)} for c in cues if c['end']>start and c['start']<start+seconds]
            write_ass(work/'captions.ass',cues,*size,job.get('caption_style'))
            filters.append('ass=filename=captions.ass')
        if job['action']=='logo' and not vf:
            raise ValueError('Hãy chọn vùng logo trước.')
        options = ['-vf',','.join(filters),*encoder_options(job)] if filters else ['-c:v','copy']
        if preview and not filters:options=encoder_options(job)
        # Input seek avoids decoding the whole video before a short proof.
        inputs=(["-ss",str(start)] if preview else [])+['-i',str(source)]
        voice_id=(job.get('preview_voice_id') or job.get('voice_job_id')) if preview else job.get('voice_job_id')
        if voice_id:inputs+=(["-ss",str(start)] if preview and job.get('voice_job_id') else [])+['-i',str(data/'audio'/f'{voice_id}.wav')]
        if voice_id:
            options=['-filter_complex',f"[0:v]{','.join(filters) if filters else 'null'}[v];[1:a]apad=whole_dur={seconds}[a]",'-map','[v]','-map','[a]',*encoder_options(job)]
            mapping=[]
        else:mapping=['-map','0:v:0','-map','0:a?']
        run_ffmpeg(['ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe',*inputs,*mapping,*options,*(['-t',str(seconds)] if preview or voice_id else []),'-c:a','aac','-b:a','192k','-movflags','+faststart','-y',str(work/'output.mp4')],work,seconds,1,99,f'Đang tạo bản xem thử' if preview else f'Đang xuất MP4 {size[0]} × {size[1]}',cwd=work)
        (work/'result.json').write_text(json.dumps({'width':size[0],'height':size[1]}),encoding='utf-8')
        update(100,'Video đã sẵn sàng')
        return
    if job.get('srt'):
        cues = parse_srt(job['srt'])
    else:
        if not meta['has_audio']:
            raise ValueError('Video không có âm thanh để nhận dạng.')
        from recognition import recognize
        cues=recognize(source,data/'models'/'whisper-base',job,work,meta,update)
    (work/'original.srt').write_text(export_srt(cues),encoding='utf-8')
    source_language=job.get('source_language','')
    if (work/'recognition.json').exists():source_language=json.loads((work/'recognition.json').read_text(encoding='utf-8')).get('language',source_language)
    target_language=job.get('target_language','')
    if target_language and source_language.split('-')[0]!=target_language.split('-')[0]:
        cues = translate_cues(cues,target_language,job.get('model',''),update,job.get('provider','ollama'),source_language or 'auto')
    (work/'result.json').write_text(json.dumps({'source_language':source_language,'caption_language':target_language or source_language}),encoding='utf-8')
    output = export_srt(cues)
    if len(output) > 200000 or len(cues) > 10000:
        raise ValueError('Phụ đề vượt 200.000 ký tự / 10.000 câu. Chia video thành các phần ngắn hơn.')
    (work/'output.srt').write_text(output,encoding='utf-8')
    (work/'output.txt').write_text('\n'.join(c['text'] for c in cues),encoding='utf-8')
    update(100,'Phụ đề đã sẵn sàng; hãy kiểm tra trước khi lồng tiếng')


if __name__ == '__main__':
    path = Path(sys.argv[1])
    try:
        run(path)
    except Exception as exc:
        message = getattr(exc,'detail',str(exc))
        (path.parent/'error.txt').write_text(str(message),encoding='utf-8')
        raise
