"""Required small runtime resources, separate from downloaded large AI models."""
from __future__ import annotations
import hashlib
from pathlib import Path

VAD_ASSET='silero_vad_v6.onnx'
VAD_BYTES=1245151
VAD_SHA256='4cbf549b8326f60f80f2536d9eefeb450a9abe83365a098031c89719f1be17d2'
VAD_ARCHIVE_PATH='AutoDocStudio/_internal/faster_whisper/assets/'+VAD_ASSET

def verify_vad_asset(folder):
    path=Path(folder)/VAD_ASSET
    if not path.is_file() or path.stat().st_size!=VAD_BYTES or hashlib.sha256(path.read_bytes()).hexdigest()!=VAD_SHA256:
        raise RuntimeError('Thiếu hoặc hỏng model lọc giọng '+VAD_ASSET+'. Giải nén lại toàn bộ bản Full mới, hoặc giải nén bản vá VAD vào thư mục chứa AutoDocStudio.exe rồi mở lại tool.')
    return path

def check_vad():
    import numpy as np
    from faster_whisper.utils import get_assets_path
    from faster_whisper.vad import get_vad_model
    path=verify_vad_asset(get_assets_path());model=get_vad_model()
    probabilities=model(np.zeros(16*512,dtype=np.float32))
    if not np.isfinite(probabilities).all() or len(probabilities)!=16:raise RuntimeError('Model VAD không chạy được. Hãy dùng bản Full mới.')
    return {'status':'ready','asset':VAD_ASSET,'asset_path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':VAD_SHA256,'onnx_inference_passed':True}

def prepare_distribution(app):
    """Prune only explicitly unused examples. Never remove runtime ONNX assets."""
    import shutil
    app=Path(app)
    for p in (app/'_internal/onnxruntime/datasets').rglob('*.onnx'):p.unlink()
    from faster_whisper.utils import get_assets_path
    source=verify_vad_asset(get_assets_path());folder=app/'_internal/faster_whisper/assets';folder.mkdir(parents=True,exist_ok=True)
    target=folder/VAD_ASSET
    if not target.exists():shutil.copyfile(source,target)
    verify_vad_asset(folder)
    return {'path':VAD_ARCHIVE_PATH,'bytes':VAD_BYTES,'sha256':VAD_SHA256,'role':'required speech activity detector bundled with faster-whisper 1.2.1'}

def validate_archive(archive):
    """Validate the delivered ZIP, after all packaging mutations."""
    import zipfile
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP bị hỏng CRC.')
        names=z.namelist()
        if VAD_ARCHIVE_PATH not in names:raise RuntimeError('Bản ZIP thiếu model VAD bắt buộc.')
        data=z.read(VAD_ARCHIVE_PATH)
        if len(data)!=VAD_BYTES or hashlib.sha256(data).hexdigest()!=VAD_SHA256:raise RuntimeError('Model VAD trong ZIP không đúng hash.')
        forbidden=[n for n in names if n.endswith(('.mp4','.mp3','.wav')) or (n.endswith('.onnx') and n!=VAD_ARCHIVE_PATH) or 'windows test/' in n or 'local test/' in n]
        if forbidden:raise RuntimeError('Có media/model ngoài danh mục cho phép trong ZIP: '+str(forbidden[:5]))
    return {'required_vad_present':True,'required_vad_sha256':VAD_SHA256,'zip_crc_passed':True}
