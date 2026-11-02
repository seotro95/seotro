"""A native Hmong RPA community VITS model. Dialect/gender remain unverified."""
import json,os,time
from pathlib import Path
from local_models import digest
MODEL=None
REPO='svue1986/hmong-tts-pilot-v1'
REVISION='d2c2c012afbf729c9542570516eb3eeaa11f42d3'
VOICE='hmong:pilot-rpa-v1'
def voices_for():return [{'id':VOICE,'name':'Hmong RPA · Pilot v1 · thử nghiệm, chưa xác minh Hmong Trắng','gender':'Unknown','backend':'hmong','locale':'hmn','download_required':True}]
def handle(request):
    global MODEL
    if request['language']!='HMN':raise ValueError('Bộ đọc Hmong chỉ nhận ngôn ngữ Hmong RPA.')
    if request['op']=='voices':return {'voices':voices_for(),'model_load_seconds':0,'warnings':['Một giọng Hmong cộng đồng; chưa có xác minh phương ngữ Hmong Trắng hoặc giới tính.']}
    text=request.get('text');threads=request.get('threads',4)
    if request['op']!='render' or request.get('voice')!=VOICE or not isinstance(text,str) or not text.strip() or len(text)>1200 or '\0' in text or type(threads) is not int or not 1<=threads<=16:raise ValueError('Kiểm tra giọng Hmong, văn bản RPA và số luồng CPU.')
    import torch,numpy as np,soundfile as sf
    from huggingface_hub import snapshot_download
    from transformers import VitsModel,AutoTokenizer
    torch.set_num_threads(threads);started=time.perf_counter();load=0
    if MODEL is None:
        record=json.loads(Path(__file__).with_name('hmong_catalog.json').read_text())
        try:folder=Path(snapshot_download(REPO,revision=REVISION,allow_patterns=list(record['files']),local_files_only=os.environ.get('HF_HUB_OFFLINE')=='1'))
        except Exception as e:raise RuntimeError('Chưa tải được mô hình Hmong RPA. Mở MO_TOOL.bat có Internet để tải một lần từ Hugging Face, rồi Nghe thử. Không dùng bộ Việt/Anh thay thế.') from e
        for name,sha in record['files'].items():
            if not (folder/name).is_file() or digest(folder/name)!=sha:raise ValueError('Tệp mô hình Hmong thiếu hoặc sai SHA256: '+name)
        tokenizer=AutoTokenizer.from_pretrained(folder,local_files_only=True,trust_remote_code=False)
        reader,info=VitsModel.from_pretrained(folder,local_files_only=True,use_safetensors=True,output_loading_info=True)
        if info['missing_keys'] or info['mismatched_keys'] or info['error_msgs'] or any(not k.startswith('discriminator.') for k in info['unexpected_keys']):raise ValueError('Trọng số Hmong không khớp bộ đọc. Không tạo âm thanh bằng trọng số ngẫu nhiên.')
        MODEL=(reader.eval().requires_grad_(False),tokenizer);load=time.perf_counter()-started
    reader,tokenizer=MODEL;inputs=tokenizer(text,return_tensors='pt')
    if (inputs['input_ids']==tokenizer.unk_token_id).any():raise ValueError('Có ký tự chưa được mô hình Hmong hỗ trợ. Dùng chữ RPA, kiểm tra nội dung trước khi tạo.')
    start=time.perf_counter()
    with torch.inference_mode():audio=reader(**inputs).waveform[0].numpy()
    if not audio.size or not np.isfinite(audio).all() or not np.any(audio):raise ValueError('Mô hình Hmong chưa tạo được WAV hợp lệ.')
    peak=float(np.max(np.abs(audio)))
    if peak>.95:audio*=.95/peak
    output=Path(request['output']);tmp=output.with_suffix('.hmong.partial.wav')
    try:sf.write(tmp,audio,reader.config.sampling_rate,subtype='PCM_16');tmp.replace(output)
    finally:tmp.unlink(missing_ok=True)
    return {'engine':'Hmong RPA Pilot VITS CPU FP32 · thử nghiệm','voice':VOICE,'model_load_seconds':load,'sample_rate':reader.config.sampling_rate,'audio_seconds':len(audio)/reader.config.sampling_rate,'peak':float(np.max(np.abs(audio))),'inference_and_save_seconds':time.perf_counter()-start}
