- MeloTTS official code: https://github.com/myshell-ai/MeloTTS
  Pinned source: 209145371cff8fc3bd60d7be902ea69cbdb7965a (latest main checked).
  Official release: v0.1.2; the source advertises CPU real-time inference,
  not a verified 30× rate for this user's hardware.
- VieNeu: https://pypi.org/project/vieneu/3.8.3/
  CPU ONNX FP32, pretrained Vietnamese presets, no voice cloning in this wrapper.
- PyTorch CPU: https://download.pytorch.org/whl/cpu
- Python dependencies and upstream models retain their own licenses.
  The installer does not bundle model weights, private reference recordings,
  third-party binaries, credentials or cloud speech credits.

This local wrapper and installer are version 1.0.1, separate from Voice Studio.
