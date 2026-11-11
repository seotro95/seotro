from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from .analysis import VIDEO_SUFFIXES,normalized
from .common import Context,binary,data_dir,digest,probe,save_json,signature,Cancelled

IMAGE_SUFFIXES={'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff'}

def inspect(folder,job,ctx,excluded=()):
    folder=Path(folder).resolve();excluded={Path(p).resolve() for p in excluded if p}
    paths=sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES|IMAGE_SUFFIXES and p.resolve() not in excluded and not p.is_relative_to(job) and not any(q.name.startswith(('AutoDoc_','AutoDoc2_')) and (q/'PROJECT.json').exists() for q in p.parents))
    if not paths:raise ValueError('Thư mục chưa có ảnh hoặc video phù hợp.')
    files=[];skipped=[];seen=set()
    for i,p in enumerate(paths):
        ctx.emit(17+3*i/len(paths),f'Đọc ảnh/video {i+1}/{len(paths)}')
        try:
            sha=digest(p)
            if sha in seen:skipped.append({'name':p.name,'reason':'Trùng nội dung SHA256'});continue
            if p.suffix.lower() in IMAGE_SUFFIXES:
                with Image.open(p) as im:im.verify()
                with Image.open(p) as im:w,h=ImageOps.exif_transpose(im).size
                if w*h>50000000:raise ValueError('Ảnh quá lớn (>50MP), hãy thu nhỏ trước.')
                item={'kind':'image','seconds':10.,'width':w,'height':h,'audio_streams':0,'rotation':0}
            else:
                j=probe(p,ctx);v=next(x for x in j['streams'] if x['codec_type']=='video');d=float(v.get('duration') or j['format']['duration'])
                if d<.6:raise ValueError('Video quá ngắn')
                rotation=next((x['rotation'] for x in v.get('side_data_list',[]) if 'rotation' in x),float(v.get('tags',{}).get('rotate',0)))
                item={'kind':'video','seconds':d,'width':v['width'],'height':v['height'],'audio_streams':sum(x['codec_type']=='audio' for x in j['streams']),'rotation':rotation}
            st=p.stat();files.append({'id':len(files),'path':str(p.resolve()),'name':p.name,'sha256':sha,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,**item});seen.add(sha)
        except Cancelled:raise
        except Exception as e:skipped.append({'name':p.name,'reason':str(e)[:300]})
    if not files:raise ValueError('Không đọc được ảnh/video nào. '+str(skipped[:2]))
    save_json(job/'source_manifest.json',{'files':files,'skipped':skipped,'originals_modified':False});return files,skipped

def _rgb(im):
    im=ImageOps.exif_transpose(im)
    if im.mode=='RGBA':
        bg=Image.new('RGB',im.size,(24,24,24));bg.paste(im,mask=im.getchannel('A'));return bg
    return im.convert('RGB')

def frame(asset,t,path,ctx,container=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():return path
    if asset['kind']=='image':
        with Image.open(asset['path']) as src:im=_rgb(src);im.thumbnail((480,270));im.save(path,quality=82)
        return path
    try:
        import av
        own=container is None;c=container or av.open(asset['path']);stream=c.streams.video[0];stream.thread_type='AUTO'
        origin=float(stream.start_time*stream.time_base) if stream.start_time is not None else 0
        c.seek(max(0,int((t+origin)*1000000)),backward=True,any_frame=False)
        picked=None
        for f in c.decode(stream):
            picked=f
            if f.time is None or f.time>=t+origin-.03:break
        if picked is None:raise ValueError('Không có khung hình')
        im=picked.to_image()
        if asset.get('rotation'):im=im.rotate(asset['rotation'],expand=True)
        im.thumbnail((480,270));im.save(path,quality=82)
        if own:c.close()
    except Exception:
        ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-threads','1','-ss',str(t),'-i',asset['path'],'-frames:v','1','-vf','scale=480:270:force_original_aspect_ratio=decrease','-threads','1','-y',path],log=path.with_suffix('.log'))
    return path

def index(files,job,model,ctx,samples=1):
    from .analysis import CLIP_REVISION
    root=data_dir()/'features-v2';root.mkdir(exist_ok=True)
    screen_vectors=model.text(['an adult man or woman','a young child, baby or teenager','a full screen title card with large text','a documentary image of a landscape, objects, science, architecture or adult people'])
    all_c=[];all_features=[];all_scores=[];hits=0
    for number,asset in enumerate(files):
        ctx.emit(20+29*number/len(files),f'AI nhận diện {number+1}/{len(files)}: {asset["name"]}')
        key=signature({'source':asset['sha256'],'samples':samples,'clip':CLIP_REVISION,'kind':asset['kind'],'version':3});folder=root/key;folder.mkdir(exist_ok=True);meta=folder/'index.json';cache=folder/'features.npz'
        if meta.exists() and cache.exists():
            try:
                candidates=json.loads(meta.read_text())['candidates']
                with np.load(cache,allow_pickle=False) as z:features=z['features'];scores=z['scores']
                if len(features)!=len(candidates):raise ValueError('cache')
                hits+=1
            except (ValueError,OSError,KeyError):meta.unlink(missing_ok=True)
        if not meta.exists() or not cache.exists():
            count=1 if asset['kind']=='image' else max(1,math.ceil(asset['seconds']/10));candidates=[];features=[];scores=[]
            if count>2000:raise ValueError('Một video quá dài cho dự án này; hãy chia nhỏ video nguồn.')
            container=None
            try:
                if asset['kind']=='video':
                    import av
                    try:container=av.open(asset['path'])
                    except Exception:pass
                for n in range(count):
                    ctx.check();start=n*10;length=10. if asset['kind']=='image' else min(10.,asset['seconds']-start)
                    if length<.6:continue
                    positions=[.5] if samples==1 else [.12,.5,.87]
                    paths=[frame(asset,start+length*x,folder/f'{n:05d}_{k}.jpg',ctx,container) for k,x in enumerate(positions)]
                    emb=model.images(paths);pix=np.asarray(Image.open(paths[len(paths)//2]).convert('RGB').resize((32,32)),dtype=np.float32)
                    quality=float(pix.std()/255)
                    candidates.append({'source_start':start,'source_duration':length,'quality':quality,'motion':.02 if asset['kind']=='video' else .015,'thumbnail':str(paths[len(paths)//2])})
                    features.append(normalized(emb.mean(axis=0)));scores.append((emb@screen_vectors.T).max(axis=0))
            finally:
                if container:container.close()
            features=np.asarray(features,dtype=np.float32);scores=np.asarray(scores,dtype=np.float32)
            tmp=folder/'features.pending.npz';np.savez_compressed(tmp,features=features,scores=scores);tmp.replace(cache);save_json(meta,{'candidates':candidates,'signature':key})
        for c in candidates:all_c.append({**c,'id':len(all_c),'file_id':asset['id']})
        all_features.extend(features);all_scores.extend(scores)
    save_json(job/'analysis_metrics.json',{'source_files':len(files),'shared_cache_hits':hits,'sample_frames_per_window':samples,'source_images':sum(x['kind']=='image' for x in files)})
    return all_c,np.asarray(all_features,dtype=np.float32),np.asarray(all_scores,dtype=np.float32)
