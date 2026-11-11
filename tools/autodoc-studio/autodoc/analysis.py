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
    if not out.exists() or not mark.exists() or json.loads(mark.read_text(encoding='utf-8-sig'))['sha256']!=sha:
        ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-y','-i',voice,'-map','0:a:0','-vn','-ac','1','-ar','48000','-c:a','pcm_s16le',out],log=job/'decode_voice.log')
        save_json(mark,{'sha256':sha,'source':str(voice)})
    with wave.open(str(out)) as w:duration=w.getnframes()/w.getframerate()
    if duration<4:raise ValueError('Voice cần dài ít nhất4giây.')
    return out,duration,sha

def transcribe(wav: Path,job: Path,ctx: Context,model_name='base',language='en',model_path=None,threads=2,fast=False,task='transcribe'):
    if task not in ['transcribe','translate']:raise ValueError('Tác vụ nhận dạng không hợp lệ.')
    marker=signature({'wav_sha':digest(wav),'model':str(model_path or model_name),'language':language,'fast':fast,'task':task,'version':3})
    cache=job/('transcript_visual_en.json' if task=='translate' else 'transcript.json')
    if cache.exists() and json.loads(cache.read_text(encoding='utf-8-sig')).get('signature')==marker:return json.loads(cache.read_text(encoding='utf-8-sig'))['cues']
    from .resources import check_vad
    check_vad()
    from faster_whisper import WhisperModel
    ctx.emit(3,'Dịch lời sang tiếng Anh theo mốc để chọn hình; giữ nguyên voice.' if task=='translate' else 'Nhận dạng ngôn ngữ và lời voice; lần đầu có thể cần tải model Whisper.')
    model=WhisperModel(str(model_path or model_name),device='cpu',compute_type='int8',cpu_threads=threads,num_workers=1,download_root=str(data_dir()/'models/whisper'))
    audio=np.frombuffer(ctx.run([binary('ffmpeg'),'-nostdin','-v','error','-i',wav,'-ac','1','-ar','16000','-f','f32le','-'],capture=True),dtype='<f4').copy()
    segments,info=model.transcribe(audio,language=None if language=='auto' else language,task=task,beam_size=1 if fast else 5,word_timestamps=task=='transcribe',vad_filter=True,condition_on_previous_text=False)
    cues=[]
    with wave.open(str(wav)) as w:duration=w.getnframes()/w.getframerate()
    for seg in segments:
        ctx.check();text=seg.text.strip()
        if text and seg.end>seg.start:
            cues.append({'start':max(0,seg.start),'end':min(duration,seg.end),'text':text,'words':[{'start':w.start,'end':w.end,'text':w.word.strip()} for w in (seg.words or [])]})
        ctx.emit(min(13,3+10*seg.end/duration),f'{"Dịch để chọn hình" if task=="translate" else "Nhận dạng lời"}: {min(100,round(100*seg.end/duration))}%')
    del model
    if not cues:raise RuntimeError('Không nhận dạng được lời trong voice. Kiểm tra tệp có giọng nói rõ và đúng ngôn ngữ.')
    if sum(x['end']-x['start'] for x in cues)<duration*.2:raise RuntimeError('Quá ít lời nói được nhận dạng. Kiểm tra voice trước khi tự dựng.')
    save_json(cache,{'signature':marker,'language':info.language,'task':task,'cues':cues});return cues

