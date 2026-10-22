"""Read-only-data native check for a cross-assembled Windows CPU bundle."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def main():
    app = Path(__file__).resolve().parent
    data = app / '.data'
    os.environ['VOICE_STUDIO_DATA_DIR'] = str(data)
    os.environ['HF_HOME'] = str(data / 'models' / 'cache')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    sys.path.insert(0, str(app))
    import numpy as np
    import soundfile as sf
    from vieneu.v3nano import V3NanoVieNeuTTS
    from local_vieneu import LocalVieneu
    for binary in ('ffmpeg', 'ffprobe'):
        subprocess.run([binary, '-version'], check=True, stdout=subprocess.DEVNULL)
    temporary = data / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bundle-check-', dir=temporary) as folder:
        folder = Path(folder)
        for engine in ('Nano', 'Turbo'):
            print(f'Dang kiem tra {engine} offline...', flush=True)
            started = time.monotonic()
            model = V3NanoVieNeuTTS(steps=8, threads=2) if engine == 'Nano' else LocalVieneu(backend='onnx', device='cpu', precision='fp32', threads=2)
            path = folder / (engine + '.wav')
            samples = model.infer('Xin chào, đây là kiểm tra giọng nói trên máy của bạn.', voice='Minh Quân' if engine == 'Nano' else 'Mai Anh')
            model.save(samples, str(path))
            audio, rate = sf.read(str(path), dtype='float32')
            if audio.size < rate or not np.all(np.isfinite(audio)) or not np.any(np.abs(audio) > .001):
                raise RuntimeError(engine + ' khong tao duoc am thanh hop le.')
            if engine == 'Turbo':
                cloned = model.infer('Đây là kiểm tra nhân bản từ bản đọc tổng hợp.', ref_audio=str(path), denoise=False)
                if not len(cloned) or not np.all(np.isfinite(cloned)) or not np.any(np.abs(cloned) > .001):
                    raise RuntimeError('Nhan ban Turbo khong tao duoc am thanh hop le.')
            print(f'PASS {engine}: {len(audio)/rate:.1f} giay audio, {time.monotonic()-started:.1f} giay xu ly.', flush=True)
            del model
        print('Dang kiem tra Whisper offline...', flush=True)
        from faster_whisper import WhisperModel
        recognizer = WhisperModel(str(data / 'models' / 'whisper-base'), device='cpu', compute_type='int8', cpu_threads=2)
        segments, info = recognizer.transcribe(str(path), language='vi', beam_size=1, vad_filter=True)
        transcript = ' '.join(segment.text.strip() for segment in segments).strip()
        if not transcript:
            raise RuntimeError('Whisper khong nhan duoc loi tu ban doc thu.')
        print('PASS Whisper: ' + transcript, flush=True)
    print('PASS: Python, FFmpeg, Nano, Turbo, nhan ban va Whisper offline. Khong xoa du lieu ca nhan.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('LOI: ' + str(exc), flush=True)
        sys.exit(1)
