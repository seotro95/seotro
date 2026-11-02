"""Supertonic 3's ten real cross-lingual presets; optional CPU INT8, no voice relabeling."""
from collections import OrderedDict
import os,time
from pathlib import Path
from local_models import ensure
LANGUAGES={'AR':'ar','BG':'bg','HR':'hr','CS':'cs','DA':'da','NL':'nl','EN':'en','ET':'et','FI':'fi','FR':'fr','DE':'de','EL':'el','HI':'hi','HU':'hu','ID':'id','IT':'it','JP':'ja','KR':'ko','LV':'lv','LT':'lt','PL':'pl','PT':'pt','RO':'ro','RU':'ru','SK':'sk','SL':'sl','ES':'es','SV':'sv','TR':'tr','UK':'uk','VI':'vi'}
MODELS=OrderedDict()
def voices_for(language):
    if language not in LANGUAGES:return []
    # Upstream generate_voices_bin.py sorts F1..F5,M1..M5 before writing voice.bin.
    return [{'id':'supertonic:'+str(sid),'name':'Supertonic 3 · '+name,'gender':'Female' if name[0]=='F' else 'Male','backend':'multi','locale':LANGUAGES[language],'download_required':True} for sid,name in enumerate(['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'])]
def handle(request):
    voices=voices_for(request['language'])
    if not voices:raise ValueError('Supertonic 3 không hỗ trợ ngôn ngữ này; chọn bộ đọc gốc.')
    if request['op']=='voices':return {'voices':voices,'model_load_seconds':0}
    if request['op']!='render' or request.get('voice') not in {v['id'] for v in voices}:raise ValueError('Chọn đúng preset Supertonic.')
    text=request.get('text');threads=request.get('threads',4)
    if type(threads) is not int or not 1<=threads<=16 or not isinstance(text,str) or not text.strip() or len(text)>1200 or '\0' in text:raise ValueError('Kiểm tra văn bản và số luồng CPU.')
    import sherpa_onnx as s,numpy as np,soundfile as sf
    started=time.perf_counter();load=0
    if threads not in MODELS:
        folder=ensure('supertonic3',os.environ.get('HF_HUB_OFFLINE')=='1')
        config=s.OfflineTtsSupertonicModelConfig(**{k:str(folder/v) for k,v in dict(duration_predictor='duration_predictor.int8.onnx',text_encoder='text_encoder.int8.onnx',vector_estimator='vector_estimator.int8.onnx',vocoder='vocoder.int8.onnx',tts_json='tts.json',unicode_indexer='unicode_indexer.bin',voice_style='voice.bin').items()})
        MODELS[threads]=s.OfflineTts(s.OfflineTtsConfig(model=s.OfflineTtsModelConfig(supertonic=config,num_threads=threads,provider='cpu')))
        while len(MODELS)>2:MODELS.popitem(last=False)
        load=time.perf_counter()-started
    MODELS.move_to_end(threads)
    generation=s.GenerationConfig();generation.sid=int(request['voice'].split(':')[1]);generation.num_steps=5;generation.speed=1.;generation.extra['lang']=LANGUAGES[request['language']]
    start=time.perf_counter();audio=MODELS[threads].generate(text,generation);x=np.asarray(audio.samples,dtype=np.float32)
    if not x.size or not np.isfinite(x).all() or not np.any(x):raise ValueError('Supertonic không trả âm thanh hợp lệ.')
    peak=float(np.max(np.abs(x)))
    if peak>.95:x*=.95/peak
    output=Path(request['output']);tmp=output.with_suffix('.multi.partial.wav')
    try:sf.write(tmp,x,audio.sample_rate,subtype='PCM_16');tmp.replace(output)
    finally:tmp.unlink(missing_ok=True)
    return {'engine':'Supertonic 3 CPU INT8 · 5 bước','voice':request['voice'],'model_load_seconds':load,'sample_rate':audio.sample_rate,'audio_seconds':len(x)/audio.sample_rate,'peak':float(np.max(np.abs(x))),'inference_and_save_seconds':time.perf_counter()-start}
