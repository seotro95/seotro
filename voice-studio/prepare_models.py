"""Explicit online preparation. Normal generation runs with offline flags."""
import argparse
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE / '.data'))).resolve()
os.environ['HF_HOME'] = str(DATA / 'models' / 'cache')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('OMP_NUM_THREADS', '4')


def validate_sample(path):
    import numpy as np
    import soundfile as sf
    samples, rate = sf.read(str(path), dtype='float32')
    if rate <= 0 or samples.size == 0 or not np.all(np.isfinite(samples)) or not np.any(samples):
        raise ValueError('Mô hình tạo âm thanh rỗng, im lặng hoặc hỏng; chưa đánh dấu sẵn sàng.')


def main():
    parser = argparse.ArgumentParser(description='Download local Voice Studio models')
    parser.add_argument('engine', choices=['vieneu', 'qwen', 'qwen_clone', 'vieneu_fast', 'vieneu_nano', 'all'])
    args = parser.parse_args()
    # Preparation is explicitly online, even when the launcher runs offline.
    os.environ.pop('HF_HUB_OFFLINE', None)
    os.environ.pop('TRANSFORMERS_OFFLINE', None)
    engines = ['vieneu', 'qwen', 'qwen_clone'] if args.engine == 'all' else [args.engine]
    (DATA / 'models').mkdir(parents=True, exist_ok=True)
    for engine in engines:
        marker = DATA / 'models' / (engine + '.ready')
        marker.unlink(missing_ok=True)
        if engine == 'vieneu_nano':
            from vieneu.v3nano import V3NanoVieNeuTTS
            model = V3NanoVieNeuTTS(steps=8, threads=4)
            samples = model.infer('Xin chào, chào mừng bạn đến với phòng thu giọng nói.', voice='Minh Quân', steps=8, sway=-1)
            sample = DATA / 'models' / 'nano-check.wav'
            model.save(samples, str(sample))
            validate_sample(sample)
        elif engine in {'vieneu', 'vieneu_fast'}:
            if engine == 'vieneu_fast':
                from hardware import supports_int8
                if not supports_int8():
                    raise RuntimeError('CPU chưa được xác nhận có VNNI. Dùng vieneu tiêu chuẩn để tránh âm thanh lỗi.')
            from local_vieneu import LocalVieneu
            model = LocalVieneu(backend='onnx', device='cpu', precision='int8' if engine == 'vieneu_fast' else 'fp32', threads=int(os.environ.get('OMP_NUM_THREADS', '4')))
            # Exercise preset inference AND cloning graph downloads before declaring ready.
            samples = model.infer('Xin chào, chào mừng bạn đến với phòng thu giọng nói.', voice='Mai Anh')
            sample = DATA / 'models' / 'vieneu-check.wav'
            model.save(samples, str(sample))
            validate_sample(sample)
            cloned = model.infer('Đây là bước kiểm tra mô hình giọng nói trên máy.', ref_audio=str(sample), denoise=False)
            clone_sample = DATA / 'models' / 'vieneu-clone-check.wav'
            model.save(cloned, str(clone_sample))
            validate_sample(clone_sample)
        else:
            import torch
            from qwen_tts import Qwen3TTSModel
            suffix = 'Base' if engine == 'qwen_clone' else 'CustomVoice'
            model = Qwen3TTSModel.from_pretrained(f'Qwen/Qwen3-TTS-12Hz-0.6B-{suffix}', device_map='cpu', dtype=torch.float32, attn_implementation='sdpa')
        marker.write_text('Prepared locally\n', encoding='utf-8')
        del model
        print(f'{engine}: ready', flush=True)


if __name__ == '__main__':
    main()
