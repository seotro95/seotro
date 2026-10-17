"""Explicit online preparation. Normal generation runs with offline flags."""
import argparse
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE / '.data'))).resolve()
os.environ['HF_HOME'] = str(DATA / 'models' / 'cache')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('OMP_NUM_THREADS', '4')


def main():
    parser = argparse.ArgumentParser(description='Download local Voice Studio models')
    parser.add_argument('engine', choices=['piper', 'vieneu', 'qwen', 'qwen_clone', 'vieneu_fast', 'vieneu_nano', 'vieneu_nano_clone', 'all'])
    args = parser.parse_args()
    if args.engine == 'piper':
        from piper_voice import prepare_all
        prepare_all(DATA)
        return
    engines = ['vieneu', 'qwen', 'qwen_clone'] if args.engine == 'all' else [args.engine]
    (DATA / 'models').mkdir(parents=True, exist_ok=True)
    for engine in engines:
        marker = DATA / 'models' / (engine + '.ready')
        marker.unlink(missing_ok=True)
        if engine in {'vieneu_nano', 'vieneu_nano_clone'}:
            from vieneu.v3nano import V3NanoVieNeuTTS
            model = V3NanoVieNeuTTS(steps=8, threads=4)
            samples = model.infer('Xin chào, chào mừng bạn đến với phòng thu giọng nói.', voice='Minh Quân', steps=8, sway=-1)
            sample = DATA / 'models' / 'nano-check.wav'
            model.save(samples, str(sample))
            if engine == 'vieneu_nano_clone':
                from nano_voice import load_nano_reference
                encoded_voice = load_nano_reference(model, sample)
                cloned = model.infer('Mẫu giọng được mã hóa một lần để tái sử dụng khi đọc các đoạn mới.',
                                     voice=encoded_voice, steps=4, sway=-1)
                import numpy as np
                if len(cloned) == 0 or not np.any(cloned):
                    raise RuntimeError('Mô hình nhân bản Nano tạo âm thanh rỗng.')
                model.save(cloned, str(DATA / 'models' / 'nano-clone-check.wav'))
                (DATA / 'models' / 'vieneu_nano.ready').write_text('Prepared locally\n', encoding='utf-8')
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
            cloned = model.infer('Đây là bước kiểm tra mô hình giọng nói trên máy.', ref_audio=str(sample), denoise=False)
            model.save(cloned, str(DATA / 'models' / 'vieneu-clone-check.wav'))
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
