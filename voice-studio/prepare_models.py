"""Explicit online preparation. Normal generation runs with offline flags."""
import argparse
import os
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE / '.data'))).resolve()
os.environ['HF_HOME'] = str(DATA / 'models' / 'cache')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('OMP_NUM_THREADS', '4')


def validate_prepared_audio(path):
    """A downloaded model is usable only after it emits real, finite audio."""
    import numpy as np
    import soundfile as sf
    audio, rate = sf.read(str(path), dtype='float32')
    if rate <= 0 or audio.size == 0 or len(audio) / rate < 0.1 or not np.isfinite(audio).all() or np.max(np.abs(audio)) < 0.0001:
        raise RuntimeError('Model tạo âm thanh rỗng/hỏng trong bước kiểm tra. Chưa đánh dấu sẵn sàng; chạy lại cài đặt hoặc tải model.')
    return round(len(audio) / rate, 3)


def prepare_engine(engine):
    (DATA / 'models').mkdir(parents=True, exist_ok=True)
    marker = DATA / 'models' / (engine + '.ready')
    marker.unlink(missing_ok=True)
    checks = {}
    if engine in {'vieneu_nano', 'vieneu_nano_clone'}:
        from local_vieneu import LocalNano
        model = LocalNano(steps=8, threads=4)
        samples = model.infer('Xin chào, chào mừng bạn đến với phòng thu giọng nói.', voice='Minh Quân', steps=8, sway=-1)
        sample = DATA / 'models' / 'nano-check.wav'
        model.save(samples, str(sample))
        checks['preset_seconds'] = validate_prepared_audio(sample)
        # Presets and cloning have independent readiness: clone graphs are lazy downloads.
        if engine == 'vieneu_nano_clone':
            cloned = model.infer('Đây là lời đọc mới dùng giọng tham chiếu, không phải phát lại bản mẫu.', ref_audio=str(sample), denoise=False, steps=8, sway=-1)
            clone_sample = DATA / 'models' / 'nano-clone-check.wav'
            model.save(cloned, str(clone_sample))
            checks['clone_seconds'] = validate_prepared_audio(clone_sample)
        write_marker('vieneu_nano', checks)
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
        checks['preset_seconds'] = validate_prepared_audio(sample)
        cloned = model.infer('Đây là bước kiểm tra mô hình giọng nói trên máy.', ref_audio=str(sample), denoise=False)
        clone_sample = DATA / 'models' / 'vieneu-clone-check.wav'
        model.save(cloned, str(clone_sample))
        checks['clone_seconds'] = validate_prepared_audio(clone_sample)
    else:
        import torch
        from qwen_tts import Qwen3TTSModel
        suffix = 'Base' if engine == 'qwen_clone' else 'CustomVoice'
        model = Qwen3TTSModel.from_pretrained(f'Qwen/Qwen3-TTS-12Hz-0.6B-{suffix}', device_map='cpu', dtype=torch.float32, attn_implementation='sdpa')
        checks['model_loaded'] = True
    write_marker(engine, checks)
    del model
    print(f'{engine}: ready', flush=True)


def write_marker(engine, checks):
    from state_io import write_json_atomic
    write_json_atomic(DATA / 'models' / (engine + '.ready'), {'engine': engine, 'prepared_at': datetime.now(timezone.utc).isoformat(), 'vieneu_version': version('vieneu'), 'checks': checks})


def main():
    parser = argparse.ArgumentParser(description='Download and verify local Voice Studio models')
    parser.add_argument('engine', choices=['vi', 'vieneu', 'qwen', 'qwen_clone', 'vieneu_fast', 'vieneu_nano', 'vieneu_nano_clone', 'all'])
    args = parser.parse_args()
    # One verified fast engine is sufficient for first use. Turbo is an on-demand
    # alternative; downloading it must not delay a working Nano installation.
    engines = ['vieneu_nano_clone'] if args.engine in {'vi', 'all'} else [args.engine]
    if args.engine == 'all':
        engines.extend(['vieneu', 'qwen', 'qwen_clone'])
    for engine in engines:
        prepare_engine(engine)


if __name__ == '__main__':
    main()
