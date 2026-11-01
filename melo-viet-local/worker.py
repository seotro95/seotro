"""One resident CPU reader per interpreter; stdout is a JSON protocol only."""
import contextlib
import gc
import json
import os
from pathlib import Path
import sys
import time
import traceback

LANGUAGES={'VI','EN','FR','JP','KR','ES','ZH'}
model=None
model_key=None


def read_model(language,threads):
    global model,model_key
    if language not in LANGUAGES or type(threads) is not int or not 1<=threads<=16:
        raise ValueError('Chọn đúng ngôn ngữ và 1–16 luồng CPU.')
    key=(language,threads)
    started=time.perf_counter()
    loaded=key!=model_key
    if loaded:
        model=None;model_key=None;gc.collect()
        if language=='VI':
            from vieneu.v3turbo import V3TurboVieNeuTTS
            model=V3TurboVieNeuTTS(backend='onnx',device='cpu',precision='fp32',threads=threads)
        else:
            import torch
            torch.set_num_threads(threads)
            from melo.api import TTS
            model=TTS(language=language,device='cpu')
        model_key=key
    voices=([{'id':ident,'name':label} for label,ident in model.list_preset_voices()]
            if language=='VI' else [{'id':ident,'name':ident} for ident in model.hps.data.spk2id])
    return model,voices,(time.perf_counter()-started if loaded else 0)


def synthesize(reader,language,voice,text,output):
    import numpy as np
    import soundfile as sf
    if not isinstance(text,str) or not text.strip() or len(text)>100000 or '\x00' in text:
        raise ValueError('Nhập 1–100.000 ký tự lời đọc hợp lệ.')
    if language=='VI':
        audio=reader.infer(text,voice=voice)
        rate=reader.sample_rate
    else:
        audio=reader.tts_to_file(text,reader.hps.data.spk2id[voice],output_path=None,speed=1.0,quiet=True)
        rate=reader.hps.data.sampling_rate
    audio=np.asarray(audio,dtype=np.float32)
    if audio.ndim!=1 or not audio.size or not np.isfinite(audio).all() or not np.any(audio):
        raise ValueError('Bộ đọc chưa tạo được âm thanh hợp lệ; không bỏ lời hay đổi giọng.')
    peak=float(np.max(np.abs(audio)))
    if peak>.95:audio*=.95/peak
    output=Path(output);temporary=output.with_suffix('.partial.wav')
    try:
        sf.write(temporary,audio,rate,subtype='PCM_16')
        temporary.replace(output)
    finally:temporary.unlink(missing_ok=True)
    return {'audio_seconds':len(audio)/rate,'sample_rate':rate,'peak':float(np.max(np.abs(audio)))}


def handle(request):
    language=request['language'];threads=request.get('threads',4)
    reader,voices,load=read_model(language,threads)
    if request['op']=='voices':return {'voices':voices,'model_load_seconds':load}
    if request['op']!='render':raise ValueError('Thao tác không hợp lệ.')
    voice=request.get('voice') or voices[0]['id']
    if voice not in {v['id'] for v in voices}:raise ValueError('Giọng không thuộc mô hình/ngôn ngữ đã chọn.')
    started=time.perf_counter()
    result=synthesize(reader,language,voice,request['text'],request['output'])
    return {**result,'language':language,'voice':voice,'model_load_seconds':load,
            'inference_and_save_seconds':time.perf_counter()-started,'engine':'VieNeu Turbo FP32' if language=='VI' else 'MeloTTS CPU'}


def main():
    # WSL/Linux: an interrupted Windows launcher must not leave model workers resident.
    if sys.platform.startswith('linux'):
        import ctypes,signal
        ctypes.CDLL(None).prctl(1,signal.SIGTERM,0,0,0)
        if os.getppid()==1:return
    print(json.dumps({'ready':True}),flush=True)
    for line in sys.stdin:
        try:
            request=json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):result=handle(request)
            response={'ok':True,**result}
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            response={'ok':False,'error':str(error)[:1600]}
        print(json.dumps(response,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
