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

This local wrapper and installer are version 1.3.0, separate from Voice Studio.

## International online voices

Optional `edge-tts` 7.3.1 (LGPL-3.0 licensed package; https://github.com/rany2/edge-tts). It accesses the Microsoft Edge Read Aloud service, not the official Azure Speech API. Voice availability is queried at runtime; no invented presets or promise of service availability. Using online voices sends the submitted text to Microsoft. The two local readers remain independent and do not send narration text to this service.

`online-lock.txt` pins the small third environment. FFmpeg is installed from the Ubuntu package repository and is used as an external program for MP3 decoding, sample-rate conversion and pitch-preserving tempo adjustment. Its build/license depends on the Ubuntu package.

1.2.0 adds persistent jobs, native TXT/SRT handling, bounded streaming WAV parts, pacing presets, cached chunks and optional online voices. It does not retrain Melo/VieNeu or claim a new emotion model or 30x fresh inference.

## Local CPU voices added in 1.2.0

Piper TTS 1.8.0: https://github.com/OHF-Voice/piper1-gpl (GPL-3.0). CPU ONNX Runtime 1.23.2, FP32; a separate interpreter, no Torch or CUDA. Piper source/releases and dependencies retain their licenses. This wrapper does not rename these voices as Melo or Turbo.

27 unmodified FP32 model exports/configs/model cards are distributed by https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models. `fast_catalog.json` pins each archive size and SHA256 as well as the SHA256 of every retained model/config/MODEL_CARD. Archive eSpeak copies are not kept per voice; the pinned Piper wheel supplies shared language resources.

The full installer includes the 27 selected model files/configs and their original MODEL_CARD files. Those cards state source, datasets and applicable model/dataset licenses, which vary; the wrapper license is not a grant of rights over every voice or dataset. No private reference recordings are included. The new voices change the model/speaker relative to Melo/VieNeu, and have not all been assessed by native human listeners.

## 1.3.0 real speaker inventory and exports

The original 27 Piper models are retained; 22 additional public FP32 models provide 51 actual speaker presets across 49 models. `fast_catalog.json` pins every archive and retained file. The extra-voice update includes only the 22 additions; the small updater downloads requested models. Gender comes from identified source speakers/datasets or explicit preset metadata. Unknown labels are not inferred from pitch. French UPMC and Spanish Sharvard expose their real multi-speaker IDs.

Supertonic 3 (99M parameters): https://github.com/supertone-oss-archive/supertonic and https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models . CPU INT8 conversion pinned in `multi_catalog.json`; Sherpa-ONNX 2.0.1, five inference steps, 44.1 kHz. Ten source presets F1–F5/M1–M5 are shared across 31 languages, not 310 distinct people. The conversion/sample code license is MIT; model weights are OpenRAIL-M (see upstream model LICENSE, retained as LICENSE-MODEL in the additional-voice pack). Model source revision for license: Supertone/supertonic-3 aafc6e32416a594460b32413efc49d7fe4ce6d46. Models retain their own terms. This optional reader does not replace the existing FP32 readers.

MP3 uses the Ubuntu FFmpeg executable/libmp3lame, 192 kbps, 44.1 kHz mono, preserving WAV. Expressive pacing and explicit emphasis change pauses, pitch-preserving tempo and bounded gain; they do not claim semantic emotion synthesis or voice training. No private reference recordings, user data or credentials are redistributed.

## Hmong RPA experimental native reader

Public community TTS model `svue1986/hmong-tts-pilot-v1`, pinned revision d2c2c012afbf729c9542570516eb3eeaa11f42d3. Inference uses Transformers 4.46.3 VitsModel, PyTorch 2.2.2 CPU FP32, safetensors only, no remote/custom model code. `hmong_catalog.json` pins every downloaded file; all inference weights must load. It has one speaker with unverified gender. RPA sample generation is verified; White Hmong (Hmong Daw) dialect accuracy has not been assessed by a native listener, and the model card leaves language/dataset/license details incomplete. It is labeled experimental; no weight redistribution in this release. Weights download directly from the original pinned repository on first use and remain local. No private reference voices are bundled or cloned.
