"""Explicit one-time online preparation of local multilingual ASR."""
import os
from pathlib import Path
os.environ.setdefault('HF_HOME',str(Path(__file__).resolve().parent/'.data/models/cache'))
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
from huggingface_hub import snapshot_download
if __name__ == '__main__':
    data = Path(os.environ.get('VOICE_STUDIO_DATA_DIR',str(Path(__file__).resolve().parent/'.data')))
    snapshot_download('Systran/faster-whisper-base',local_dir=data/'models'/'whisper-base')
    from faster_whisper import WhisperModel
    WhisperModel(str(data/'models'/'whisper-base'),device='cpu',compute_type='int8')
    print('Whisper base: ready')
