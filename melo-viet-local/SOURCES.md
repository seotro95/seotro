- MeloTTS official code: https://github.com/myshell-ai/MeloTTS
  Pinned source: 209145371cff8fc3bd60d7be902ea69cbdb7965a (latest main checked).
  Official release: v0.1.2; the source advertises CPU real-time inference,
  not a verified 30× rate for this user's hardware.
- VieNeu: https://pypi.org/project/vieneu/3.8.3/
  CPU ONNX FP32, pretrained Vietnamese presets, no voice cloning in this wrapper.
- PyTorch CPU: https://download.pytorch.org/whl/cpu
- Python dependencies and upstream models retain their own licenses.
  The small updater does not bundle weights. The full CPU edition includes
  the pinned public Piper weights/configs/model cards described below. Neither
  edition bundles private reference recordings, credentials or cloud credits.

This local wrapper and installer are version 1.2.0, separate from Voice Studio.

## International online voices

Optional `edge-tts` 7.3.1 (LGPL-3.0 licensed package; https://github.com/rany2/edge-tts). It accesses the Microsoft Edge Read Aloud service, not the official Azure Speech API. Voice availability is queried at runtime; no invented presets or promise of service availability. Using online voices sends the submitted text to Microsoft. The two local readers remain independent and do not send narration text to this service.

`online-lock.txt` pins the small third environment. FFmpeg is installed from the Ubuntu package repository and is used as an external program for MP3 decoding, sample-rate conversion and pitch-preserving tempo adjustment. Its build/license depends on the Ubuntu package.

1.2.0 adds persistent jobs, native TXT/SRT handling, bounded streaming WAV parts, pacing presets, cached chunks and optional online voices. It does not retrain Melo/VieNeu or claim a new emotion model or 30x fresh inference.

## Local CPU voices added in 1.2.0

Piper TTS 1.8.0: https://github.com/OHF-Voice/piper1-gpl (GPL-3.0). CPU ONNX Runtime 1.23.2, FP32; a separate interpreter, no Torch or CUDA. Piper source/releases and dependencies retain their licenses. This wrapper does not rename these voices as Melo or Turbo.

27 unmodified FP32 model exports/configs/model cards are distributed by https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models. `fast_catalog.json` pins each archive size and SHA256 as well as the SHA256 of every retained model/config/MODEL_CARD. Archive eSpeak copies are not kept per voice; the pinned Piper wheel supplies shared language resources.

The full installer includes the 27 selected model files/configs and their original MODEL_CARD files. Those cards state source, datasets and applicable model/dataset licenses, which vary; the wrapper license is not a grant of rights over every voice or dataset. No private reference recordings are included. The new voices change the model/speaker relative to Melo/VieNeu, and have not all been assessed by native human listeners.
