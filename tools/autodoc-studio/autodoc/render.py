from __future__ import annotations
import csv,hashlib,json,math,shutil,wave
from pathlib import Path
import numpy as np
from .common import Context,binary,probe,save_json,signature

def render_shot(item,previous,files,job,ctx,width,height,fps):
    shot_dir=job/'shots';shot_dir.mkdir(exist_ok=True);out=shot_dir/f"{item['index']:05d}.mp4"
    sig=signature({'shot':item,'previous':previous if item['transition']=='dissolve' else None,'sources':[x['sha256'] for x in files],'resolution':[width,height,fps],'renderer':4})
    mark=out.with_suffix('.json')
    if out.exists() and mark.exists() and json.loads(mark.read_text()).get('signature')==sig:return out
    ff=binary('ffmpeg');cmd=[ff,'-nostdin','-hide_banner','-loglevel','error','-filter_complex_threads','1','-y']
    sec=item['frames']/fps;src=files[item['source_id']]
    def add_input(s,offset):
        cmd.extend(['-threads','1','-stream_loop','-1','-ss',str(max(0,min(offset,s['seconds']-.1))),'-i',s['path']])
    add_input(src,item['source_in']);filters=[]
    def scale(label,duration,crop):
        vf=f'trim=duration={duration},setpts=PTS-STARTPTS,fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},setsar=1'
        if crop>1:
            cw=int(width/crop)//2*2;ch=int(height/crop)//2*2;vf+=f',crop={cw}:{ch},scale={width}:{height}:flags=lanczos'
        return f'{label}{vf},format=yuv420p,setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709,settb=AVTB'
    filters.append(scale('[0:v]',sec,item['crop'])+'[current]');stage='current'
    if item['transition']=='dissolve' and previous:
        tail=files[previous['source_id']];offset=previous['source_in']+previous['frames']/fps
        offset=min(offset,max(0,tail['seconds']-.4));add_input(tail,offset)
        filters.append(scale('[1:v]',.35,previous['crop'])+'[old]')
        filters.append('[old][current]xfade=transition=fade:duration=0.35:offset=0[mixed]');stage='mixed'
    if item.get('last'):
        fade=min(.5,sec*.3);filters.append(f'[{stage}]fade=t=out:st={sec-fade}:d={fade}[ending]');stage='ending'
    filters.append(f'[{stage}]trim=duration={sec},setpts=PTS-STARTPTS,format=yuv420p[final]')
    cmd+=['-filter_complex',';'.join(filters),'-map','[final]','-an','-frames:v',str(item['frames']),'-r',str(fps),'-c:v','libx264','-preset','veryfast','-crf','21','-maxrate','4000k' if width>1280 else '2400k','-bufsize','8000k' if width>1280 else '4800k','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',out]
    temporary=out.with_name(out.stem+'.pending.mp4');cmd[-1]=temporary
    ctx.run(cmd,log=shot_dir/f"{item['index']:05d}.log")
    p=probe(temporary,ctx);v=next(x for x in p['streams'] if x['codec_type']=='video')
    if int(v['nb_frames'])!=item['frames']:raise RuntimeError('Cảnh xuất thiếu khung hình; không tiếp tục ghép bản hỏng.')
    temporary.replace(out);save_json(mark,{'signature':sig,'frames':item['frames']});return out

def render_project(plan,files,voice,job,ctx,resolution=720,embed_subtitles=False):
    width,height=(1920,1080) if resolution==1080 else (1280,720);fps=plan['fps'];shots=plan['shots'];shots[-1]['last']=True
    for i,item in enumerate(shots):
        ctx.emit(52+34*i/len(shots),f'Dựng cảnh {i+1}/{len(shots)}: {item["source_name"]}')
        render_shot(item,shots[i-1] if i else None,files,job,ctx,width,height,fps)
    concat=job/'concat.txt';concat.write_text(''.join(f"file 'shots/{i:05d}.mp4'\n" for i in range(len(shots))),encoding='utf-8')
    ctx.emit(87,'Chuẩn hóa độ lớn voice và ghép phim; chỉ lấy tiếng từ voice.')
    ff=binary('ffmpeg');log=job/'loudness.log'
    ctx.run([ff,'-nostdin','-hide_banner','-nostats','-i',voice,'-af','loudnorm=I=-16:TP=-2:LRA=11:print_format=json','-f','null','-'],log=log)
    text=log.read_text(errors='replace');m=json.loads(text[text.rfind('{'):text.rfind('}')+1])
    if not math.isfinite(float(m['input_i'])):raise RuntimeError('Voice không có mức tiếng hợp lệ.')
    af=f"loudnorm=I=-16:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000,atrim=duration={plan['voice_seconds']},asetpts=PTS-STARTPTS"
    temp=job/'VIDEO_HOAN_CHINH.pending.mp4';out=job/'VIDEO_HOAN_CHINH.mp4'
    cmd=[ff,'-nostdin','-hide_banner','-loglevel','warning','-y','-f','concat','-safe','0','-i',concat,'-i',voice]
    if embed_subtitles:cmd+=['-i',job/'LOI_DOC.srt']
    cmd+=['-map','0:v:0','-map','1:a:0']
    if embed_subtitles:cmd+=['-map','2:0','-c:s','mov_text','-metadata:s:s:0','language=eng','-disposition:s:0','0']
    cmd+=['-c:v','copy','-af',af,'-c:a','aac','-b:a','160k','-ar','48000','-metadata:s:a:0','language=eng','-metadata:s:a:0','title=Original narration only','-t',str(plan['video_seconds']),'-movflags','+faststart',temp]
    ctx.run(cmd,log=job/'mux.log');temp.replace(out)
    return out

def validate_output(output,voice,plan,job,ctx):
    ctx.emit(91,'Kiểm thời lượng, giải mã toàn bộ và đối chiếu đồng bộ voice.')
    p=probe(output,ctx);videos=[x for x in p['streams'] if x['codec_type']=='video'];audio=[x for x in p['streams'] if x['codec_type']=='audio']
    if len(videos)!=1 or len(audio)!=1:raise RuntimeError('Bản xuất phải có đúng một video và một đường voice.')
    v=videos[0];a=audio[0]
    if int(v['nb_frames'])!=plan['total_frames']:raise RuntimeError('Tổng số khung hình không khớp timeline.')
    if abs(float(a['duration'])-plan['voice_seconds'])>.055:raise RuntimeError('Thời lượng tiếng không khớp voice.')
    if abs(float(v['duration'])-plan['voice_seconds'])>1/plan['fps']+.001:raise RuntimeError('Thời lượng hình lệch quá một khung hình.')
    ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-xerror','-threads','1','-i',output,'-map','0:v:0','-map','0:a:0','-f','null','-'],log=job/'full_decode.log')
    # Compare actual audio, rather than trusting a matching subtitle or filename.
    lags=[];duration=plan['voice_seconds']
    def full_pcm(path):
        data=ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-i',path,'-map','0:a:0','-ac','1','-ar','8000','-f','s16le','-'],capture=True)
        return np.frombuffer(data,dtype='<i2').astype(np.float32)
    reference=full_pcm(voice);actual=full_pcm(output);n=8000;pad=400;selected=set()
    # Decode once, then compare sample indices. Seeking AAC separately can reset
    # its overlap/filter state and gives unreliable correlations near quiet words.
    for fraction in [.08,.25,.5,.75,.92]:
        target=round(duration*fraction*8000)
        lo=max(pad,target-12000);hi=min(len(reference)-n-pad,target+12000)
        candidates=list(range(lo,max(lo+1,hi+1),2000))
        candidates=[c for c in candidates if c+n<=len(reference) and c-pad>=0 and c+n+pad<=len(actual)]
        if not candidates:continue
        c=max(candidates,key=lambda t:float(np.mean(reference[t:t+n]**2)))
        if c in selected:continue
        selected.add(c);ref=reference[c:c+n].copy();test=actual[c-pad:c+n+pad].copy();ref-=ref.mean();test-=test.mean()
        rms=float(np.sqrt(np.mean(ref**2)))
        if rms<40:continue  # Quiet noise is not a trustworthy speech alignment anchor.
        k=int(np.argmax(np.correlate(test,ref,mode='valid')));matched=test[k:k+n]
        corr=float(np.dot(matched,ref)/(np.linalg.norm(matched)*np.linalg.norm(ref)+1e-8));lag=(k-pad)/8000
        if abs(lag)>.025 or corr<.9:raise RuntimeError(f'Đồng bộ voice chưa đạt tại{c/8000:.3f}s: lệch{lag:.3f}s,tương quan{corr:.3f}.')
        lags.append({'at_seconds':round(c/8000,3),'lag_seconds':lag,'correlation':round(corr,6),'reference_rms':round(rms,2)})
    if not lags:raise RuntimeError('Voice quá nhỏ/ít tiếng để xác minh đồng bộ đáng tin cậy.')
    result={'status':'passed','file':output.name,'voice_seconds':duration,'video_seconds':float(v['duration']),'audio_seconds':float(a['duration']),'frames':int(v['nb_frames']),'fps':plan['fps'],'width':v['width'],'height':v['height'],'audio_streams':1,'clip_audio_included':False,'music_added':False,'original_voice_timing_and_pitch_preserved':True,'audio_alignment':lags,'full_decode_exit_code':0,'opening_shots':plan['opening_shots'],'opening_distinct_source_files':plan['opening_distinct_files'],'substitution_still_images':0,'warnings':plan['warnings'],'bytes':output.stat().st_size,'sha256':hashlib.file_digest(output.open('rb'),'sha256').hexdigest()}
    save_json(job/'KIEM_TRA_VIDEO.json',result);return result
