# Verified local cloning implementation

Version0.4 uses CosyVoice3 Hmong instruct2 with each supplied male/female audio reference, without a reference transcript. The user-provided poem is not used as reference text. No API key or paid runtime service is needed.

Model source: https://huggingface.co/Xuajpaj2026/hmong-tts-weights , pinned revision5663e0df2589c2ca2403cd327a52702c3ff96e8f. The bundled manifest selects118 files (~5.43GB), avoiding optional duplicate ONNX and training artifacts. Downloader validates LFS SHA256 or Git blob SHA1, supports Range resume and rejects traversal/symlink escapes. Model code hashes are checked again before loading. Tensor checkpoints use weights_only=True; primitive epoch/step training metadata is removed only in memory. Inference YAML is selected and its constructors allowlisted before construction; training objects are not evaluated. No source/checkpoint files are rewritten.

The runtime uses offline Hub settings and local files, float32 CPU with four Torch threads. Each request runs in a cancellable worker process. Supplied references are decoded to mono24kHz and limited to10 seconds for instruct2 conditioning. Original MP3s remain unchanged. Nine style choices become actual model instructions; speed is passed to synthesis. Style strength, voice similarity and correct native pronunciation still require listening checks.

Validation on Linux CPU:

- Female neutral, expected text “Nyob zoo, kuv hais lus Hmoob.”: PCM16 mono24kHz,2.71seconds,130124bytes. Cold execution64.68seconds, peak RSS7.84GiB.
- Male Review, same expected text: PCM16 mono24kHz,2.51seconds,120524bytes. Real browser/API job completed in93.617seconds.
- Real browser stopped a worker, then completed a new job. No microphone request was made while selecting supplied references or creating voice. Mobile390px had no overflow or JS errors.
- Both outputs decode and contain nonzero finite samples. No native pronunciation or similarity rating has been performed.
- 63 Python tests and8 Chromium microphone checks passed; dependencies pass pip check. Windows dependency resolution and wheel availability checked for CPython3.12x64; native Windows BAT/model inference unrun.

The cloud download restriction was resolved after network publication. Model bytes and sources are now verified under /workspace/models/hmong-cosy on the current cloud machine; set HMONG_COSY_DIR to that root there. Windows default is the extracted app's .data/models/hmong-cosy. Binary model weights are downloaded by install_clone_ai.bat, not included in the small source ZIP or Git repository.
