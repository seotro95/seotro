from __future__ import annotations
import hashlib,json,math,os,wave
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from .common import Context,binary,data_dir,digest,probe,save_json,signature

CLIP_REPO='Xenova/clip-vit-base-patch32'
CLIP_REVISION='6b7c523703ae26e39be4b03774966f8571c7f523'
CLIP_FILES={
 'tokenizer.json':(2224119,None),
 'onnx/text_model_quantized.onnx':(64504507,'73baab855d406190da9faa498cfedf65f15cf309f4cc7385b7b032e6d08e5c3a'),
 'onnx/vision_model_quantized.onnx':(89117001,'583fd1110a514667812fee7d684952aaf82a99b959760c8d7dca7e0ab9839299')}
VIDEO_SUFFIXES={'.mp4','.mkv','.mov','.m4v','.avi','.webm','.mts','.m2ts'}

def normalized(x):
    x=np.asarray(x,dtype=np.float32);return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-9)

class SemanticModel:
    def __init__(self,ctx: Context,folder: Path | None=None,threads=2):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        from huggingface_hub import hf_hub_download
        self.ctx=ctx;folder=folder or data_dir()/'models/clip'
        for i,(name,(size,sha)) in enumerate(CLIP_FILES.items()):
            ctx.emit(14+i,f'Chuẩn bị AI hình ảnh: {name.split("/")[-1]} (chỉ tải lần đầu)')
            p=folder/name
            if not p.is_file() or p.stat().st_size!=size:
                hf_hub_download(CLIP_REPO,name,revision=CLIP_REVISION,local_dir=str(folder))
            if p.stat().st_size!=size or (sha and digest(p)!=sha):raise RuntimeError(f'Model hỏng: {name}. Xóa tệp model này rồi chạy lại.')
        self.tokenizer=Tokenizer.from_file(str(folder/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=77)
        self.tokenizer.enable_padding(length=77,pad_id=49407,pad_token='<|endoftext|>')
        opts=ort.SessionOptions();opts.intra_op_num_threads=max(1,threads);opts.inter_op_num_threads=1
        self.text_session=ort.InferenceSession(str(folder/'onnx/text_model_quantized.onnx'),opts,providers=['CPUExecutionProvider'])
        self.image_session=ort.InferenceSession(str(folder/'onnx/vision_model_quantized.onnx'),opts,providers=['CPUExecutionProvider'])

    def text(self,texts):
        values=[];names={x.name for x in self.text_session.get_inputs()}
        for start in range(0,len(texts),24):
            self.ctx.check();enc=self.tokenizer.encode_batch([str(x) for x in texts[start:start+24]])
            all_inputs={'input_ids':np.asarray([x.ids for x in enc],dtype=np.int64),'attention_mask':np.asarray([x.attention_mask for x in enc],dtype=np.int64)}
            outputs=self.text_session.run(None,{k:v for k,v in all_inputs.items() if k in names})
            index=next((i for i,x in enumerate(self.text_session.get_outputs()) if x.name=='text_embeds'),0)
            values.append(normalized(outputs[index]))
        return np.concatenate(values)

    def images(self,paths):
        values=[]
        for start in range(0,len(paths),6):
            self.ctx.check();batch=[]
            for path in paths[start:start+6]:
                with Image.open(path) as im:
                    im=ImageOps.fit(im.convert('RGB'),(224,224),method=Image.Resampling.BICUBIC)
                    a=np.asarray(im,dtype=np.float32)/255
                a=(a-np.array([.48145466,.4578275,.40821073]))/np.array([.26862954,.26130258,.27577711]);batch.append(a.transpose(2,0,1))
            outputs=self.image_session.run(None,{'pixel_values':np.asarray(batch,dtype=np.float32)})
            index=next((i for i,x in enumerate(self.image_session.get_outputs()) if x.name=='image_embeds'),0)
            values.append(normalized(outputs[index]))
        return np.concatenate(values)

def decode_voice(voice: Path,job: Path,ctx: Context):
    out=job/'voice.wav';mark=job/'voice_fingerprint.json';sha=digest(voice)
    if not out.exists() or not mark.exists() or json.loads(mark.read_text())['sha256']!=sha:
        ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-y','-i',voice,'-map','0:a:0','-vn','-ac','1','-ar','48000','-c:a','pcm_s16le',out],log=job/'decode_voice.log')
        save_json(mark,{'sha256':sha,'source':str(voice)})
    with wave.open(str(out)) as w:duration=w.getnframes()/w.getframerate()
    if duration<4:raise ValueError('Voice cần dài ít nhất4giây.')
    return out,duration,sha

def transcribe(wav: Path,job: Path,ctx: Context,model_name='base',language='en',model_path=None,threads=2):
    marker=signature({'wav_sha':digest(wav),'model':str(model_path or model_name),'language':language,'version':1})
    cache=job/'transcript.json'
    if cache.exists() and json.loads(cache.read_text()).get('signature')==marker:return json.loads(cache.read_text())['cues']
    from faster_whisper import WhisperModel
    ctx.emit(3,'Nhận dạng lời voice; lần đầu có thể cần tải model Whisper.')
    model=WhisperModel(str(model_path or model_name),device='cpu',compute_type='int8',cpu_threads=threads,num_workers=1,download_root=str(data_dir()/'models/whisper'))
    audio=np.frombuffer(ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-i',wav,'-ac','1','-ar','16000','-f','f32le','-'],capture=True),dtype='<f4').copy()
    segments,info=model.transcribe(audio,language=None if language=='auto' else language,beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    cues=[]
    with wave.open(str(wav)) as w:duration=w.getnframes()/w.getframerate()
    for seg in segments:
        ctx.check();text=seg.text.strip()
        if text and seg.end>seg.start:
            cues.append({'start':max(0,seg.start),'end':min(duration,seg.end),'text':text,'words':[{'start':w.start,'end':w.end,'text':w.word.strip()} for w in (seg.words or [])]})
        ctx.emit(min(13,3+10*seg.end/duration),f'Nhận dạng lời: {min(100,round(100*seg.end/duration))}%')
    del model
    if not cues:raise RuntimeError('Không nhận dạng được lời trong voice. Kiểm tra tệp có giọng nói rõ và đúng ngôn ngữ.')
    if sum(x['end']-x['start'] for x in cues)<duration*.2:raise RuntimeError('Quá ít lời nói được nhận dạng. Kiểm tra voice trước khi tự dựng.')
    save_json(cache,{'signature':marker,'language':info.language,'cues':cues});return cues

def inspect_videos(folder: Path,job: Path,ctx: Context):
    paths=sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not p.is_relative_to(job) and not any(q.name.startswith('AutoDoc_') and (q/'PROJECT.json').is_file() for q in p.parents))
    # Output nested inside the input folder is excluded by path, never by a broad name match.
    if not paths:raise ValueError('Thư mục không có video hỗ trợ, hoặc thư mục xuất trùng thư mục đầu vào.')
    files=[];skipped=[];seen_hashes=set()
    for i,p in enumerate(paths):
        ctx.emit(17+3*i/len(paths),f'Kiểm tra video {i+1}/{len(paths)}')
        try:
            j=probe(p,ctx);v=next(x for x in j['streams'] if x['codec_type']=='video');seconds=float(v.get('duration') or j['format']['duration'])
            if seconds<.6:raise ValueError('clip quá ngắn')
            sha=digest(p)
            if sha in seen_hashes:
                skipped.append({'name':p.name,'reason':'Duplicate SHA256;đã có clip giống hệt.'});continue
            seen_hashes.add(sha)
            files.append({'id':len(files),'path':str(p.resolve()),'name':p.name,'sha256':sha,'seconds':seconds,'width':v['width'],'height':v['height'],'audio_streams':sum(x['codec_type']=='audio' for x in j['streams'])})
        except Exception as e:
            from .common import Cancelled
            if isinstance(e,Cancelled):raise
            skipped.append({'name':p.name,'reason':str(e)[:300]})
    if not files:raise RuntimeError('Không đọc được video nào. '+str(skipped[:2]))
    save_json(job/'source_manifest.json',{'files':files,'skipped':skipped,'originals_modified':False});return files,skipped

def visual_index(files,job: Path,model: SemanticModel,ctx: Context):
    cache=job/'visual_index.npz';manifest=job/'visual_index.json'
    key=signature({'files':[(f['sha256'],f['seconds']) for f in files],'model':CLIP_REVISION,'version':2})
    if cache.exists() and manifest.exists():
        m=json.loads(manifest.read_text())
        if m.get('signature')==key:
            with np.load(cache,allow_pickle=False) as z:return m['candidates'],z['features'],z['screen_scores']
    candidates=[];features=[];screen=[]
    screens=model.text(['a photograph of an adult man or woman','a photograph of a young child, baby or teenager','a full screen title card with large text and letters','documentary photography of a landscape, objects, science, architecture or adult people'])
    # Each window is analyzed at three points, not assumed to match its filename.
    windows=[]
    for f in files:
        count=max(1,math.ceil(f['seconds']/10))
        for n in range(count):
            start=n*10;length=min(10,f['seconds']-start)
            if length<.6:continue
            windows.append((f,start,length))
    if len(windows)>4000:raise ValueError('Quá nhiều đoạn nguồn (>4000). Chia thư mục thành các dự án nhỏ hơn.')
    frame_dir=job/'frames';frame_dir.mkdir(exist_ok=True)
    for i,(f,start,length) in enumerate(windows):
        ctx.emit(20+30*i/len(windows),f'AI xem hình {i+1}/{len(windows)}')
        paths=[]
        for k,fraction in enumerate([.12,.5,.87]):
            path=frame_dir/f'{i:05d}_{k}.jpg';paths.append(path)
            if not path.exists():ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-threads','1','-ss',str(start+length*fraction),'-i',f['path'],'-frames:v','1','-vf','scale=320:320:force_original_aspect_ratio=decrease','-threads','1','-y',path],log=job/'extract.log')
        emb=model.images(paths);vector=normalized(emb.mean(axis=0))
        pixels=[np.asarray(Image.open(p).convert('RGB').resize((32,32)),dtype=np.float32) for p in paths]
        motion=float((np.abs(pixels[0]-pixels[1]).mean()+np.abs(pixels[1]-pixels[2]).mean())/2/255)
        quality=float(np.std(pixels[1])/255)
        # Screening is a relative CLIP estimate, not a certified age/OCR detector.
        screen.append((emb@screens.T).max(axis=0));features.append(vector)
        candidates.append({'id':i,'file_id':f['id'],'source_start':start,'source_duration':length,'motion':motion,'quality':quality})
    fts=np.asarray(features,dtype=np.float32);sc=np.asarray(screen,dtype=np.float32)
    np.savez_compressed(cache,features=fts,screen_scores=sc);save_json(manifest,{'signature':key,'candidates':candidates})
    return candidates,fts,sc
