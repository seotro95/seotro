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

This local wrapper and installer are version 1.1.0, separate from Voice Studio.

## International online voices

Optional `edge-tts` 7.3.1 (LGPL-3.0 licensed package; https://github.com/rany2/edge-tts). It accesses the Microsoft Edge Read Aloud service, not the official Azure Speech API. Voice availability is queried at runtime; no invented presets or promise of service availability. Using online voices sends the submitted text to Microsoft. The two local readers remain independent and do not send narration text to this service.

`online-lock.txt` pins the small third environment. FFmpeg is installed from the Ubuntu package repository and is used as an external program for MP3 decoding, sample-rate conversion and pitch-preserving tempo adjustment. Its build/license depends on the Ubuntu package.

1.1.0 adds persistent jobs, native TXT/SRT handling, bounded streaming WAV parts, pacing presets, cached chunks and optional online voices. It does not retrain Melo/VieNeu or claim a new emotion model or 30x fresh inference.
