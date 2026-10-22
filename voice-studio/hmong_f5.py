"""Local F5-Hmong inference without the upstream plotting or ASR API.

The model classes remain supplied by pinned f5-tts 1.1.22. This adapter follows
its F5TTS_Base checkpoint and single-batch inference contracts, but does not
import f5_tts.api or f5_tts.infer.utils_infer. Model imports still include the
upstream model package's training dependencies.
"""
from __future__ import annotations

from importlib import metadata
from importlib.resources import files
import os
from pathlib import Path
from types import SimpleNamespace


TARGET_SAMPLE_RATE = 24000
HOP_LENGTH = 256
TARGET_RMS = 0.1


def _progress(callback, message):
    if callback is not None:
        callback(message)


def _load_ema_checkpoint(model, checkpoint_path, device):
    import torch
    from safetensors.torch import load_file

    # Match F5-TTS's CUDA precision choice and compatibility conversion.
    dtype = (torch.float16 if "cuda" in device
             and torch.cuda.get_device_properties(device).major >= 7
             and not torch.cuda.get_device_name().endswith("[ZLUDA]") else torch.float32)
    model = model.to(dtype)
    checkpoint = load_file(str(checkpoint_path), device=device)
    state = {key.replace("ema_model.", ""): value for key, value in checkpoint.items()
             if key not in ("initted", "step")}
    for key in ("mel_spec.mel_stft.mel_scale.fb", "mel_spec.mel_stft.spectrogram.window"):
        state.pop(key, None)
    model.load_state_dict(state)
    del state, checkpoint
    torch.cuda.empty_cache()
    return model.to(device)


def load_local_model(root, device, progress=None, precision=None):
    """Load the verified local F5TTS_Base/Vocos files; never download weights."""
    if metadata.version("f5-tts") != "1.1.22":
        raise RuntimeError("Bộ tạo giọng cần đúng phiên bản f5-tts 1.1.22.")
    root = Path(root)
    _progress(progress, "Đang nạp lõi F5-Hmong…")
    import torch
    import yaml
    from f5_tts.model import CFM, DiT
    from f5_tts.model.utils import get_tokenizer

    config = yaml.safe_load(files("f5_tts").joinpath("configs/F5TTS_Base.yaml").read_text(encoding="utf-8"))["model"]
    if config["backbone"] != "DiT" or config["mel_spec"]["mel_spec_type"] != "vocos":
        raise RuntimeError("Cấu hình F5TTS_Base/Vocos không tương thích với bộ tạo giọng.")

    _progress(progress, "Đang nạp bộ giải mã Vocos…")
    from vocos import Vocos
    from vocos.feature_extractors import EncodecFeatures
    vocoder = Vocos.from_hparams(str(root / "vocos/config.yaml"))
    vocoder_state = torch.load(str(root / "vocos/pytorch_model.bin"), map_location="cpu", weights_only=True)
    if isinstance(vocoder.feature_extractor, EncodecFeatures):
        vocoder_state.update({"feature_extractor.encodec." + key: value
                              for key, value in vocoder.feature_extractor.encodec.state_dict().items()})
    vocoder.load_state_dict(vocoder_state)
    del vocoder_state
    vocoder = vocoder.eval().to(device)

    _progress(progress, "Đang nạp trọng số F5-Hmong…")
    vocabulary, vocabulary_size = get_tokenizer(str(root / "f5-hmong/vocab.txt"), "custom")
    def original_network():
        candidate = CFM(
            transformer=DiT(**config["arch"], text_num_embeds=vocabulary_size, mel_dim=100),
            mel_spec_kwargs=dict(config["mel_spec"]),
            odeint_kwargs={"method": "euler"},
            vocab_char_map=vocabulary,
        ).to(device)
        return _load_ema_checkpoint(candidate, root / "f5-hmong/model_159952.safetensors", device).eval()

    requested = precision or os.getenv('HMOOB_PRECISION', 'auto')
    if requested not in {'auto', 'fp32', 'int8'}:
        raise ValueError('HMOOB_PRECISION chỉ nhận auto, fp32 hoặc int8.')
    network = original_network()
    actual = 'fp16' if 'cuda' in device and next(network.parameters()).dtype == torch.float16 else 'fp32'
    if device == 'cpu' and requested != 'fp32':
        engines = torch.backends.quantized.supported_engines
        backend = next((name for name in ('x86', 'fbgemm', 'onednn') if name in engines), None)
        if backend is None and requested == 'int8':
            raise RuntimeError('Bản PyTorch này không hỗ trợ tăng tốc INT8 trên CPU.')
        if backend:
            _progress(progress, 'Đang tối ưu bộ tạo giọng cho máy…')
            try:
                torch.backends.quantized.engine = backend
                # In-place conversion bounds RAM rather than duplicating the
                # complete 1.3 GB model. Rebuild verified FP32 on auto failure.
                network = torch.ao.quantization.quantize_dynamic(
                    network, {torch.nn.Linear}, dtype=torch.qint8, inplace=True)
                actual = 'int8'
            except (RuntimeError, NotImplementedError):
                if requested == 'int8':
                    raise
                del network
                import gc
                gc.collect()
                _progress(progress, 'Đang nạp bộ tạo giọng tương thích…')
                network = original_network()
                actual = 'fp32'
    return SimpleNamespace(ema_model=network, vocoder=vocoder, mel_spec_type="vocos", precision=actual)


def infer_batch(reference, reference_text, text, model, *, steps, speed, device):
    """Render one bounded batch with upstream normalization and selected pace."""
    import torch
    from f5_tts.model.utils import convert_char_to_pinyin

    audio, rate = reference
    if audio.shape[0] > 1:
        audio = torch.mean(audio, dim=0, keepdim=True)
    rms = torch.sqrt(torch.mean(torch.square(audio)))
    if not torch.isfinite(rms) or float(rms) <= 1e-12:
        raise ValueError("Đoạn giọng mẫu chỉ có im lặng hoặc dữ liệu không hợp lệ.")
    if rms < TARGET_RMS:
        audio = audio * TARGET_RMS / rms
    if rate != TARGET_SAMPLE_RATE:
        import torchaudio
        audio = torchaudio.transforms.Resample(rate, TARGET_SAMPLE_RATE)(audio)
    audio = audio.to(device)

    # Upstream appends one ASCII space even when normalized text ends in one.
    if len(reference_text[-1].encode("utf-8")) == 1:
        reference_text += " "
    final_text = convert_char_to_pinyin([reference_text + text])
    reference_frames = audio.shape[-1] // HOP_LENGTH
    new_frames = max(1, int(reference_frames / len(reference_text.encode("utf-8"))
                            * len(text.encode("utf-8")) / speed))
    duration = reference_frames + new_frames
    with torch.inference_mode():
        generated, _ = model.ema_model.sample(
            cond=audio, text=final_text, duration=duration, steps=steps,
            cfg_strength=2.0, sway_sampling_coef=-1,
        )
        generated = generated.to(torch.float32)[:, reference_frames:, :].permute(0, 2, 1)
        waveform = model.vocoder.decode(generated)
        if rms < TARGET_RMS:
            waveform = waveform * rms / TARGET_RMS
        return waveform.squeeze().cpu().numpy(), TARGET_SAMPLE_RATE
