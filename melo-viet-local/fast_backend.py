"""Real local Piper FP32 voices. Only requested model files are downloaded."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

MODELS = OrderedDict()
VERIFIED = set()


def catalog():
    return json.loads(Path(__file__).with_name('fast_catalog.json').read_text(encoding='utf-8'))['models']


def labels():
    return {m['language']:m['label'] for m in catalog()}


def voices_for(language):
    voices=[]
    for model in catalog():
        if model['language']!=language:
            continue
        for speaker,sid in model['speaker_map'].items():
            label=model['id']+((' · '+speaker) if len(model['speaker_map'])>1 else '')
            voices.append({'id':f"piper:{model['id']}:{sid}",'name':'ONNX nhanh · '+label,'backend':'piper',
                           'sample_rate':model['sample_rate'],'quality':model['quality'],
                           'gender':model.get('speaker_genders',{}).get(str(sid),model.get('gender','Unknown')),
                           'locale':model['id'].split('-')[0].replace('_','-'),'download_required':not model.get('bundled',True)})
    return voices


def model_root():
    return Path(os.environ.get('MELO_VIET_ROOT',Path.home()/'.local/share/melo-viet-local'))/'models/piper'


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as source:
        while block:=source.read(1024*1024):
            digest.update(block)
    return digest.hexdigest()


def verify_folder(folder,record):
    return all((folder/name).is_file() and sha256(folder/name)==digest for name,digest in record['files'].items())


def ensure_model(record,offline=False):
    root=model_root();root.mkdir(parents=True,exist_ok=True);folder=root/record['id']
    if str(folder) in VERIFIED:
        return folder
    if verify_folder(folder,record):
        VERIFIED.add(str(folder));return folder
    if offline:
        raise ValueError('Chưa có đủ mô hình ngoại tuyến '+record['id']+'. Mở MO_TOOL.bat có Internet để tải, hoặc dùng bản ĐẦY ĐỦ chứa sẵn các mô hình.')
    # Do not extract arbitrary paths, links or extra engine assets from a tarball.
    # The upstream archive includes eSpeak data; the pinned Piper wheel supplies
    # this once, so only model/config/model-card are retained per voice.
    with tempfile.TemporaryDirectory(prefix='download-',dir=root) as scratch:
        scratch=Path(scratch);archive=scratch/'voice.tar.bz2';staged=scratch/'model';staged.mkdir()
        error=None
        for attempt in range(3):
            try:
                request=urllib.request.Request(record['archive_url'],headers={'User-Agent':'Melo-Viet-Studio/1.3.0'})
                with urllib.request.urlopen(request,timeout=90) as source,archive.open('wb') as output:
                    received=0
                    while block:=source.read(1024*1024):
                        received+=len(block)
                        if received>record['archive_bytes']:
                            raise ValueError('Tệp mô hình lớn hơn kích thước đã xác minh.')
                        output.write(block)
                if archive.stat().st_size!=record['archive_bytes'] or sha256(archive)!=record['archive_sha256']:
                    raise ValueError('Mã SHA256 mô hình không khớp. Không sử dụng tệp tải lỗi.')
                break
            except (OSError,ValueError) as caught:
                error=caught
                if attempt==2:
                    raise RuntimeError('Không tải được mô hình '+record['id']+'. Kiểm tra kết nối GitHub hoặc dùng bản đầy đủ.') from caught
                time.sleep(1.5*(attempt+1))
        names={record['id']+'.onnx':'model.onnx',record['id']+'.onnx.json':'config.json','MODEL_CARD':'MODEL_CARD'}
        with tarfile.open(archive,'r:bz2') as tar:
            for member in tar:
                parts=PurePosixPath(member.name).parts
                if len(parts)==2 and parts[0]=='vits-piper-'+record['id'] and parts[1] in names and member.isfile():
                    if member.size>250*1024*1024:
                        raise ValueError('Thành phần mô hình vượt kích thước cho phép.')
                    with tar.extractfile(member) as source,(staged/names[parts[1]]).open('wb') as output:
                        shutil.copyfileobj(source,output,1024*1024)
        if not verify_folder(staged,record):
            raise ValueError('Mô hình thiếu hoặc sai mã xác minh. Không tạo giọng bằng tệp lỗi.')
        folder.mkdir(exist_ok=True)
        for name in record['files']:
            temporary=folder/(name+'.'+str(os.getpid())+'.partial')
            shutil.copyfile(staged/name,temporary);temporary.replace(folder/name)
    VERIFIED.add(str(folder));return folder


def load_voice(record,threads,offline,lane=0,keep=2):
    import onnxruntime as ort
    from piper.voice import PiperVoice
    from piper.config import PiperConfig
    key=(record['id'],threads,lane);started=time.perf_counter();loaded=key not in MODELS
    if loaded:
        folder=ensure_model(record,offline)
        options=ort.SessionOptions();options.intra_op_num_threads=threads;options.inter_op_num_threads=1
        options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session=ort.InferenceSession(str(folder/'model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        # Arabic diacritization uses a small bundled ONNX model; keep its threads
        # bounded as well. This does not download another language or change text.
        import piper.tashkeel as tashkeel
        tashkeel.InferenceSession=lambda path:ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
        candidate=PiperVoice(session=session,config=PiperConfig.from_dict(json.loads((folder/'config.json').read_text(encoding='utf-8'))),download_dir=folder)
        if candidate.config.espeak_voice=='ar':
            candidate.tashkeel_diacritizier=tashkeel.TashkeelDiacritizer()
        MODELS[key]=candidate
        while len(MODELS)>max(2,keep):
            MODELS.popitem(last=False)
    MODELS.move_to_end(key)
    return MODELS[key],time.perf_counter()-started if loaded else 0


def generate(reader,text,output,voice):
    import numpy as np
    import soundfile as sf
    from piper.config import SynthesisConfig
    if not isinstance(text,str) or not text.strip() or len(text)>1200 or '\x00' in text:
        raise ValueError('Đoạn Piper cần 1–1.200 ký tự hợp lệ.')
    began=time.perf_counter();parts=[]
    for part in reader.synthesize(text,SynthesisConfig(speaker_id=int(voice.rsplit(':',1)[1]),length_scale=1.0,normalize_audio=False)):
        parts.append(part.audio_float_array)
    if not parts:
        raise ValueError('Mô hình không tạo được âm thanh; không thay giọng hoặc bỏ lời.')
    audio=np.concatenate(parts).astype(np.float32,copy=False)
    if not audio.size or not np.isfinite(audio).all() or not np.any(audio):
        raise ValueError('Âm thanh Piper rỗng/không hợp lệ.')
    peak=float(np.max(np.abs(audio)))
    if peak>.95:audio*=.95/peak
    output=Path(output);temporary=output.with_suffix('.piper.partial.wav')
    try:
        sf.write(temporary,audio,reader.config.sample_rate,subtype='PCM_16');temporary.replace(output)
    finally:temporary.unlink(missing_ok=True)
    return {'voice':voice,'engine':'Piper ONNX FP32 CPU','sample_rate':reader.config.sample_rate,
        'audio_seconds':len(audio)/reader.config.sample_rate,'inference_and_save_seconds':time.perf_counter()-began,
        'peak':float(np.max(np.abs(audio)))}


def handle(request):
    language=request['language'];voices=voices_for(language)
    if not voices:raise ValueError('Ngôn ngữ chưa có mô hình Piper trong bản này.')
    if request['op']=='voices':return {'voices':voices,'model_load_seconds':0,'download_on_render':True}
    voice=request.get('voice');op=request['op']
    if op not in {'render','render_many'} or voice not in {v['id'] for v in voices}:
        raise ValueError('Chọn đúng giọng Piper của ngôn ngữ đang đọc.')
    threads=request.get('threads',4)
    if type(threads) is not int or not 1<=threads<=16:raise ValueError('Chọn 1–16 luồng CPU.')
    record=next(m for m in catalog() if m['id']==voice.split(':')[1])
    if op=='render_many':
        entries=request.get('entries')
        if not isinstance(entries,list) or not 1<=len(entries)<=4:raise ValueError('Piper xử lý 1–4 đoạn trong một nhóm.')
    else:entries=[{'text':request.get('text'),'output':request['output']}]
    # Validate every entry before starting or writing output files.
    for entry in entries:
        text=entry.get('text')
        if not isinstance(text,str) or not text.strip() or len(text)>1200 or '\x00' in text:
            raise ValueError('Đoạn Piper cần 1–1.200 ký tự hợp lệ.')
    readers=[];load=0
    for lane in range(len(entries)):
        reader,elapsed=load_voice(record,threads,os.environ.get('HF_HUB_OFFLINE')=='1',lane=lane,keep=len(entries))
        readers.append(reader);load+=elapsed
    def task(index):return generate(readers[index],entries[index]['text'],entries[index]['output'],voice)
    if len(entries)>1:
        with ThreadPoolExecutor(max_workers=len(entries)) as pool:results=list(pool.map(task,range(len(entries))))
    else:results=[task(0)]
    if op=='render_many':return {'results':results,'model_load_seconds':load}
    return {**results[0],'model_load_seconds':load}
