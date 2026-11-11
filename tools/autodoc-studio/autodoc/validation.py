from __future__ import annotations
import hashlib,json
import numpy as np
from .common import binary,probe

def validate_output(output,voice,p,ctx):
    plan=p['plan'];job=__import__('pathlib').Path(p['job']);duration=plan['voice_seconds'];fps=plan['fps']
    ctx.emit(92,'Kiểm tra thời lượng, số khung và đồng bộ âm thanh…')
    meta=probe(output,ctx);vs=[x for x in meta['streams'] if x['codec_type']=='video'];aus=[x for x in meta['streams'] if x['codec_type']=='audio']
    if len(vs)!=1 or len(aus)!=1:raise RuntimeError('Video cần đúng một luồng hình và một luồng tiếng.')
    v,a=vs[0],aus[0];vd=float(v.get('duration') or meta['format']['duration']);ad=float(a.get('duration') or meta['format']['duration'])
    if v.get('nb_frames'):frames=int(v['nb_frames'])
    else:
        packets=json.loads(ctx.run([binary('ffprobe'),'-v','error','-select_streams','v:0','-count_packets','-show_entries','stream=nb_read_packets','-of','json',output],capture=True));frames=int(packets['streams'][0]['nb_read_packets']);vd=frames/fps
    if frames!=plan['total_frames'] or abs(vd-duration)>1/fps+.003 or abs(ad-duration)>.065:raise RuntimeError('Thời lượng/số khung xuất không khớp voice.')
    if p['settings']['full_verify']:ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-xerror','-threads','1','-i',output,'-map','0:v:0','-map','0:a:0','-f','null','-'],log=job/'full_decode.log')
    mixed=not p['settings']['mute_source'] and p['settings']['source_volume']>0;lags=[]
    if not mixed:
        def pcm(path):return np.frombuffer(ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-i',path,'-map','0:a:0','-ac','1','-ar','8000','-f','s16le','-'],capture=True),dtype='<i2').astype(np.float32)
        reference=pcm(voice);actual=pcm(output);n=8000;pad=400;selected=set()
        for fraction in [.08,.25,.5,.75,.92]:
            target=round(duration*fraction*8000);lo=max(pad,target-12000);hi=min(len(reference)-n-pad,target+12000)
            choices=[c for c in range(lo,max(lo+1,hi+1),2000) if c+n<=len(reference) and c-pad>=0 and c+n+pad<=len(actual)]
            if not choices:continue
            c=max(choices,key=lambda t:float(np.mean(reference[t:t+n]**2)))
            if c in selected:continue
            selected.add(c);ref=reference[c:c+n].copy();test=actual[c-pad:c+n+pad].copy();ref-=ref.mean();test-=test.mean();rms=float(np.sqrt(np.mean(ref**2)))
            if rms<40:continue
            k=int(np.argmax(np.correlate(test,ref,mode='valid')));matched=test[k:k+n];corr=float(np.dot(matched,ref)/(np.linalg.norm(matched)*np.linalg.norm(ref)+1e-8));lag=(k-pad)/8000
            if abs(lag)>.025 or corr<.9:raise RuntimeError(f'Voice lệch tại {c/8000:.2f}s: {lag:.3f}s, tương quan {corr:.3f}.')
            lags.append({'at_seconds':round(c/8000,3),'lag_seconds':lag,'correlation':round(corr,6)})
        if not lags:raise RuntimeError('Voice quá nhỏ để xác minh đồng bộ.')
    return {'status':'passed','voice_seconds':duration,'video_seconds':vd,'audio_seconds':ad,'frames':frames,'fps':fps,'width':v['width'],'height':v['height'],'audio_streams':1,'source_audio_kept':mixed,'audio_alignment':lags,'alignment_note':'Không đo tương quan khi chủ động trộn tiếng clip.' if mixed else 'Đã đối chiếu mẫu âm thanh thực tế.','full_decode_performed':p['settings']['full_verify'],'image_scenes':sum(p['files'][s['source_id']]['kind']=='image' for s in plan['shots']),'opening_shots':sum(s['start_frame']<30*fps for s in plan['shots']),'warnings':plan.get('warnings',[]),'bytes':output.stat().st_size,'sha256':hashlib.file_digest(output.open('rb'),'sha256').hexdigest()}
