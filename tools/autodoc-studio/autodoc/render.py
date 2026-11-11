from __future__ import annotations
import concurrent.futures,copy,json,math,os,wave
from pathlib import Path
from PIL import Image,ImageOps
from .common import Context,binary,data_dir,digest,probe,save_json,signature
from .effects import FILTERS,MOTIONS,TRANSITIONS
from .subtitles import write_ass
from .framing import dimensions

_ENCODERS={}
def source_offset(asset,offset):
    # Splitting a looped scene must continue at the same source frame, including
    # when the split point falls after one or more complete source loops.
    return max(0,float(offset))%asset['seconds'] if asset['kind']=='video' else 0

def choose_encoder(requested,ctx):
    if requested=='cpu':return 'libx264'
    key=(binary('ffmpeg'),requested)
    if key in _ENCODERS:return _ENCODERS[key]
    names=['h264_nvenc','h264_qsv','h264_amf'] if requested=='auto' else [{'nvenc':'h264_nvenc','qsv':'h264_qsv','amf':'h264_amf'}[requested]]
    for name in names:
        try:
            ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-f','lavfi','-i','color=s=128x128:r=24:d=0.1','-frames:v','1','-c:v',name,'-f','null','-'],log=data_dir()/f'encoder_{name}.log');_ENCODERS[key]=name;return name
        except RuntimeError:continue
    _ENCODERS[key]='libx264';return 'libx264'

def encoder_args(codec,quality,threads):
    q={'fast':25,'balanced':22,'quality':19}[quality]
    if codec=='h264_nvenc':return ['-c:v',codec,'-preset','p2' if quality=='fast' else 'p5','-cq',str(q),'-b:v','0']
    if codec=='h264_qsv':return ['-c:v',codec,'-preset','veryfast' if quality=='fast' else 'medium','-global_quality',str(q)]
    if codec=='h264_amf':return ['-c:v',codec,'-quality','speed' if quality=='fast' else 'quality','-rc','cqp','-qp_i',str(q),'-qp_p',str(q)]
    return ['-c:v','libx264','-preset',{'fast':'ultrafast','balanced':'veryfast','quality':'medium'}[quality],'-crf',str(q),'-threads',str(max(1,threads))]

def _file_key(path):
    p=Path(path)
    if not p.is_file():raise ValueError(f'Không tìm thấy tệp: {p}')
    s=p.stat();return (str(p.resolve()),s.st_size,s.st_mtime_ns)

def normalize_logo(settings,job):
    if not settings.get('logo_path'):return None
    key=signature(_file_key(settings['logo_path']));p=job/'logos'/f'{key[:16]}.png';p.parent.mkdir(exist_ok=True)
    if not p.exists():
        with Image.open(settings['logo_path']) as im:
            im=ImageOps.exif_transpose(im).convert('RGBA');im.thumbnail((2048,2048));im.save(p)
    return p

def _scale(label,duration,shot,asset,w,h,fps,fit):
    speed=float(shot.get('speed',1));fx=shot.get('focus_x',.5);fy=shot.get('focus_y',.5)
    vf=f'trim=duration={duration*speed},setpts=(PTS-STARTPTS)/{speed},fps={fps}'
    if fit=='contain':vf+=f',scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black'
    else:vf+=f',scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:x=(iw-ow)*{fx}:y=(ih-oh)*{fy}'
    crop=float(shot.get('crop',1))
    if crop>1:
        cw=int(w/crop)//2*2;ch=int(h/crop)//2*2;vf+=f',crop={cw}:{ch}:(iw-ow)*{fx}:(ih-oh)*{fy},scale={w}:{h}'
    effect=shot.get('effect','none')
    if effect in MOTIONS:
        count=max(2,round(duration*fps));step=.07/(count-1)
        if effect=='zoom_in':z=f'1+on*{step}'
        elif effect=='zoom_out':z=f'1.07-on*{step}'
        else:z='1.07'
        x='iw/2-iw/zoom/2';y='ih/2-ih/zoom/2'
        if effect=='pan_left':x=f'(iw-iw/zoom)*(1-on/{count-1})'
        if effect=='pan_right':x=f'(iw-iw/zoom)*on/{count-1}'
        vf+=f",zoompan=z='{z}':x='{x}':y='{y}':d=1:s={w}x{h}:fps={fps}"
    elif effect in FILTERS and FILTERS[effect]:vf+=','+FILTERS[effect]
    return f'{label}{vf},setsar=1,format=yuv420p,setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709,settb=AVTB'

def render_shot(p,item,previous,ctx,resolution=None,preview=False,codec='libx264'):
    job=Path(p['job']);settings=p['settings'];fps=p['plan']['fps'];w,h=dimensions(resolution or settings['resolution'],settings.get('aspect_ratio','16:9'));sec=item['frames']/fps
    asset=p['files'][item['source_id']];prev=p['files'][previous['source_id']] if previous else None
    logo=normalize_logo(settings,job);local_cues=[c for c in p['cues'] if c['end']>item['start_frame']/fps and c['start']<item['end_frame']/fps]
    visual_settings={k:settings[k] for k in ['fit','subtitle_mode','subtitle_style','logo_position','logo_size','logo_opacity']}
    sig=signature({'renderer':21,'item':item,'previous':previous if item['transition']!='cut' else None,'source':asset['sha256'],'prev_source':prev['sha256'] if prev else None,'size':[w,h,fps],'settings':visual_settings,'logo':_file_key(logo) if logo else None,'cues':local_cues if settings['subtitle_mode']=='burn' else None,'codec':codec,'quality':'fast' if preview else settings['quality']})
    folder=job/('preview_cache' if preview else 'renders')/sig[:18];folder.mkdir(parents=True,exist_ok=True);out=folder/'scene.mp4'
    if out.exists():return out
    cmd=[binary('ffmpeg'),'-nostdin','-hide_banner','-loglevel','error','-filter_complex_threads','1','-y'];filters=[];ninputs=0
    def add_input(a,offset):
        nonlocal ninputs
        if not Path(a['path']).is_file():raise ValueError(f'Thiếu nguồn: {a["path"]}')
        if a['kind']=='image':cmd.extend(['-loop','1','-framerate',str(fps),'-i',a['path']])
        else:cmd.extend(['-threads','1','-stream_loop','-1','-ss',str(source_offset(a,offset)),'-i',a['path']])
        idx=ninputs;ninputs+=1;return idx
    add_input(asset,item['source_in']);filters.append(_scale('[0:v]',sec,item,asset,w,h,fps,settings['fit'])+'[current]');stage='current'
    if previous and item['transition']!='cut':
        handle=min(.35,sec*.25);offset=previous['source_in']+previous['frames']/fps*previous.get('speed',1)
        idx=add_input(prev,offset);filters.append(_scale(f'[{idx}:v]',handle,previous,prev,w,h,fps,settings['fit'])+'[old]')
        trans='fade' if item['transition']=='dissolve' else item['transition']
        filters.append(f'[old][current]xfade=transition={trans}:duration={handle}:offset=0[mixed]');stage='mixed'
    if logo:
        idx=ninputs;ninputs+=1;cmd+=['-loop','1','-framerate',str(fps),'-i',str(logo)]
        lw=max(8,round(w*settings['logo_size']/100));margin=round(w*.02)
        positions={'top_left':(str(margin),str(margin)),'top_right':(f'W-w-{margin}',str(margin)),'bottom_left':(str(margin),f'H-h-{margin}'),'bottom_right':(f'W-w-{margin}',f'H-h-{margin}'),'center':('(W-w)/2','(H-h)/2')};x,y=positions[settings['logo_position']]
        filters.append(f'[{idx}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={settings["logo_opacity"]}[logo]');filters.append(f'[{stage}][logo]overlay=x={x}:y={y}:shortest=1[branded]');stage='branded'
    if settings['subtitle_mode']=='burn':
        ass=folder/'captions.ass';write_ass(ass,local_cues,w,h,settings['subtitle_style'],item['start_frame']/fps,sec)
        # Relative path and cwd avoid Windows drive-colon/filter escaping bugs.
        filters.append(f'[{stage}]ass=filename=captions.ass[captioned]');stage='captioned'
    if item.get('last'):
        fade=min(.5,sec*.3);filters.append(f'[{stage}]fade=t=out:st={sec-fade}:d={fade}[end]');stage='end'
    filters.append(f'[{stage}]trim=duration={sec},setpts=PTS-STARTPTS,format=yuv420p[final]')
    temp=folder/'pending.mp4';args=['-filter_complex',';'.join(filters),'-map','[final]','-an','-frames:v',str(item['frames']),'-r',str(fps)]
    opts=encoder_args(codec,'fast' if preview else settings['quality'],min(8,max(1,int(settings['threads']))))
    try:ctx.run(cmd+args+opts+['-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],log=folder/'render.log',cwd=folder)
    except RuntimeError:
        if codec=='libx264':raise
        ctx.run(cmd+args+encoder_args('libx264','fast',2)+['-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],log=folder/'fallback.log',cwd=folder);codec='libx264'
    v=next(x for x in probe(temp,ctx)['streams'] if x['codec_type']=='video')
    if int(v['nb_frames'])!=item['frames']:raise RuntimeError('Cảnh xuất thiếu khung hình.')
    temp.replace(out);save_json(folder/'render_info.json',{'codec':codec,'signature':sig});return out

def source_audio(p,item,ctx):
    job=Path(p['job']);asset=p['files'][item['source_id']];fps=p['plan']['fps'];sec=item['frames']/fps;speed=item.get('speed',1)
    key=signature({'version':2,'source':asset['sha256'],'start':item['source_in'],'frames':item['frames'],'fps':fps,'speed':speed});folder=job/'source_audio';folder.mkdir(exist_ok=True);out=folder/f'{key[:20]}.wav'
    if out.exists():return out
    if asset['kind']=='image' or not asset['audio_streams']:
        with wave.open(str(out),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);remaining=round(sec*48000)
            while remaining:n=min(remaining,48000);w.writeframesraw(b'\0'*(n*2));remaining-=n
    else:
        tempos=[];t=speed
        while t<.5:tempos.append(.5);t/=.5
        while t>2:tempos.append(2);t/=2
        tempos.append(t);af=','.join(f'atempo={x}' for x in tempos)+f',aresample=48000,apad,atrim=duration={sec},afade=t=in:d=0.06,afade=t=out:st={max(0,sec-.06)}:d=0.06'
        temp=out.with_suffix('.pending.wav');ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-stream_loop','-1','-ss',str(source_offset(asset,item['source_in'])),'-i',asset['path'],'-map','0:a:0','-vn','-af',af,'-ac','1','-ar','48000','-c:a','pcm_s16le','-t',str(sec),'-y',temp],log=folder/'extract.log');temp.replace(out)
    return out

def concatenate_audio(paths,out):
    with wave.open(str(out),'wb') as dest:
        dest.setnchannels(1);dest.setsampwidth(2);dest.setframerate(48000)
        for p in paths:
            with wave.open(str(p)) as src:
                while True:
                    b=src.readframes(48000)
                    if not b:break
                    dest.writeframesraw(b)

def export_movie(p,out,ctx):
    from .project import validate_project,change_fps
    from .subtitles import export
    p=validate_project(copy.deepcopy(p))
    if p['settings']['fps']!=p['plan']['fps']:change_fps(p,p['settings']['fps'])
    job=Path(p['job']);settings=p['settings'];shots=p['plan']['shots'];out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    protected={Path(p['voice_source']).resolve()}|{Path(x['path']).resolve() for x in p['files']}
    protected|={Path(settings[k]).resolve() for k in ['logo_path','subtitle_path','visual_script_path'] if settings.get(k)}
    candidate=out.with_name(out.stem+'.checking'+out.suffix)
    if out in protected or candidate in protected or out.suffix.lower() not in ['.mp4','.mkv']:raise ValueError('Chọn tên MP4/MKV mới,không ghi đè nguồn hoặc trùng đường dẫn tạm với nguồn.')
    for source in p['files']:
        source_path=Path(source['path'])
        if not source_path.is_file():raise ValueError(f'Thiếu nguồn: {source_path}')
        st=source_path.stat()
        if (st.st_size!=source.get('bytes') or st.st_mtime_ns!=source.get('mtime_ns')) and digest(source_path)!=source['sha256']:raise ValueError(f'Nguồn đã đổi sau khi phân tích: {source_path.name}. Hãy Tự xếp cảnh lại.')
    normalize_logo(settings,job)
    codec=choose_encoder(settings['encoder'],ctx);workers=2 if len(shots)>1 else 1
    paths=[None]*len(shots);done=0
    def task(i):return i,render_shot(p,shots[i],shots[i-1] if i else None,ctx,codec=codec)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for i,path in ex.map(task,range(len(shots))):paths[i]=path;done+=1;ctx.emit(55+30*done/len(shots),f'Xuất cảnh {done}/{len(shots)} — {codec}')
    listfile=job/'export_concat.txt'
    # All render paths are generated app-owned ASCII names. Paths are escaped for concat syntax.
    quote=lambda path:str(path).replace('\\','/').replace("'","'\\''")
    listfile.write_text(''.join("file '"+quote(x)+"'\n" for x in paths),encoding='utf-8')
    ctx.emit(87,'Ghép video,logo,phụ đề và âm thanh đã chọn…')
    log=job/'loudness_v2.log';voice=Path(p['voice_wav']);key=signature(_file_key(voice));measure=job/'loudness_measure.json'
    if not measure.exists() or json.loads(measure.read_text(encoding='utf-8-sig')).get('key')!=key:
        ctx.run([binary('ffmpeg'),'-nostdin','-hide_banner','-nostats','-i',voice,'-af','loudnorm=I=-16:TP=-2:LRA=11:print_format=json','-f','null','-'],log=log);text=log.read_text(encoding='utf-8',errors='replace');m=json.loads(text[text.rfind('{'):text.rfind('}')+1]);save_json(measure,{'key':key,'measurement':m})
    m=json.loads(measure.read_text(encoding='utf-8-sig'))['measurement']
    if not math.isfinite(float(m['input_i'])):raise ValueError('Voice không có mức âm thanh hợp lệ.')
    af=f"loudnorm=I=-16:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000,atrim=duration={p['plan']['voice_seconds']},asetpts=PTS-STARTPTS"
    cmd=[binary('ffmpeg'),'-nostdin','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',listfile,'-i',voice];audio_index=2
    mixed=not settings['mute_source'] and settings['source_volume']>0
    if mixed:
        audio_paths=[source_audio(p,x,ctx) for x in shots];source=job/'source_mix.wav';concatenate_audio(audio_paths,source);cmd+=['-i',source];audio_index+=1
        afs=f'[1:a]{af}[voice];[2:a]volume={settings["source_volume"]},aresample=48000[src];[voice][src]amix=inputs=2:duration=first:normalize=0,alimiter=limit=.95:level=false[audio]'
    else:afs=f'[1:a]{af}[audio]'
    export(p['cues'],job/'LOI_DOC.srt')
    if settings['subtitle_mode']=='soft':cmd+=['-i',job/'LOI_DOC.srt']
    cmd+=['-filter_complex',afs,'-map','0:v:0','-map','[audio]']
    if settings['subtitle_mode']=='soft':cmd+=['-map',f'{audio_index}:0','-c:s','mov_text' if out.suffix.lower()=='.mp4' else 'srt','-metadata:s:s:0','language=eng','-disposition:s:0','0']
    candidate=out.with_name(out.stem+'.checking'+out.suffix)
    cmd+=['-c:v','copy','-c:a','aac','-b:a','160k','-ar','48000','-metadata:s:a:0','title=Voice and selected source audio' if mixed else 'title=Voice only','-t',str(p['plan']['video_seconds'])]
    if out.suffix.lower()=='.mp4':cmd+=['-movflags','+faststart']
    ctx.run(cmd+[candidate],log=job/'export.log')
    from .validation import validate_output
    report=validate_output(candidate,voice,p,ctx)
    candidate.replace(out);report.update(file=out.name,output=str(out),codec_requested=settings['encoder'],encoder_selected=codec,source_audio_kept=mixed,source_volume=settings['source_volume'] if mixed else 0,logo_applied=bool(settings.get('logo_path')),subtitle_mode=settings['subtitle_mode'],version='2.3.0')
    report.update(aspect_ratio=settings['aspect_ratio'],detected_language=p.get('detected_language','unknown'),visual_matching=p.get('visual_matching','original_en'),scenes_needing_review=[s['index']+1 for s in shots if s.get('semantic_score',0)<.19])
    save_json(out.with_suffix('.qa.json'),report);save_json(job/'KIEM_TRA_VIDEO.json',report);ctx.emit(100,'Đã lưu video và báo cáo kiểm tra.');return {'output':str(out),'project':p['project_file'],'report':report}
